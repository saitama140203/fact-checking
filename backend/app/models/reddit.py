from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class Author(BaseModel):
    username: str = Field(..., description="Tên người dùng")
    account_created_utc: Optional[datetime] = Field(default=None, description="Ngày tạo tài khoản")
    comment_karma: Optional[int] = Field(default=None, description="Karma bình luận")
    link_karma: Optional[int] = Field(default=None, description="Karma bài đăng")
    has_verified_email: Optional[bool] = Field(default=None, description="Đã xác thực email")

class Subreddit(BaseModel):
    name: str = Field(..., description="Tên Subreddit (ví dụ: news)")
    subscribers: Optional[int] = Field(default=None, description="Số người theo dõi")
    description: Optional[str] = Field(default=None, description="Mô tả")

class RedditPost(BaseModel):
    """
    Model RedditPost - Optimized (không load comments để tăng tốc)
    """
    post_id: str = Field(..., description="ID của bài đăng")
    title: str = Field(..., description="Tiêu đề")
    selftext: Optional[str] = Field(default=None, description="Nội dung text")
    url: str = Field(..., description="URL")
    domain: str = Field(..., description="Tên miền")
    permalink: str = Field(..., description="Đường dẫn tới bài đăng")
    
    score: int = Field(..., description="Số điểm")
    upvote_ratio: float = Field(..., description="Tỷ lệ upvote")
    num_comments: int = Field(..., description="Số lượng comments")
    locked: bool = Field(..., description="Bài đăng có bị khóa không")
    over_18: bool = Field(..., description="Nội dung 18+")
    spoiler: bool = Field(..., description="Có spoiler không")
    created_utc: datetime = Field(..., description="Thời gian tạo")
    edited: bool = Field(..., description="Đã chỉnh sửa chưa")
    flair_text: Optional[str] = Field(default=None, description="Nhãn (flair)")
    
    author: Optional[Author] = Field(default=None, description="Tác giả")
    subreddit: Subreddit = Field(..., description="Subreddit")