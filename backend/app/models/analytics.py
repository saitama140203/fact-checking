"""
Pydantic models cho Analytics API responses.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime


# ========================
# Base Response Models
# ========================

class FakeVsRealResponse(BaseModel):
    """Response cho pie chart fake vs real."""
    fake_count: int = Field(..., description="Số lượng fake news")
    real_count: int = Field(..., description="Số lượng real news")
    total_count: int = Field(..., description="Tổng số bài posts")
    fake_percentage: float = Field(..., description="Phần trăm fake news")
    real_percentage: float = Field(..., description="Phần trăm real news")


class TimelineDataPoint(BaseModel):
    """Một điểm dữ liệu trên timeline."""
    date: str = Field(..., description="Ngày (format: YYYY-MM-DD)")
    fake_count: int = Field(..., description="Số fake news")
    real_count: int = Field(..., description="Số real news")
    total_count: int = Field(..., description="Tổng số posts")


class TimelineResponse(BaseModel):
    """Response cho line chart timeline."""
    data: List[TimelineDataPoint] = Field(..., description="Dữ liệu timeline")
    granularity: str = Field(..., description="Độ chi tiết: daily, weekly, monthly")
    start_date: str = Field(..., description="Ngày bắt đầu")
    end_date: str = Field(..., description="Ngày kết thúc")


class SubredditStats(BaseModel):
    """Thống kê fake news theo subreddit."""
    subreddit: str = Field(..., description="Tên subreddit")
    fake_count: int = Field(..., description="Số fake news")
    real_count: int = Field(..., description="Số real news")
    total_count: int = Field(..., description="Tổng số posts")
    fake_percentage: float = Field(..., description="Phần trăm fake news")


class SubredditResponse(BaseModel):
    """Response cho bar chart theo subreddit."""
    data: List[SubredditStats] = Field(..., description="Thống kê từng subreddit")
    total_subreddits: int = Field(..., description="Tổng số subreddits")


class DomainStats(BaseModel):
    """Thống kê fake news theo domain."""
    domain: str = Field(..., description="Tên miền")
    fake_count: int = Field(..., description="Số fake news")
    real_count: int = Field(..., description="Số real news")
    total_count: int = Field(..., description="Tổng số posts")
    fake_percentage: float = Field(..., description="Phần trăm fake news")


class DomainResponse(BaseModel):
    """Response cho bar chart theo domain."""
    data: List[DomainStats] = Field(..., description="Top domains")
    total_domains: int = Field(..., description="Tổng số domains")


class EngagementStats(BaseModel):
    """Thống kê engagement metrics."""
    label: str = Field(..., description="FAKE hoặc REAL")
    avg_score: float = Field(..., description="Điểm trung bình")
    avg_comments: float = Field(..., description="Số comments trung bình")
    avg_upvote_ratio: float = Field(..., description="Tỷ lệ upvote trung bình")
    median_score: float = Field(..., description="Điểm trung vị")
    median_comments: float = Field(..., description="Số comments trung vị")
    total_posts: int = Field(..., description="Tổng số posts")


class EngagementResponse(BaseModel):
    """Response cho comparison chart engagement."""
    fake_stats: EngagementStats = Field(..., description="Stats cho fake news")
    real_stats: EngagementStats = Field(..., description="Stats cho real news")


class TimeDistributionCell(BaseModel):
    """Một cell trong heatmap."""
    hour: int = Field(..., description="Giờ trong ngày (0-23)")
    day_of_week: int = Field(..., description="Ngày trong tuần (0=Monday, 6=Sunday)")
    day_name: str = Field(..., description="Tên ngày (Monday, Tuesday, ...)")
    fake_count: int = Field(..., description="Số fake news")
    real_count: int = Field(..., description="Số real news")
    total_count: int = Field(..., description="Tổng số posts")


class TimeDistributionResponse(BaseModel):
    """Response cho heatmap phân bố theo thời gian."""
    data: List[TimeDistributionCell] = Field(..., description="Dữ liệu heatmap")
    total_posts: int = Field(..., description="Tổng số posts")


class KeywordFrequency(BaseModel):
    """Tần suất từ khóa."""
    word: str = Field(..., description="Từ khóa")
    frequency: int = Field(..., description="Số lần xuất hiện")
    percentage: float = Field(..., description="Phần trăm trong nhóm")


class KeywordsResponse(BaseModel):
    """Response cho word frequency data."""
    fake_keywords: List[KeywordFrequency] = Field(..., description="Top keywords trong fake news")
    real_keywords: List[KeywordFrequency] = Field(..., description="Top keywords trong real news")
    top_n: int = Field(..., description="Số lượng keywords trả về")


class ConfidenceBucket(BaseModel):
    """Một bucket trong histogram confidence."""
    range_start: float = Field(..., description="Giá trị bắt đầu của bucket")
    range_end: float = Field(..., description="Giá trị kết thúc của bucket")
    fake_count: int = Field(..., description="Số fake news trong bucket")
    real_count: int = Field(..., description="Số real news trong bucket")
    total_count: int = Field(..., description="Tổng số posts trong bucket")


class ConfidenceDistributionResponse(BaseModel):
    """Response cho histogram confidence score."""
    data: List[ConfidenceBucket] = Field(..., description="Các buckets")
    bucket_size: float = Field(..., description="Kích thước mỗi bucket (0.1 = 10%)")


class FlairStats(BaseModel):
    """Thống kê theo flair."""
    flair: Optional[str] = Field(..., description="Tên flair (None nếu không có)")
    fake_count: int = Field(..., description="Số fake news")
    real_count: int = Field(..., description="Số real news")
    total_count: int = Field(..., description="Tổng số posts")
    fake_percentage: float = Field(..., description="Phần trăm fake news")


class FlairResponse(BaseModel):
    """Response cho pie chart theo flair."""
    data: List[FlairStats] = Field(..., description="Thống kê từng flair")
    total_flairs: int = Field(..., description="Tổng số flairs")


class AuthorCredibilityPoint(BaseModel):
    """Một điểm dữ liệu cho scatter plot."""
    username: str = Field(..., description="Tên tác giả")
    total_karma: int = Field(..., description="Tổng karma (comment + link)")
    fake_post_count: int = Field(..., description="Số fake posts")
    real_post_count: int = Field(..., description="Số real posts")
    total_post_count: int = Field(..., description="Tổng số posts")
    fake_ratio: float = Field(..., description="Tỷ lệ fake posts (0-1)")
    account_age_days: Optional[int] = Field(default=None, description="Tuổi tài khoản (ngày)")


class AuthorCredibilityResponse(BaseModel):
    """Response cho scatter plot author credibility."""
    data: List[AuthorCredibilityPoint] = Field(..., description="Dữ liệu các tác giả")
    total_authors: int = Field(..., description="Tổng số tác giả")


# ========================
# Filter/Query Parameters
# ========================

class AnalyticsFilter(BaseModel):
    """Base filter parameters cho analytics."""
    start_date: Optional[datetime] = Field(default=None, description="Ngày bắt đầu")
    end_date: Optional[datetime] = Field(default=None, description="Ngày kết thúc")
    subreddit: Optional[str] = Field(default=None, description="Lọc theo subreddit")
    min_confidence: Optional[float] = Field(default=0.5, description="Confidence tối thiểu")

