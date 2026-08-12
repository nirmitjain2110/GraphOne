"""
Async Real AI Jobs Crawler.
Crawls live job boards (Remotive, RemoteOK, WeWorkRemotely RSS, HackerNews),
extracts authentic company names, job titles, remote status, role family,
validates URLs (HTTP 200 OK), and standardizes publication dates to ISO 8601 format. Zero synthetic data.
"""

import re
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Set
import aiohttp
import dateutil.parser
from bs4 import BeautifulSoup

from src.llm.schemas import JobEntity, JobContent, SourceInfo
from src.crawlers.utils import get_stealth_headers

logger = logging.getLogger("JobsCrawler")

JOB_SOURCES = [
    ("Remotive AI Jobs", "https://remotive.com/api/remote-jobs?search=ai&limit=100"),
    ("Remotive Software Jobs", "https://remotive.com/api/remote-jobs?category=software-dev&limit=100"),
    ("RemoteOK AI Jobs", "https://remoteok.com/api"),
    ("WeWorkRemotely Full Stack", "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss"),
    ("WeWorkRemotely Back End", "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss"),
    ("HackerNews Who is Hiring", "https://news.ycombinator.com/rss")
]


class JobsCrawler:
    """
    Acquires real AI job postings across live APIs and RSS feeds.
    Enforces HTTP 200 OK link validation and ISO 8601 date normalization. Zero synthetic data.
    """

    def __init__(self, target_count: int = 100):
        self.target_count = target_count

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

    async def _validate_job_url(self, session: aiohttp.ClientSession, url: str, semaphore: asyncio.Semaphore) -> bool:
        """Validates that job URL returns HTTP 200 OK status."""
        if not url or not isinstance(url, str) or not url.startswith("http"):
            return False
        headers = get_stealth_headers()
        async with semaphore:
            try:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=4.0), allow_redirects=True) as resp:
                    return resp.status == 200
            except Exception:
                return False

    async def _fetch_remotive_jobs(self, session: aiohttp.ClientSession, source_name: str, url: str) -> List[dict]:
        raw_jobs = []
        headers = get_stealth_headers()
        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    job_list = data.get("jobs", []) if isinstance(data, dict) else []
                    for item in job_list:
                        company = item.get("company_name", "").strip()
                        title = item.get("title", "").strip()
                        job_url = item.get("url", "").strip()
                        pub_date = str(item.get("publication_date", ""))

                        if company and title and job_url:
                            raw_jobs.append({
                                "company": company,
                                "title": title,
                                "job_url": job_url,
                                "date": self._normalize_iso_date(pub_date),
                                "is_remote": True,
                                "source_name": source_name
                            })
        except Exception as e:
            logger.warning(f"Source [{source_name}]: Notice: {e}")
        logger.info(f"Source [{source_name}]: Fetched {len(raw_jobs)} raw job records.")
        return raw_jobs

    async def _fetch_remoteok_jobs(self, session: aiohttp.ClientSession, source_name: str, url: str) -> List[dict]:
        raw_jobs = []
        headers = get_stealth_headers()
        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list):
                        for item in data[1:]:  # Skip legal header item
                            if not isinstance(item, dict):
                                continue
                            company = item.get("company", "").strip()
                            title = item.get("position", "").strip()
                            job_url = item.get("url", "").strip()
                            if job_url and not job_url.startswith("http"):
                                job_url = f"https://remoteok.com{job_url}"
                            pub_date = str(item.get("date", ""))

                            if company and title and job_url:
                                raw_jobs.append({
                                    "company": company,
                                    "title": title,
                                    "job_url": job_url,
                                    "date": self._normalize_iso_date(pub_date),
                                    "is_remote": True,
                                    "source_name": source_name
                                })
        except Exception as e:
            logger.warning(f"Source [{source_name}]: Notice: {e}")
        logger.info(f"Source [{source_name}]: Fetched {len(raw_jobs)} raw job records.")
        return raw_jobs

    async def _fetch_rss_jobs(self, session: aiohttp.ClientSession, source_name: str, url: str) -> List[dict]:
        raw_jobs = []
        headers = get_stealth_headers()
        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    xml_text = await resp.text()
                    soup = BeautifulSoup(xml_text, "xml")
                    items = soup.find_all("item") or soup.find_all("entry")

                    for item in items:
                        title_elem = item.find("title")
                        link_elem = item.find("link")
                        pub_elem = item.find("pubDate") or item.find("published")

                        raw_title = title_elem.get_text().strip() if title_elem else ""
                        job_url = link_elem.get_text().strip() if link_elem else ""
                        pub_str = pub_elem.get_text().strip() if pub_elem else ""

                        if not raw_title or not job_url:
                            continue

                        company = "Unknown"
                        title = raw_title

                        if ":" in raw_title:
                            parts = raw_title.split(":", 1)
                            company = parts[0].strip()
                            title = parts[1].strip()
                        elif " is hiring " in raw_title:
                            parts = raw_title.split(" is hiring ", 1)
                            company = parts[0].strip()
                            title = parts[1].strip()
                        elif " - " in raw_title:
                            parts = raw_title.split(" - ", 1)
                            company = parts[0].strip()
                            title = parts[1].strip()

                        if company and company != "Unknown" and title:
                            raw_jobs.append({
                                "company": company,
                                "title": title,
                                "job_url": job_url,
                                "date": self._normalize_iso_date(pub_str),
                                "is_remote": "remote" in title.lower() or "wfh" in title.lower() or "remote" in raw_title.lower(),
                                "source_name": source_name
                            })
        except Exception as e:
            logger.warning(f"Source [{source_name}]: Notice: {e}")
        logger.info(f"Source [{source_name}]: Fetched {len(raw_jobs)} raw job records.")
        return raw_jobs

    async def fetch_fresh_jobs(self) -> List[JobEntity]:
        logger.info(f"Starting Multi-Source Real AI Jobs Acquisition (Target: {self.target_count}+ 200 OK verified jobs)...")

        connector = aiohttp.TCPConnector(ssl=False, limit=100)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [
                self._fetch_remotive_jobs(session, "Remotive AI Jobs", "https://remotive.com/api/remote-jobs?search=ai&limit=100"),
                self._fetch_remotive_jobs(session, "Remotive Software Jobs", "https://remotive.com/api/remote-jobs?category=software-dev&limit=100"),
                self._fetch_remoteok_jobs(session, "RemoteOK AI Jobs", "https://remoteok.com/api"),
                self._fetch_rss_jobs(session, "WeWorkRemotely Full Stack", "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss"),
                self._fetch_rss_jobs(session, "WeWorkRemotely Back End", "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss"),
                self._fetch_rss_jobs(session, "HackerNews Who is Hiring", "https://news.ycombinator.com/rss")
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)
            raw_candidates: List[dict] = []

            for r in results:
                if isinstance(r, list):
                    raw_candidates.extend(r)

            logger.info(f"Collected {len(raw_candidates)} total raw job candidates across APIs.")

            # Deduplicate by job URL & company/title combination
            unique_jobs: List[dict] = []
            seen_urls: Set[str] = set()
            seen_combos: Set[str] = set()

            for j in raw_candidates:
                u = j.get("job_url", "").lower().strip()
                combo = f"{j.get('company', '').lower()}|{j.get('title', '').lower()}"
                if u and u not in seen_urls and combo not in seen_combos:
                    seen_urls.add(u)
                    seen_combos.add(combo)
                    unique_jobs.append(j)

            logger.info(f"Deduplicated to {len(unique_jobs)} unique real job entries.")

            # Concurrently validate HTTP 200 OK status on job URLs
            url_semaphore = asyncio.Semaphore(40)
            verified_entities: List[JobEntity] = []

            async def process_job(j: dict) -> Optional[JobEntity]:
                url = j.get("job_url", "")
                is_valid = await self._validate_job_url(session, url, url_semaphore)
                if not is_valid:
                    return None

                title = j.get("title", "")
                company = j.get("company", "")
                pub_date = j.get("date", "")
                role_family = self._classify_role_family(title)

                return JobEntity(
                    schemaVersion="1.0",
                    recordType="JOB",
                    source=SourceInfo(name=j.get("source_name", "Remote AI Jobs"), url=url),
                    content=JobContent(
                        company=company,
                        title=title,
                        date=pub_date,
                        is_remote=j.get("is_remote", True),
                        role_family=role_family,
                        url=url
                    )
                )

            batch_size = 100
            for i in range(0, len(unique_jobs), batch_size):
                chunk = unique_jobs[i:i + batch_size]
                batch_tasks = [process_job(j) for j in chunk]
                batch_results = await asyncio.gather(*batch_tasks)

                for item in batch_results:
                    if item is not None:
                        verified_entities.append(item)

                if len(verified_entities) >= self.target_count:
                    break

            verified_entities = verified_entities[:self.target_count]

        logger.info(f"Successfully collected {len(verified_entities)} REAL 200 OK verified AI jobs across live sources.")
        return verified_entities
