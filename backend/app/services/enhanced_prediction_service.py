"""
Enhanced Prediction Service - combines HuggingFace model + DeepSeek classifier + DeepSeek explainer.
"""
from typing import Dict, Optional
from datetime import datetime

from app.services.fake_news_service import fake_news_detector
from app.services.deepseek_service import deepseek_service
from app.core.logger import get_logger

logger = get_logger(__name__)


class EnhancedPredictionService:
    """
    Composite service to analyse fake news with the full workflow:
    1. HuggingFace model (local or API)
    2. DeepSeek classifier
    3. DeepSeek explainer (analysis and warnings)
    """
    
    def __init__(self):
        """Khởi tạo service."""
        self.hf_service = fake_news_detector
        self.generation_service = deepseek_service
    
    def _prepare_text_from_post(self, post: Dict) -> str:
        """
        Chuẩn bị text từ post để phân tích.
        
        Args:
            post: Dict chứa thông tin post (title, selftext, ...)
            
        Returns:
            Text đã được chuẩn bị
        """
        title = post.get("title", "")
        selftext = post.get("selftext", "")
        
        # Ưu tiên title, thêm selftext nếu có
        if selftext and len(selftext) > 20:
            text = f"{title}. {selftext}"
        else:
            text = title
        
        # Giới hạn độ dài
        max_length = 512
        if len(text) > max_length:
            logger.debug(f"Text dài {len(text)} ký tự, cắt xuống {max_length}")
            text = text[:max_length]
        
        return text
    
    async def analyze_news(self, text: str) -> Dict:
        """
        Run the full enhanced workflow on raw news text.

        Returns a dict:
            {
                "hf": {...},                    # HuggingFace result
                "gemini_classifier": {...},     # DeepSeek classifier result (key kept for backwards-compat)
                "analysis": str,                # Explanation and warning text
                "analyzed_at": str,             # Timestamp
                "workflow_version": str
            }
        """
        logger.info("🔍 Starting enhanced analysis workflow...")
        
        # Step 1: HuggingFace prediction
        logger.debug("Step 1/3: Running HuggingFace model...")
        hf_result = await self.hf_service.predict_text(text)
        
        if not hf_result:
            logger.warning("⚠️  HuggingFace prediction failed, returning default result")
            hf_result = {
                "label": "UNKNOWN",
                "confidence": 0.0,
                "scores": {"fake": 0.0, "real": 0.0},
                "predicted_at": datetime.now().isoformat(),
                "model": self.hf_service.model_name,
                "error": "Prediction failed"
            }
        
        # Step 2: Classify with DeepSeek
        logger.debug("Step 2/3: Running DeepSeek classifier...")
        logger.debug(f"📝 Text sent to DeepSeek (length: {len(text)}): {text[:200]}...")
        
        gemini_quota_exceeded = False
        try:
            gemini_classifier_result = self.generation_service.classify_fake_news(text)
            logger.debug(f"✅ DeepSeek classifier result: {gemini_classifier_result}")
            
            # Check for quota-like errors encoded in result
            if (gemini_classifier_result.get("label") == "uncertain" and 
                gemini_classifier_result.get("confidence", 0.0) == 0.0 and
                "quota" in gemini_classifier_result.get("reason", "").lower()):
                gemini_quota_exceeded = True
                logger.warning("⚠️  Detected DeepSeek quota exceeded from classifier result")
                
        except Exception as e:
            logger.error(f"❌ Error when calling DeepSeek classifier: {e}", exc_info=True)
            # Check if this looks like a quota error
            error_str = str(e).lower()
            if "429" in str(e) or "quota" in error_str:
                gemini_quota_exceeded = True
                logger.warning("⚠️  DeepSeek quota exceeded - skipping explanation step")
            
            # Default classifier result on error
            gemini_classifier_result = {
                "label": "uncertain",
                "confidence": 0.0,
                "reason": f"Error calling DeepSeek: {str(e)[:100]}",
                "model": self.generation_service.model_name,
                "classified_at": datetime.now().isoformat()
            }
        
        # Step 3: Explanation and warnings (skip if quota exceeded)
        if gemini_quota_exceeded:
            logger.warning("⏭️  Skipping DeepSeek explanation due to quota exceeded")
            analysis = (
                "⚠️ **Note:** DeepSeek API appears to have hit a quota or rate limit.\n\n"
                "**HuggingFace model result:**\n"
                f"- Label: **{hf_result.get('label', 'UNKNOWN')}**\n"
                f"- Confidence: **{hf_result.get('confidence', 0.0):.1%}**\n\n"
                "*This result is based only on the HuggingFace model. For a full DeepSeek explanation, "
                "please retry later or increase your plan limits.*"
            )
        else:
            logger.debug("Step 3/3: Generating explanation and warnings with DeepSeek...")
            analysis = self.generation_service.explain_and_warn(
                text,
                hf_result,
                gemini_classifier_result
            )
        
        result = {
            "hf": hf_result,
            "gemini_classifier": gemini_classifier_result,
            "analysis": analysis,
            "analyzed_at": datetime.now().isoformat(),
            "workflow_version": "2.0"  # Enhanced workflow using DeepSeek
        }
        
        logger.info("✅ Enhanced analysis workflow completed")
        
        return result
    
    async def analyze_post(self, post: Dict) -> Optional[Dict]:
        """
        Phân tích một Reddit post với workflow đầy đủ.
        
        Args:
            post: Dict chứa thông tin post (title, selftext, post_id, ...)
            
        Returns:
            Dict với kết quả phân tích đầy đủ hoặc None nếu thất bại
        """
        post_id = post.get("post_id", "unknown")
        logger.info(f"🔍 Phân tích post: {post_id}")
        
        try:
            # Chuẩn bị text
            text = self._prepare_text_from_post(post)
            
            if not text or len(text.strip()) < 10:
                logger.warning(f"⚠️  Post {post_id} có text quá ngắn để phân tích")
                return None
            
            # Phân tích với workflow đầy đủ
            result = await self.analyze_news(text)
            
            # Thêm metadata
            result["post_id"] = post_id
            result["title"] = post.get("title", "")
            
            logger.info(
                f"✅ Phân tích hoàn tất cho post {post_id}: "
                f"HF={result['hf'].get('label')}, "
                f"Gemini={result['gemini_classifier'].get('label')}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi phân tích post {post_id}: {e}")
            return None
    
    def _get_summary_label(self, result: Dict) -> str:
        """
        Tạo label tổng hợp từ cả 2 model.
        
        Args:
            result: Kết quả từ analyze_news()
            
        Returns:
            Label tổng hợp: "FAKE", "REAL", hoặc "UNCERTAIN"
        """
        hf_label = result.get("hf", {}).get("label", "UNKNOWN").upper()
        gemini_label = result.get("gemini_classifier", {}).get("label", "unknown").upper()
        
        # Nếu cả 2 đều đồng thuận
        if hf_label == gemini_label and hf_label in ["FAKE", "REAL"]:
            return hf_label
        
        # Nếu mâu thuẫn
        if hf_label in ["FAKE", "REAL"] and gemini_label in ["FAKE", "REAL"]:
            if hf_label != gemini_label:
                return "UNCERTAIN"
        
        # Nếu một trong hai là uncertain
        if "UNCERTAIN" in [hf_label, gemini_label]:
            other = hf_label if gemini_label == "UNCERTAIN" else gemini_label
            if other in ["FAKE", "REAL"]:
                return other
        
        return "UNCERTAIN"
    
    def format_for_database(self, result: Dict) -> Dict:
        """
        Format kết quả để lưu vào database.
        
        Args:
            result: Kết quả từ analyze_news() hoặc analyze_post()
            
        Returns:
            Dict được format để lưu vào DB
        """
        summary_label = self._get_summary_label(result)
        
        return {
            "label": summary_label,
            "confidence": result.get("hf", {}).get("confidence", 0.0),
            "hf": result.get("hf"),
            "gemini_classifier": result.get("gemini_classifier"),
            "analysis": result.get("analysis"),
            "analyzed_at": result.get("analyzed_at"),
            "workflow_version": result.get("workflow_version", "2.0")
        }


# Global instance
enhanced_prediction_service = EnhancedPredictionService()

