"""
Database service for Reddit posts operations using PyMongo Async API.
"""
from app.core.database import mongodb
from app.core.logger import get_logger
from app.models.reddit import RedditPost
from typing import List, Optional, Dict, Any
from datetime import datetime
from pymongo.errors import DuplicateKeyError

logger = get_logger(__name__)

class RedditPostService:
    """Service để xử lý CRUD operations cho Reddit posts"""
    
    @staticmethod
    async def insert_post(post: RedditPost) -> bool:
        """
        Insert một bài post vào database
        
        Args:
            post: RedditPost Pydantic model
            
        Returns:
            bool: True nếu insert thành công, False nếu duplicate
        """
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            # Chuyển Pydantic model sang dict
            post_dict = post.model_dump(mode="json")
            post_dict["inserted_at"] = datetime.now()  # Thêm timestamp
            
            await collection.insert_one(post_dict)
            logger.info(f"✅ Inserted post: {post.post_id}")
            return True
            
        except DuplicateKeyError:
            logger.warning(f"⚠️  Post {post.post_id} already exists (skipped)")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to insert post {post.post_id}: {e}")
            raise
    
    @staticmethod
    async def insert_posts_batch(posts: List[RedditPost]) -> Dict[str, int]:
        """
        Insert nhiều posts cùng lúc (bulk insert)
        
        Args:
            posts: List các RedditPost
            
        Returns:
            Dict với thống kê: {"inserted": X, "duplicates": Y, "errors": Z}
        """
        stats = {"inserted": 0, "duplicates": 0, "errors": 0}
        
        for post in posts:
            try:
                success = await RedditPostService.insert_post(post)
                if success:
                    stats["inserted"] += 1
                else:
                    stats["duplicates"] += 1
            except Exception:
                stats["errors"] += 1
        
        logger.info(f"📊 Batch insert stats: {stats}")
        return stats
    
    @staticmethod
    async def get_post_by_id(post_id: str) -> Optional[Dict[str, Any]]:
        """Lấy post theo post_id"""
        try:
            collection = mongodb.get_collection("reddit_posts")
            post = await collection.find_one({"post_id": post_id})
            return post
        except Exception as e:
            logger.error(f"Failed to get post {post_id}: {e}")
            return None
    
    @staticmethod
    async def get_posts_by_subreddit(
        subreddit_name: str, 
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Lấy posts theo subreddit"""
        try:
            collection = mongodb.get_collection("reddit_posts")
            cursor = collection.find(
                {"subreddit.name": subreddit_name}
            ).sort("created_utc", -1).skip(skip).limit(limit)
            
            posts = await cursor.to_list(length=limit)
            return posts
        except Exception as e:
            logger.error(f"Failed to get posts from r/{subreddit_name}: {e}")
            return []
    
    @staticmethod
    async def get_total_posts() -> int:
        """Đếm tổng số posts trong database"""
        try:
            collection = mongodb.get_collection("reddit_posts")
            count = await collection.count_documents({})
            return count
        except Exception as e:
            logger.error(f"Failed to count posts: {e}")
            return 0


class CrawlMetadataService:
    """Service để track metadata của các lần crawl"""
    
    @staticmethod
    async def get_last_crawl_time(subreddit_name: str) -> Optional[datetime]:
        """
        Lấy thời gian crawl gần nhất cho subreddit
        
        Returns:
            datetime hoặc None nếu chưa crawl lần nào
        """
        try:
            collection = mongodb.get_collection("crawl_metadata")
            metadata = await collection.find_one({"subreddit": subreddit_name})
            
            if metadata and "last_crawl_time" in metadata:
                return metadata["last_crawl_time"]
            return None
            
        except Exception as e:
            logger.error(f"Failed to get last crawl time for r/{subreddit_name}: {e}")
            return None
    
    @staticmethod
    async def update_last_crawl_time(subreddit_name: str, crawl_time: datetime) -> bool:
        """
        Cập nhật thời gian crawl mới nhất
        """
        try:
            collection = mongodb.get_collection("crawl_metadata")
            
            await collection.update_one(
                {"subreddit": subreddit_name},
                {
                    "$set": {
                        "last_crawl_time": crawl_time,
                        "updated_at": datetime.now()
                    }
                },
                upsert=True  # Tạo mới nếu chưa tồn tại
            )
            
            logger.info(f"✅ Updated last_crawl_time for r/{subreddit_name}: {crawl_time}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update last crawl time: {e}")
            return False
    
    @staticmethod
    async def get_latest_post_time() -> Optional[datetime]:
        """
        Lấy thời gian của post mới nhất trong database
        Dùng làm fallback nếu metadata bị mất
        """
        try:
            collection = mongodb.get_collection("reddit_posts")
            latest_post = await collection.find_one(
                {},
                sort=[("created_utc", -1)]
            )
            
            if latest_post and "created_utc" in latest_post:
                return latest_post["created_utc"]
            return None
            
        except Exception as e:
            logger.error(f"Failed to get latest post time: {e}")
            return None