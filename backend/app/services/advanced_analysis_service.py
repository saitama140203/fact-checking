"""
Advanced Analysis Service - Phân tích chuyên sâu fake news.
Cung cấp các phân tích nâng cao về:
- Source credibility (độ tin cậy nguồn tin)
- Trend analysis (xu hướng fake news)
- Content analysis (phân tích nội dung)
- Risk assessment (đánh giá rủi ro)
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter
import re
import statistics

from app.core.database import mongodb
from app.core.logger import get_logger

logger = get_logger(__name__)


class AdvancedAnalysisService:
    """Service phân tích chuyên sâu fake news."""
    
    # ========================
    # SOURCE CREDIBILITY
    # ========================
    
    @staticmethod
    async def get_source_credibility_score(
        domain: str,
        min_posts: int = 5
    ) -> Dict[str, Any]:
        """
        Tính điểm độ tin cậy của một nguồn tin (domain).
        
        Scoring factors:
        - Fake ratio (tỷ lệ fake news)
        - Average confidence (độ chắc chắn của model)
        - Engagement ratio (tương tác thật vs fake)
        - Post volume (số lượng posts)
        
        Returns:
            Dict với credibility_score (0-100) và breakdown
        """
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            # Get all posts from this domain with predictions
            posts = await collection.find({
                "domain": domain,
                "prediction": {"$exists": True, "$ne": None}
            }).to_list(length=10000)
            
            if len(posts) < min_posts:
                return {
                    "domain": domain,
                    "credibility_score": None,
                    "message": f"Không đủ dữ liệu (cần ít nhất {min_posts} posts)",
                    "total_posts": len(posts)
                }
            
            # Calculate metrics
            fake_posts = [p for p in posts if p.get("prediction", {}).get("label") == "FAKE"]
            real_posts = [p for p in posts if p.get("prediction", {}).get("label") == "REAL"]
            
            fake_ratio = len(fake_posts) / len(posts) if posts else 0
            
            # Average confidence for fake news
            fake_confidences = [p.get("prediction", {}).get("confidence", 0) for p in fake_posts]
            avg_fake_confidence = statistics.mean(fake_confidences) if fake_confidences else 0
            
            # Engagement metrics
            fake_avg_score = statistics.mean([p.get("score", 0) for p in fake_posts]) if fake_posts else 0
            real_avg_score = statistics.mean([p.get("score", 0) for p in real_posts]) if real_posts else 0
            
            # Calculate credibility score (0-100, higher is more credible)
            # Formula: Base 100, subtract penalties for fake news
            credibility_score = 100
            
            # Penalty for fake ratio (max -50 points)
            credibility_score -= fake_ratio * 50
            
            # Penalty for high confidence fake news (max -20 points)
            credibility_score -= avg_fake_confidence * 20
            
            # Bonus for having mostly real news with high engagement
            if real_avg_score > fake_avg_score and len(real_posts) > len(fake_posts):
                credibility_score += 10
            
            # Clamp to 0-100
            credibility_score = max(0, min(100, credibility_score))
            
            # Risk level
            if credibility_score >= 80:
                risk_level = "LOW"
                risk_color = "green"
            elif credibility_score >= 60:
                risk_level = "MEDIUM"
                risk_color = "yellow"
            elif credibility_score >= 40:
                risk_level = "HIGH"
                risk_color = "orange"
            else:
                risk_level = "VERY_HIGH"
                risk_color = "red"
            
            return {
                "domain": domain,
                "credibility_score": round(credibility_score, 2),
                "risk_level": risk_level,
                "risk_color": risk_color,
                "breakdown": {
                    "total_posts": len(posts),
                    "fake_posts": len(fake_posts),
                    "real_posts": len(real_posts),
                    "fake_ratio": round(fake_ratio, 4),  # Ratio 0-1
                    "fake_percentage": round(fake_ratio * 100, 2),  # Percentage 0-100
                    "avg_fake_confidence": round(avg_fake_confidence * 100, 2),
                    "fake_avg_score": round(fake_avg_score, 2),
                    "real_avg_score": round(real_avg_score, 2)
                },
                "recommendation": AdvancedAnalysisService._get_source_recommendation(credibility_score)
            }
            
        except Exception as e:
            logger.error(f"Error calculating source credibility: {e}")
            return {"error": str(e), "domain": domain}
    
    @staticmethod
    def _get_source_recommendation(score: float) -> str:
        """Generate recommendation based on credibility score."""
        if score >= 80:
            return "Nguồn tin đáng tin cậy. Có thể tham khảo nhưng vẫn nên đối chiếu."
        elif score >= 60:
            return "Nguồn tin có độ tin cậy trung bình. Nên đối chiếu với nhiều nguồn khác."
        elif score >= 40:
            return "Nguồn tin có rủi ro cao. Cần kiểm chứng kỹ trước khi tin."
        else:
            return "Nguồn tin không đáng tin cậy. Khuyến nghị không sử dụng."
    
    @staticmethod
    async def get_top_credible_sources(
        limit: int = 20,
        min_posts: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Lấy danh sách các nguồn tin đáng tin cậy nhất.
        """
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            # Aggregate by domain
            pipeline = [
                {"$match": {"prediction": {"$exists": True, "$ne": None}}},
                {
                    "$group": {
                        "_id": "$domain",
                        "total": {"$sum": 1},
                        "fake_count": {
                            "$sum": {"$cond": [{"$eq": ["$prediction.label", "FAKE"]}, 1, 0]}
                        },
                        "real_count": {
                            "$sum": {"$cond": [{"$eq": ["$prediction.label", "REAL"]}, 1, 0]}
                        },
                        "avg_confidence": {"$avg": "$prediction.confidence"}
                    }
                },
                {"$match": {"total": {"$gte": min_posts}}},
                {"$addFields": {
                    "fake_ratio": {"$divide": ["$fake_count", "$total"]},
                    "credibility": {
                        "$subtract": [
                            100,
                            {"$multiply": [{"$divide": ["$fake_count", "$total"]}, 50]}
                        ]
                    }
                }},
                {"$sort": {"credibility": -1}},
                {"$limit": limit}
            ]
            
            # PyMongo 4.10+ aggregate() is a coroutine, need to await it first
            cursor = await collection.aggregate(pipeline)
            results = await cursor.to_list(length=limit)
            
            sources = []
            for item in results:
                credibility = item.get("credibility", 0)
                if credibility >= 80:
                    risk_level = "LOW"
                elif credibility >= 60:
                    risk_level = "MEDIUM"
                elif credibility >= 40:
                    risk_level = "HIGH"
                else:
                    risk_level = "VERY_HIGH"
                
                sources.append({
                    "domain": item["_id"],
                    "credibility_score": round(credibility, 2),
                    "risk_level": risk_level,
                    "risk_color": "green" if risk_level == "LOW" else "yellow" if risk_level == "MEDIUM" else "orange" if risk_level == "HIGH" else "red",
                    "breakdown": {
                        "total_posts": item["total"],
                        "fake_posts": item["fake_count"],
                        "real_posts": item["real_count"],
                        "fake_ratio": round(item["fake_ratio"], 4),  # Ratio 0-1
                        "fake_percentage": round(item["fake_ratio"] * 100, 2),  # Percentage 0-100
                        "avg_fake_confidence": 0,  # Not calculated in this endpoint
                        "fake_avg_score": 0,  # Not calculated in this endpoint
                        "real_avg_score": 0  # Not calculated in this endpoint
                    },
                    "recommendation": AdvancedAnalysisService._get_source_recommendation(credibility)
                })
            
            return sources
            
        except Exception as e:
            logger.error(f"Error getting top credible sources: {e}")
            return []
    
    @staticmethod
    async def get_least_credible_sources(
        limit: int = 20,
        min_posts: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Lấy danh sách các nguồn tin ít đáng tin cậy nhất (nhiều fake news nhất).
        """
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            pipeline = [
                {"$match": {"prediction": {"$exists": True, "$ne": None}}},
                {
                    "$group": {
                        "_id": "$domain",
                        "total": {"$sum": 1},
                        "fake_count": {
                            "$sum": {"$cond": [{"$eq": ["$prediction.label", "FAKE"]}, 1, 0]}
                        },
                        "avg_confidence": {"$avg": "$prediction.confidence"}
                    }
                },
                {"$match": {"total": {"$gte": min_posts}, "fake_count": {"$gte": 1}}},
                {"$addFields": {
                    "fake_ratio": {"$divide": ["$fake_count", "$total"]}
                }},
                {"$sort": {"fake_ratio": -1}},
                {"$limit": limit}
            ]
            
            # PyMongo 4.10+ aggregate() is a coroutine, need to await it first
            cursor = await collection.aggregate(pipeline)
            results = await cursor.to_list(length=limit)
            
            return [
                {
                    "domain": item["_id"],
                    "credibility_score": None,  # Not calculated for warning sources
                    "risk_level": "VERY_HIGH" if item["fake_ratio"] > 0.5 else "HIGH",
                    "risk_color": "red" if item["fake_ratio"] > 0.5 else "orange",
                    "breakdown": {
                        "total_posts": item["total"],
                        "fake_posts": item["fake_count"],
                        "real_posts": item["total"] - item["fake_count"],
                        "fake_ratio": round(item["fake_ratio"], 4),  # Ratio 0-1
                        "fake_percentage": round(item["fake_ratio"] * 100, 2),  # Percentage 0-100
                        "avg_fake_confidence": round(item.get("avg_confidence", 0) * 100, 2),
                        "fake_avg_score": 0,  # Not calculated in this endpoint
                        "real_avg_score": 0  # Not calculated in this endpoint
                    },
                    "recommendation": "⚠️ Nguồn này có tỷ lệ fake news cao. Cần kiểm chứng kỹ thông tin từ nguồn này."
                }
                for item in results
            ]
            
        except Exception as e:
            logger.error(f"Error getting least credible sources: {e}")
            return []
    
    # ========================
    # TREND ANALYSIS
    # ========================
    
    @staticmethod
    async def get_fake_news_trend(
        days: int = 30,
        subreddit: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Phân tích xu hướng fake news trong khoảng thời gian.
        
        Returns:
            - Trend direction (increasing/decreasing/stable)
            - Daily statistics
            - Peak days
            - Comparison with previous period
        """
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            prev_start_date = start_date - timedelta(days=days)
            
            # Normalize dates to start of day (00:00:00) for accurate date comparison
            # This fixes bug where date comparison fails when comparing datetime(YYYY-MM-DD 00:00:00)
            # with start_date that has time component (e.g., 23:52:03)
            start_date_normalized = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            prev_start_date_normalized = prev_start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # CRITICAL FIX: created_utc trong DB là STRING (do post.model_dump(mode="json"))
            # nhưng query dùng datetime object → MongoDB không match string với datetime!
            # Solution: Convert datetime query thành string ISO format để match với string trong DB
            prev_start_date_str = prev_start_date.isoformat()
            end_date_str = end_date.isoformat()
            
            # Build match query với string ISO format (match với string trong DB)
            match_query = {
                "prediction": {"$exists": True, "$ne": None},
                "created_utc": {"$gte": prev_start_date_str, "$lte": end_date_str}
            }
            
            if subreddit:
                match_query["subreddit.name"] = subreddit
            
            # Aggregate by date
            # Handle cả string và datetime: convert string → datetime trước khi format
            pipeline = [
                {"$match": match_query},
                {
                    "$addFields": {
                        # Convert created_utc từ string → datetime nếu cần
                        # Vì DB lưu string (do model_dump(mode="json")), cần convert để dùng $dateToString
                        "created_utc_datetime": {
                            "$cond": {
                                "if": {"$eq": [{"$type": "$created_utc"}, "string"]},
                                "then": {
                                    "$dateFromString": {
                                        "dateString": "$created_utc",
                                        "onError": None  # Nếu parse fail, return None (sẽ bị filter out)
                                    }
                                },
                                "else": "$created_utc"  # Đã là datetime rồi
                            }
                        }
                    }
                },
                {
                    "$match": {
                        "created_utc_datetime": {"$ne": None}  # Filter out những record parse datetime fail
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_utc_datetime"}},
                            "label": "$prediction.label"
                        },
                        "count": {"$sum": 1}
                    }
                },
                {"$sort": {"_id.date": 1}}
            ]
            
            # PyMongo 4.10+ aggregate() is a coroutine, need to await it first
            cursor = await collection.aggregate(pipeline)
            results = await cursor.to_list(length=10000)
            
            # Organize by date
            daily_data = {}
            for item in results:
                date = item["_id"]["date"]
                label = item["_id"]["label"]
                
                if date not in daily_data:
                    daily_data[date] = {"date": date, "fake": 0, "real": 0}
                
                if label == "FAKE":
                    daily_data[date]["fake"] = item["count"]
                else:
                    daily_data[date]["real"] = item["count"]
            
            # Split into current and previous periods
            current_period = []
            previous_period = []
            
            for date_str, data in sorted(daily_data.items()):
                date = datetime.strptime(date_str, "%Y-%m-%d")
                data["total"] = data["fake"] + data["real"]
                data["fake_percentage"] = round(
                    (data["fake"] / data["total"] * 100) if data["total"] > 0 else 0, 2
                )
                
                # Use normalized start_date for comparison to fix date boundary bug
                if date >= start_date_normalized:
                    current_period.append(data)
                else:
                    previous_period.append(data)
            
            # Calculate trends
            current_fake_total = sum(d["fake"] for d in current_period)
            current_total = sum(d["total"] for d in current_period)
            previous_fake_total = sum(d["fake"] for d in previous_period)
            previous_total = sum(d["total"] for d in previous_period)
            
            current_fake_ratio = current_fake_total / current_total if current_total > 0 else 0
            previous_fake_ratio = previous_fake_total / previous_total if previous_total > 0 else 0
            
            # Determine trend direction
            if previous_fake_ratio > 0:
                change_percentage = ((current_fake_ratio - previous_fake_ratio) / previous_fake_ratio) * 100
            else:
                change_percentage = 0
            
            if change_percentage > 5:
                trend_direction = "INCREASING"
                trend_emoji = "📈"
            elif change_percentage < -5:
                trend_direction = "DECREASING"
                trend_emoji = "📉"
            else:
                trend_direction = "STABLE"
                trend_emoji = "➡️"
            
            # Find peak day
            peak_day = max(current_period, key=lambda x: x["fake"]) if current_period else None
            
            # Calculate daily average
            daily_avg_fake = current_fake_total / len(current_period) if current_period else 0
            
            return {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "days": days
                },
                "trend": {
                    "direction": trend_direction,
                    "emoji": trend_emoji,
                    "change_percentage": round(change_percentage, 2),
                    "interpretation": AdvancedAnalysisService._interpret_trend(trend_direction, change_percentage)
                },
                "current_period": {
                    "total_posts": current_total,
                    "fake_posts": current_fake_total,
                    "real_posts": current_total - current_fake_total,
                    "fake_percentage": round(current_fake_ratio * 100, 2),
                    "daily_avg_fake": round(daily_avg_fake, 2)
                },
                "previous_period": {
                    "total_posts": previous_total,
                    "fake_posts": previous_fake_total,
                    "fake_percentage": round(previous_fake_ratio * 100, 2)
                },
                "peak_day": peak_day,
                "daily_data": current_period,
                "subreddit": subreddit
            }
            
        except Exception as e:
            logger.error(f"Error analyzing fake news trend: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _interpret_trend(direction: str, change: float) -> str:
        """Generate interpretation of trend."""
        if direction == "INCREASING":
            if change > 20:
                return "Tỷ lệ fake news tăng đáng báo động! Cần tăng cường kiểm chứng thông tin."
            else:
                return "Tỷ lệ fake news có xu hướng tăng nhẹ. Nên cảnh giác hơn."
        elif direction == "DECREASING":
            if change < -20:
                return "Tỷ lệ fake news giảm đáng kể. Môi trường thông tin đang cải thiện."
            else:
                return "Tỷ lệ fake news giảm nhẹ. Xu hướng tích cực."
        else:
            return "Tỷ lệ fake news ổn định. Tiếp tục theo dõi và kiểm chứng thông tin."
    
    @staticmethod
    async def get_trending_fake_topics(
        days: int = 7,
        top_n: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Lấy các chủ đề fake news đang trending.
        Phân tích keywords trong tiêu đề các bài fake news gần đây.
        """
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            start_date = datetime.now() - timedelta(days=days)
            
            posts = await collection.find({
                "prediction.label": "FAKE",
                "prediction.confidence": {"$gte": 0.7},
                "created_utc": {"$gte": start_date}
            }).to_list(length=1000)
            
            if not posts:
                return []
            
            # Extract and count keywords
            stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
                'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                'could', 'should', 'may', 'might', 'must', 'can', 'it', 'its', 'this',
                'that', 'these', 'those', 'i', 'you', 'he', 'she', 'we', 'they', 'what',
                'which', 'who', 'when', 'where', 'why', 'how', 'all', 'each', 'every',
                'says', 'said', 'new', 'just', 'after', 'before', 'video', 'news'
            }
            
            all_words = []
            for post in posts:
                title = post.get("title", "").lower()
                words = re.findall(r'\b[a-z]{4,}\b', title)
                words = [w for w in words if w not in stop_words]
                all_words.extend(words)
            
            word_counts = Counter(all_words)
            top_words = word_counts.most_common(top_n)
            
            return [
                {
                    "keyword": word,
                    "frequency": count,
                    "trending_score": round((count / len(posts)) * 100, 2),
                    "sample_titles": [
                        p["title"] for p in posts 
                        if word in p.get("title", "").lower()
                    ][:3]
                }
                for word, count in top_words
            ]
            
        except Exception as e:
            logger.error(f"Error getting trending fake topics: {e}")
            return []
    
    # ========================
    # CONTENT ANALYSIS
    # ========================
    
    @staticmethod
    async def analyze_post_content(
        post_id: str
    ) -> Dict[str, Any]:
        """
        Phân tích chi tiết nội dung của một post.
        
        Includes:
        - Prediction details
        - Title sentiment analysis
        - Source credibility
        - Similar fake news
        - Risk indicators
        """
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            post = await collection.find_one({"post_id": post_id})
            
            if not post:
                return {"error": "Post not found", "post_id": post_id}
            
            prediction = post.get("prediction", {})
            
            # Risk indicators
            risk_indicators = []
            
            # Check title for clickbait patterns
            title = post.get("title", "").lower()
            
            clickbait_patterns = [
                "shocking", "unbelievable", "you won't believe",
                "breaking", "urgent", "exclusive", "leaked",
                "secret", "hidden truth", "they don't want you to know"
            ]
            
            for pattern in clickbait_patterns:
                if pattern in title:
                    risk_indicators.append({
                        "type": "CLICKBAIT",
                        "pattern": pattern,
                        "severity": "MEDIUM"
                    })
            
            # Check for all caps
            caps_ratio = sum(1 for c in post.get("title", "") if c.isupper()) / len(post.get("title", "a"))
            if caps_ratio > 0.3:
                risk_indicators.append({
                    "type": "EXCESSIVE_CAPS",
                    "ratio": round(caps_ratio * 100, 2),
                    "severity": "LOW"
                })
            
            # Check domain credibility
            domain = post.get("domain", "")
            domain_credibility = await AdvancedAnalysisService.get_source_credibility_score(domain)
            
            if domain_credibility.get("credibility_score") and domain_credibility["credibility_score"] < 50:
                risk_indicators.append({
                    "type": "LOW_CREDIBILITY_SOURCE",
                    "domain": domain,
                    "score": domain_credibility["credibility_score"],
                    "severity": "HIGH"
                })
            
            # Find similar posts
            similar_posts = await collection.find({
                "prediction.label": prediction.get("label"),
                "post_id": {"$ne": post_id},
                "domain": domain
            }).limit(5).to_list(length=5)
            
            # Calculate overall risk score
            risk_score = 0
            if prediction.get("label") == "FAKE":
                risk_score += prediction.get("confidence", 0) * 50
            
            for indicator in risk_indicators:
                if indicator["severity"] == "HIGH":
                    risk_score += 20
                elif indicator["severity"] == "MEDIUM":
                    risk_score += 10
                else:
                    risk_score += 5
            
            risk_score = min(100, risk_score)
            
            return {
                "post_id": post_id,
                "title": post.get("title"),
                "url": post.get("url"),
                "domain": domain,
                "created_at": post.get("created_utc"),
                "prediction": {
                    "label": prediction.get("label"),
                    "confidence": prediction.get("confidence"),
                    "confidence_percentage": round(prediction.get("confidence", 0) * 100, 2),
                    "predicted_at": prediction.get("predicted_at")
                },
                "analysis": {
                    "risk_score": round(risk_score, 2),
                    "risk_level": AdvancedAnalysisService._get_risk_level(risk_score),
                    "risk_indicators": risk_indicators,
                    "domain_credibility": domain_credibility.get("credibility_score"),
                    "domain_risk_level": domain_credibility.get("risk_level")
                },
                "engagement": {
                    "score": post.get("score", 0),
                    "num_comments": post.get("num_comments", 0),
                    "upvote_ratio": post.get("upvote_ratio", 0)
                },
                "similar_posts": [
                    {
                        "post_id": p["post_id"],
                        "title": p["title"],
                        "prediction_label": p.get("prediction", {}).get("label")
                    }
                    for p in similar_posts
                ],
                "recommendation": AdvancedAnalysisService._get_content_recommendation(
                    prediction.get("label"), 
                    risk_score
                )
            }
            
        except Exception as e:
            logger.error(f"Error analyzing post content: {e}")
            return {"error": str(e), "post_id": post_id}
    
    @staticmethod
    def _get_risk_level(score: float) -> str:
        """Convert risk score to level."""
        if score < 20:
            return "LOW"
        elif score < 40:
            return "MEDIUM"
        elif score < 60:
            return "HIGH"
        else:
            return "CRITICAL"
    
    @staticmethod
    def _get_content_recommendation(label: str, risk_score: float) -> str:
        """Generate content-specific recommendation."""
        if label == "REAL" and risk_score < 30:
            return "Nội dung có vẻ đáng tin cậy. Vẫn nên đối chiếu với các nguồn khác."
        elif label == "REAL" and risk_score >= 30:
            return "Nội dung được phân loại là thật nhưng có một số dấu hiệu đáng nghi. Nên kiểm chứng kỹ."
        elif label == "FAKE" and risk_score < 50:
            return "Nội dung có khả năng là tin giả. Không nên chia sẻ trước khi xác minh."
        else:
            return "⚠️ Nội dung có rủi ro cao là tin giả. Khuyến nghị KHÔNG chia sẻ và cần kiểm chứng từ nhiều nguồn uy tín."
    
    @staticmethod
    def _get_risk_recommendation(risk_level: str) -> str:
        """Generate risk-based recommendation."""
        recommendations = {
            "LOW": "Môi trường thông tin an toàn. Tiếp tục thực hành kiểm chứng thông tin thường xuyên.",
            "MEDIUM": "Cần cẩn thận hơn khi tiếp nhận thông tin. Nên đối chiếu nhiều nguồn.",
            "HIGH": "Cảnh báo! Tỷ lệ fake news cao. Cần kiểm chứng kỹ mọi thông tin trước khi tin.",
            "CRITICAL": "⚠️ RỦI RO CAO! Môi trường thông tin có nhiều tin giả. Chỉ tin các nguồn đã được xác minh."
        }
        return recommendations.get(risk_level, "Tiếp tục theo dõi và kiểm chứng thông tin.")
    
    # ========================
    # STATISTICS & REPORTS
    # ========================
    
    @staticmethod
    async def get_comprehensive_report(
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Tạo báo cáo tổng hợp về tình trạng fake news.
        """
        try:
            collection = mongodb.get_collection("reddit_posts")
            
            start_date = datetime.now() - timedelta(days=days)
            
            # Basic stats
            pipeline = [
                {
                    "$match": {
                        "prediction": {"$exists": True, "$ne": None},
                        "created_utc": {"$gte": start_date}
                    }
                },
                {
                    "$group": {
                        "_id": "$prediction.label",
                        "count": {"$sum": 1},
                        "avg_confidence": {"$avg": "$prediction.confidence"},
                        "avg_score": {"$avg": "$score"},
                        "avg_comments": {"$avg": "$num_comments"}
                    }
                }
            ]
            
            # PyMongo 4.10+ aggregate() is a coroutine, need to await it first
            cursor = await collection.aggregate(pipeline)
            basic_stats = await cursor.to_list(length=10)
            
            # Parse stats
            stats = {"FAKE": {}, "REAL": {}}
            for item in basic_stats:
                label = item["_id"]
                if label in stats:
                    stats[label] = {
                        "count": item["count"],
                        "avg_confidence": round(item["avg_confidence"] * 100, 2),
                        "avg_score": round(item["avg_score"], 2),
                        "avg_comments": round(item["avg_comments"], 2)
                    }
            
            total = stats["FAKE"].get("count", 0) + stats["REAL"].get("count", 0)
            
            # Get top sources
            top_credible = await AdvancedAnalysisService.get_top_credible_sources(limit=5)
            least_credible = await AdvancedAnalysisService.get_least_credible_sources(limit=5)
            
            # Get trend
            trend = await AdvancedAnalysisService.get_fake_news_trend(days=days)
            
            # Get trending topics
            trending_topics = await AdvancedAnalysisService.get_trending_fake_topics(days=7, top_n=10)
            
            return {
                "report_period": {
                    "start": start_date.isoformat(),
                    "end": datetime.now().isoformat(),
                    "days": days
                },
                "summary": {
                    "total_analyzed": total,
                    "fake_news_count": stats["FAKE"].get("count", 0),
                    "real_news_count": stats["REAL"].get("count", 0),
                    "fake_percentage": round(
                        (stats["FAKE"].get("count", 0) / total * 100) if total > 0 else 0, 2
                    )
                },
                "fake_news_stats": stats["FAKE"],
                "real_news_stats": stats["REAL"],
                "trend_analysis": {
                    "direction": trend.get("trend", {}).get("direction"),
                    "change_percentage": trend.get("trend", {}).get("change_percentage"),
                    "interpretation": trend.get("trend", {}).get("interpretation")
                },
                "top_credible_sources": top_credible[:5],
                "warning_sources": least_credible[:5],
                "trending_fake_topics": trending_topics[:5],
                "recommendations": [
                    "Luôn kiểm chứng thông tin từ nhiều nguồn uy tín",
                    "Cẩn thận với các nguồn tin có tỷ lệ fake news cao",
                    "Chú ý các chủ đề đang có nhiều tin giả: " + ", ".join(
                        [t["keyword"] for t in trending_topics[:3]]
                    ) if trending_topics else "N/A"
                ],
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating comprehensive report: {e}")
            return {"error": str(e)}


# Global instance
advanced_analysis = AdvancedAnalysisService()

