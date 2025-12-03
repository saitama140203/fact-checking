"""
Automated crawler pipeline với incremental crawling.
Pipeline tự động: Crawl từ Reddit → Insert trực tiếp vào MongoDB (không qua JSON).
Sử dụng PyMongo Async API (native asyncio, không dùng Motor).
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.core.config import settings
from app.core.logger import get_logger
from app.services.crawler import RedditCrawler
from app.services.database_service import RedditPostService, CrawlMetadataService, PredictionService
from app.services.fake_news_service import fake_news_detector
from app.services.enhanced_prediction_service import enhanced_prediction_service
from app.models.reddit import RedditPost

logger = get_logger(__name__)

class CrawlerPipeline:
    """Pipeline tự động crawl + save vào database"""
    
    def __init__(self):
        self.crawler = RedditCrawler()
        self.is_running = False
    
    async def run_incremental_crawl(self) -> Dict[str, Any]:
        """
        Chạy incremental crawl cho tất cả subreddits
        
        Returns:
            Dict với thống kê crawl
        """
        if self.is_running:
            logger.warning("⚠️  Crawl already running, skipping...")
            return {"status": "skipped", "reason": "already_running"}
        
        self.is_running = True
        start_time = datetime.now()
        
        try:
            logger.info("=" * 80)
            logger.info("🚀 STARTING INCREMENTAL CRAWL PIPELINE")
            logger.info("=" * 80)
            
            all_stats = {
                "start_time": start_time,
                "subreddits": {},
                "total_crawled": 0,
                "total_inserted": 0,
                "total_duplicates": 0,
                "total_errors": 0
            }
            
            # Crawl từng subreddit
            for subreddit_name in settings.subreddit_list:
                try:
                    logger.info(f"\n📡 Processing r/{subreddit_name}...")
                    
                    # 1. Lấy thời gian crawl lần trước
                    last_crawl_time = await CrawlMetadataService.get_last_crawl_time(subreddit_name)
                    
                    if last_crawl_time:
                        # ========================================
                        # INCREMENTAL CRAWL (Đã có data)
                        # ========================================
                        logger.info(f"   Last crawl: {last_crawl_time}")
                        time_diff = datetime.now() - last_crawl_time
                        minutes_back = int(time_diff.total_seconds() / 60) + 5
                        
                        logger.info(f"   Incremental crawl from last {minutes_back} minutes")
                        
                        # Crawl posts mới
                        posts = await self.crawler.crawl_for_analysis(
                            subreddit=subreddit_name,
                            limit=settings.posts_per_subreddit
                        )
                        
                        # Filter posts theo thời gian
                        filtered_posts = [
                            post for post in posts 
                            if post.created_utc > last_crawl_time
                        ]
                        logger.info(f"   Filtered: {len(filtered_posts)}/{len(posts)} new posts")
                        posts = filtered_posts
                        
                    else:
                        # ========================================
                        # FIRST TIME - HISTORICAL CRAWL (5 THÁNG)
                        # ========================================
                        logger.info(f"   🎯 First time crawling r/{subreddit_name}")
                        logger.info(f"   📅 Fetching historical data from last 5 months...")
                        
                        # Crawl historical data
                        posts = await self.crawler.crawl_historical(
                            subreddit=subreddit_name,
                            months_back=settings.initial_crawl_months,
                            limit_total=settings.initial_crawl_limit
                        )
                        
                        logger.info(f"   ✅ Found {len(posts)} posts from last {settings.initial_crawl_months} months")
                    
                    # 3. Save trực tiếp vào database (async)
                    if posts:
                        insert_stats = await RedditPostService.insert_posts_batch(posts)

                        # Đảm bảo có stats entry cho subreddit hiện tại
                        if subreddit_name not in all_stats["subreddits"]:
                            all_stats["subreddits"][subreddit_name] = {}

                        # 4. Auto-predict newly inserted posts
                        if insert_stats["inserted"] > 0:
                            logger.info(
                                f"   🔍 Auto-predicting {insert_stats['inserted']} new posts "
                                f"({'Enhanced HF + Gemini' if settings.enable_gemini_in_background else 'HF-only'})..."
                            )

                            predicted_count = 0
                            fake_detected = 0

                            try:
                                # Lọc các post vừa insert (chưa có prediction)
                                newly_inserted = [
                                    post for post in posts
                                    if not hasattr(post, 'prediction') or post.prediction is None
                                ][:insert_stats["inserted"]]

                                for post in newly_inserted:
                                    post_dict = post.model_dump()

                                    try:
                                        if settings.enable_gemini_in_background:
                                            # Workflow đầy đủ (HF + Gemini) – CHỈ khi được bật rõ ràng
                                            enhanced_result = await enhanced_prediction_service.analyze_post(post_dict)
                                            if not enhanced_result:
                                                logger.warning(
                                                    f"   ⚠️  Enhanced prediction failed for post {post.post_id}, skipping..."
                                                )
                                                continue
                                            prediction = enhanced_prediction_service.format_for_database(enhanced_result)
                                        else:
                                            # Mặc định: dùng HuggingFace-only để tránh tốn quota Gemini
                                            prediction = await fake_news_detector.predict_post(post_dict)
                                            if not prediction:
                                                logger.warning(
                                                    f"   ⚠️  HF prediction failed for post {post.post_id}, skipping..."
                                                )
                                                continue

                                        # Lưu prediction vào DB
                                        await PredictionService.update_post_prediction(post.post_id, prediction)
                                        predicted_count += 1

                                        label = prediction.get("label") or prediction.get("label".upper(), "")
                                        if isinstance(label, str) and label.upper() == "FAKE":
                                            fake_detected += 1

                                    except Exception as e:
                                        logger.error(f"   ❌ Error predicting post {post.post_id}: {e}")
                                        continue

                                    # Rate limiting:
                                    # - Nếu có Gemini: giữ delay 5s như cũ để tôn trọng quota free-tier.
                                    # - Nếu chỉ HF: delay nhẹ để tránh spam API bên ngoài.
                                    if settings.enable_gemini_in_background:
                                        await asyncio.sleep(5.0)
                                    else:
                                        await asyncio.sleep(0.1)

                                logger.info(
                                    f"   ✅ Predicted {predicted_count} posts "
                                    f"({'Enhanced' if settings.enable_gemini_in_background else 'HF-only'}), "
                                    f"detected {fake_detected} fake news"
                                )

                                all_stats["subreddits"][subreddit_name]["predicted"] = predicted_count
                                all_stats["subreddits"][subreddit_name]["fake_detected"] = fake_detected

                            except Exception as e:
                                logger.error(f"   ❌ Auto-prediction failed: {e}", exc_info=True)
                                all_stats["subreddits"][subreddit_name]["prediction_error"] = str(e)

                        # 5. Update last_crawl_time
                        await CrawlMetadataService.update_last_crawl_time(
                            subreddit_name,
                            datetime.now()
                        )

                        # Thống kê
                        all_stats["subreddits"][subreddit_name].update({
                            "crawled": len(posts),
                            "inserted": insert_stats["inserted"],
                            "duplicates": insert_stats["duplicates"],
                            "errors": insert_stats["errors"]
                        })

                        all_stats["total_crawled"] += len(posts)
                        all_stats["total_inserted"] += insert_stats["inserted"]
                        all_stats["total_duplicates"] += insert_stats["duplicates"]
                        all_stats["total_errors"] += insert_stats["errors"]

                        logger.info(
                            f"   ✅ Inserted: {insert_stats['inserted']}, "
                            f"Duplicates: {insert_stats['duplicates']}, "
                            f"Errors: {insert_stats['errors']}"
                        )
                    else:
                        logger.info(f"   ℹ️  No new posts found")
                        all_stats["subreddits"][subreddit_name] = {
                            "crawled": 0,
                            "inserted": 0,
                            "duplicates": 0,
                            "errors": 0
                        }
                    
                    # Rate limiting giữa các subreddit
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ Error processing r/{subreddit_name}: {e}")
                    all_stats["subreddits"][subreddit_name] = {"error": str(e)}
                    continue
            
            # Kết thúc
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            all_stats["end_time"] = end_time
            all_stats["duration_seconds"] = duration
            all_stats["status"] = "completed"
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ CRAWL PIPELINE COMPLETED")
            logger.info(f"   Duration: {duration:.2f}s")
            logger.info(f"   Total crawled: {all_stats['total_crawled']}")
            logger.info(f"   Total inserted: {all_stats['total_inserted']}")
            logger.info(f"   Total duplicates: {all_stats['total_duplicates']}")
            total_in_db = await RedditPostService.get_total_posts()
            logger.info(f"   Total in DB: {total_in_db}")
            logger.info("=" * 80 + "\n")
            
            return all_stats
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "start_time": start_time
            }
        finally:
            self.is_running = False
    
    async def cleanup(self):
        """Dọn dẹp resources"""
        await self.crawler.close()