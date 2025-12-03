"""
DeepSeek Service - Use DeepSeek chat-completions API for classification and explanations.

This replaces the previous Gemini-based implementation but keeps the same public interface:
- classify_fake_news(text) -> JSON-style dict (label, confidence, reason, model, classified_at)
- explain_and_warn(text, hf_result, llm_classifier_result) -> markdown/HTML-ready string

The implementation uses the OpenAI-compatible HTTP API:
POST https://api.deepseek.com/v1/chat/completions
"""
import json
import re
import time
from datetime import datetime
from typing import Any, Deque, Dict, Optional
from collections import deque

import httpx

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class DeepSeekService:
    """Service wrapper around DeepSeek chat-completions API."""

    def __init__(self) -> None:
        self.api_key: Optional[str] = getattr(settings, "DEEPSEEK_API_KEY", None)
        
        # Allow overriding model via settings; default to general-purpose chat model
        self.model_name: str = getattr(settings, "deepseek_model", "deepseek-chat")
        self.base_url = "https://api.deepseek.com/v1/chat/completions"

        # Simple sliding-window rate limiter (requests per minute).
        self.rate_limit_window: int = 60
        self.rate_limit_max_requests: int = 60
        self.request_timestamps: Deque[float] = deque()

        # --- DEBUG LOGGING: KIỂM TRA KEY ĐƯỢC LOAD ---
        if self.api_key:
            masked_key = f"{self.api_key[:6]}...{self.api_key[-4:]}" if len(self.api_key) > 10 else "***"
            logger.info(f"✅ DeepSeek Service initialized with key: {masked_key}")
        else:
            logger.warning(
                "⚠️  DEEPSEEK_API_KEY is missing in settings! "
                "DeepSeek service will be disabled (is_available=False)."
            )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def is_available(self) -> bool:
        return bool(self.api_key)

    def _wait_for_rate_limit(self) -> None:
        """Basic client-side rate limiter using sliding window."""
        now = time.time()

        # Remove old timestamps
        while self.request_timestamps and (now - self.request_timestamps[0]) > self.rate_limit_window:
            self.request_timestamps.popleft()

        if len(self.request_timestamps) >= self.rate_limit_max_requests:
            oldest = self.request_timestamps[0]
            wait_time = max(0.0, (oldest + self.rate_limit_window) - now) + 0.5
            if wait_time > 0:
                logger.info(
                    "⏳ DeepSeek client-side rate limit reached (%s req/%ss). Sleeping for %.1fs...",
                    self.rate_limit_max_requests,
                    self.rate_limit_window,
                    wait_time,
                )
                time.sleep(wait_time)

        self.request_timestamps.append(time.time())

    def _clean_json_response(self, raw_text: str) -> str:
        """Remove markdown fences etc. and return bare JSON string."""
        text = raw_text.strip()
        if text.startswith("```"):
            # Remove fences like ```json ... ```
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE | re.MULTILINE)
            text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
        return text.strip()

    # ------------------------------------------------------------------ #
    # DeepSeek API wrappers
    # ------------------------------------------------------------------ #
    def _call_chat_api(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 3,
        temperature: float = 0.3,
    ) -> Optional[str]:
        """Low-level helper to call DeepSeek chat-completions and return message content."""
        if not self.is_available():
            logger.error("DeepSeek API called but service is unavailable (Missing Key).")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }

        last_error: Optional[Exception] = None

        for attempt in range(max_retries):
            try:
                self._wait_for_rate_limit()
                # Sử dụng timeout 60s để tránh treo nếu mạng lag
                with httpx.Client(timeout=60.0) as client:
                    resp = client.post(self.base_url, headers=headers, json=payload)

                if resp.status_code == 429:
                    logger.warning(
                        "⚠️  DeepSeek rate limited (429) on attempt %s/%s",
                        attempt + 1, max_retries
                    )
                    time.sleep(2 ** attempt + 1)
                    continue

                if resp.status_code >= 500:
                    logger.warning(
                        "⚠️  DeepSeek server error %s on attempt %s/%s",
                        resp.status_code, attempt + 1, max_retries
                    )
                    time.sleep(2 ** attempt + 1)
                    continue

                # Nếu lỗi 401 Unauthorized -> Dừng ngay, không retry (vì retry cũng sai key thôi)
                if resp.status_code == 401:
                    logger.error("❌ DeepSeek API Key Invalid (401 Unauthorized). Check your .env file!")
                    return None

                resp.raise_for_status()
                data = resp.json()
                
                choices = data.get("choices") or []
                if not choices:
                    logger.error("DeepSeek response has no choices: %s", data)
                    return None

                message = choices[0].get("message") or {}
                content = message.get("content")
                
                if not isinstance(content, str):
                    logger.error("DeepSeek response message has no content")
                    return None

                return content.strip()

            except Exception as exc:
                last_error = exc
                logger.error(
                    "❌ DeepSeek call failed (attempt %s/%s): %s",
                    attempt + 1, max_retries, exc
                )
                time.sleep(2 ** attempt + 1)

        if last_error:
            logger.error("❌ DeepSeek chat API finally failed after retries.")
        return None

    # ------------------------------------------------------------------ #
    # Public interface
    # ------------------------------------------------------------------ #
    def classify_fake_news(self, text: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Classify news as fake/real/uncertain using DeepSeek.
        """
        if not self.is_available():
            # Trả về kết quả mặc định thay vì lỗi crash app
            return {
                "label": "uncertain",
                "confidence": 0.0,
                "reason": "DeepSeek API Key is missing",
                "model": self.model_name,
                "classified_at": datetime.now().isoformat(),
            }

        system_prompt = (
            "You are a fake-news classifier for English news articles. "
            "You must respond ONLY with valid JSON as specified by the user."
        )

        user_prompt = f"""
Your task: Classify the following news headline/content as "fake" or "real" based on:
- Language patterns (sensationalist, clickbait, emotional manipulation)
- Claim credibility (extreme claims without evidence, conspiracy theories)
- Writing style (professional vs. unprofessional)

News:
---
{text}
---

Return ONLY a JSON object with this exact structure:
{{
  "label": "<fake|real|uncertain>",
  "confidence": <a number between 0 and 1>,
  "reason": "<short explanation in English>"
}}
No extra commentary, no markdown.
"""
        raw_content = self._call_chat_api(system_prompt, user_prompt, max_retries=max_retries)

        if raw_content is None:
            return {
                "label": "uncertain",
                "confidence": 0.0,
                "reason": "DeepSeek API call failed",
                "model": self.model_name,
                "classified_at": datetime.now().isoformat(),
            }

        try:
            cleaned = self._clean_json_response(raw_content)
            data = json.loads(cleaned)
        except Exception as exc:
            logger.error("Failed to parse DeepSeek JSON: %s | raw=%s", exc, raw_content[:200])
            return {
                "label": "uncertain",
                "confidence": 0.0,
                "reason": "JSON Parse Error",
                "model": self.model_name,
                "classified_at": datetime.now().isoformat(),
            }

        label = str(data.get("label", "uncertain")).lower()
        if label not in {"fake", "real", "uncertain"}:
            label = "uncertain"

        try:
            confidence = float(data.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0

        confidence = max(0.0, min(1.0, confidence))

        result = {
            "label": label,
            "confidence": round(confidence, 4),
            "reason": str(data.get("reason", "")),
            "model": self.model_name,
            "classified_at": datetime.now().isoformat(),
        }

        logger.info(
            "✅ DeepSeek classified: %s (conf: %.2f%%)",
            result["label"],
            result["confidence"] * 100,
        )
        return result

    def explain_and_warn(
        self,
        text: str,
        hf_result: Dict[str, Any],
        llm_classifier_result: Dict[str, Any],
    ) -> str:
        """
        Generate an explanation and warning based on HF + DeepSeek classifier results.
        """
        if not self.is_available():
            return self._get_default_explanation(hf_result, llm_classifier_result)

        hf_label = hf_result.get("label", "unknown")
        hf_confidence = hf_result.get("confidence", 0.0)

        llm_label = llm_classifier_result.get("label", "unknown")
        llm_confidence = llm_classifier_result.get("confidence", 0.0)
        llm_reason = llm_classifier_result.get("reason", "")

        system_prompt = (
            "You are a careful misinformation analyst. "
            "You will explain risks and recommendations clearly in English using bullet points."
        )

        user_prompt = f"""
Analyze this news article:

--- NEWS TEXT ---
{text}
------------------

Model Results:
1. HuggingFace: {hf_label} ({hf_confidence:.4f})
2. DeepSeek: {llm_label} ({llm_confidence:.4f}) - Reason: {llm_reason}

Tasks:
1. State agreement/disagreement between models.
2. Explain suspicious/trustworthy elements.
3. Assess Risk Level (LOW/MEDIUM/HIGH).
4. Provide recommendations.

Format: English, Markdown (bullet points), No JSON.
"""

        content = self._call_chat_api(system_prompt, user_prompt, max_retries=3, temperature=0.5)
        if content is None:
            return self._get_default_explanation(hf_result, llm_classifier_result)

        logger.info("✅ DeepSeek explanation generated.")
        return content.strip()

    def _get_default_explanation(
        self,
        hf_result: Dict[str, Any],
        llm_classifier_result: Dict[str, Any],
    ) -> str:
        """Fallback explanation when DeepSeek is not available."""
        hf_label = hf_result.get("label", "unknown")
        hf_confidence = hf_result.get("confidence", 0.0)
        
        return (
            "## Automatic Analysis (Fallback)\n\n"
            f"- **HuggingFace model**: {hf_label} ({hf_confidence:.2%})\n"
            "- **DeepSeek**: Not Available\n\n"
            "**Recommendation:** Verify with reputable sources."
        )


# Global singleton instance
deepseek_service = DeepSeekService()