"""
Application configuration management.
Supports both development and production environments.
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional, Any
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ========================
    # MongoDB Configuration
    # ========================
    mongodb_atlas_uri: str
    mongodb_db_name: str = "fake_news_detector"
    
    # ========================
    # Reddit API Configuration
    # ========================
    reddit_client_id: str
    reddit_client_secret: str
    reddit_user_agent: str = "FakeNewsDetector/2.0"
    
    # ========================
    # HuggingFace Configuration
    # ========================
    huggingface_api_key: str = os.getenv("HUGGINGFACE_API_KEY")
    huggingface_model: str = "Pulk17/Fake-News-Detection"
    huggingface_api_base_url: Optional[str] = None
    # ========================
    # LLM Configuration (DeepSeek – replaces legacy Gemini)
    # ========================
    # New fields for DeepSeek; ai_studio_api_key kept for backwards compatibility
    DEEPSEEK_API_KEY : Optional[str] = os.getenv("DEEPSEEK_API_KEY")
    deepseek_model: str = "deepseek-chat"
    # Legacy Gemini fields (no longer used but kept to avoid breaking existing envs)
    ai_studio_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash-exp"
    
    # ========================
    # Model Configuration
    # ========================
    use_local_hf_model: bool = True  # True = local model, False = API
    hf_model_device: str = "cuda"  # "cuda" hoặc "cpu"
    
    # ========================
    # Crawler Configuration
    # ========================
    enable_crawler: bool = False  # Tắt/bật crawler scheduler
    subreddits: str = "news,worldnews,politics,technology,science"
    crawl_interval_minutes: int = 30
    posts_per_subreddit: int = 100
    
    # Historical Crawl Configuration (cho lần đầu tiên)
    initial_crawl_months: int = 5
    initial_crawl_limit: int = 500
    
    # ========================
    # API Configuration
    # ========================
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    
    # ========================
    # Production Configuration
    # ========================
    environment: str = "development"
    debug: bool = True
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    
    @field_validator('debug', mode='before')
    @classmethod
    def parse_debug(cls, v: Any) -> bool:
        """Parse debug value, handling non-boolean strings."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower in ('true', '1', 'yes', 'on'):
                return True
            elif v_lower in ('false', '0', 'no', 'off', 'warn', 'warning', 'info', 'error'):
                return False
        return False
    
    # SSL/TLS Configuration (for production)
    ssl_allow_invalid_certs: bool = False
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds
    
    # Cache Configuration
    cache_ttl_seconds: int = 300  # 5 minutes

    # Gemini Usage Optimization
    enable_gemini_in_background: bool = False
    
    @property
    def subreddit_list(self) -> List[str]:
        """Parse subreddits string into list."""
        return [s.strip() for s in self.subreddits.split(",")]
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() == "development"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
settings = Settings()





