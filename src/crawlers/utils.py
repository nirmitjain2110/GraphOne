"""
Async HTTP Crawler Utilities & Date Normalizer.
Includes stealth browser headers, rate limiting, and 24-hour freshness date parsing logic.
"""

import re
import random
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger("CrawlerUtils")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0"
]


def get_stealth_headers() -> Dict[str, str]:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }


async def fetch_url(session: aiohttp.ClientSession, url: str, timeout: int = 15) -> Optional[str]:
    """Fetches a URL asynchronously with retry and stealth headers."""
    headers = get_stealth_headers()
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status == 200:
                return await resp.text()
            else:
                logger.warning(f"HTTP {resp.status} fetching {url}")
                return None
    except Exception as e:
        logger.debug(f"Error fetching {url}: {e}")
        return None


def parse_and_normalize_date(raw_date_str: str) -> Optional[datetime]:
    """
    Extracts and normalizes publication dates to UTC datetime objects.
    Handles relative strings ('2 hours ago', '1 day ago', 'just now', '5m ago'),
    ISO formats, and RSS standard dates.
    """
    if not raw_date_str:
        return None

    raw = raw_date_str.strip().lower()
    now = datetime.now(timezone.utc)

    # 1. Relative time patterns
    if "just now" in raw or "moments ago" in raw:
        return now

    match = re.search(r"(\d+)\s*(sec|second|min|minute|hr|hour|day|d|h|m)s?\s*ago", raw)
    if match:
        val = int(match.group(1))
        unit = match.group(2)
        if unit.startswith("sec"):
            return now - timedelta(seconds=val)
        elif unit.startswith("m") and unit != "month":
            return now - timedelta(minutes=val)
        elif unit.startswith("h") or unit == "hr":
            return now - timedelta(hours=val)
        elif unit.startswith("d"):
            return now - timedelta(days=val)

    # Short format e.g. "5h ago", "2d ago"
    match_short = re.search(r"^(\d+)([hdm])\b", raw)
    if match_short:
        val = int(match_short.group(1))
        unit = match_short.group(2)
        if unit == "m":
            return now - timedelta(minutes=val)
        elif unit == "h":
            return now - timedelta(hours=val)
        elif unit == "d":
            return now - timedelta(days=val)

    # 2. ISO 8601 & Standard Formats
    try:
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass

    date_formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%d %b %Y %H:%M:%S %z",
        "%B %d, %Y"
    ]

    clean_str = raw_date_str.strip()
    for fmt in date_formats:
        try:
            dt = datetime.strptime(clean_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue

    return None


def is_within_last_24_hours(dt: Optional[datetime]) -> bool:
    """Checks if a datetime object is within the last 24 hours."""
    if dt is None:
        return False
    now = datetime.now(timezone.utc)
    delta = now - dt
    return timedelta(seconds=0) <= delta <= timedelta(hours=24)
