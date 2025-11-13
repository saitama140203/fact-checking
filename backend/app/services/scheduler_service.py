"""
Background scheduler for automated crawling using APScheduler.
"""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from app.core.config import settings
from app.core.logger import get_logger
from app.services.crawler_pipeline import CrawlerPipeline

logger = get_logger(__name__)

class CrawlerScheduler:
    """Scheduler để chạy automated crawl pipeline"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.pipeline = CrawlerPipeline()
        self.is_started = False
    
    async def _scheduled_crawl_job(self):
        """Job chạy định kỳ"""
        try:
            logger.info(f"⏰ Scheduled crawl triggered at {datetime.now()}")
            stats = await self.pipeline.run_incremental_crawl()
            logger.info(f"📊 Crawl stats: {stats}")
        except Exception as e:
            logger.error(f"❌ Scheduled crawl failed: {e}")
    
    def start(self):
        """Khởi động scheduler"""
        if self.is_started:
            logger.warning("Scheduler already started")
            return
        
        # Thêm job với interval từ config
        self.scheduler.add_job(
            self._scheduled_crawl_job,
            trigger=IntervalTrigger(minutes=settings.crawl_interval_minutes),
            id="reddit_crawler_job",
            name="Reddit Incremental Crawler",
            replace_existing=True,
            max_instances=1,  # Chỉ chạy 1 instance tại 1 thời điểm
            misfire_grace_time=300  # 5 phút grace time
        )
        
        self.scheduler.start()
        self.is_started = True
        
        logger.info("=" * 80)
        logger.info("🎯 CRAWLER SCHEDULER STARTED")
        logger.info(f"   Interval: Every {settings.crawl_interval_minutes} minutes")
        logger.info(f"   Subreddits: {settings.subreddit_list}")
        logger.info(f"   Next run: {self.scheduler.get_jobs()[0].next_run_time}")
        logger.info("=" * 80)
    
    def stop(self):
        """Dừng scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("🛑 Scheduler stopped")
        self.is_started = False
    
    async def run_now(self):
        """Chạy crawl ngay lập tức (manual trigger)"""
        logger.info("🔥 Manual crawl triggered")
        return await self.pipeline.run_incremental_crawl()
    
    def get_next_run_time(self):
        """Lấy thời gian chạy tiếp theo"""
        jobs = self.scheduler.get_jobs()
        if jobs:
            return jobs[0].next_run_time
        return None
    
    def get_status(self):
        """Lấy status của scheduler"""
        return {
            "is_running": self.scheduler.running if self.scheduler else False,
            "is_started": self.is_started,
            "next_run_time": self.get_next_run_time(),
            "interval_minutes": settings.crawl_interval_minutes,
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time
                }
                for job in self.scheduler.get_jobs()
            ] if self.scheduler else []
        }

# Global instance
crawler_scheduler = CrawlerScheduler()

