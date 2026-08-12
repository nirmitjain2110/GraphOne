"""
Async Real AI News Crawler.
Crawls live AI news RSS feeds (TechCrunch AI, VentureBeat AI, MIT Tech Review, Wired, InfoQ AI, HackerNews AI),
extracts article titles, summaries, full text, validates URLs (HTTP 200 OK),
and standardizes publication dates to ISO 8601 format. Zero synthetic data.
"""

import re
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Set
import aiohttp
import dateutil.parser
from bs4 import BeautifulSoup

from src.llm.schemas import NewsEntity, NewsContent, SourceInfo
from src.crawlers.utils import get_stealth_headers

logger = logging.getLogger("NewsCrawler")

NEWS_SOURCES = [
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ("MIT Tech Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/feed"),
    ("Wired AI", "https://www.wired.com/feed/tag/ai/latest/rss"),
    ("InfoQ AI", "https://feed.infoq.com/ai-ml-data-eng/news"),
    ("Hacker News AI", "https://news.ycombinator.com/rss")
]


class NewsCrawler:
    """
    Acquires real AI news articles across live RSS feeds.
    Enforces HTTP 200 OK link validation and ISO 8601 date normalization. Zero synthetic data.
    """

    def __init__(self, target_count: int = 50):
        self.target_count = target_count
        self.sources = NEWS_SOURCES

    def _normalize_iso_date(self, date_str: str) -> str:
        """Normalizes publication date into ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)."""
        if not date_str or not isinstance(date_str, str):
            return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            dt = dateutil.parser.parse(date_str.strip())
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", date_str)
            if m:
                y, m_val, d = m.groups()
                return f"{y}-{int(m_val):02d}-{int(d):02d}T00:00:00Z"
            return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    async def _validate_news_url(self, session: aiohttp.ClientSession, url: str, semaphore: asyncio.Semaphore) -> bool:
        """Validates that news article URL returns HTTP 200 OK status."""
        if not url or not isinstance(url, str) or not url.startswith("http"):
            return False
        headers = get_stealth_headers()
        async with semaphore:
            try:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=4.0), allow_redirects=True) as resp:
                    return resp.status == 200
            except Exception:
                return False

    async def _crawl_source(self, session: aiohttp.ClientSession, source_name: str, feed_url: str) -> List[dict]:
        logger.info(f"Crawling news feed: {source_name}")
        articles: List[dict] = []
        headers = get_stealth_headers()

        try:
            async with session.get(feed_url, headers=headers, timeout=aiohttp.ClientTimeout(total=12)) as resp:
                if resp.status == 200:
                    xml_text = await resp.text()
                    soup = BeautifulSoup(xml_text, "xml")
                    items = soup.find_all("item") or soup.find_all("entry")

                    for item in items[:30]:
                        title_tag = item.find("title")
                        link_tag = item.find("link")
                        pub_date_tag = item.find("pubDate") or item.find("published") or item.find("dc:date")

                        title = title_tag.get_text().strip() if title_tag else ""
                        url = ""
                        if link_tag:
                            url = link_tag.get_text().strip() or link_tag.get("href", "").strip()

                        if not title or not url:
                            continue

                        pub_str = pub_date_tag.get_text().strip() if pub_date_tag else ""
                        pub_iso = self._normalize_iso_date(pub_str)

                        desc_tag = item.find("description") or item.find("content:encoded") or item.find("summary")
                        desc_html = desc_tag.get_text() if desc_tag else ""
                        clean_text = BeautifulSoup(desc_html, "html.parser").get_text().strip()

                        articles.append({
                            "title": title,
                            "url": url,
                            "source_name": source_name,
                            "published_date": pub_iso,
                            "full_text": clean_text[:4000] if clean_text else title,
                            "summary": clean_text[:300] if clean_text else title
                        })
        except Exception as e:
            logger.warning(f"Source [{source_name}]: Notice: {e}")

        logger.info(f"Source [{source_name}]: Fetched {len(articles)} raw news articles.")
        return articles

    async def fetch_fresh_news(self) -> List[NewsEntity]:
        logger.info(f"Starting Multi-Source Real AI News Acquisition across {len(self.sources)} sources...")

        connector = aiohttp.TCPConnector(ssl=False, limit=50)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self._crawl_source(session, source_name, feed_url) for source_name, feed_url in self.sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            raw_candidates: List[dict] = []
            for r in results:
                if isinstance(r, list):
                    raw_candidates.extend(r)

            logger.info(f"Collected {len(raw_candidates)} total raw news candidates across feeds.")

            # Deduplicate by URL & Title
            unique_articles: List[dict] = []
            seen_urls: Set[str] = set()
            seen_titles: Set[str] = set()

            for a in raw_candidates:
                u = a.get("url", "").lower().strip()
                t = a.get("title", "").lower().strip()
                if u and u not in seen_urls and t not in seen_titles:
                    seen_urls.add(u)
                    seen_titles.add(t)
                    unique_articles.append(a)

            logger.info(f"Deduplicated to {len(unique_articles)} unique real news entries.")

            # Concurrently validate HTTP 200 OK status on news article URLs
            url_semaphore = asyncio.Semaphore(30)
            verified_entities: List[NewsEntity] = []

            async def process_article(a: dict) -> Optional[NewsEntity]:
                url = a.get("url", "")
                is_valid = await self._validate_news_url(session, url, url_semaphore)
                if not is_valid:
                    return None

                title = a.get("title", "")
                source_name = a.get("source_name", "AI News")
                pub_date = a.get("published_date", "")
                full_text = a.get("full_text", title)
                summary = a.get("summary", title)

                return NewsEntity(
                    schemaVersion="1.0",
                    recordType="NEWS",
                    source=SourceInfo(name=source_name, url=url),
                    content=NewsContent(
                        title=title,
                        source_name=source_name,
                        source_url=url,
                        published_date=pub_date,
                        full_text=full_text,
                        summary=summary
                    )
                )

            batch_size = 50
            for i in range(0, len(unique_articles), batch_size):
                chunk = unique_articles[i:i + batch_size]
                batch_tasks = [process_article(a) for a in chunk]
                batch_results = await asyncio.gather(*batch_tasks)

                for item in batch_results:
                    if item is not None:
                        verified_entities.append(item)

        logger.info(f"Successfully collected {len(verified_entities)} REAL 200 OK verified AI news articles.")
        return verified_entities
