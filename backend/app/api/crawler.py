from fastapi import APIRouter
from app.services.crawler import RedditCrawler

router = APIRouter()

@router.get("/crawl")
async def crawl():
    crawler = RedditCrawler()
    return await crawler.crawl()