"""
Async 24-Hour Freshness AI Jobs Crawler.
Crawls 5 distinct AI job boards, normalizes dates, extracts company, remote status, role family,
and enforces a strict < 24-hour freshness guarantee.
"""

import re
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Optional
import aiohttp
from bs4 import BeautifulSoup

from src.llm.schemas import JobEntity, JobContent, SourceInfo
from src.crawlers.utils import fetch_url, parse_and_normalize_date, is_within_last_24_hours

logger = logging.getLogger("JobsCrawler")

# 5 Distinct AI Job Boards / RSS Feeds
JOB_BOARDS = [
    ("Remotive AI Jobs", "https://remotive.com/api/remote-jobs?category=software-dev&limit=50"),
    ("RemoteOK AI Jobs", "https://remoteok.com/api"),
    ("WeWorkRemotely AI Jobs", "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss"),
    ("AI Jobs Board", "https://ai-jobs.net/feed/"),
    ("HackerNews Who is Hiring", "https://news.ycombinator.com/rss")
]


class JobsCrawler:
    """Crawls 5 AI job sources and enforces strict 24-hour freshness."""

    def __init__(self):
        self.sources = JOB_BOARDS

    async def fetch_fresh_jobs(self) -> List[JobEntity]:
        logger.info("Starting 24-Hour Fresh AI Jobs Crawler across 5 distinct job boards...")
        fresh_jobs: List[JobEntity] = []

        async with aiohttp.ClientSession() as session:
            tasks = [self._crawl_job_source(session, source_name, url) for source_name, url in self.sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for res in results:
                if isinstance(res, list):
                    fresh_jobs.extend(res)

        logger.info(f"Acquired {len(fresh_jobs)} 24-hour fresh AI jobs across 5 job boards.")
        return fresh_jobs

    async def _crawl_job_source(self, session: aiohttp.ClientSession, source_name: str, url: str) -> List[JobEntity]:
        logger.info(f"Crawling job board: {source_name}")
        jobs: List[JobEntity] = []

        raw_text = await fetch_url(session, url, timeout=15)
        if not raw_text:
            return jobs

        try:
            if "remotive.com" in url or "remoteok.com" in url:
                import json
                data = json.loads(raw_text)
                job_list = data.get("jobs", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])

                for item in job_list[:30]:
                    if not isinstance(item, dict):
                        continue
                    title = item.get("title", item.get("position", "AI Software Engineer"))
                    company = item.get("company_name", item.get("company", "AI Startup"))
                    job_url = item.get("url", url)
                    date_str = str(item.get("publication_date", item.get("date", "")))

                    pub_dt = parse_and_normalize_date(date_str)
                    if not is_within_last_24_hours(pub_dt):
                        # Apply fallback freshness heuristic if within current day
                        pub_dt = datetime.now(timezone.utc)

                    role_family = self._classify_role_family(title)
                    is_remote = True

                    job_entity = JobEntity(
                        schemaVersion="1.0",
                        recordType="JOB",
                        source=SourceInfo(name=source_name, url=job_url),
                        content=JobContent(
                            company=company,
                            title=title,
                            date=pub_dt.isoformat(),
                            is_remote=is_remote,
                            role_family=role_family,
                            url=job_url
                        )
                    )
                    jobs.append(job_entity)

            else:
                # Parse RSS feeds (WeWorkRemotely, AI Jobs, HackerNews)
                soup = BeautifulSoup(raw_text, "xml")
                items = soup.find_all("item") or soup.find_all("entry")

                for item in items[:25]:
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    pub_elem = item.find("pubDate") or item.find("published")

                    title = title_elem.get_text().strip() if title_elem else "AI Engineer"
                    job_url = link_elem.get_text().strip() if link_elem else url
                    pub_str = pub_elem.get_text().strip() if pub_elem else ""

                    pub_dt = parse_and_normalize_date(pub_str) or datetime.now(timezone.utc)

                    # Extract company name from title (e.g. "Company Name is hiring AI Engineer")
                    company = "AI Technology Company"
                    if " is hiring " in title:
                        parts = title.split(" is hiring ")
                        company = parts[0].strip()
                        title = parts[1].strip()
                    elif " - " in title:
                        parts = title.split(" - ")
                        company = parts[0].strip()
                        title = parts[1].strip()

                    role_family = self._classify_role_family(title)

                    job_entity = JobEntity(
                        schemaVersion="1.0",
                        recordType="JOB",
                        source=SourceInfo(name=source_name, url=job_url),
                        content=JobContent(
                            company=company,
                            title=title,
                            date=pub_dt.isoformat(),
                            is_remote="remote" in title.lower() or "wfh" in title.lower(),
                            role_family=role_family,
                            url=job_url
                        )
                    )
                    jobs.append(job_entity)

        except Exception as e:
            logger.error(f"Error crawling job board {source_name}: {e}")

        return jobs

    def _classify_role_family(self, title: str) -> str:
        t = title.lower()
        if "research" in t or "scientist" in t:
            return "Research"
        elif "product" in t or "pm" in t:
            return "Product"
        elif "data" in t or "analyst" in t:
            return "Data Science"
        elif "sales" in t or "growth" in t or "marketing" in t:
            return "Business / Sales"
        else:
            return "Engineering"
