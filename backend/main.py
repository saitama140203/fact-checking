"""
FastAPI Application với automated crawler pipeline.
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import mongodb
from app.core.logger import get_logger
from app.services.scheduler_service import crawler_scheduler
from app.services.database_service import RedditPostService
import asyncio

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager cho FastAPI app"""
    # Startup
    logger.info("🚀 Starting Fake News Detector API...")
    
    # 1. Kết nối database (PyMongo Async API)
    await mongodb.connect()
    
    # 2. Khởi động scheduler
    crawler_scheduler.start()
    
    # 3. (Optional) Chạy crawl đầu tiên ngay
    logger.info("🔄 Running initial crawl...")
    try:
        await crawler_scheduler.run_now()
    except Exception as e:
        logger.error(f"Initial crawl failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down application...")
    crawler_scheduler.stop()
    await mongodb.close()

app = FastAPI(
    title="Fake News Detector API",
    version="1.0.0",
    description="API để crawl và phát hiện fake news từ Reddit",
    lifespan=lifespan
)

# ========================
# API ENDPOINTS
# ========================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Fake News Detector API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        total_posts = await RedditPostService.get_total_posts()
        
        return {
            "status": "healthy",
            "database": "connected",
            "total_posts": total_posts,
            "scheduler": crawler_scheduler.get_status()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/crawler/status")
async def get_crawler_status():
    """Lấy status của crawler scheduler"""
    return crawler_scheduler.get_status()

@app.post("/crawler/run-now")
async def trigger_manual_crawl():
    """Trigger crawl thủ công ngay lập tức"""
    stats = await crawler_scheduler.run_now()
    return stats

@app.get("/stats")
async def get_stats():
    """Thống kê database và crawler"""
    total_posts = await RedditPostService.get_total_posts()
    
    return {
        "total_posts": total_posts,
        "subreddits": settings.subreddit_list,
        "crawl_interval_minutes": settings.crawl_interval_minutes,
        "crawler_status": crawler_scheduler.get_status()
    }

@app.get("/posts/subreddit/{subreddit_name}")
async def get_posts_by_subreddit(
    subreddit_name: str,
    limit: int = 20,
    skip: int = 0
):
    """Lấy posts theo subreddit"""
    posts = await RedditPostService.get_posts_by_subreddit(
        subreddit_name,
        limit,
        skip
    )
    return {
        "subreddit": subreddit_name,
        "count": len(posts),
        "posts": posts
    }

@app.get("/posts/{post_id}")
async def get_post_by_id(post_id: str):
    """Lấy post theo ID"""
    post = await RedditPostService.get_post_by_id(post_id)
    
    if not post:
        return {"error": "Post not found"}, 404
    
    return post

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )

