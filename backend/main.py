"""
FastAPI Application - Fake News Detector API.
Production-ready với comprehensive API endpoints.

Author: Fake News Detector Team
Version: 2.0.0
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import mongodb
from app.core.logger import get_logger
from app.services.scheduler_service import crawler_scheduler
from app.services.database_service import RedditPostService
from app.api import prediction, analytics, crawler, advanced_analysis, user_analysis
import asyncio
import time

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager cho FastAPI app"""
    # Startup
    logger.info("=" * 60)
    logger.info("🚀 STARTING FAKE NEWS DETECTOR API")
    logger.info(f"   Environment: {settings.environment}")
    logger.info(f"   Debug: {settings.debug}")
    logger.info("=" * 60)
    
    # 1. Kết nối database (PyMongo Async API)
    try:
        await mongodb.connect()
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        logger.warning("⚠️  API will start but database operations will fail")
    
    # 2. Khởi động scheduler (nếu được bật)
    if settings.enable_crawler:
        try:
            crawler_scheduler.start()
            logger.info("✅ Crawler scheduler started")
        except Exception as e:
            logger.error(f"❌ Failed to start scheduler: {e}")
    else:
        logger.info("⏸️  Crawler scheduler disabled (ENABLE_CRAWLER=False)")
    
    # 3. (Optional) Chạy crawl đầu tiên ngay (chỉ trong development và nếu crawler được bật)
    if settings.is_development and settings.enable_crawler:
        logger.info("🔄 Running initial crawl (development mode)...")
        try:
            await crawler_scheduler.run_now()
        except Exception as e:
            logger.error(f"Initial crawl failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("🛑 SHUTTING DOWN APPLICATION")
    logger.info("=" * 60)
    
    # Dừng scheduler nếu đã được khởi động
    if settings.enable_crawler and crawler_scheduler.is_started:
        try:
            crawler_scheduler.stop()
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    try:
        await mongodb.close()
    except Exception as e:
        logger.error(f"Error closing database connection: {e}")


# ========================
# APP INITIALIZATION
# ========================
app = FastAPI(
    title="Fake News Detector API",
    version="2.0.0",
    description="""
        ## 🔍 Fake News Detector API

        API để crawl và phát hiện fake news từ Reddit với AI-powered detection và analytics.

        ### Features:
        - 🤖 **AI Detection**: Sử dụng Hugging Face model để phát hiện fake news
        - 📊 **Analytics**: 10+ endpoints cho visualization và thống kê
        - 🔄 **Auto Crawler**: Tự động crawl Reddit posts định kỳ
        - 📈 **Advanced Analysis**: Phân tích xu hướng, source credibility, risk assessment
        - 📝 **User Analysis**: Phân tích bài viết do người dùng gửi vào
        - 🌐 **Cloud Ready**: Docker support cho cloud deployment

        ### API Groups:
        - `/prediction` - Fake news detection (batch)
        - `/analytics` - Statistics và charts data
        - `/analysis` - Advanced analysis và reports
        - `/analyze` - **User-submitted content analysis**
        - `/crawler` - Crawler management
        """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# ========================
# MIDDLEWARE
# ========================

# GZip compression for large responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list + [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "https://fact-checking-iota.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware (for production monitoring)
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header for monitoring."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions gracefully."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.debug else "An unexpected error occurred"
        }
    )

# ========================
# ROUTERS
# ========================
app.include_router(prediction.router)
app.include_router(analytics.router)
app.include_router(crawler.router)
app.include_router(advanced_analysis.router)
app.include_router(user_analysis.router)

# ========================
# ROOT ENDPOINTS
# ========================

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - API information.
    """
    return {
        "name": "Fake News Detector API",
        "version": "2.0.0",
        "status": "running",
        "environment": settings.environment,
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "analyze": "/analyze - User-submitted content analysis",
            "prediction": "/prediction - Batch fake news prediction",
            "analytics": "/analytics - Statistics and charts",
            "analysis": "/analysis - Advanced analysis and reports",
            "crawler": "/crawler - Crawler management"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    """
    from datetime import datetime
    
    try:
        # Test database connection
        total_posts = await RedditPostService.get_total_posts()
        db_status = "connected"
        db_healthy = True
    except Exception as e:
        total_posts = 0
        db_status = f"error: {str(e)}"
        db_healthy = False
    
    scheduler_status = crawler_scheduler.get_status()
    
    overall_healthy = db_healthy
    
    return {
        "status": "healthy" if overall_healthy else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "environment": settings.environment,
        "components": {
            "database": {
                "status": db_status,
                "healthy": db_healthy,
                "total_posts": total_posts
            },
            "scheduler": {
                "status": "running" if scheduler_status.get("is_running") else "stopped",
                "healthy": scheduler_status.get("is_started", False),
                "next_run": scheduler_status.get("next_run_time")
            }
        }
    }


@app.get("/stats", tags=["Statistics"])
async def get_stats():
    """
    Thống kê tổng quan về hệ thống.
    """
    from app.services.database_service import PredictionService
    
    try:
        total_posts = await RedditPostService.get_total_posts()
        posts_with_prediction = await PredictionService.count_posts_by_prediction()
        fake_count = await PredictionService.count_posts_by_prediction(label="FAKE")
        real_count = await PredictionService.count_posts_by_prediction(label="REAL")
        
        return {
            "database": {
                "total_posts": total_posts,
                "posts_with_prediction": posts_with_prediction,
                "posts_without_prediction": total_posts - posts_with_prediction,
                "prediction_coverage": round(
                    (posts_with_prediction / total_posts * 100) if total_posts > 0 else 0, 2
                )
            },
            "predictions": {
                "fake_news": fake_count,
                "real_news": real_count,
                "fake_percentage": round(
                    (fake_count / (fake_count + real_count) * 100) if (fake_count + real_count) > 0 else 0, 2
                )
            },
            "crawler": {
                "subreddits": settings.subreddit_list,
                "crawl_interval_minutes": settings.crawl_interval_minutes,
                "status": crawler_scheduler.get_status()
            }
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stats: {str(e)}")


# ========================
# SERVER STARTUP
# ========================

if __name__ == "__main__":
    import uvicorn
    import argparse
    
    parser = argparse.ArgumentParser(description="Fake News Detector API")
    parser.add_argument("--prod", action="store_true", help="Run in production mode")
    parser.add_argument("--host", type=str, default=settings.api_host, help="Host to bind to")
    parser.add_argument("--port", type=int, default=settings.api_port, help="Port to bind to")
    parser.add_argument("--workers", type=int, default=4, help="Number of workers (production only)")
    
    args = parser.parse_args()
    
    if args.prod:
        # Production mode
        logger.info("=" * 60)
        logger.info("🚀 STARTING FAKE NEWS DETECTOR API - PRODUCTION MODE")
        logger.info(f"   Host: {args.host}:{args.port}")
        logger.info(f"   Workers: {args.workers}")
        logger.info("=" * 60)
        
        uvicorn.run(
            "main:app",
            host=args.host,
            port=args.port,
            workers=args.workers,
            log_level="info",
            access_log=True
        )
    else:
        # Development mode
        logger.info("=" * 60)
        logger.info("🔧 STARTING FAKE NEWS DETECTOR API - DEVELOPMENT MODE")
        logger.info(f"   Host: {args.host}:{args.port}")
        logger.info("   Hot reload: Enabled")
        logger.info("=" * 60)
        
        uvicorn.run(
            "main:app",
            host=args.host,
            port=args.port,
            reload=True,
            log_level="debug"
        )

