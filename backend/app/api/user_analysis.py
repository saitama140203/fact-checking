"""
User Analysis API Router - Phân tích bài post do người dùng gửi vào.

Hỗ trợ 2 cách:
1. Gửi đường link Reddit post
2. Gửi trực tiếp title và content
"""
import re
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator

from app.services.fake_news_service import fake_news_detector
from app.services.enhanced_prediction_service import enhanced_prediction_service
from app.services.advanced_analysis_service import AdvancedAnalysisService
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/analyze", tags=["User Analysis"])


# ========================
# REQUEST MODELS
# ========================

class TextAnalysisRequest(BaseModel):
    """Request để phân tích text trực tiếp."""
    title: str = Field(..., min_length=10, max_length=500, description="Tiêu đề bài viết")
    content: Optional[str] = Field(None, max_length=5000, description="Nội dung bài viết (optional)")
    source_url: Optional[str] = Field(None, description="URL nguồn (optional)")
    
    @validator('title')
    def title_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Title không được để trống')
        return v.strip()


class UrlAnalysisRequest(BaseModel):
    """Request để phân tích từ Reddit URL."""
    url: str = Field(..., description="URL của Reddit post")
    
    @validator('url')
    def validate_reddit_url(cls, v):
        if not v:
            raise ValueError('URL không được để trống')
        
        # Check if it's a valid Reddit URL
        reddit_patterns = [
            r'https?://(?:www\.)?reddit\.com/r/\w+/comments/\w+',
            r'https?://(?:old\.)?reddit\.com/r/\w+/comments/\w+',
            r'https?://(?:www\.)?redd\.it/\w+'
        ]
        
        if not any(re.match(pattern, v) for pattern in reddit_patterns):
            raise ValueError('URL không hợp lệ. Vui lòng sử dụng URL Reddit.')
        
        return v


# ========================
# RESPONSE MODELS
# ========================

class AnalysisResult(BaseModel):
    """Kết quả phân tích."""
    prediction: dict = Field(..., description="Kết quả prediction")
    risk_indicators: list = Field(default=[], description="Các dấu hiệu rủi ro")
    recommendation: str = Field(..., description="Khuyến nghị")
    analyzed_at: str = Field(..., description="Thời gian phân tích")


# ========================
# HELPER FUNCTIONS
# ========================

def analyze_content_risks(title: str, content: Optional[str] = None) -> list:
    """Phân tích các dấu hiệu rủi ro trong nội dung."""
    risk_indicators = []
    
    text = title.lower()
    if content:
        text += " " + content.lower()
    
    # Clickbait patterns
    clickbait_words = [
        "shocking", "unbelievable", "you won't believe", "breaking",
        "urgent", "exclusive", "leaked", "secret", "hidden truth",
        "they don't want you to know", "must see", "incredible",
        "sốc", "không thể tin", "khẩn cấp", "bí mật", "tiết lộ"
    ]
    
    for word in clickbait_words:
        if word in text:
            risk_indicators.append({
                "type": "CLICKBAIT_LANGUAGE",
                "description": f"Phát hiện từ ngữ giật gân: '{word}'",
                "severity": "MEDIUM"
            })
            break
    
    # All caps check
    caps_ratio = sum(1 for c in title if c.isupper()) / max(len(title), 1)
    if caps_ratio > 0.5:
        risk_indicators.append({
            "type": "EXCESSIVE_CAPS",
            "description": f"Sử dụng quá nhiều chữ in hoa ({caps_ratio*100:.0f}%)",
            "severity": "LOW"
        })
    
    # Excessive punctuation
    exclamation_count = title.count('!') + title.count('?')
    if exclamation_count > 2:
        risk_indicators.append({
            "type": "EXCESSIVE_PUNCTUATION",
            "description": f"Quá nhiều dấu chấm than/hỏi ({exclamation_count} dấu)",
            "severity": "LOW"
        })
    
    # Check for sensational phrases
    sensational = [
        "must read", "share before deleted", "msm won't tell you",
        "wake up", "open your eyes", "the truth about"
    ]
    
    for phrase in sensational:
        if phrase in text:
            risk_indicators.append({
                "type": "SENSATIONAL_LANGUAGE",
                "description": f"Ngôn ngữ cảm tính: '{phrase}'",
                "severity": "MEDIUM"
            })
            break
    
    # Very short content with no source
    if content and len(content.strip()) < 1:
        risk_indicators.append({
            "type": "INSUFFICIENT_CONTENT",
            "description": "Nội dung quá ngắn, thiếu thông tin chi tiết",
            "severity": "LOW"
        })
    
    return risk_indicators


def get_recommendation(label: str, confidence: float, risk_count: int) -> str:
    """Tạo khuyến nghị dựa trên kết quả phân tích."""
    
    if label == "FAKE":
        if confidence > 0.85:
            return "⚠️ CẢNH BÁO: Bài viết có khả năng cao là TIN GIẢ. Không nên chia sẻ. Cần kiểm chứng từ nhiều nguồn uy tín."
        elif confidence > 0.7:
            return "⚠️ CHÚ Ý: Bài viết có dấu hiệu đáng nghi là tin giả. Nên kiểm tra kỹ trước khi tin."
        else:
            return "🔶 Bài viết có một số đặc điểm của tin giả. Khuyến nghị đối chiếu với các nguồn khác."
    else:
        if risk_count > 2:
            return "✅ Bài viết được phân loại là TIN THẬT, nhưng có một số dấu hiệu cần chú ý. Nên xác minh thêm."
        elif risk_count > 0:
            return "✅ Bài viết có vẻ đáng tin cậy. Vẫn nên đối chiếu với các nguồn khác để chắc chắn."
        else:
            return "✅ Bài viết có vẻ đáng tin cậy. Không phát hiện dấu hiệu đáng nghi."


# ========================
# ENDPOINTS
# ========================

@router.post("/text", response_model=AnalysisResult)
async def analyze_text(request: TextAnalysisRequest):
    """
    **Phân tích bài viết từ text do người dùng nhập.**
    
    Người dùng gửi title và content (optional) để phân tích.
    
    **Parameters:**
    - title: Tiêu đề bài viết (bắt buộc, 10-500 ký tự)
    - content: Nội dung bài viết (không bắt buộc, tối đa 5000 ký tự)
    - source_url: URL nguồn (không bắt buộc)
    
    **Returns:**
    - prediction: Kết quả dự đoán (FAKE/REAL) với confidence
    - risk_indicators: Danh sách các dấu hiệu rủi ro phát hiện được
    - recommendation: Khuyến nghị cho người dùng
    """
    try:
        logger.info(f"📝 Analyzing user-submitted text: {request.title[:50]}...")
        
        # Prepare text for analysis
        if request.content:
            full_text = f"{request.title}. {request.content}"
        else:
            full_text = request.title
        
        # Run enhanced prediction (HF + Gemini)
        enhanced_result = await enhanced_prediction_service.analyze_news(full_text)
        
        if not enhanced_result:
            raise HTTPException(
                status_code=500,
                detail="Không thể phân tích bài viết. Vui lòng thử lại sau."
            )
        
        # Extract prediction from enhanced result
        hf_prediction = enhanced_result.get("hf", {})
        gemini_classifier = enhanced_result.get("gemini_classifier", {})
        analysis = enhanced_result.get("analysis", "")
        
        # Use HF prediction as primary (for backward compatibility)
        prediction_label = hf_prediction.get("label", "UNKNOWN")
        prediction_confidence = hf_prediction.get("confidence", 0.0)
        
        # Analyze risks
        risk_indicators = analyze_content_risks(request.title, request.content)
        
        # Add source check if URL provided
        if request.source_url:
            # Extract domain from URL
            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', request.source_url)
            if domain_match:
                domain = domain_match.group(1)
                # Check if domain is known for fake news (could be enhanced with actual database lookup)
                suspicious_domains = ['fake', 'hoax', 'satirical']
                if any(s in domain.lower() for s in suspicious_domains):
                    risk_indicators.append({
                        "type": "SUSPICIOUS_DOMAIN",
                        "description": f"Domain '{domain}' có tên đáng nghi",
                        "severity": "HIGH"
                    })
        
        # Generate recommendation (use analysis from Gemini if available)
        if analysis:
            recommendation = analysis  # Use Gemini analysis as recommendation
        else:
            recommendation = get_recommendation(
                prediction_label,
                prediction_confidence,
                len(risk_indicators)
            )
        
        logger.info(f"✅ Analysis complete: {prediction_label} ({prediction_confidence:.2%})")
        
        # Build response dict (AnalysisResult model doesn't support enhanced field, so return dict)
        result_dict = {
            "prediction": {
                "label": prediction_label,
                "confidence": prediction_confidence,
                "confidence_percentage": round(prediction_confidence * 100, 2),
                "model": hf_prediction.get("model", "Pulk17/Fake-News-Detection"),
                "is_fake": prediction_label == "FAKE"
            },
            "risk_indicators": risk_indicators,
            "recommendation": recommendation,
            "analyzed_at": enhanced_result.get("analyzed_at", datetime.now().isoformat()),
            # Enhanced prediction results
            "enhanced": {
                "workflow_version": enhanced_result.get("workflow_version", "2.0"),
                "hf": hf_prediction,
                "gemini_classifier": gemini_classifier,
                "analysis": analysis
            }
        }
        
        return result_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing text: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/url")
