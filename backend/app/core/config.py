"""
Application configuration management.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # MongoDB Configuration
    mongodb_atlas_uri: str
    mongodb_db_name: str = "fake_news_detector"
    
    # Reddit API Configuration
    reddit_client_id: str
    reddit_client_secret: str
    reddit_user_agent: str = "FakeNewsDetector/1.0"
    
    # HuggingFace Configuration
    huggingface_api_key: str
    huggingface_model: str = "hamzab/roberta-fake-news-classification"
    
    # Crawler Configuration
    subreddits: str = "news,worldnews,politics,technology,science"
    crawl_interval_minutes: int = 30
    posts_per_subreddit: int = 100
    
    # Historical Crawl Configuration (cho lần đầu tiên)
    initial_crawl_months: int = 5
    initial_crawl_limit: int = 500
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    
    @property
    def subreddit_list(self) -> List[str]:
        """Parse subreddits string into list."""
        return [s.strip() for s in self.subreddits.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()





