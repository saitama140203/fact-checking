"""
Fake News Detection Service sử dụng Hugging Face model.
Model: Pulk17/Fake-News-Detection
Hỗ trợ cả local model (transformers) và Inference API.
"""
import httpx
import asyncio
from typing import Dict, Optional, List, Tuple
from datetime import datetime

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# Import cho local model (optional - chỉ load khi cần)
_local_model_imported = False
try:
    import torch
    import torch.nn.functional as F
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    _local_model_imported = True
except ImportError:
    logger.warning(
        "⚠️  PyTorch/Transformers chưa được cài đặt. "
        "Local model sẽ không hoạt động. Cài đặt: pip install torch transformers"
    )


class FakeNewsDetectionService:
    """
    Service để phát hiện fake news sử dụng Hugging Face model.
    Hỗ trợ cả local model (transformers) và Inference API.
    """
    
    # Hugging Face Inference API base endpoint (model sẽ được gắn động theo config)
    API_BASE_URL = "https://router.huggingface.co/models"
    
    # Rate limiting settings (cho API mode)
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    TIMEOUT = 30  # seconds
    
    # Batch settings
    BATCH_SIZE = 10  # Số posts xử lý cùng lúc để tránh rate limit (API mode)
    BATCH_DELAY = 1  # Delay giữa các batches (seconds) - chỉ cho API mode
    
    # Labels mapping
    HF_LABELS = ["fake", "real"]  # Theo thứ tự của model
    
    def __init__(self):
        """Initialize service với cấu hình từ settings."""
        self.api_key = settings.huggingface_api_key
        self.model_name = settings.huggingface_model
        self.use_local_model = settings.use_local_hf_model
        self.device = settings.hf_model_device if _local_model_imported else "cpu"
        # Cho phép override base URL qua env nếu dùng endpoint enterprise/custom
        base_url = settings.huggingface_api_base_url or self.API_BASE_URL
        # Ghép URL đầy đủ tới model, tránh trùng dấu '/'
        self.api_url = f"{base_url.rstrip('/')}/{self.model_name}"
        
        # Headers cho API requests (chỉ dùng khi không dùng local model)
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Local model components (khởi tạo lazy)
        self.tokenizer = None
        self.local_model = None
        self._model_loaded = False
        
        # Load local model nếu cần
        if self.use_local_model:
            self._load_local_model()
        else:
            logger.info(f"🔧 Sử dụng HuggingFace Inference API mode")
    
    def _load_local_model(self):
        """Load local HuggingFace model và tokenizer."""
        if not _local_model_imported:
            logger.error(
                "❌ Không thể load local model: PyTorch/Transformers chưa được cài đặt. "
                "Falling back to API mode."
            )
            self.use_local_model = False
            return
        
        if self._model_loaded:
            return
        
        try:
            logger.info(f"📦 Đang tải local model: {self.model_name}...")
            
            # Kiểm tra device
            if self.device == "cuda" and not torch.cuda.is_available():
                logger.warning("⚠️  CUDA không khả dụng, chuyển sang CPU")
                self.device = "cpu"
            
            device_str = self.device if self.device == "cpu" else f"cuda:{torch.cuda.current_device()}" if torch.cuda.is_available() else "cpu"
            logger.info(f"🔧 Sử dụng device: {device_str}")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # Load model
            self.local_model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name
            ).to(self.device)
            self.local_model.eval()
            
            self._model_loaded = True
            logger.info(f"✅ Local model đã được tải thành công trên {device_str}")
            
        except Exception as e:
            logger.error(f"❌ Không thể tải local model: {e}")
            logger.warning("⚠️  Falling back to API mode")
            self.use_local_model = False
            self._model_loaded = False
    
    async def _make_api_call(
        self, 
        text: str, 
        retry_count: int = 0
    ) -> Optional[Dict]:
        """
        Gọi Hugging Face Inference API.
        
        Args:
            text: Nội dung cần phân tích
            retry_count: Số lần retry hiện tại
            
        Returns:
            Dict với kết quả prediction hoặc None nếu thất bại
        """
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                payload = {"inputs": text}
                
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                )
                
                # Handle rate limiting (503)
                if response.status_code == 503:
                    error_data = response.json()
                    
                    # Model đang loading
                    if "estimated_time" in error_data:
                        wait_time = error_data.get("estimated_time", 20)
                        logger.warning(
                            f"⏳ Model đang loading, chờ {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                        
                        # Retry
                        if retry_count < self.MAX_RETRIES:
                            return await self._make_api_call(text, retry_count + 1)
                    
                    logger.error(f"❌ Service unavailable: {error_data}")
                    return None
                
                # Handle other errors
                if response.status_code != 200:
                    if response.status_code in (404, 410):
                        logger.error(
                            "❌ HuggingFace API responded %s for model '%s'. "
                            "Double-check that the model name is correct and that the token has access. "
                            "URL: %s | response: %s",
                            response.status_code,
                            self.model_name,
                            self.api_url,
                            response.text[:200],
                        )
                    else:
                        logger.error(
                            "❌ HuggingFace API error %s for model '%s' via URL '%s': %s",
                            response.status_code,
                            self.model_name,
                            self.api_url,
                            response.text[:200],
                        )
                    return None
                
                # Parse response
                result = response.json()
                return result
                
        except httpx.TimeoutException:
            logger.error(f"⏱️  API timeout after {self.TIMEOUT}s")
            
            # Retry
            if retry_count < self.MAX_RETRIES:
                await asyncio.sleep(self.RETRY_DELAY)
                return await self._make_api_call(text, retry_count + 1)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ API call failed: {e}")
            return None
    
    def _predict_with_local_model(self, text: str) -> Optional[Dict]:
        """
        Dự đoán bằng local HuggingFace model.
        
        Args:
            text: Nội dung cần phân tích
            
        Returns:
            Dict với prediction result
        """
        if not self._model_loaded or not self.local_model:
            logger.error("❌ Local model chưa được load")
            return None
        
        try:
            # Tokenize input
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True,
            ).to(self.device)
            
            # Predict
            with torch.no_grad():
                outputs = self.local_model(**inputs)
                probs = F.softmax(outputs.logits, dim=-1)[0]
            
            # Tạo scores dict
            scores = {
                self.HF_LABELS[i]: probs[i].item() 
                for i in range(len(self.HF_LABELS))
            }
            
            # Tìm label có score cao nhất
            label = max(scores, key=scores.get)
            
            return {
                "label": label.upper(),  # "FAKE" hoặc "REAL"
                "confidence": round(scores[label], 4),
                "scores": {k: round(v, 4) for k, v in scores.items()},
                "predicted_at": datetime.now().isoformat(),
                "model": self.model_name,
                "method": "local"
            }
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi predict với local model: {e}")
            return None
    
    def _parse_prediction(self, api_result: List[List[Dict]]) -> Optional[Dict]:
        """
        Parse kết quả từ Hugging Face API.
        
        Expected format:
        [[
            {"label": "LABEL_0", "score": 0.95},
            {"label": "LABEL_1", "score": 0.05}
        ]]
        
        LABEL_0 = REAL, LABEL_1 = FAKE
        
        Returns:
            Dict với label, confidence, và scores
        """
        try:
            # API trả về list of list
            if not api_result or not isinstance(api_result, list):
                logger.error("Invalid API result format")
                return None
            
            predictions = api_result[0]  # Lấy prediction đầu tiên
            
            # Map label từ API format
            label_map = {
                "LABEL_0": "REAL",
                "LABEL_1": "FAKE"
            }
            
            # Tạo scores dict
            scores = {}
            for pred in predictions:
                label_key = label_map.get(pred["label"], pred["label"])
                scores[label_key.lower()] = pred["score"]
            
            # Tìm prediction với score cao nhất
            best_pred = max(predictions, key=lambda x: x["score"])
            label = label_map.get(best_pred["label"], "UNKNOWN")
            confidence = best_pred["score"]
            
            return {
                "label": label,
                "confidence": round(confidence, 4),
                "scores": {k: round(v, 4) for k, v in scores.items()},
                "predicted_at": datetime.now().isoformat(),
                "model": self.model_name,
                "method": "api"
            }
            
        except Exception as e:
            logger.error(f"Failed to parse prediction: {e}")
            return None
    
    async def predict_text(self, text: str) -> Optional[Dict]:
        """
        Predict fake news cho một đoạn text.
        Sử dụng local model nếu được cấu hình, ngược lại dùng API.
        
        Args:
            text: Tiêu đề hoặc nội dung bài báo
            
        Returns:
            Dict với prediction result hoặc None nếu thất bại
            Format: {
                "label": "FAKE" | "REAL",
                "confidence": float,
                "scores": {"fake": float, "real": float},
                "predicted_at": str,
                "model": str,
                "method": "local" | "api"
            }
        """
        if not text or len(text.strip()) < 10:
            logger.warning("⚠️  Text quá ngắn để phân tích")
            return None
        
        # Giới hạn độ dài text
        max_length = 512
        if len(text) > max_length:
            logger.debug(f"Text dài {len(text)} ký tự, cắt xuống {max_length}")
            text = text[:max_length]
        
        # Sử dụng local model nếu có
        if self.use_local_model and self._model_loaded:
            logger.debug("🔧 Sử dụng local model để predict")
            return self._predict_with_local_model(text)
        
        # Fallback to API
        logger.debug("🌐 Sử dụng HuggingFace API để predict")
        api_result = await self._make_api_call(text)
        
        if not api_result:
            return None
        
        # Parse kết quả
        prediction = self._parse_prediction(api_result)
        
        return prediction
    
    async def predict_post(self, post: Dict) -> Optional[Dict]:
        """
        Predict fake news cho một Reddit post.
        
        Args:
            post: Dict chứa thông tin post (title, selftext, ...)
            
        Returns:
            Dict với prediction result
        """
        # Tạo text để phân tích (title + selftext)
        title = post.get("title", "")
        selftext = post.get("selftext", "")
        
        # Ưu tiên title, thêm selftext nếu có
        if selftext and len(selftext) > 20:
            text = f"{title}. {selftext}"
        else:
            text = title
        
        logger.info(f"🔍 Predicting post: {post.get('post_id')}")
        
        prediction = await self.predict_text(text)
        
        if prediction:
            logger.info(
                f"✅ Prediction: {prediction['label']} "
                f"(confidence: {prediction['confidence']:.2%})"
            )
        
        return prediction
    
    async def batch_predict_posts(
        self, 
        posts: List[Dict],
        progress_callback: Optional[callable] = None
    ) -> List[Tuple[str, Optional[Dict]]]:
        """
        Batch predict nhiều posts với rate limiting.
        
        Args:
            posts: List các Reddit posts
            progress_callback: Function để báo cáo progress (optional)
            
        Returns:
            List of tuples (post_id, prediction_result)
        """
        results = []
        total = len(posts)
        
        logger.info(f"🚀 Starting batch prediction for {total} posts...")
        
        # Chia thành các batches nhỏ
        for i in range(0, total, self.BATCH_SIZE):
            batch = posts[i:i + self.BATCH_SIZE]
            batch_num = (i // self.BATCH_SIZE) + 1
            total_batches = (total + self.BATCH_SIZE - 1) // self.BATCH_SIZE
            
            logger.info(
                f"📦 Processing batch {batch_num}/{total_batches} "
                f"({len(batch)} posts)"
            )
            
            # Process batch
            batch_results = []
            for post in batch:
                post_id = post.get("post_id")
                prediction = await self.predict_post(post)
                batch_results.append((post_id, prediction))
                
                # Small delay giữa các posts trong batch
                await asyncio.sleep(0.1)
            
            results.extend(batch_results)
            
            # Progress callback
            if progress_callback:
                progress = {
                    "completed": i + len(batch),
                    "total": total,
                    "percentage": ((i + len(batch)) / total) * 100
                }
                progress_callback(progress)
            
            # Delay giữa các batches để tránh rate limit
            if i + self.BATCH_SIZE < total:
                logger.info(f"⏸️  Waiting {self.BATCH_DELAY}s before next batch...")
                await asyncio.sleep(self.BATCH_DELAY)
        
        # Thống kê
        successful = sum(1 for _, pred in results if pred is not None)
        failed = total - successful
        
        logger.info(
            f"✅ Batch prediction completed: "
            f"{successful} successful, {failed} failed"
        )
        
        return results


# Global instance
fake_news_detector = FakeNewsDetectionService()

