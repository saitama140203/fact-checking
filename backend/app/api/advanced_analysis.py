"""
Advanced Analysis API Router - Phân tích chuyên sâu fake news.

Endpoints:
1. Source Credibility - Đánh giá độ tin cậy nguồn tin
2. Trend Analysis - Phân tích xu hướng fake news
3. Content Analysis - Phân tích chi tiết bài viết
4. Comprehensive Report - Báo cáo tổng hợp
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.services.advanced_analysis_service import advanced_analysis, AdvancedAnalysisService
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/analysis", tags=["Advanced Analysis"])


# ========================
# SOURCE CREDIBILITY
# ========================

@router.get("/source/{domain}")
async def get_source_credibility(
    domain: str,
    min_posts: int = Query(5, ge=1, description="Số posts tối thiểu để đánh giá")
):
    """
    **Đánh giá độ tin cậy của một nguồn tin (domain).**
    
    Tính điểm credibility dựa trên:
    - Tỷ lệ fake news từ nguồn
    - Độ chắc chắn của model prediction
    - So sánh engagement giữa fake vs real posts
    
    **Returns:**
    - credibility_score: Điểm tin cậy (0-100)
    - risk_level: LOW, MEDIUM, HIGH, VERY_HIGH
    - breakdown: Chi tiết các thống kê
    - recommendation: Khuyến nghị sử dụng
    """
    import re
    
    # Validate domain format
    domain = domain.strip().lower()
    domain_pattern = re.compile(
        r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$'
    )
    
    if not domain_pattern.match(domain):
        raise HTTPException(
            status_code=400,
            detail="Invalid domain format. Please provide a valid domain name."
        )
    
    # Additional security: prevent path traversal attempts
    if ".." in domain or "/" in domain or "\\" in domain:
        raise HTTPException(
            status_code=400,
            detail="Invalid domain format. Path traversal not allowed."
        )
    try:
        result = await advanced_analysis.get_source_credibility_score(
            domain=domain,
            min_posts=min_posts
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in source credibility endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources/top-credible")
async def get_top_credible_sources(
    limit: int = Query(20, ge=1, le=100, description="Số lượng sources"),
    min_posts: int = Query(10, ge=1, description="Số posts tối thiểu")
):
    """
    **Lấy danh sách các nguồn tin đáng tin cậy nhất.**
    
    Sắp xếp theo điểm credibility từ cao xuống thấp.
    Chỉ bao gồm các nguồn có đủ số lượng posts để đánh giá.
    
    **Returns:**
    - List các sources với credibility_score và risk_level
    """
    try:
        sources = await advanced_analysis.get_top_credible_sources(
            limit=limit,
            min_posts=min_posts
        )
        
        return {
            "sources": sources,
            "total": len(sources),
            "min_posts_threshold": min_posts
        }
        
    except Exception as e:
        logger.error(f"Error getting top credible sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources/warning-list")
async def get_warning_sources(
    limit: int = Query(20, ge=1, le=100, description="Số lượng sources"),
    min_posts: int = Query(5, ge=1, description="Số posts tối thiểu")
):
    """
    **Lấy danh sách các nguồn tin có nhiều fake news nhất.**
    
    ⚠️ Warning list - Các nguồn cần cảnh giác.
    Sắp xếp theo tỷ lệ fake news từ cao xuống thấp.
    
    **Returns:**
    - List các sources với fake_percentage và warning_level
    """
    try:
        sources = await advanced_analysis.get_least_credible_sources(
            limit=limit,
            min_posts=min_posts
        )
        
        return {
            "warning_sources": sources,
            "total": len(sources),
            "disclaimer": "Đây là danh sách các nguồn có tỷ lệ fake news cao dựa trên phân tích AI. Nên kiểm chứng kỹ thông tin từ các nguồn này."
        }
        
    except Exception as e:
        logger.error(f"Error getting warning sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================
# TREND ANALYSIS
# ========================

@router.get("/trend")
async def get_fake_news_trend(
    days: int = Query(30, ge=1, le=365, description="Số ngày phân tích"),
    subreddit: Optional[str] = Query(None, description="Lọc theo subreddit")
):
    """
    **Phân tích xu hướng fake news.**
    
    So sánh giai đoạn hiện tại với giai đoạn trước đó.
    
    **Returns:**
    - trend: Hướng xu hướng (INCREASING, DECREASING, STABLE)
    - change_percentage: Phần trăm thay đổi
    - daily_data: Dữ liệu theo ngày
    - peak_day: Ngày có nhiều fake news nhất
    - interpretation: Giải thích xu hướng
    """
    try:
        trend = await advanced_analysis.get_fake_news_trend(
            days=days,
            subreddit=subreddit
        )
        
        if "error" in trend:
            raise HTTPException(status_code=500, detail=trend["error"])
        
        return trend
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in trend analysis endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending-topics")
async def get_trending_fake_topics(
    days: int = Query(7, ge=1, le=30, description="Số ngày phân tích"),
    top_n: int = Query(20, ge=5, le=50, description="Số keywords")
):
    """
    **Lấy các chủ đề fake news đang trending.**
    
    Phân tích keywords trong tiêu đề các bài fake news gần đây.
    Giúp nhận biết các chủ đề "hot" đang có nhiều thông tin sai lệch.
    
    **Returns:**
    - List keywords với frequency và sample_titles
    """
    try:
        topics = await advanced_analysis.get_trending_fake_topics(
            days=days,
            top_n=top_n
        )
        
        return {
            "trending_topics": topics,
            "total": len(topics),
            "period_days": days,
            "note": "Các chủ đề này đang có nhiều tin giả. Cần cẩn thận khi tiếp nhận thông tin."
        }
        
    except Exception as e:
        logger.error(f"Error getting trending fake topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================
# CONTENT ANALYSIS
# ========================

@router.get("/post/{post_id}")
async def analyze_post(post_id: str):
    """
    **Phân tích chi tiết một bài post.**
    
    Cung cấp đánh giá toàn diện về:
    - Prediction result và confidence
    - Risk indicators (dấu hiệu rủi ro)
    - Domain credibility
    - Similar posts
    - Recommendation
    
    **Returns:**
    - Comprehensive analysis của post
    """
    try:
        analysis = await advanced_analysis.analyze_post_content(post_id=post_id)
        
        if "error" in analysis and analysis["error"] == "Post not found":
            raise HTTPException(status_code=404, detail=f"Post {post_id} not found")
        
        if "error" in analysis:
            raise HTTPException(status_code=500, detail=analysis["error"])
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing post {post_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================
# REPORTS
# ========================

@router.get("/report")
async def get_comprehensive_report(
    days: int = Query(30, ge=7, le=365, description="Số ngày cho báo cáo")
):
    """
    **Tạo báo cáo tổng hợp về tình trạng fake news.**
    
    Báo cáo bao gồm:
    - Tổng quan thống kê
    - Phân tích xu hướng
    - Top nguồn tin cậy và warning list
    - Các chủ đề fake news trending
    - Khuyến nghị
    
    **Returns:**
    - Comprehensive report
    """
    try:
        report = await advanced_analysis.get_comprehensive_report(days=days)
        
        if "error" in report:
            raise HTTPException(status_code=500, detail=report["error"])
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk-assessment")
async def get_risk_assessment(
    subreddit: Optional[str] = Query(None, description="Lọc theo subreddit"),
    days: int = Query(7, ge=1, le=30, description="Số ngày đánh giá")
):
    """
    **Đánh giá rủi ro fake news tổng thể.**
    
    Cung cấp điểm đánh giá rủi ro dựa trên:
    - Tỷ lệ fake news hiện tại
    - Xu hướng thay đổi
    - Độ tin cậy các nguồn
    
    **Returns:**
    - risk_score: Điểm rủi ro (0-100)
    - risk_level: LOW, MEDIUM, HIGH, CRITICAL
    - contributing_factors: Các yếu tố đóng góp
    """
    try:
        # Get trend data
        trend = await advanced_analysis.get_fake_news_trend(days=days, subreddit=subreddit)
        
        if "error" in trend:
            raise HTTPException(status_code=500, detail=trend["error"])
        
        # Calculate risk score
        current_fake_percentage = trend.get("current_period", {}).get("fake_percentage", 0)
        change = trend.get("trend", {}).get("change_percentage", 0)
        
        # Base risk from fake percentage
        risk_score = current_fake_percentage
        
        # Add penalty for increasing trend
        if change > 0:
            risk_score += min(change * 0.5, 20)  # Max +20 for increasing trend
        
        risk_score = min(100, risk_score)
        
        # Determine risk level
        if risk_score < 20:
            risk_level = "LOW"
            color = "green"
        elif risk_score < 40:
            risk_level = "MEDIUM"
            color = "yellow"
        elif risk_score < 60:
            risk_level = "HIGH"
            color = "orange"
        else:
            risk_level = "CRITICAL"
            color = "red"
        
        return {
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "color": color,
            "period_days": days,
            "subreddit": subreddit or "all",
            "contributing_factors": [
                {
                    "factor": "Current fake news ratio",
                    "value": f"{current_fake_percentage}%",
                    "impact": "HIGH" if current_fake_percentage > 30 else "MEDIUM" if current_fake_percentage > 15 else "LOW"
                },
                {
                    "factor": "Trend direction",
                    "value": trend.get("trend", {}).get("direction"),
                    "impact": "HIGH" if change > 10 else "MEDIUM" if change > 0 else "LOW"
                },
                {
                    "factor": "Change percentage",
                    "value": f"{change}%",
                    "impact": "HIGH" if abs(change) > 20 else "MEDIUM" if abs(change) > 10 else "LOW"
                }
            ],
            "recommendation": AdvancedAnalysisService._get_risk_recommendation(risk_level),
            "evaluated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in risk assessment: {e}")
        raise HTTPException(status_code=500, detail=str(e))



