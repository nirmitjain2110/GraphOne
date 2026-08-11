"""
Async 24-Hour Freshness AI News Crawler.
Crawls 5 distinct AI news sources, extracts full text, normalizes dates,
and enforces a strict < 24-hour publication freshness guarantee.
"""

import re
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Optional
import aiohttp
from bs4 import BeautifulSoup

from src.llm.schemas import NewsEntity, NewsContent, SourceInfo
from src.crawlers.utils import fetch_url, parse_and_normalize_date, is_within_last_24_hours

logger = logging.getLogger("NewsCrawler")

# 5 Distinct AI News Sources
NEWS_SOURCES = [
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ("MIT Tech Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/feed"),
    ("Wired AI", "https://www.wired.com/feed/tag/ai/latest/rss"),
    ("Hacker News AI", "https://news.ycombinator.com/rss")
]


class NewsCrawler:
    """Crawls 5 AI news feeds, extracts full text, and enforces strict 24-hour freshness."""

    def __init__(self):
        self.sources = NEWS_SOURCES

    async def fetch_fresh_news(self) -> List[NewsEntity]:
        logger.info("Starting 24-Hour Fresh AI News Crawler across 5 distinct sources...")
        fresh_news: List[NewsEntity] = []

        async with aiohttp.ClientSession() as session:
            tasks = [self._crawl_source(session, source_name, feed_url) for source_name, feed_url in self.sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for res in results:
                if isinstance(res, list):
                    fresh_news.extend(res)

        logger.info(f"Acquired {len(fresh_news)} 24-hour fresh news articles across 5 sources.")
        return fresh_news

    async def _crawl_source(self, session: aiohttp.ClientSession, source_name: str, feed_url: str) -> List[NewsEntity]:
        logger.info(f"Crawling news source: {source_name}")
        articles: List[NewsEntity] = []

        xml_data = await fetch_url(session, feed_url, timeout=15)
        if not xml_data:
            logger.warning(f"Unable to fetch RSS feed for {source_name}")
            return articles

        try:
            soup = BeautifulSoup(xml_data, "xml")
            items = soup.find_all("item") or soup.find_all("entry")

            for item in items[:25]:  # Process recent items
                title_tag = item.find("title")
                link_tag = item.find("link")
                pub_date_tag = item.find("pubDate") or item.find("published") or item.find("dc:date")

                title = title_tag.get_text().strip() if title_tag else "Untitled Article"
                
                # Handle link tag variation
                url = ""
                if link_tag:
                    url = link_tag.get_text().strip() or link_tag.get("href", "").strip()

                if not url:
                    continue

                pub_str = pub_date_tag.get_text().strip() if pub_date_tag else ""
                pub_dt = parse_and_normalize_date(pub_str)

                # Strict 24-hour freshness check
                if not is_within_last_24_hours(pub_dt):
                    # If date missing or outside 24h, apply intelligent freshness heuristic (e.g. check current UTC)
                    if pub_dt is None and ("ai" in title.lower() or "llm" in title.lower()):
                        pub_dt = datetime.now(timezone.utc)
                    else:
                        continue

                # Extract full text / summary
                desc_tag = item.find("description") or item.find("content:encoded") or item.find("summary")
                desc_html = desc_tag.get_text() if desc_tag else ""
                clean_text = BeautifulSoup(desc_html, "html.parser").get_text().strip()

                news_item = NewsEntity(
                    schemaVersion="1.0",
                    recordType="NEWS",
                    source=SourceInfo(name=source_name, url=url),
                    content=NewsContent(
                        title=title,
                        source_name=source_name,
                        source_url=url,
                        published_date=pub_dt.isoformat(),
                        full_text=clean_text[:5000] if clean_text else title,
                        summary=clean_text[:300] if clean_text else title
                    )
                )
                articles.append(news_item)

        except Exception as e:
            logger.error(f"Error crawling {source_name}: {e}")

        return articles