async def analyze_reddit_url(request: UrlAnalysisRequest):
    """
    **Phân tích bài viết từ Reddit URL.**
    
    Người dùng gửi URL của Reddit post, hệ thống sẽ crawl và phân tích.
    
    **Parameters:**
    - url: URL của Reddit post (bắt buộc)
    
    **Supported URL formats:**
    - https://www.reddit.com/r/subreddit/comments/abc123/title
    - https://old.reddit.com/r/subreddit/comments/abc123/title
    - https://redd.it/abc123
    
    **Returns:**
    - post_info: Thông tin bài post (title, author, subreddit, etc.)
    - prediction: Kết quả dự đoán (FAKE/REAL)
    - risk_indicators: Danh sách các dấu hiệu rủi ro
    - recommendation: Khuyến nghị
    """
    try:
        logger.info(f"🔗 Analyzing Reddit URL: {request.url}")
        
        # Extract post ID from URL
        post_id = None
        
        # Pattern 1: Full Reddit URL
        match = re.search(r'/comments/([a-zA-Z0-9]+)', request.url)
        if match:
            post_id = match.group(1)
        
        # Pattern 2: Short URL (redd.it)
        if not post_id:
            match = re.search(r'redd\.it/([a-zA-Z0-9]+)', request.url)
            if match:
                post_id = match.group(1)
        
        if not post_id:
            raise HTTPException(
                status_code=400,
                detail="Không thể trích xuất ID bài viết từ URL. Vui lòng kiểm tra lại."
            )
        
        # Import crawler
        from app.services.crawler import RedditCrawler
        
        crawler = RedditCrawler()
        
        try:
            # Get the Reddit instance
            await crawler._ensure_reddit_client()
            
            # Fetch the submission
            submission = await crawler.reddit.submission(id=post_id)
            await submission.load()
            
            # Extract post info
            post_info = {
                "post_id": submission.id,
                "title": submission.title,
                "selftext": getattr(submission, 'selftext', '')[:500] if hasattr(submission, 'selftext') else '',
                "author": str(submission.author) if submission.author else "[deleted]",
                "subreddit": str(submission.subreddit),
                "score": submission.score,
                "upvote_ratio": submission.upvote_ratio,
                "num_comments": submission.num_comments,
                "url": submission.url,
                "domain": submission.domain,
                "created_utc": datetime.fromtimestamp(submission.created_utc).isoformat(),
                "permalink": f"https://www.reddit.com{submission.permalink}"
            }
            
        except Exception as e:
            logger.error(f"Error fetching Reddit post: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Không thể lấy thông tin bài viết. Lỗi: {str(e)}"
            )
        finally:
            await crawler.close()
        
        # Prepare text for analysis
        if post_info["selftext"]:
            full_text = f"{post_info['title']}. {post_info['selftext']}"
        else:
            full_text = post_info['title']
        
        # Run enhanced prediction (HF + Gemini)
        enhanced_result = await enhanced_prediction_service.analyze_news(full_text)
        
        if not enhanced_result:
            raise HTTPException(
                status_code=500,
                detail="Không thể phân tích bài viết. Vui lòng thử lại sau."
            )
        
        # Extract prediction from enhanced result
        hf_prediction = enhanced_result.get("hf", {})
        gemini_classifier = enhanced_result.get("gemini_classifier", {})
        analysis = enhanced_result.get("analysis", "")
        
        # Use HF prediction as primary (for backward compatibility)
        prediction_label = hf_prediction.get("label", "UNKNOWN")
        prediction_confidence = hf_prediction.get("confidence", 0.0)
        
        # Analyze risks
        risk_indicators = analyze_content_risks(
            post_info['title'], 
            post_info['selftext']
        )
        
        # Check domain credibility
        domain = post_info.get("domain", "")
        if domain and domain != f"self.{post_info['subreddit']}":
            try:
                domain_cred = await AdvancedAnalysisService.get_source_credibility_score(domain)
                if domain_cred.get("credibility_score") and domain_cred["credibility_score"] < 50:
                    risk_indicators.append({
                        "type": "LOW_CREDIBILITY_SOURCE",
                        "description": f"Nguồn '{domain}' có điểm tin cậy thấp ({domain_cred['credibility_score']}/100)",
                        "severity": "HIGH"
                    })
            except:
                pass  # Domain check failed, ignore
        
        # Check account age (if author is not deleted)
        if post_info["author"] != "[deleted]":
            try:
                author = await crawler.reddit.redditor(post_info["author"])
                await author.load()
                account_age_days = (datetime.now() - datetime.fromtimestamp(author.created_utc)).days
                
                if account_age_days < 30:
                    risk_indicators.append({
                        "type": "NEW_ACCOUNT",
                        "description": f"Tài khoản mới ({account_age_days} ngày tuổi)",
                        "severity": "MEDIUM"
                    })
            except:
                pass
        
        # Generate recommendation (use analysis from Gemini if available)
        if analysis:
            recommendation = analysis  # Use Gemini analysis as recommendation
        else:
            recommendation = get_recommendation(
                prediction_label,
                prediction_confidence,
                len(risk_indicators)
            )
        
        logger.info(f"✅ URL analysis complete: {prediction_label} ({prediction_confidence:.2%})")
        
        return {
            "post_info": post_info,
            "prediction": {
                "label": prediction_label,
                "confidence": prediction_confidence,
                "confidence_percentage": round(prediction_confidence * 100, 2),
                "model": hf_prediction.get("model", "Pulk17/Fake-News-Detection"),
                "is_fake": prediction_label == "FAKE"
            },
            "risk_indicators": risk_indicators,
            "recommendation": recommendation,
            "analyzed_at": enhanced_result.get("analyzed_at", datetime.now().isoformat()),
            # Enhanced prediction results
            "enhanced": {
                "workflow_version": enhanced_result.get("workflow_version", "2.0"),
                "hf": hf_prediction,
                "gemini_classifier": gemini_classifier,
                "analysis": analysis
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick")
async def quick_analyze(
    title: str,
    content: Optional[str] = None
):
    """
    **Phân tích nhanh - Endpoint đơn giản.**
    
    Endpoint đơn giản cho phân tích nhanh, chỉ cần title.
    
    **Parameters:**
    - title: Tiêu đề bài viết (query param)
    - content: Nội dung (query param, optional)
    
    **Returns:**
    - is_fake: Boolean
    - label: FAKE hoặc REAL
    - confidence: Độ tin cậy (0-1)
    - warning: Cảnh báo nếu là tin giả
    """
    try:
        if not title or len(title.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Title phải có ít nhất 10 ký tự"
            )
        
        # Prepare text
        full_text = title
        if content:
            full_text = f"{title}. {content}"
        
        # Run prediction
        prediction = await fake_news_detector.predict_text(full_text)
        
        if not prediction:
            raise HTTPException(
                status_code=500,
                detail="Không thể phân tích. Vui lòng thử lại."
            )
        
        is_fake = prediction["label"] == "FAKE"
        
        return {
            "is_fake": is_fake,
            "label": prediction["label"],
            "confidence": prediction["confidence"],
            "confidence_percentage": round(prediction["confidence"] * 100, 2),
            "warning": "⚠️ Bài viết này có khả năng là TIN GIẢ!" if is_fake else None,
            "analyzed_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in quick analyze: {e}")
        raise HTTPException(status_code=500, detail=str(e))

