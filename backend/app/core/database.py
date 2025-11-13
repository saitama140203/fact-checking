"""
MongoDB database connection management using PyMongo Async API.
PyMongo 4.5+ có native async support với AsyncMongoClient.
Performance tốt hơn Motor (không qua thread pool).
"""
from pymongo import AsyncMongoClient, ASCENDING, DESCENDING
from app.core.config import settings
from app.core.logger import get_logger
from typing import Optional
import certifi

logger = get_logger(__name__)

class MongoDB:
    """MongoDB connection manager using PyMongo Async API (native async)"""
    
    client: Optional[AsyncMongoClient] = None
    
    @classmethod
    async def connect(cls):
        """Kết nối đến MongoDB Atlas sử dụng PyMongo Async API"""
        try:
            cls.client = AsyncMongoClient(
                settings.mongodb_atlas_uri,
                tlsCAFile=certifi.where(),
                serverSelectionTimeoutMS=5000
            )
            # Ping để test connection
            await cls.client.admin.command("ping")
            logger.info(f"✅ Connected to MongoDB: {settings.mongodb_db_name}")
            logger.info("✅ Using PyMongo Async API (native asyncio)")
            
            # Tạo indexes
            await cls.create_indexes()
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    @classmethod
    async def close(cls):
        """Đóng kết nối"""
        if cls.client:
            cls.client.close()
            logger.info("MongoDB connection closed")
    
    @classmethod
    def get_database(cls):
        """Lấy database instance"""
        if not cls.client:
            raise RuntimeError("Database not connected. Call connect() first.")
        return cls.client[settings.mongodb_db_name]
    
    @classmethod
    def get_collection(cls, collection_name: str):
        """Lấy collection"""
        db = cls.get_database()
        return db[collection_name]
    
    @classmethod
    async def create_indexes(cls):
        """Tạo indexes cho collections"""
        try:
            posts_collection = cls.get_collection("reddit_posts")
            
            # Index cho post_id (unique)
            await posts_collection.create_index(
                [("post_id", ASCENDING)], 
                unique=True,
                name="idx_post_id"
            )
            
            # Index cho created_utc (để sort theo thời gian)
            await posts_collection.create_index(
                [("created_utc", DESCENDING)],
                name="idx_created_utc"
            )
            
            # Index cho subreddit name
            await posts_collection.create_index(
                [("subreddit.name", ASCENDING)],
                name="idx_subreddit_name"
            )
            
            # Index cho score (để lọc trending)
            await posts_collection.create_index(
                [("score", DESCENDING)],
                name="idx_score"
            )
            
            logger.info("✅ Database indexes created")
            
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}")


# Singleton instance
mongodb = MongoDB()