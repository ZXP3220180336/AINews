"""
Base crawler with rate limiting, robots.txt compliance, and error handling.
"""

from __future__ import annotations

import asyncio
import urllib.parse
import urllib.robotparser
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any  # noqa: UP035

import httpx
from loguru import logger


@dataclass
class CrawlResult:
    """Result of a crawl operation."""

    url: str
    content: str | None = None
    status_code: int | None = None
    error: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class BaseCrawler(ABC):
    """Abstract base crawler with rate limiting and robots.txt compliance."""

    def __init__(
        self,
        user_agent: str = "AINewsBot/1.0 (+https://github.com/yourusername/ainews)",
        delay_seconds: float = 1.0,
        max_retries: int = 3,
        timeout: float = 30.0,
        respect_robots: bool = True,
    ):
        self.user_agent = user_agent
        self.delay_seconds = delay_seconds
        self.max_retries = max_retries
        self.timeout = timeout
        self.respect_robots = respect_robots

        self._last_request_time: dict[str, datetime] = {}
        self._robot_parsers: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._client: httpx.AsyncClient | None = None

        logger.debug(
            f"Initialized crawler with delay={delay_seconds}s, retries={max_retries}"
        )

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    async def _respect_rate_limit(self, domain: str) -> None:
        """Enforce rate limiting for a domain."""
        if domain not in self._last_request_time:
            return

        last_time = self._last_request_time[domain]
        elapsed = (datetime.now() - last_time).total_seconds()

        if elapsed < self.delay_seconds:
            wait_time = self.delay_seconds - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s for {domain}")
            await asyncio.sleep(wait_time)

    def _update_request_time(self, domain: str) -> None:
        """Update last request time for a domain."""
        self._last_request_time[domain] = datetime.now()

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc

    async def _check_robots_txt(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        if not self.respect_robots:
            return True

        domain = self._get_domain(url)

        # Get or create robot parser
        if domain not in self._robot_parsers:
            parsed_url = urllib.parse.urlparse(url)
            robots_url = urllib.parse.urlunparse(
                parsed_url._replace(path="/robots.txt")
            )
            parser = urllib.robotparser.RobotFileParser()
            parser.set_url(robots_url)

            try:
                # Fetch robots.txt
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        robots_url, headers={"User-Agent": self.user_agent}
                    )
                    if response.status_code == 200:
                        parser.parse(response.text.splitlines())
                    else:
                        # If no robots.txt, assume allowed
                        parser.allow_all = True  # type: ignore
            except Exception as e:
                logger.warning(f"Failed to fetch robots.txt for {domain}: {e}")
                parser.allow_all = True  # type: ignore

            self._robot_parsers[domain] = parser

        parser = self._robot_parsers[domain]
        return parser.can_fetch(self.user_agent, url)

    async def fetch(self, url: str, **kwargs) -> CrawlResult:
        """
        Fetch a URL with rate limiting and error handling.

        Args:
            url: URL to fetch
            **kwargs: Additional arguments for httpx

        Returns:
            CrawlResult object
        """
        domain = self._get_domain(url)

        # Check robots.txt
        if not await self._check_robots_txt(url):
            logger.warning(f"URL blocked by robots.txt: {url}")
            return CrawlResult(url=url, error="Blocked by robots.txt")

        # Respect rate limiting
        await self._respect_rate_limit(domain)

        # Make request with retries
        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"Fetching {url} (attempt {attempt + 1}/{self.max_retries})"
                )

                if not self._client:
                    raise RuntimeError(
                        "Crawler not initialized as async context manager"
                    )

                response = await self._client.get(url, **kwargs)
                self._update_request_time(domain)

                # Log rate limit headers if present
                if "X-RateLimit-Remaining" in response.headers:
                    remaining = response.headers.get("X-RateLimit-Remaining")
                    logger.debug(f"Rate limit remaining: {remaining}")

                return CrawlResult(
                    url=url,
                    content=response.text,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    metadata={
                        "attempt": attempt + 1,
                        "response_time": response.elapsed.total_seconds(),
                    },
                )

            except httpx.TimeoutException:
                error_msg = f"Timeout fetching {url}"
                logger.warning(f"{error_msg} (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    return CrawlResult(url=url, error=error_msg)
                await self._exponential_backoff(attempt)

            except httpx.HTTPError as e:
                error_msg = f"HTTP error fetching {url}: {e}"
                logger.warning(f"{error_msg} (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    return CrawlResult(url=url, error=error_msg)
                await self._exponential_backoff(attempt)

            except Exception as e:
                error_msg = f"Unexpected error fetching {url}: {e}"
                logger.error(f"{error_msg} (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    return CrawlResult(url=url, error=error_msg)
                await self._exponential_backoff(attempt)

        # Should not reach here
        return CrawlResult(url=url, error="Max retries exceeded")

    async def _exponential_backoff(self, attempt: int) -> None:
        """Exponential backoff between retries."""
        backoff_time = min(2**attempt, 60)  # Cap at 60 seconds
        logger.debug(f"Backing off for {backoff_time}s before retry")
        await asyncio.sleep(backoff_time)

    @abstractmethod
    async def crawl(self, **kwargs) -> list[CrawlResult]:
        """
        Main crawl method to be implemented by subclasses.

        Returns:
            List of crawl results
        """
        pass

    def should_crawl_today(self, last_crawled: datetime | None) -> bool:
        """
        Determine if we should crawl today based on last crawl time.

        Args:
            last_crawled: Last crawl datetime or None

        Returns:
            True if should crawl today
        """
        if last_crawled is None:
            return True

        # Check if last crawl was yesterday or earlier
        yesterday = datetime.now() - timedelta(days=1)
        return last_crawled.date() <= yesterday.date()
