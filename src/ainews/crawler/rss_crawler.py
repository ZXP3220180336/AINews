"""
RSS/Atom feed crawler.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

import feedparser
from feedparser import FeedParserDict
from loguru import logger

from ..models import Article, ArticleCategory, CrawlSource
from .base import BaseCrawler, CrawlResult


class RSSCrawler(BaseCrawler):
    """Crawler for RSS/Atom feeds."""

    def __init__(self, source: CrawlSource, max_age_days: int = 1, **kwargs):
        super().__init__(**kwargs)
        self.source = source
        self.max_age_days = max_age_days

    async def crawl(self, **kwargs) -> list[CrawlResult]:
        """
        Crawl RSS feed and return articles.

        Returns:
            List of crawl results (one per feed entry)
        """
        logger.info(f"Crawling RSS feed: {self.source.name} ({self.source.url})")

        try:
            # Fetch feed using feedparser (synchronous)
            # We run it in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, self.source.url)

            if feed.bozo:
                logger.warning(
                    f"Feed parsing error for {self.source.url}: {feed.bozo_exception}"
                )

            results = []
            for entry in feed.entries[: self.source.max_pages]:
                result = await self._process_entry(entry, feed.feed)  # type: ignore
                if result:
                    results.append(result)

            logger.info(f"Found {len(results)} articles from {self.source.name}")
            return results

        except Exception as e:
            logger.error(f"Failed to crawl RSS feed {self.source.url}: {e}")
            return []

    async def _process_entry(
        self, entry: FeedParserDict, feed_info: dict[str, Any]
    ) -> CrawlResult | None:
        """Process a single feed entry."""
        try:
            # Extract basic info
            title = entry.get("title", "Untitled")
            url = entry.get("link", "")
            summary = entry.get("summary", entry.get("description", ""))

            # Parse publication date
            published = self._parse_date(entry)

            # Check if article is recent enough
            if not self._is_recent(published):
                logger.debug(f"Skipping old article: {title} ({published})")
                return None

            # Fetch full content if needed
            content = summary
            if self.source.config.get("fetch_full_content", False):
                # TODO: Implement full content fetching
                pass

            # Create crawl result
            result = CrawlResult(
                url=url,  # type: ignore
                content=content,  # type: ignore
                metadata={
                    "title": title,
                    "summary": summary,
                    "published": published.isoformat() if published else None,
                    "authors": self._extract_authors(entry),
                    "categories": self._extract_categories(entry),
                    "feed_title": feed_info.get("title", ""),
                    "feed_url": feed_info.get("link", ""),
                    "entry": entry,  # Keep raw entry for later processing
                },
            )

            return result

        except Exception as e:
            logger.error(f"Failed to process feed entry: {e}")
            return None

    def _parse_date(self, entry: FeedParserDict) -> datetime | None:
        """Parse publication date from feed entry."""
        date_fields = ["published_parsed", "updated_parsed", "created_parsed"]

        for field in date_fields:
            if field in entry and entry[field]:
                try:
                    # feedparser returns time.struct_time
                    struct_time = entry[field]
                    return datetime(*struct_time[:6])  # type: ignore
                except Exception as e:
                    logger.debug(f"Failed to parse date field {field}: {e}")

        # Fallback to string dates
        str_fields = ["published", "updated", "created"]
        for field in str_fields:
            if field in entry and entry[field]:
                try:
                    # Try common date formats
                    import dateutil.parser

                    return dateutil.parser.parse(entry[field])  # type: ignore
                except Exception as e:
                    logger.debug(f"Failed to parse string date {field}: {e}")

        logger.warning(
            f"No valid date found for entry: {entry.get('title', 'Unknown')}"
        )
        return None

    def _is_recent(self, published: datetime | None) -> bool:
        """Check if article is within max_age_days."""
        if published is None:
            return False

        cutoff = datetime.now() - timedelta(days=self.max_age_days)
        return published >= cutoff

    def _extract_authors(self, entry: FeedParserDict) -> list[str]:
        """Extract authors from feed entry."""
        authors = []

        # Handle different feed formats
        if "authors" in entry:
            for author in entry.authors:
                authors.append(author.get("name", ""))

        if "author" in entry:
            authors.append(entry.author)

        # Deduplicate and clean
        authors = [a.strip() for a in authors if a and a.strip()]
        return list(set(authors))

    def _extract_categories(self, entry: FeedParserDict) -> list[str]:
        """Extract categories/tags from feed entry."""
        categories = []

        if "tags" in entry:
            for tag in entry.tags:
                categories.append(tag.get("term", ""))

        if "categories" in entry:
            for cat in entry.categories:
                categories.append(cat.get("term", ""))

        # Deduplicate and clean
        categories = [c.strip() for c in categories if c and c.strip()]
        return list(set(categories))

    def entry_to_article(self, result: CrawlResult) -> Article | None:
        """Convert crawl result to Article model."""
        try:
            metadata = result.metadata
            entry = metadata.get("entry", {})

            # Map feed categories to our ArticleCategory
            categories = []
            raw_categories = metadata.get("categories", [])
            for cat in raw_categories:
                cat_lower = cat.lower()
                if any(keyword in cat_lower for keyword in ["model", "llm", "gpt"]):
                    categories.append(ArticleCategory.MODELS)
                elif any(keyword in cat_lower for keyword in ["agent", "auto"]):
                    categories.append(ArticleCategory.AGENTS)
                elif any(
                    keyword in cat_lower for keyword in ["research", "paper", "arxiv"]
                ):
                    categories.append(ArticleCategory.RESEARCH)
                elif any(
                    keyword in cat_lower
                    for keyword in ["business", "company", "funding"]
                ):
                    categories.append(ArticleCategory.BUSINESS)
                elif any(
                    keyword in cat_lower for keyword in ["tool", "library", "framework"]
                ):
                    categories.append(ArticleCategory.TOOLS)

            if not categories:
                categories = [ArticleCategory.OTHER]

            # Parse published date
            published_str = metadata.get("published")
            if published_str:
                try:
                    import dateutil.parser

                    published_at = dateutil.parser.parse(published_str)
                except Exception as e:
                    logger.debug(f"Failed to parse published date: {e}")
                    published_at = datetime.now()
            else:
                published_at = datetime.now()

            # Create article
            article = Article(
                title=metadata.get("title", "Untitled"),
                url=result.url,
                source=self.source.name,
                published_at=published_at,
                summary=metadata.get("summary", ""),
                content=result.content,
                authors=metadata.get("authors", []),
                categories=categories,
                tags=raw_categories,
                raw_data={"entry": entry, "feed_info": metadata.get("feed_title")},
            )

            return article

        except Exception as e:
            logger.error(f"Failed to convert crawl result to article: {e}")
            return None


async def crawl_sources(sources: list[CrawlSource], **kwargs) -> list[Article]:
    """Crawl multiple RSS sources."""
    articles = []

    for source in sources:
        if not source.enabled or source.type != "rss":
            continue

        try:
            crawler = RSSCrawler(source, **kwargs)
            async with crawler:
                results = await crawler.crawl()

                for result in results:
                    article = crawler.entry_to_article(result)
                    if article:
                        articles.append(article)

        except Exception as e:
            logger.error(f"Failed to crawl source {source.name}: {e}")

    logger.info(f"Total articles crawled: {len(articles)}")
    return articles
