"""
Database service for Reddit posts operations using PyMongo Async API.
"""
from app.core.database import mongodb
from app.core.logger import get_logger
from app.models.reddit import RedditPost
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pymongo.errors import DuplicateKeyError
from collections import Counter
import re

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


class PredictionService:
    """Service để xử lý prediction operations"""
    
    @staticmethod
    async def update_post_prediction(
        post_id: str, 
        prediction: Dict[str, Any]
    ) -> bool:
        """
        Cập nhật prediction cho một post.
        
        Args:
            post_id: ID của post
            prediction: Dict chứa prediction result
            
        Returns:
            bool: True nếu update thành công
        """
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            result = await collection.update_one(
                {"post_id": post_id},
                {"$set": {"prediction": prediction}}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Updated prediction for post {post_id}")
                return True
            else:
                logger.warning(f"⚠️  Post {post_id} not found or already has same prediction")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update prediction for {post_id}: {e}")
            return False
    
    @staticmethod
    async def get_posts_without_prediction(
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Lấy các posts chưa có prediction.
        
        Args:
            limit: Số lượng posts tối đa
            skip: Bỏ qua bao nhiêu posts
            
        Returns:
            List các posts chưa được predict
        """
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            # Query posts không có prediction hoặc prediction = None
            cursor = collection.find(
                {
                    "$or": [
                        {"prediction": {"$exists": False}},
                        {"prediction": None}
                    ]
                }
            ).sort("created_utc", -1).skip(skip).limit(limit)
            
            posts = await cursor.to_list(length=limit)
            return posts
            
        except Exception as e:
            logger.error(f"Failed to get posts without prediction: {e}")
            return []
    
    @staticmethod
    async def get_posts_with_prediction(
        label: Optional[str] = None,
        min_confidence: float = 0.0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        subreddit: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Lấy các posts đã có prediction với filters.
        
        Args:
            label: Filter theo label (FAKE hoặc REAL)
            min_confidence: Confidence tối thiểu
            start_date: Ngày bắt đầu
            end_date: Ngày kết thúc
            subreddit: Filter theo subreddit
            limit: Số lượng posts
            skip: Bỏ qua
            
        Returns:
            List các posts đã được predict
        """
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            # Build query
            query = {"prediction": {"$exists": True, "$ne": None}}
            
            if label:
                query["prediction.label"] = label.upper()
            
            if min_confidence > 0:
                query["prediction.confidence"] = {"$gte": min_confidence}
            
            if start_date or end_date:
                date_query = {}
                if start_date:
                    date_query["$gte"] = start_date
                if end_date:
                    date_query["$lte"] = end_date
                query["created_utc"] = date_query
            
            if subreddit:
                query["subreddit.name"] = subreddit
            
            cursor = collection.find(query).sort("created_utc", -1).skip(skip).limit(limit)
            posts = await cursor.to_list(length=limit)
            
            return posts
            
        except Exception as e:
            logger.error(f"Failed to get posts with prediction: {e}")
            return []
    
    @staticmethod
    async def count_posts_by_prediction(
        label: Optional[str] = None,
        min_confidence: float = 0.5
    ) -> int:
        """
        Đếm số posts theo prediction label.
        
        Args:
            label: FAKE, REAL hoặc None (tất cả)
            min_confidence: Confidence tối thiểu
            
        Returns:
            Số lượng posts
        """
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            query = {
                "prediction": {"$exists": True, "$ne": None},
                "prediction.confidence": {"$gte": min_confidence}
            }
            
            if label:
                query["prediction.label"] = label.upper()
            
            count = await collection.count_documents(query)
            return count
            
        except Exception as e:
            logger.error(f"Failed to count posts: {e}")
            return 0


class AnalyticsService:
    """Service để aggregate data cho analytics/visualization"""
    
    @staticmethod
    async def get_fake_vs_real_stats(
        min_confidence: float = 0.5,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        subreddit: Optional[str] = None
    ) -> Dict[str, Any]:
        """Thống kê tổng quan fake vs real."""
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            # Build match query
            match_query = {
                "prediction": {"$exists": True, "$ne": None},
                "prediction.confidence": {"$gte": min_confidence}
            }
            
            if start_date or end_date:
                date_query = {}
                if start_date:
                    date_query["$gte"] = start_date
                if end_date:
                    date_query["$lte"] = end_date
                match_query["created_utc"] = date_query
            
            if subreddit:
                match_query["subreddit.name"] = subreddit
            
            # Aggregate
            pipeline = [
                {"$match": match_query},
                {
                    "$group": {
                        "_id": "$prediction.label",
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            # PyMongo 4.10+ aggregate() is a coroutine, need to await it first
            cursor = await collection.aggregate(pipeline)
            result = await cursor.to_list(length=10)
            
            # Parse result
            fake_count = 0
            real_count = 0
            
            for item in result:
                if item["_id"] == "FAKE":
                    fake_count = item["count"]
                elif item["_id"] == "REAL":
                    real_count = item["count"]
            
            total = fake_count + real_count
            
            return {
                "fake_count": fake_count,
                "real_count": real_count,
                "total_count": total,
                "fake_percentage": (fake_count / total * 100) if total > 0 else 0,
                "real_percentage": (real_count / total * 100) if total > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get fake vs real stats: {e}")
            return {
                "fake_count": 0,
                "real_count": 0,
                "total_count": 0,
                "fake_percentage": 0,
                "real_percentage": 0
            }
    
    @staticmethod
    async def get_timeline_data(
        granularity: str = "daily",
        min_confidence: float = 0.5,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        subreddit: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Lấy dữ liệu timeline fake news theo thời gian.
        
        Args:
            granularity: daily, weekly, monthly
        """
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            # Build match query
            match_query = {
                "prediction": {"$exists": True, "$ne": None},
                "prediction.confidence": {"$gte": min_confidence}
            }
            
            if start_date or end_date:
                date_query = {}
                if start_date:
                    date_query["$gte"] = start_date
                if end_date:
                    date_query["$lte"] = end_date
                match_query["created_utc"] = date_query
            
            if subreddit:
                match_query["subreddit.name"] = subreddit
            
            # Date format based on granularity
            date_format = {
                "daily": "%Y-%m-%d",
                "weekly": "%Y-W%U",
                "monthly": "%Y-%m"
            }.get(granularity, "%Y-%m-%d")
            
            # Aggregate
            pipeline = [
                {"$match": match_query},
                {
                    "$group": {
                        "_id": {
                            "date": {"$dateToString": {"format": date_format, "date": "$created_utc"}},
                            "label": "$prediction.label"
                        },
                        "count": {"$sum": 1}
                    }
                },
                {"$sort": {"_id.date": 1}}
            ]
            
            # PyMongo 4.10+ aggregate() is a coroutine, need to await it first
            cursor = await collection.aggregate(pipeline)
            result = await cursor.to_list(length=1000)
            
            # Reorganize data
            timeline_dict = {}
            for item in result:
                date = item["_id"]["date"]
                label = item["_id"]["label"]
                count = item["count"]
                
                if date not in timeline_dict:
                    timeline_dict[date] = {"date": date, "fake_count": 0, "real_count": 0}
                
                if label == "FAKE":
                    timeline_dict[date]["fake_count"] = count
                elif label == "REAL":
                    timeline_dict[date]["real_count"] = count
            
            # Convert to list and add total
            timeline_data = []
            for data in timeline_dict.values():
                data["total_count"] = data["fake_count"] + data["real_count"]
                timeline_data.append(data)
            
            return timeline_data
            
        except Exception as e:
            logger.error(f"Failed to get timeline data: {e}")
            return []
    
    @staticmethod
    async def get_subreddit_stats(
        min_confidence: float = 0.5,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Thống kê fake news theo subreddit."""
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            # Build match query
            match_query = {
                "prediction": {"$exists": True, "$ne": None},
                "prediction.confidence": {"$gte": min_confidence}
            }
            
            if start_date or end_date:
                date_query = {}
                if start_date:
                    date_query["$gte"] = start_date
                if end_date:
                    date_query["$lte"] = end_date
                match_query["created_utc"] = date_query
            
            # Aggregate
            pipeline = [
                {"$match": match_query},
                {
                    "$group": {
                        "_id": {
                            "subreddit": "$subreddit.name",
                            "label": "$prediction.label"
                        },
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            # PyMongo 4.10+ aggregate() is a coroutine, need to await it first
            cursor = await collection.aggregate(pipeline)
            result = await cursor.to_list(length=1000)
            
            # Reorganize data
            subreddit_dict = {}
            for item in result:
                subreddit = item["_id"]["subreddit"]
                label = item["_id"]["label"]
                count = item["count"]
                
                if subreddit not in subreddit_dict:
                    subreddit_dict[subreddit] = {
                        "subreddit": subreddit,
                        "fake_count": 0,
                        "real_count": 0
                    }
                
                if label == "FAKE":
                    subreddit_dict[subreddit]["fake_count"] = count
                elif label == "REAL":
                    subreddit_dict[subreddit]["real_count"] = count
            
            # Convert to list and calculate percentages
            subreddit_data = []
            for data in subreddit_dict.values():
                total = data["fake_count"] + data["real_count"]
                data["total_count"] = total
                data["fake_percentage"] = (data["fake_count"] / total * 100) if total > 0 else 0
                subreddit_data.append(data)
            
            # Sort by fake count descending
            subreddit_data.sort(key=lambda x: x["fake_count"], reverse=True)
            
            return subreddit_data
            
        except Exception as e:
            logger.error(f"Failed to get subreddit stats: {e}")
            return []
    
    @staticmethod
    async def get_domain_stats(
        top_n: int = 20,
        min_confidence: float = 0.5,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        subreddit: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Thống kê fake news theo domain."""
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            # Build match query
            match_query = {
                "prediction": {"$exists": True, "$ne": None},
                "prediction.confidence": {"$gte": min_confidence}
            }
            
            if start_date or end_date:
                date_query = {}
                if start_date:
                    date_query["$gte"] = start_date
                if end_date:
                    date_query["$lte"] = end_date
                match_query["created_utc"] = date_query
            
            if subreddit:
                match_query["subreddit.name"] = subreddit
            
            # Aggregate
            pipeline = [
                {"$match": match_query},
                {
                    "$group": {
                        "_id": {
                            "domain": "$domain",
                            "label": "$prediction.label"
                        },
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            # PyMongo 4.10+ aggregate() is a coroutine, need to await it first
            cursor = await collection.aggregate(pipeline)
            result = await cursor.to_list(length=10000)
            
            # Reorganize data
            domain_dict = {}
            for item in result:
                domain = item["_id"]["domain"]
                label = item["_id"]["label"]
                count = item["count"]
                
                if domain not in domain_dict:
                    domain_dict[domain] = {
                        "domain": domain,
                        "fake_count": 0,
                        "real_count": 0
                    }
                
                if label == "FAKE":
                    domain_dict[domain]["fake_count"] = count
                elif label == "REAL":
                    domain_dict[domain]["real_count"] = count
            
            # Convert to list and calculate percentages
            domain_data = []
            for data in domain_dict.values():
                total = data["fake_count"] + data["real_count"]
                data["total_count"] = total
                data["fake_percentage"] = (data["fake_count"] / total * 100) if total > 0 else 0
                domain_data.append(data)
            
            # Sort by total count descending and get top N
            domain_data.sort(key=lambda x: x["total_count"], reverse=True)
            
            return domain_data[:top_n]
            
        except Exception as e:
            logger.error(f"Failed to get domain stats: {e}")
            return []
    
    @staticmethod
    async def get_engagement_comparison(
        min_confidence: float = 0.5,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        subreddit: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """So sánh engagement metrics giữa fake và real news."""
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            # Build match query
            match_query = {
                "prediction": {"$exists": True, "$ne": None},
                "prediction.confidence": {"$gte": min_confidence}
            }
            
            if start_date or end_date:
                date_query = {}
                if start_date:
                    date_query["$gte"] = start_date
                if end_date:
                    date_query["$lte"] = end_date
                match_query["created_utc"] = date_query
            
            if subreddit:
                match_query["subreddit.name"] = subreddit
            
            # Aggregate
            pipeline = [
                {"$match": match_query},
                {
                    "$group": {
                        "_id": "$prediction.label",
                        "avg_score": {"$avg": "$score"},
                        "avg_comments": {"$avg": "$num_comments"},
                        "avg_upvote_ratio": {"$avg": "$upvote_ratio"},
                        "total_posts": {"$sum": 1},
                        "scores": {"$push": "$score"},
                        "comments": {"$push": "$num_comments"}
                    }
                }
            ]
            
            # PyMongo 4.10+ aggregate() is a coroutine, need to await it first
            cursor = await collection.aggregate(pipeline)
            result = await cursor.to_list(length=10)
            
            # Parse result
            stats = {"fake_stats": {}, "real_stats": {}}
            
            for item in result:
                label = item["_id"]
                
                # Calculate median (approximate from sorted array)
                scores = sorted(item["scores"])
                comments = sorted(item["comments"])
                n = len(scores)
                median_score = scores[n // 2] if n > 0 else 0
                median_comments = comments[n // 2] if n > 0 else 0
                
                stat_data = {
                    "label": label,
                    "avg_score": round(item["avg_score"], 2),
                    "avg_comments": round(item["avg_comments"], 2),
                    "avg_upvote_ratio": round(item["avg_upvote_ratio"], 4),
                    "median_score": median_score,
                    "median_comments": median_comments,
                    "total_posts": item["total_posts"]
                }
                
                if label == "FAKE":
                    stats["fake_stats"] = stat_data
                elif label == "REAL":
                    stats["real_stats"] = stat_data
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get engagement comparison: {e}")
            return {"fake_stats": {}, "real_stats": {}}
    
    @staticmethod
    async def get_time_distribution(
        min_confidence: float = 0.5,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        subreddit: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Phân bố fake news theo giờ và ngày trong tuần (heatmap data)."""
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            # Build match query
            match_query = {
                "prediction": {"$exists": True, "$ne": None},
                "prediction.confidence": {"$gte": min_confidence}
            }
            
            if start_date or end_date:
                date_query = {}
                if start_date:
                    date_query["$gte"] = start_date
                if end_date:
                    date_query["$lte"] = end_date
                match_query["created_utc"] = date_query
            
            if subreddit:
                match_query["subreddit.name"] = subreddit
            
            # Aggregate by hour and day of week
            pipeline = [
                {"$match": match_query},
                {
                    "$group": {
                        "_id": {
                            "hour": {"$hour": "$created_utc"},
                            "dayOfWeek": {"$dayOfWeek": "$created_utc"},
                            "label": "$prediction.label"
                        },
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            # PyMongo 4.10+ aggregate() is a coroutine, need to await it first
            cursor = await collection.aggregate(pipeline)
            result = await cursor.to_list(length=10000)
            
            # Reorganize data
            heatmap_dict = {}
            for item in result:
                hour = item["_id"]["hour"]
                day_of_week = item["_id"]["dayOfWeek"] - 1  # MongoDB: 1=Sunday, convert to 0=Monday
                if day_of_week < 0:
                    day_of_week = 6
                label = item["_id"]["label"]
                count = item["count"]
                
                key = f"{hour}_{day_of_week}"
                if key not in heatmap_dict:
                    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                    heatmap_dict[key] = {
                        "hour": hour,
                        "day_of_week": day_of_week,
                        "day_name": day_names[day_of_week],
                        "fake_count": 0,
                        "real_count": 0
                    }
                
                if label == "FAKE":
                    heatmap_dict[key]["fake_count"] = count
                elif label == "REAL":
                    heatmap_dict[key]["real_count"] = count
            
            # Convert to list and add total
            heatmap_data = []
            for data in heatmap_dict.values():
                data["total_count"] = data["fake_count"] + data["real_count"]
                heatmap_data.append(data)
            
            # Sort by day and hour
            heatmap_data.sort(key=lambda x: (x["day_of_week"], x["hour"]))
            
            return heatmap_data
            
        except Exception as e:
            logger.error(f"Failed to get time distribution: {e}")
            return []
    
    @staticmethod
    async def get_keywords_frequency(
        top_n: int = 50,
        min_confidence: float = 0.5,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        subreddit: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Trích xuất top keywords từ fake vs real news.
        
        Returns:
            Dict với fake_keywords và real_keywords
        """
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            # Build match query
            match_query = {
                "prediction": {"$exists": True, "$ne": None},
                "prediction.confidence": {"$gte": min_confidence}
            }
            
            if start_date or end_date:
                date_query = {}
                if start_date:
                    date_query["$gte"] = start_date
                if end_date:
                    date_query["$lte"] = end_date
                match_query["created_utc"] = date_query
            
            if subreddit:
                match_query["subreddit.name"] = subreddit
            
            # Get fake news titles
            fake_posts = await collection.find(
                {**match_query, "prediction.label": "FAKE"}
            ).to_list(length=1000)
            
            # Get real news titles
            real_posts = await collection.find(
                {**match_query, "prediction.label": "REAL"}
            ).to_list(length=1000)
            
            # Extract keywords (simple word frequency)
            def extract_keywords(posts):
                # Stop words (common words to ignore)
                stop_words = {
                    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
                    'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                    'could', 'should', 'may', 'might', 'must', 'can', 'it', 'its', 'this',
                    'that', 'these', 'those', 'i', 'you', 'he', 'she', 'we', 'they', 'what',
                    'which', 'who', 'when', 'where', 'why', 'how', 'all', 'each', 'every',
                    'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
                    'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't',
                    'just', 'don', 'now', 'if', 'after', 'says', 'new', 'video'
                }
                
                all_words = []
                for post in posts:
                    title = post.get("title", "")
                    # Tokenize and clean
                    words = re.findall(r'\b[a-z]{3,}\b', title.lower())
                    # Filter stop words
                    words = [w for w in words if w not in stop_words]
                    all_words.extend(words)
                
                # Count frequency
                word_counts = Counter(all_words)
                
                # Get top N
                top_words = word_counts.most_common(top_n)
                
                # Calculate percentage
                total = sum(word_counts.values())
                
                return [
                    {
                        "word": word,
                        "frequency": count,
                        "percentage": round((count / total * 100), 2) if total > 0 else 0
                    }
                    for word, count in top_words
                ]
            
            fake_keywords = extract_keywords(fake_posts)
            real_keywords = extract_keywords(real_posts)
            
            return {
                "fake_keywords": fake_keywords,
                "real_keywords": real_keywords
            }
            
        except Exception as e:
            logger.error(f"Failed to get keywords frequency: {e}")
            return {"fake_keywords": [], "real_keywords": []}

    
    @staticmethod
    async def get_confidence_distribution(
        bucket_size: float = 0.1,
        min_confidence: float = 0.0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        subreddit: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Phân bố confidence scores (histogram data)."""
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            # Build match query
            match_query = {
                "prediction": {"$exists": True, "$ne": None},
                "prediction.confidence": {"$gte": min_confidence}
            }
            
            if start_date or end_date:
                date_query = {}
                if start_date:
                    date_query["$gte"] = start_date
                if end_date:
                    date_query["$lte"] = end_date
                match_query["created_utc"] = date_query
            
            if subreddit:
                match_query["subreddit.name"] = subreddit
            
            # Get all posts with predictions
            posts = await collection.find(match_query).to_list(length=10000)
            
            # Create buckets
            buckets = {}
            for i in range(int(1 / bucket_size)):
                range_start = round(i * bucket_size, 2)
                range_end = round((i + 1) * bucket_size, 2)
                buckets[range_start] = {
                    "range_start": range_start,
                    "range_end": range_end,
                    "fake_count": 0,
                    "real_count": 0,
                    "total_count": 0
                }
            
            # Distribute posts into buckets
            for post in posts:
                confidence = post.get("prediction", {}).get("confidence", 0)
                label = post.get("prediction", {}).get("label", "")
                
                # Find bucket
                bucket_index = int(confidence / bucket_size) * bucket_size
                bucket_index = min(bucket_index, 0.9)  # Cap at 0.9 for 1.0 range
                
                if bucket_index in buckets:
                    buckets[bucket_index]["total_count"] += 1
                    if label == "FAKE":
                        buckets[bucket_index]["fake_count"] += 1
                    elif label == "REAL":
                        buckets[bucket_index]["real_count"] += 1
            
            # Convert to list
            distribution_data = list(buckets.values())
            distribution_data.sort(key=lambda x: x["range_start"])
            
            return distribution_data
            
        except Exception as e:
            logger.error(f"Failed to get confidence distribution: {e}")
            return []
    
    @staticmethod
    async def get_flair_stats(
        min_confidence: float = 0.5,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        subreddit: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Thống kê fake news theo flair."""
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            # Build match query
            match_query = {
                "prediction": {"$exists": True, "$ne": None},
                "prediction.confidence": {"$gte": min_confidence}
            }
            
            if start_date or end_date:
                date_query = {}
                if start_date:
                    date_query["$gte"] = start_date
                if end_date:
                    date_query["$lte"] = end_date
                match_query["created_utc"] = date_query
            
            if subreddit:
                match_query["subreddit.name"] = subreddit
            
            # Aggregate
            pipeline = [
                {"$match": match_query},
                {
                    "$group": {
                        "_id": {
                            "flair": "$flair_text",
                            "label": "$prediction.label"
                        },
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            # PyMongo 4.10+ aggregate() is a coroutine, need to await it first
            cursor = await collection.aggregate(pipeline)
            result = await cursor.to_list(length=1000)
            
            # Reorganize data
            flair_dict = {}
            for item in result:
                flair = item["_id"]["flair"] or "No Flair"
                label = item["_id"]["label"]
                count = item["count"]
                
                if flair not in flair_dict:
                    flair_dict[flair] = {
                        "flair": flair,
                        "fake_count": 0,
                        "real_count": 0
                    }
                
                if label == "FAKE":
                    flair_dict[flair]["fake_count"] = count
                elif label == "REAL":
                    flair_dict[flair]["real_count"] = count
            
            # Convert to list and calculate percentages
            flair_data = []
            for data in flair_dict.values():
                total = data["fake_count"] + data["real_count"]
                data["total_count"] = total
                data["fake_percentage"] = (data["fake_count"] / total * 100) if total > 0 else 0
                flair_data.append(data)
            
            # Sort by total count descending
            flair_data.sort(key=lambda x: x["total_count"], reverse=True)
            
            return flair_data
            
        except Exception as e:
            logger.error(f"Failed to get flair stats: {e}")
            return []
    
    @staticmethod
    async def get_author_credibility(
        min_posts: int = 2,
        min_confidence: float = 0.5,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        subreddit: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Phân tích credibility của tác giả (scatter plot data).
        
        Args:
            min_posts: Số posts tối thiểu để tính credibility
        """
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            # Build match query
            match_query = {
                "prediction": {"$exists": True, "$ne": None},
                "prediction.confidence": {"$gte": min_confidence},
                "author": {"$exists": True, "$ne": None}
            }
            
            if start_date or end_date:
                date_query = {}
                if start_date:
                    date_query["$gte"] = start_date
                if end_date:
                    date_query["$lte"] = end_date
                match_query["created_utc"] = date_query
            
            if subreddit:
                match_query["subreddit.name"] = subreddit
            
            # Aggregate by author
            pipeline = [
                {"$match": match_query},
                {
                    "$group": {
                        "_id": "$author.username",
                        "total_karma": {"$first": {
                            "$add": [
                                {"$ifNull": ["$author.comment_karma", 0]},
                                {"$ifNull": ["$author.link_karma", 0]}
                            ]
                        }},
                        "account_created": {"$first": "$author.account_created_utc"},
                        "fake_count": {
                            "$sum": {
                                "$cond": [{"$eq": ["$prediction.label", "FAKE"]}, 1, 0]
                            }
                        },
                        "real_count": {
                            "$sum": {
                                "$cond": [{"$eq": ["$prediction.label", "REAL"]}, 1, 0]
                            }
                        }
                    }
                },
                {
                    "$match": {
                        "$expr": {
                            "$gte": [{"$add": ["$fake_count", "$real_count"]}, min_posts]
                        }
                    }
                }
            ]
            
            # PyMongo 4.10+ aggregate() is a coroutine, need to await it first
            cursor = await collection.aggregate(pipeline)
            result = await cursor.to_list(length=1000)
            
            # Calculate metrics
            author_data = []
            now = datetime.now()
            
            for item in result:
                fake_count = item["fake_count"]
                real_count = item["real_count"]
                total_posts = fake_count + real_count
                
                # Calculate account age
                account_age_days = None
                if item.get("account_created"):
                    age_delta = now - item["account_created"]
                    account_age_days = age_delta.days
                
                author_data.append({
                    "username": item["_id"],
                    "total_karma": item.get("total_karma", 0),
                    "fake_post_count": fake_count,
                    "real_post_count": real_count,
                    "total_post_count": total_posts,
                    "fake_ratio": round(fake_count / total_posts, 4) if total_posts > 0 else 0,
                    "account_age_days": account_age_days
                })
            
            # Sort by fake ratio descending
            author_data.sort(key=lambda x: x["fake_ratio"], reverse=True)
            
            return author_data
            
        except Exception as e:
            logger.error(f"Failed to get author credibility: {e}")
            return []