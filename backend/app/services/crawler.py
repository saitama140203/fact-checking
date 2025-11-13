"""
Reddit Crawler Service - Production Ready
Crawl posts từ Reddit và convert sang Pydantic models.
KHÔNG load comments (chỉ lấy num_comments) để tối ưu performance.
"""
import asyncpraw
import asyncio
import json
from app.core.config import settings
from app.core.logger import get_logger
from app.models.reddit import RedditPost, Author, Subreddit
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import time

logger = get_logger(__name__)

class RedditCrawler:
    """Reddit Crawler sử dụng asyncpraw"""
    
    def __init__(self):
        """Khởi tạo crawler - lazy initialization"""
        self.reddit = None
        self._reddit_initialized = False
        
        # Store credentials
        self.client_id = settings.reddit_client_id
        self.client_secret = settings.reddit_client_secret
        self.user_agent = settings.reddit_user_agent
        
        # Production settings
        self.rate_limit_delay = 0.2
        self.max_retries = 3
        self.timeout_seconds = 30
        
        logger.info("RedditCrawler initialized (lazy mode)")
    
    async def _ensure_reddit_client(self):
        """Lazy init Reddit client trong async context"""
        if not self._reddit_initialized:
            self.reddit = asyncpraw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
                read_only=True,
                timeout=self.timeout_seconds
            )
            self._reddit_initialized = True
            logger.debug("Reddit client initialized")

    async def crawl_for_analysis(self, subreddit: str, limit: int = 50) -> List[RedditPost]:
        """Crawl bài đăng từ subreddit"""
        await self._ensure_reddit_client()
        
        posts_data: List[RedditPost] = []
        try:
            subreddit_obj = await self.reddit.subreddit(subreddit)
            
            try:
                await subreddit_obj.load()
            except Exception as e:
                logger.error(f"Subreddit r/{subreddit} not accessible: {e}")
                return []
            
            logger.info(f"Crawling r/{subreddit}")
            
            async for post in subreddit_obj.new(limit=limit):
                try:
                    processed_post = await self._process_post(post, subreddit_obj) 
                    if processed_post:
                        posts_data.append(processed_post)
                    
                    await asyncio.sleep(self.rate_limit_delay)
                    
                except Exception as e:
                    logger.warning(f"Failed to process post {getattr(post, 'id', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Crawled {len(posts_data)} posts from r/{subreddit}")
            return posts_data
            
        except Exception as e:
            logger.error(f"Critical error crawling r/{subreddit}: {e}")
            return []

    async def _process_post(
        self, 
        post: asyncpraw.models.Submission, 
        subreddit_obj: asyncpraw.models.Subreddit
    ) -> Optional[RedditPost]:
        """
        Xử lý bài đăng Reddit thành Pydantic model.
        KHÔNG load comments - chỉ dùng num_comments để tối ưu performance.
        
        Args:
            post: Reddit Submission object
            subreddit_obj: Subreddit object (đã load)
            
        Returns:
            RedditPost hoặc None nếu có lỗi
        """
        try:
            # 1. Xử lý Author
            processed_author: Optional[Author] = None
            if post.author:
                try:
                    await post.author.load()
                    created_utc_val = getattr(post.author, 'created_utc', None)
                    
                    processed_author = Author(
                        username=getattr(post.author, 'name', 'N/A'),
                        account_created_utc=datetime.fromtimestamp(created_utc_val) if created_utc_val else None,
                        comment_karma=getattr(post.author, 'comment_karma', 0),
                        link_karma=getattr(post.author, 'link_karma', 0),
                        has_verified_email=getattr(post.author, 'has_verified_email', None)
                    )
                except Exception as e:
                    logger.debug(f"Failed to load author for {post.id}: {e}")
                    processed_author = Author(username=getattr(post.author, 'name', '[deleted]'))

            # 2. Xử lý Subreddit
            processed_subreddit = Subreddit(
                name=subreddit_obj.display_name,
                subscribers=getattr(subreddit_obj, 'subscribers', 0),
                description=getattr(subreddit_obj, 'public_description', None)
            )

            # 3. Tạo RedditPost (num_comments đã có sẵn, không cần load)
            return RedditPost(
                post_id=post.id,
                title=post.title,
                selftext=getattr(post, 'selftext', None),
                url=post.url,
                domain=post.domain,
                permalink=f"https://www.reddit.com{post.permalink}",
                score=post.score,
                upvote_ratio=post.upvote_ratio,
                num_comments=post.num_comments,
                locked=post.locked,
                over_18=post.over_18,
                spoiler=post.spoiler,
                created_utc=datetime.fromtimestamp(post.created_utc),
                edited=bool(post.edited),
                flair_text=getattr(post, 'link_flair_text', None),
                author=processed_author,
                subreddit=processed_subreddit
            )
            
        except Exception as e:
            logger.error(f"Failed to process post {getattr(post, 'id', 'unknown')}: {e}")
            return None

    async def crawl_realtime_batch(self, subreddits: List[str], minutes_back: int = 5) -> List[RedditPost]:
        """Crawl batch real-time từ nhiều subreddits"""
        await self._ensure_reddit_client()
        
        all_new_posts: List[RedditPost] = []
        cutoff_time = datetime.now() - timedelta(minutes=minutes_back)
        
        for subreddit_name in subreddits:
            try:
                logger.info(f"Checking r/{subreddit_name}")
                
                subreddit_obj = await self.reddit.subreddit(subreddit_name)
                await subreddit_obj.load()
                
                new_posts_count = 0
                
                async for post in subreddit_obj.new(limit=30):
                    post_time = datetime.fromtimestamp(post.created_utc)
                    
                    if post_time > cutoff_time:
                        processed_post = await self._process_post(post, subreddit_obj) 
                        if processed_post:
                            all_new_posts.append(processed_post)
                            new_posts_count += 1
                    else:
                        break
                    
                    await asyncio.sleep(self.rate_limit_delay)
                
                logger.info(f"r/{subreddit_name}: {new_posts_count} new posts")
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to crawl r/{subreddit_name}: {e}")
                continue
        
        logger.info(f"Total: {len(all_new_posts)} posts from {len(subreddits)} subreddits")
        return all_new_posts

    async def crawl_historical(
        self, 
        subreddit: str, 
        months_back: int = 5,
        limit_total: int = 500
    ) -> List[RedditPost]:
        """
        Crawl historical posts từ X tháng trước (cho lần đầu tiên).
        Sử dụng top posts theo year để lấy posts quan trọng.
        
        Args:
            subreddit: Tên subreddit
            months_back: Số tháng muốn crawl (mặc định 5)
            limit_total: Tổng số posts muốn lấy (mặc định 500)
            
        Returns:
            List[RedditPost]: Danh sách posts từ X tháng trước
        """
        await self._ensure_reddit_client()
        
        posts_data: List[RedditPost] = []
        try:
            subreddit_obj = await self.reddit.subreddit(subreddit)
            await subreddit_obj.load()
            
            logger.info(f"📅 Historical crawl: {months_back} months from r/{subreddit}")
            
            # Xác định time_filter
            time_filter = "year" if months_back >= 1 else "month"
            
            logger.info(f"   Using time_filter='{time_filter}', limit={limit_total}")
            
            # Crawl top posts
            async for post in subreddit_obj.top(time_filter=time_filter, limit=limit_total):
                try:
                    # Tính tuổi của post
                    post_created = datetime.fromtimestamp(post.created_utc)
                    post_age_days = (datetime.now() - post_created).days
                    post_age_months = post_age_days / 30
                    
                    # Chỉ lấy posts trong khoảng thời gian mong muốn
                    if post_age_months <= months_back:
                        processed_post = await self._process_post(post, subreddit_obj)
                        if processed_post:
                            posts_data.append(processed_post)
                    
                    await asyncio.sleep(self.rate_limit_delay)
                    
                except Exception as e:
                    logger.warning(f"Failed to process post {getattr(post, 'id', 'unknown')}: {e}")
                    continue
            
            logger.info(f"✅ Historical crawl: {len(posts_data)} posts from {months_back} months")
            return posts_data
            
        except Exception as e:
            logger.error(f"❌ Historical crawl failed for r/{subreddit}: {e}")
            return []

    async def get_trending_posts(self, subreddit: str, limit: int = 20) -> List[RedditPost]:
        """Lấy bài đăng trending (rising)"""
        await self._ensure_reddit_client()
        
        trending_posts: List[RedditPost] = []
        try:
            subreddit_obj = await self.reddit.subreddit(subreddit)
            await subreddit_obj.load()
            
            async for post in subreddit_obj.rising(limit=limit):
                processed_post = await self._process_post(post, subreddit_obj) 
                if processed_post:
                    trending_posts.append(processed_post)
                
                await asyncio.sleep(self.rate_limit_delay)
            
            logger.info(f"Found {len(trending_posts)} trending posts in r/{subreddit}")
            return trending_posts
            
        except Exception as e:
            logger.error(f"Failed to get trending posts from r/{subreddit}: {e}")
            return []

    async def health_check(self) -> Dict[str, Any]:
        """Health check cho crawler"""
        await self._ensure_reddit_client()
        
        try:
            start_time = time.time()
            test_subreddit = await self.reddit.subreddit("test")
            await test_subreddit.load()
            
            async for post in test_subreddit.new(limit=1):
                test_post = await self._process_post(post, test_subreddit) 
                break
            
            response_time = time.time() - start_time
            
            if not test_post:
                raise Exception("Health check failed: Post processing error")

            return {
                "status": "healthy",
                "response_time_seconds": round(response_time, 2),
                "reddit_api_accessible": True,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy", 
                "error": str(e), 
                "reddit_api_accessible": False, 
                "timestamp": datetime.now().isoformat()
            }

    async def save_pydantic_json(self, posts: List[RedditPost], filename: str = "realtime_posts.json"):
        """Lưu posts vào JSON file"""
        try:
            posts_as_dicts = [post.model_dump(mode="json") for post in posts]

            output_data = {
                "metadata": {
                    "total_posts": len(posts),
                    "crawled_at": datetime.now().isoformat(),
                    "subreddits": list(set(post.subreddit.name for post in posts)), 
                    "time_range": {
                        "earliest": min(post.created_utc for post in posts) if posts else None,
                        "latest": max(post.created_utc for post in posts) if posts else None
                    }
                },
                "posts": posts_as_dicts
            }
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False, default=str) 
            
            logger.info(f"Saved {len(posts)} posts to {filename}")
            
        except Exception as e:
            logger.error(f"Failed to save posts to {filename}: {e}")

    async def close(self):
        """Đóng kết nối Reddit"""
        try:
            if self._reddit_initialized and self.reddit:
                if hasattr(self.reddit, '_core') and hasattr(self.reddit._core, '_requestor'):
                    await self.reddit._core._requestor._http.close()
                logger.info("Reddit connection closed")
        except Exception as e:
            logger.warning(f"Error closing Reddit connection: {e}")

