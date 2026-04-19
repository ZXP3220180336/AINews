"""
Data models for AI news articles.
"""

import typing  # noqa: UP035
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ArticleCategory(Enum):
    """Categories for AI news articles."""

    MODELS = "models"  # New model releases
    AGENTS = "agents"  # Agent frameworks and developments
    RESEARCH = "research"  # Research papers and breakthroughs
    BUSINESS = "business"  # Company news, funding, mergers
    TOOLS = "tools"  # New tools and libraries
    ETHICS = "ethics"  # Ethics, safety, alignment
    POLICY = "policy"  # Regulations, policies
    OTHER = "other"


@dataclass
class Article:
    """Represents an AI news article."""

    # Core fields
    title: str
    url: str
    source: str  # e.g., "arXiv", "TechCrunch", "机器之心"
    published_at: datetime

    # Content
    summary: str | None = None
    content: str | None = None
    authors: list[str] = field(default_factory=list)

    # Metadata
    categories: list[ArticleCategory] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    importance_score: float = 0.0  # 0-1 score of importance

    # Processing info
    crawled_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # External references
    external_ids: dict[str, str] = field(
        default_factory=dict
    )  # e.g., {"arxiv": "1234.5678"}
    references: list[str] = field(default_factory=list)  # URLs to related articles

    # LLM-generated fields
    llm_summary: str | None = None
    llm_key_points: list[str] = field(default_factory=list)
    llm_tags: list[str] = field(default_factory=list)

    # Technical fields
    raw_data: dict[str, typing.Any] = field(default_factory=dict)  # Original raw data
    embedding: list[float] | None = None  # Vector embedding for similarity

    def __post_init__(self):
        """Ensure datetime fields are timezone-aware."""
        if self.published_at.tzinfo is None:
            # Assume UTC if no timezone
            self.published_at = self.published_at.replace(tzinfo=None)
        if self.crawled_at.tzinfo is None:
            self.crawled_at = self.crawled_at.replace(tzinfo=None)
        if self.updated_at.tzinfo is None:
            self.updated_at = self.updated_at.replace(tzinfo=None)

    @property
    def is_recent(self, days: int = 1) -> bool:
        """Check if article was published within last N days."""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        return self.published_at >= cutoff

    @property
    def is_today(self) -> bool:
        """Check if article was published today."""
        return self.published_at.date() == datetime.now().date()

    @property
    def is_yesterday(self) -> bool:
        """Check if article was published yesterday."""
        from datetime import timedelta

        yesterday = datetime.now() - timedelta(days=1)
        return self.published_at.date() == yesterday.date()


@dataclass
class CrawlSource:
    """Configuration for a crawl source."""

    name: str
    url: str
    type: str  # "rss", "api", "web"
    enabled: bool = True
    priority: int = 1  # 1-5, higher is more important
    config: dict[str, typing.Any] = field(default_factory=dict)

    # Rate limiting
    delay_seconds: float = 1.0
    max_pages: int = 10

    # Content filtering
    required_keywords: list[str] = field(default_factory=list)
    excluded_keywords: list[str] = field(default_factory=list)

    # Processing
    parser: str | None = None  # Custom parser name
    category: ArticleCategory | None = None

    def __str__(self) -> str:
        return f"{self.name} ({self.type}: {self.url})"
