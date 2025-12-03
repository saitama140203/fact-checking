"""
API routes and endpoints.

Available routers:
- prediction: Fake news prediction endpoints
- analytics: Statistics and charts data
- crawler: Crawler management
- advanced_analysis: Advanced analysis and reports
- user_analysis: User-submitted content analysis
"""
from . import prediction
from . import analytics
from . import crawler
from . import advanced_analysis
from . import user_analysis

__all__ = ["prediction", "analytics", "crawler", "advanced_analysis", "user_analysis"]





