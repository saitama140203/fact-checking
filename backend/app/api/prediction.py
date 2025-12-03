"""
Prediction API Router - Endpoints cho fake news prediction.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

from app.services.fake_news_service import fake_news_detector
from app.services.enhanced_prediction_service import enhanced_prediction_service
from app.services.database_service import PredictionService, RedditPostService
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/prediction", tags=["Prediction"])

# Global variable để track batch prediction progress
batch_prediction_status = {
    "is_running": False,
    "total": 0,
    "completed": 0,
    "successful": 0,
    "failed": 0,
    "started_at": None,
    "completed_at": None,
    "error": None
}


@router.post("/single/{post_id}")
async def predict_single_post(post_id: str, enhanced: bool = True):
    """
    Predict fake news cho một post cụ thể với enhanced workflow.
    
    Args:
        post_id: ID của post cần predict
        enhanced: Sử dụng enhanced workflow (HF + Gemini) hay chỉ HF (mặc định: True)
        
    Returns:
        Prediction result với workflow đầy đủ hoặc cơ bản
    """
    try:
        # Get post from database
        post = await RedditPostService.get_post_by_id(post_id)
        
        if not post:
            raise HTTPException(status_code=404, detail=f"Post {post_id} not found")
        
        # Check if already predicted
        if post.get("prediction"):
            logger.info(f"Post {post_id} already has prediction")
            return {
                "post_id": post_id,
                "status": "already_predicted",
                "prediction": post["prediction"],
                "title": post.get("title", "")
            }
        
        # Run prediction với enhanced workflow hoặc legacy
        if enhanced:
            logger.info(f"🔍 Running enhanced prediction for post {post_id}")
            result = await enhanced_prediction_service.analyze_post(post)
            
            if not result:
                raise HTTPException(
                    status_code=500, 
                    detail="Enhanced prediction failed. Please try again later."
                )
            
            # Format để lưu vào DB
            prediction = enhanced_prediction_service.format_for_database(result)
            
            # Update database
            success = await PredictionService.update_post_prediction(post_id, prediction)
            
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to save prediction to database"
                )
            
            logger.info(f"✅ Enhanced prediction completed for post {post_id}")
            
            return {
                "post_id": post_id,
                "status": "success",
                "prediction": prediction,
                "full_result": result,  # Kết quả đầy đủ với analysis
                "title": post.get("title", "")
            }
        else:
            # Legacy workflow (chỉ HuggingFace)
            logger.info(f"🔍 Running legacy prediction for post {post_id}")
            prediction = await fake_news_detector.predict_post(post)
            
            if not prediction:
                raise HTTPException(
                    status_code=500, 
                    detail="Prediction failed. Please try again later."
                )
            
            # Update database
            success = await PredictionService.update_post_prediction(post_id, prediction)
            
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to save prediction to database"
                )
            
            logger.info(f"✅ Legacy prediction completed for post {post_id}")
            
            return {
                "post_id": post_id,
                "status": "success",
                "prediction": prediction,
                "title": post.get("title", "")
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error predicting post {post_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _run_batch_prediction_task(limit: Optional[int] = None, enhanced: bool = True):
    """
    Background task để chạy batch prediction.
    
    Args:
        limit: Giới hạn số posts cần predict (None = all)
        enhanced: Sử dụng enhanced workflow (HF + Gemini) hay chỉ HF
    """
    global batch_prediction_status
    
    try:
        # Reset status
        batch_prediction_status["is_running"] = True
        batch_prediction_status["completed"] = 0
        batch_prediction_status["successful"] = 0
        batch_prediction_status["failed"] = 0
        batch_prediction_status["started_at"] = datetime.now().isoformat()
        batch_prediction_status["completed_at"] = None
        batch_prediction_status["error"] = None

        # Nếu cấu hình không cho phép dùng Gemini trong background,
        # thì dù client yêu cầu enhanced cũng sẽ fallback sang HF-only.
        use_enhanced = enhanced and settings.enable_gemini_in_background
        workflow_type = "enhanced" if use_enhanced else "legacy"
        if enhanced and not settings.enable_gemini_in_background:
            logger.info(
                "⚠️  Enhanced workflow requested for batch prediction nhưng "
                "enable_gemini_in_background=False → fallback sang HF-only để tránh hết quota Gemini."
            )

        logger.info(f"🚀 Starting batch prediction ({workflow_type} workflow)...")
        
        # Get posts without prediction
        posts = await PredictionService.get_posts_without_prediction(
            limit=limit or 10000
        )
        
        total = len(posts)
        batch_prediction_status["total"] = total
        
        if total == 0:
            logger.info("✅ No posts to predict")
            batch_prediction_status["is_running"] = False
            batch_prediction_status["completed_at"] = datetime.now().isoformat()
            return
        
        logger.info(f"📊 Found {total} posts without prediction")
        
        # Process posts
        results = []
        
        for i, post in enumerate(posts, 1):
            post_id = post.get("post_id")
            
            try:
                if use_enhanced:
                    # Enhanced workflow với HF + Gemini (chỉ khi được bật trong config)
                    result = await enhanced_prediction_service.analyze_post(post)
                    if result:
                        prediction = enhanced_prediction_service.format_for_database(result)
                    else:
                        prediction = None
                else:
                    # Legacy workflow (chỉ HuggingFace)
                    prediction = await fake_news_detector.predict_post(post)
                
                if prediction:
                    # Lưu vào database
                    await PredictionService.update_post_prediction(post_id, prediction)
                    batch_prediction_status["successful"] += 1
                    results.append((post_id, prediction))
                else:
                    batch_prediction_status["failed"] += 1
                    results.append((post_id, None))
                
                # Update progress
                batch_prediction_status["completed"] = i
                
                if i % 10 == 0 or i == total:
                    progress_pct = (i / total) * 100
                    logger.info(
                        f"Progress: {i}/{total} ({progress_pct:.1f}%) - "
                        f"✅ {batch_prediction_status['successful']} successful, "
                        f"❌ {batch_prediction_status['failed']} failed"
                    )
                
                # Small delay để tránh overload (đặc biệt với Gemini)
                # Free tier Gemini: 15 requests/minute → cần delay ít nhất 4s giữa các requests
                if enhanced:
                    await asyncio.sleep(5.0)  # Delay 5s cho enhanced workflow (tránh quota exceeded)
                else:
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"❌ Lỗi khi xử lý post {post_id}: {e}")
                batch_prediction_status["failed"] += 1
                results.append((post_id, None))
                continue
        
        # Mark as completed
        batch_prediction_status["is_running"] = False
        batch_prediction_status["completed_at"] = datetime.now().isoformat()
        
        logger.info(
            f"✅ Batch prediction completed ({workflow_type}): "
            f"{batch_prediction_status['successful']} successful, "
            f"{batch_prediction_status['failed']} failed"
        )
        
    except Exception as e:
        logger.error(f"❌ Batch prediction failed: {e}", exc_info=True)
        batch_prediction_status["is_running"] = False
        batch_prediction_status["error"] = str(e)
        batch_prediction_status["completed_at"] = datetime.now().isoformat()


@router.post("/batch")
async def start_batch_prediction(
    background_tasks: BackgroundTasks,
    limit: Optional[int] = None,
    enhanced: bool = True
):
    """
    Bắt đầu batch prediction cho tất cả posts chưa có prediction.
    
    Args:
        limit: Giới hạn số posts (mặc định: all)
        enhanced: Sử dụng enhanced workflow (HF + Gemini) hay chỉ HF (mặc định: True)
        
    Returns:
        Status message
    """
    global batch_prediction_status
    
    # Check if already running
    if batch_prediction_status["is_running"]:
        return {
            "status": "already_running",
            "message": "Batch prediction is already in progress",
            "progress": batch_prediction_status
        }
    
    # Count posts without prediction
    posts_to_predict = await PredictionService.get_posts_without_prediction(limit=1)
    
    if not posts_to_predict:
        return {
            "status": "nothing_to_do",
            "message": "All posts already have predictions"
        }
    
    # Start background task
    background_tasks.add_task(_run_batch_prediction_task, limit, enhanced)

    effective_enhanced = enhanced and settings.enable_gemini_in_background
    workflow_type = "enhanced" if effective_enhanced else "legacy"
    logger.info(
        f"🚀 Batch prediction job started ({workflow_type} workflow, limit: {limit or 'all'})"
    )
    
    return {
        "status": "started",
        "message": f"Batch prediction job has been started in background ({workflow_type} workflow)",
        "limit": limit,
        "enhanced": effective_enhanced,
        "workflow": workflow_type,
        "gemini_background_enabled": settings.enable_gemini_in_background,
        "note": "Use GET /prediction/status to check progress"
    }


@router.get("/status")
async def get_batch_prediction_status():
    """
    Lấy status của batch prediction job.
    
    Returns:
        Current status and progress
    """
    global batch_prediction_status
    
    # Calculate progress percentage
    progress_percentage = 0
    if batch_prediction_status["total"] > 0:
        progress_percentage = round(
            (batch_prediction_status["completed"] / batch_prediction_status["total"]) * 100,
            2
        )
    
    return {
        **batch_prediction_status,
        "progress_percentage": progress_percentage
    }


@router.get("/stats")
async def get_prediction_stats():
    """
    Thống kê tổng quan về predictions.
    
    Returns:
        Prediction statistics
    """
    try:
        # Count posts with/without prediction
        total_posts = await RedditPostService.get_total_posts()
        posts_with_prediction = await PredictionService.count_posts_by_prediction()
        posts_without_prediction = total_posts - posts_with_prediction
        
        # Count fake vs real
        fake_count = await PredictionService.count_posts_by_prediction(label="FAKE")
        real_count = await PredictionService.count_posts_by_prediction(label="REAL")
        
        return {
            "total_posts": total_posts,
            "posts_with_prediction": posts_with_prediction,
            "posts_without_prediction": posts_without_prediction,
            "fake_news_count": fake_count,
            "real_news_count": real_count,
            "prediction_coverage": round(
                (posts_with_prediction / total_posts * 100) if total_posts > 0 else 0,
                2
            )
        }
        
    except Exception as e:
        logger.error(f"Error getting prediction stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/posts/fake")
async def get_fake_news_posts(
    limit: int = 20,
    skip: int = 0,
    min_confidence: float = 0.5
):
    """
    Lấy danh sách fake news posts.
    
    Args:
        limit: Số lượng posts
        skip: Bỏ qua
        min_confidence: Confidence tối thiểu
        
    Returns:
        List of fake news posts
    """
    try:
        posts = await PredictionService.get_posts_with_prediction(
            label="FAKE",
            min_confidence=min_confidence,
            limit=limit,
            skip=skip
        )
        
        return {
            "count": len(posts),
            "limit": limit,
            "skip": skip,
            "min_confidence": min_confidence,
            "posts": posts
        }
        
    except Exception as e:
        logger.error(f"Error getting fake news posts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/posts/real")
async def get_real_news_posts(
    limit: int = 20,
    skip: int = 0,
    min_confidence: float = 0.5
):
    """
    Lấy danh sách real news posts.
    
    Args:
        limit: Số lượng posts
        skip: Bỏ qua
        min_confidence: Confidence tối thiểu
        
    Returns:
        List of real news posts
    """
    try:
        posts = await PredictionService.get_posts_with_prediction(
            label="REAL",
            min_confidence=min_confidence,
            limit=limit,
            skip=skip
        )
        
        return {
            "count": len(posts),
            "limit": limit,
            "skip": skip,
            "min_confidence": min_confidence,
            "posts": posts
        }
        
    except Exception as e:
        logger.error(f"Error getting real news posts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

