"""
Analytics API Router - 10 endpoints cho visualization/charts.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta

from app.services.database_service import AnalyticsService
from app.models.analytics import (
    FakeVsRealResponse,
    TimelineResponse,
    TimelineDataPoint,
    SubredditResponse,
    SubredditStats,
    DomainResponse,
    DomainStats,
    EngagementResponse,
    EngagementStats,
    TimeDistributionResponse,
    TimeDistributionCell,
    KeywordsResponse,
    KeywordFrequency,
    ConfidenceDistributionResponse,
    ConfidenceBucket,
    FlairResponse,
    FlairStats,
    AuthorCredibilityResponse,
    AuthorCredibilityPoint
)
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Helper function để parse date string."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except:
        return None


@router.get("/fake-vs-real", response_model=FakeVsRealResponse)
async def get_fake_vs_real_distribution(
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Confidence tối thiểu"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    subreddit: Optional[str] = Query(None, description="Filter by subreddit")
):
    """
    **Chart 1: Pie Chart - Fake vs Real Distribution**
    
    Thống kê tổng quan số lượng fake news vs real news.
    
    **Returns:**
    - fake_count: Số lượng fake news
    - real_count: Số lượng real news
    - total_count: Tổng số posts
    - fake_percentage: Phần trăm fake news
    - real_percentage: Phần trăm real news
    """
    try:
        start = parse_date(start_date)
        end = parse_date(end_date)
        
        stats = await AnalyticsService.get_fake_vs_real_stats(
            min_confidence=min_confidence,
            start_date=start,
            end_date=end,
            subreddit=subreddit
        )
        
        return FakeVsRealResponse(**stats)
        
    except Exception as e:
        logger.error(f"Error in fake-vs-real endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline")
async def get_timeline_distribution(
    granularity: str = Query("daily", description="Độ chi tiết: daily, weekly, monthly"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    subreddit: Optional[str] = Query(None, description="Filter by subreddit")
):
    """
    **Chart 2: Line Chart - Fake News Timeline**
    
    Phân bố fake news theo thời gian (daily/weekly/monthly).
    
    **Returns:**
    - data: List các time points với fake_count, real_count, total_count
    - granularity: Độ chi tiết (daily/weekly/monthly)
    - start_date, end_date: Range của dữ liệu
    """
    try:
        # Validate granularity
        if granularity not in ["daily", "weekly", "monthly"]:
            raise HTTPException(
                status_code=400,
                detail="Granularity must be 'daily', 'weekly', or 'monthly'"
            )
        
        start = parse_date(start_date)
        end = parse_date(end_date)
        
        timeline_data = await AnalyticsService.get_timeline_data(
            granularity=granularity,
            min_confidence=min_confidence,
            start_date=start,
            end_date=end,
            subreddit=subreddit
        )
        
        # Determine actual date range from data
        actual_start = timeline_data[0]["date"] if timeline_data else "N/A"
        actual_end = timeline_data[-1]["date"] if timeline_data else "N/A"
        
        return {
            "data": timeline_data,
            "granularity": granularity,
            "start_date": actual_start,
            "end_date": actual_end
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in timeline endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-subreddit")
async def get_subreddit_distribution(
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """
    **Chart 3: Bar Chart - Fake News by Subreddit**
    
    Thống kê fake news theo từng subreddit.
    
    **Returns:**
    - data: List các subreddits với fake_count, real_count, fake_percentage
    - total_subreddits: Tổng số subreddits
    """
    try:
        start = parse_date(start_date)
        end = parse_date(end_date)
        
        subreddit_data = await AnalyticsService.get_subreddit_stats(
            min_confidence=min_confidence,
            start_date=start,
            end_date=end
        )
        
        return {
            "data": subreddit_data,
            "total_subreddits": len(subreddit_data)
        }
        
    except Exception as e:
        logger.error(f"Error in by-subreddit endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-domain")
async def get_domain_distribution(
    top_n: int = Query(20, ge=1, le=100, description="Top N domains"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    subreddit: Optional[str] = Query(None)
):
    """
    **Chart 4: Bar Chart - Top Domains with Fake News**
    
    Top domains có nhiều fake news nhất.
    
    **Returns:**
    - data: List top domains với fake_count, real_count, fake_percentage
    - total_domains: Tổng số domains unique
    """
    try:
        start = parse_date(start_date)
        end = parse_date(end_date)
        
        domain_data = await AnalyticsService.get_domain_stats(
            top_n=top_n,
            min_confidence=min_confidence,
            start_date=start,
            end_date=end,
            subreddit=subreddit
        )
        
        return {
            "data": domain_data,
            "total_domains": len(domain_data)
        }
        
    except Exception as e:
        logger.error(f"Error in by-domain endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/engagement-comparison")
async def get_engagement_comparison(
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    subreddit: Optional[str] = Query(None)
):
    """
    **Chart 5: Comparison Chart - Engagement Metrics (Fake vs Real)**
    
    So sánh engagement metrics (score, comments, upvote_ratio) giữa fake và real news.
    
    **Returns:**
    - fake_stats: Statistics cho fake news
    - real_stats: Statistics cho real news
    """
    try:
        start = parse_date(start_date)
        end = parse_date(end_date)
        
        engagement_data = await AnalyticsService.get_engagement_comparison(
            min_confidence=min_confidence,
            start_date=start,
            end_date=end,
            subreddit=subreddit
        )
        
        return engagement_data
        
    except Exception as e:
        logger.error(f"Error in engagement-comparison endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/time-distribution")
async def get_time_distribution(
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    subreddit: Optional[str] = Query(None)
):
    """
    **Chart 6: Heatmap - Time Distribution**
    
    Phân bố fake news theo giờ trong ngày và ngày trong tuần (heatmap).
    
    **Returns:**
    - data: List cells với hour (0-23), day_of_week (0-6), fake_count, real_count
    - total_posts: Tổng số posts
    """
    try:
        start = parse_date(start_date)
        end = parse_date(end_date)
        
        time_dist_data = await AnalyticsService.get_time_distribution(
            min_confidence=min_confidence,
            start_date=start,
            end_date=end,
            subreddit=subreddit
        )
        
        total = sum(cell["total_count"] for cell in time_dist_data)
        
        return {
            "data": time_dist_data,
            "total_posts": total
        }
        
    except Exception as e:
        logger.error(f"Error in time-distribution endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keywords")
async def get_keywords_frequency(
    top_n: int = Query(50, ge=10, le=200, description="Top N keywords"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    subreddit: Optional[str] = Query(None)
):
    """
    **Chart 7: Word Cloud Data - Keywords Frequency**
    
    Top keywords trong fake news vs real news (word cloud data).
    
    **Returns:**
    - fake_keywords: List top keywords trong fake news
    - real_keywords: List top keywords trong real news
    - top_n: Số lượng keywords
    """
    try:
        start = parse_date(start_date)
        end = parse_date(end_date)
        
        keywords_data = await AnalyticsService.get_keywords_frequency(
            top_n=top_n,
            min_confidence=min_confidence,
            start_date=start,
            end_date=end,
            subreddit=subreddit
        )
        
        return {
            **keywords_data,
            "top_n": top_n
        }
        
    except Exception as e:
        logger.error(f"Error in keywords endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/confidence-distribution")
async def get_confidence_distribution(
    bucket_size: float = Query(0.1, ge=0.01, le=0.5, description="Bucket size"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    subreddit: Optional[str] = Query(None)
):
    """
    **Chart 8: Histogram - Confidence Score Distribution**
    
    Phân bố confidence scores của predictions (histogram).
    
    **Returns:**
    - data: List buckets với range_start, range_end, fake_count, real_count
    - bucket_size: Kích thước mỗi bucket
    """
    try:
        start = parse_date(start_date)
        end = parse_date(end_date)
        
        confidence_data = await AnalyticsService.get_confidence_distribution(
            bucket_size=bucket_size,
            min_confidence=min_confidence,
            start_date=start,
            end_date=end,
            subreddit=subreddit
        )
        
        return {
            "data": confidence_data,
            "bucket_size": bucket_size
        }
        
    except Exception as e:
        logger.error(f"Error in confidence-distribution endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-flair")
async def get_flair_distribution(
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    subreddit: Optional[str] = Query(None)
):
    """
    **Chart 9: Pie Chart - Fake News by Flair**
    
    Phân bố fake news theo flair/tag.
    
    **Returns:**
    - data: List flairs với fake_count, real_count, fake_percentage
    - total_flairs: Tổng số flairs unique
    """
    try:
        start = parse_date(start_date)
        end = parse_date(end_date)
        
        flair_data = await AnalyticsService.get_flair_stats(
            min_confidence=min_confidence,
            start_date=start,
            end_date=end,
            subreddit=subreddit
        )
        
        return {
            "data": flair_data,
            "total_flairs": len(flair_data)
        }
        
    except Exception as e:
        logger.error(f"Error in by-flair endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/author-credibility")
async def get_author_credibility(
    min_posts: int = Query(2, ge=1, description="Số posts tối thiểu"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    subreddit: Optional[str] = Query(None)
):
    """
    **Chart 10: Scatter Plot - Author Credibility**
    
    Phân tích credibility của tác giả (karma vs fake post ratio).
    
    **Returns:**
    - data: List authors với total_karma, fake_ratio, account_age
    - total_authors: Tổng số authors
    """
    try:
        start = parse_date(start_date)
        end = parse_date(end_date)
        
        author_data = await AnalyticsService.get_author_credibility(
            min_posts=min_posts,
            min_confidence=min_confidence,
            start_date=start,
            end_date=end,
            subreddit=subreddit
        )
        
        return {
            "data": author_data,
            "total_authors": len(author_data)
        }
        
    except Exception as e:
        logger.error(f"Error in author-credibility endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_analytics_summary(
    min_confidence: float = Query(0.5, ge=0.0, le=1.0)
):
    """
    **Bonus Endpoint: Analytics Summary**
    
    Tóm tắt tất cả analytics metrics trong một endpoint.
    Useful cho dashboard overview.
    """
    try:
        # Get basic stats
        fake_vs_real = await AnalyticsService.get_fake_vs_real_stats(
            min_confidence=min_confidence
        )
        
        # Get subreddit stats
        subreddit_stats = await AnalyticsService.get_subreddit_stats(
            min_confidence=min_confidence
        )
        
        # Get top domain
        domain_stats = await AnalyticsService.get_domain_stats(
            top_n=5,
            min_confidence=min_confidence
        )
        
        # Get engagement comparison
        engagement = await AnalyticsService.get_engagement_comparison(
            min_confidence=min_confidence
        )
        
        return {
            "overview": fake_vs_real,
            "top_subreddits": subreddit_stats[:5] if subreddit_stats else [],
            "top_domains": domain_stats[:5] if domain_stats else [],
            "engagement": engagement,
            "min_confidence": min_confidence
        }
        
    except Exception as e:
        logger.error(f"Error in analytics summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

