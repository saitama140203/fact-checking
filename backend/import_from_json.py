"""
Script để import dữ liệu từ JSON file vào MongoDB.
Sử dụng PyMongo (sync).
"""
import json
import sys
from app.core.database import mongodb
from app.core.config import settings
from app.models.reddit import RedditPost
from app.services.database_service import RedditPostService
from app.core.logger import get_logger

logger = get_logger(__name__)

def import_from_json(json_file: str):
    """
    Import posts từ JSON file vào MongoDB
    
    Args:
        json_file: Đường dẫn tới file JSON
    """
    try:
        # 1. Kết nối database
        logger.info("🔌 Connecting to MongoDB...")
        mongodb.connect()
        
        # 2. Đọc file JSON
        logger.info(f"📖 Reading file: {json_file}")
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        posts_data = data.get("posts", [])
        logger.info(f"📊 Found {len(posts_data)} posts in JSON file")
        
        # 3. Convert sang Pydantic models
        posts = []
        for post_dict in posts_data:
            try:
                post = RedditPost(**post_dict)
                posts.append(post)
            except Exception as e:
                logger.warning(f"⚠️  Failed to parse post: {e}")
        
        logger.info(f"✅ Parsed {len(posts)} valid RedditPost objects")
        
        # 4. Insert vào MongoDB
        logger.info("💾 Inserting posts into MongoDB...")
        stats = RedditPostService.insert_posts_batch(posts)
        
        # 5. In kết quả
        logger.info("=" * 60)
        logger.info("✅ IMPORT COMPLETED")
        logger.info(f"   Inserted: {stats['inserted']}")
        logger.info(f"   Duplicates: {stats['duplicates']}")
        logger.info(f"   Errors: {stats['errors']}")
        logger.info(f"   Total in DB: {RedditPostService.get_total_posts()}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        raise
    finally:
        # 6. Đóng kết nối
        mongodb.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_from_json.py <json_file>")
        print("Example: python import_from_json.py production_crawl.json")
        sys.exit(1)
    
    json_file = sys.argv[1]
    import_from_json(json_file)

