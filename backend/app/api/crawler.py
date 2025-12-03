"""
Crawler API Router - Endpoints để quản lý Reddit crawler.

Endpoints:
1. Status - Xem trạng thái crawler
2. Manual trigger - Chạy crawl thủ công
3. Configuration - Xem/cập nhật cấu hình
4. Statistics - Thống kê crawl
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime

from app.services.scheduler_service import crawler_scheduler
from app.services.database_service import RedditPostService, CrawlMetadataService
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/crawler", tags=["Crawler"])


# ========================
# STATUS & CONTROL
# ========================

@router.get("/status")
async def get_crawler_status():
    """
    **Lấy trạng thái hiện tại của crawler scheduler.**
    
    **Returns:**
    - is_running: Scheduler có đang chạy không
    - next_run_time: Thời gian chạy tiếp theo
    - interval_minutes: Khoảng cách giữa các lần crawl
    - jobs: Danh sách các jobs
    """
    try:
        status = crawler_scheduler.get_status()
        
        return {
            **status,
            "subreddits": settings.subreddit_list,
            "posts_per_subreddit": settings.posts_per_subreddit
        }
        
    except Exception as e:
        logger.error(f"Error getting crawler status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run")
async def trigger_manual_crawl():
    """
    **Chạy crawl thủ công ngay lập tức.**
    
    Không ảnh hưởng đến schedule tự động.
    
    **Returns:**
    - Thống kê của lần crawl
    """
    try:
        logger.info("🔥 Manual crawl triggered via API")
        stats = await crawler_scheduler.run_now()
        
        return {
            "status": "completed",
            "message": "Manual crawl completed successfully",
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error in manual crawl: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_scheduler():
    """
    **Khởi động crawler scheduler.**
    
    Scheduler sẽ tự động crawl theo interval đã cấu hình.
    """
    try:
        if crawler_scheduler.is_started:
            return {
                "status": "already_running",
                "message": "Scheduler is already running"
            }
        
        crawler_scheduler.start()
        
        return {
            "status": "started",
            "message": "Scheduler started successfully",
            "next_run": crawler_scheduler.get_next_run_time()
        }
        
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_scheduler():
    """
    **Dừng crawler scheduler.**
    
    Scheduler sẽ không tự động crawl nữa.
    """
    try:
        if not crawler_scheduler.is_started:
            return {
                "status": "not_running",
                "message": "Scheduler is not running"
            }
        
        crawler_scheduler.stop()
        
        return {
            "status": "stopped",
            "message": "Scheduler stopped successfully"
        }
        
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================
# CONFIGURATION
# ========================

@router.get("/config")
async def get_crawler_config():
    """
    **Xem cấu hình crawler hiện tại.**
    
    **Returns:**
    - Các settings của crawler
    """
    return {
        "subreddits": settings.subreddit_list,
        "crawl_interval_minutes": settings.crawl_interval_minutes,
        "posts_per_subreddit": settings.posts_per_subreddit,
        "initial_crawl_months": settings.initial_crawl_months,
        "initial_crawl_limit": settings.initial_crawl_limit,
        "scheduler_status": crawler_scheduler.get_status()
    }


# ========================
# STATISTICS
# ========================

@router.get("/stats")
async def get_crawler_stats():
    """
    **Lấy thống kê tổng quan về crawler.**
    
    **Returns:**
    - Tổng số posts trong database
    - Số posts theo từng subreddit
    - Thời gian crawl gần nhất
    """
    try:
        total_posts = await RedditPostService.get_total_posts()
        
        # Get posts by subreddit
        subreddit_stats = []
        for subreddit in settings.subreddit_list:
            posts = await RedditPostService.get_posts_by_subreddit(subreddit, limit=1)
            count = len(posts)  # This is just checking if we have data
            
            last_crawl = await CrawlMetadataService.get_last_crawl_time(subreddit)
            
            subreddit_stats.append({
                "subreddit": subreddit,
                "last_crawl_time": last_crawl.isoformat() if last_crawl else None,
                "has_data": count > 0
            })
        
        return {
            "total_posts": total_posts,
            "subreddits": subreddit_stats,
            "crawler_status": crawler_scheduler.get_status()
        }
        
    except Exception as e:
        logger.error(f"Error getting crawler stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/{subreddit}")
async def get_subreddit_crawl_stats(
    subreddit: str,
    limit: int = Query(10, ge=1, le=100)
):
    """
    **Lấy thống kê crawl cho một subreddit cụ thể.**
    
    **Returns:**
    - Số posts
    - Posts gần đây
    - Thời gian crawl cuối
    """
    try:
        posts = await RedditPostService.get_posts_by_subreddit(subreddit, limit=limit)
        last_crawl = await CrawlMetadataService.get_last_crawl_time(subreddit)
        
        return {
            "subreddit": subreddit,
            "last_crawl_time": last_crawl.isoformat() if last_crawl else None,
            "recent_posts_count": len(posts),
            "recent_posts": [
                {
                    "post_id": p.get("post_id"),
                    "title": p.get("title"),
                    "created_at": p.get("created_utc"),
                    "score": p.get("score"),
                    "prediction": p.get("prediction", {}).get("label")
                }
                for p in posts
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting subreddit stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================
# POSTS
# ========================

@router.get("/posts/recent")
async def get_recent_posts(
    limit: int = Query(20, ge=1, le=100),
    subreddit: Optional[str] = Query(None, description="Filter by subreddit")
):
    """
    **Lấy các posts gần đây nhất.**
    
    **Returns:**
    - List posts sorted by created_utc
    """
    try:
        collection = mongodb.get_collection("reddit_posts")
        
        query = {}
        if subreddit:
            query["subreddit.name"] = subreddit
        
        posts = await collection.find(query).sort("created_utc", -1).limit(limit).to_list(length=limit)
        
        return {
            "count": len(posts),
            "subreddit": subreddit,
            "posts": [
                {
                    "post_id": p.get("post_id"),
                    "title": p.get("title"),
                    "domain": p.get("domain"),
                    "subreddit": p.get("subreddit", {}).get("name"),
                    "score": p.get("score"),
                    "num_comments": p.get("num_comments"),
                    "created_at": p.get("created_utc"),
                    "prediction": p.get("prediction")
                }
                for p in posts
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting recent posts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/posts/{post_id}")
async def get_post_by_id(post_id: str):
    """
    **Lấy chi tiết một post theo ID.**
    
    **Returns:**
    - Full post data
    """
    try:
        post = await RedditPostService.get_post_by_id(post_id)
        
        if not post:
            raise HTTPException(status_code=404, detail=f"Post {post_id} not found")
        
        # Remove MongoDB _id field
        if "_id" in post:
            del post["_id"]
        
        return post
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting post {post_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Import for mongodb
from app.core.database import mongodb

