"""
LLM summarization using OpenAI API.
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from loguru import logger

from ..models import Article


@dataclass
class SummarizationConfig:
    """Configuration for summarization."""

    # Model settings
    model: str = "gpt-3.5-turbo"
    max_tokens: int = 500
    temperature: float = 0.3

    # Prompt settings
    language: str = "en"  # "en" or "zh" or "auto"
    style: str = "concise"  # "concise", "detailed", "bullet_points"

    # Cost management
    max_cost_per_day: float = 1.0  # USD
    cache_enabled: bool = True
    cache_ttl_hours: int = 24

    # Batch processing
    batch_size: int = 5
    batch_delay_seconds: float = 1.0

    # Fallback settings
    enable_fallback: bool = True
    fallback_method: str = "extractive"  # "extractive" or "lead"


class OpenAISummarizer:
    """Summarize articles using OpenAI API."""

    def __init__(self, config: SummarizationConfig | None = None):
        self.config = config or SummarizationConfig()
        self._client = None
        self._cost_today = 0.0
        self._cost_reset_date = datetime.now().date()

        # Simple in-memory cache
        self._cache: dict[str, tuple] = {}

        logger.info(f"Initialized OpenAI summarizer with model {self.config.model}")

    def _get_client(self):
        """Lazy load OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI()
            except ImportError:
                logger.error(
                    "OpenAI package not installed. \
                        Please install with: pip install openai"
                )
                raise
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                raise

        return self._client

    def _reset_cost_if_needed(self):
        """Reset daily cost counter if date changed."""
        today = datetime.now().date()
        if today != self._cost_reset_date:
            self._cost_today = 0.0
            self._cost_reset_date = today
            logger.info("Reset daily cost counter")

    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost based on token usage."""
        # Rough pricing (per 1K tokens)
        prices = {
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.0020},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        }

        model = self.config.model
        if model not in prices:
            logger.warning(
                f"Unknown model {model} for cost estimation, \
                    using gpt-3.5-turbo pricing"
            )
            model = "gpt-3.5-turbo"

        price = prices[model]
        cost = (prompt_tokens / 1000 * price["input"]) + (
            completion_tokens / 1000 * price["output"]
        )
        return cost

    def _check_cost_limit(self) -> bool:
        """Check if we've exceeded daily cost limit."""
        self._reset_cost_if_needed()
        return self._cost_today < self.config.max_cost_per_day

    def _update_cost(self, prompt_tokens: int, completion_tokens: int):
        """Update cost tracking."""
        cost = self._estimate_cost(prompt_tokens, completion_tokens)
        self._cost_today += cost
        logger.debug(f"Added cost ${cost:.4f}, total today: ${self._cost_today:.4f}")

    def _get_cache_key(self, article: Article) -> str:
        """Generate cache key for article."""
        # Use title + source + published date
        key_data = {
            "title": article.title,
            "source": article.source,
            "published": article.published_at.isoformat()[:10],  # Date only
            "config": {
                "model": self.config.model,
                "language": self.config.language,
                "style": self.config.style,
            },
        }
        return json.dumps(key_data, sort_keys=True)

    def _check_cache(self, article: Article) -> dict[str, Any] | None:
        """Check if article summary is cached."""
        if not self.config.cache_enabled:
            return None

        cache_key = self._get_cache_key(article)

        if cache_key in self._cache:
            cached_time, summary_data = self._cache[cache_key]
            age_hours = (datetime.now() - cached_time).total_seconds() / 3600

            if age_hours < self.config.cache_ttl_hours:
                logger.debug(f"Cache hit for article: {article.title}")
                return summary_data
            else:
                # Cache expired
                del self._cache[cache_key]

        return None

    def _save_to_cache(self, article: Article, summary_data: dict[str, Any]):
        """Save summary to cache."""
        if not self.config.cache_enabled:
            return

        cache_key = self._get_cache_key(article)
        self._cache[cache_key] = (datetime.now(), summary_data)
        logger.debug(f"Cached summary for article: {article.title}")

    def _build_prompt(self, article: Article) -> str:
        """Build prompt for summarization."""
        language = self.config.language
        if language == "auto":
            # Detect language from content
            content = article.content or article.summary or ""
            # Simple detection: check for Chinese characters
            if any("\u4e00" <= char <= "\u9fff" for char in content[:100]):
                language = "zh"
            else:
                language = "en"

        # Truncate content to fit token limit
        content = article.content or article.summary or ""
        if len(content) > 8000:
            content = content[:8000] + "..."

        if language == "zh":
            prompt = f"""请为以下AI新闻文章生成摘要：

标题: {article.title}
来源: {article.source}
内容: {content}

请生成：
1. 3-5个关键要点（使用中文）
2. 文章主要贡献或创新点
3. 对AI领域的影响
4. 相关技术或模型名称（如果有）

请使用简洁专业的中文，避免重复信息。"""
        else:
            prompt = f"""Please summarize the following AI news article:

Title: {article.title}
Source: {article.source}
Content: {content}

Please provide:
1. 3-5 key bullet points
2. Main contribution or innovation
3. Impact on AI field
4. Relevant technologies or model names (if any)

Use concise, professional language. Avoid repeating information."""

        return prompt

    async def summarize_article(self, article: Article) -> dict[str, Any] | None:
        """
        Summarize a single article.

        Args:
            article: Article to summarize

        Returns:
            Dictionary with summary, key_points, tags, etc.
        """
        # Check cache first
        cached = self._check_cache(article)
        if cached:
            return cached

        # Check cost limit
        if not self._check_cost_limit():
            logger.warning(
                f"Daily cost limit exceeded (${self.config.max_cost_per_day})"
            )
            if self.config.enable_fallback:
                return self._fallback_summarization(article)
            return None

        # Build prompt
        prompt = self._build_prompt(article)

        try:
            client = self._get_client()

            response = await client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI news analyst specializing in \
                            summarizing technical AI news articles.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                response_format={"type": "json_object"},
            )

            # Parse response
            content = response.choices[0].message.content
            if content is None:
                logger.warning("Response content is None, using empty summary")
                result = {"summary": ""}
            else:
                try:
                    result = json.loads(content)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON response, using raw text")
                    result = {"summary": content}

            # Extract key points
            key_points = self._extract_key_points(result)
            tags = self._extract_tags(result, article)

            # Prepare summary data
            summary_data = {
                "llm_summary": result.get("summary", ""),
                "llm_key_points": key_points,
                "llm_tags": tags,
                "model_used": self.config.model,
                "tokens_used": response.usage.total_tokens  # type: ignore
                if hasattr(response, "usage")
                else 0,
            }

            # Update cost tracking
            if hasattr(response, "usage"):
                self._update_cost(
                    response.usage.prompt_tokens,  # type: ignore
                    response.usage.completion_tokens,  # type: ignore
                )

            # Cache result
            self._save_to_cache(article, summary_data)

            logger.info(f"Summarized article: {article.title}")
            return summary_data

        except Exception as e:
            logger.error(f"Failed to summarize article {article.title}: {e}")
            if self.config.enable_fallback:
                return self._fallback_summarization(article)
            return None

    async def summarize_batch(self, articles: list[Article]) -> list[dict[str, Any]]:
        """
        Summarize multiple articles in batches.

        Args:
            articles: List of articles to summarize

        Returns:
            List of summary data (in same order as input)
        """
        results = []

        for i in range(0, len(articles), self.config.batch_size):
            batch = articles[i : i + self.config.batch_size]
            logger.info(
                f"Processing batch {i // self.config.batch_size + 1} \
                    of {len(batch)} articles"
            )

            # Summarize each article in batch
            batch_results = []
            for article in batch:
                result = await self.summarize_article(article)
                batch_results.append(result)

            results.extend(batch_results)

            # Delay between batches to avoid rate limiting
            if i + self.config.batch_size < len(articles):
                await asyncio.sleep(self.config.batch_delay_seconds)

        return results

    def _extract_key_points(self, result: dict[str, Any]) -> list[str]:
        """Extract key points from LLM response."""
        key_points = []

        # Try different possible response formats
        if "key_points" in result and isinstance(result["key_points"], list):
            key_points = result["key_points"]
        elif "bullet_points" in result and isinstance(result["bullet_points"], list):
            key_points = result["bullet_points"]
        elif "key_insights" in result and isinstance(result["key_insights"], list):
            key_points = result["key_insights"]
        elif "summary" in result and isinstance(result["summary"], str):
            # Split summary into sentences
            import re

            sentences = re.split(r"[.!?]+", result["summary"])
            key_points = [s.strip() for s in sentences if len(s.strip()) > 20][:5]

        # Ensure we have list of strings
        if not isinstance(key_points, list):
            key_points = []

        # Truncate each point
        key_points = [str(point)[:200] for point in key_points[:5]]
        return key_points

    def _extract_tags(self, result: dict[str, Any], article: Article) -> list[str]:
        """Extract tags from LLM response."""
        tags = []

        # Try to get tags from LLM response
        if "tags" in result and isinstance(result["tags"], list):
            tags.extend(result["tags"])

        # Add article's existing tags
        tags.extend(article.tags)

        # Deduplicate
        return list(set(tags[:10]))

    def _fallback_summarization(self, article: Article) -> dict[str, Any]:
        """Fallback summarization when LLM fails or cost limit exceeded."""
        logger.info(f"Using fallback summarization for: {article.title}")

        if self.config.fallback_method == "extractive":
            summary = self._extractive_summary(article)
        else:
            summary = self._lead_summary(article)

        return {
            "llm_summary": summary,
            "llm_key_points": [
                summary[:100] + "..." if len(summary) > 100 else summary
            ],
            "llm_tags": article.tags[:5],
            "model_used": "fallback",
            "tokens_used": 0,
        }

    def _extractive_summary(self, article: Article) -> str:
        """Extractive summary using simple text rank (simplified)."""
        content = article.content or article.summary or ""
        if not content:
            return article.title

        # Simple approach: take first few sentences
        import re

        sentences = re.split(r"[.!?]+", content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

        # Take first 3 sentences or first 300 chars
        summary = " ".join(sentences[:3])
        if len(summary) > 300:
            summary = summary[:300] + "..."

        return summary

    def _lead_summary(self, article: Article) -> str:
        """Lead summary (first part of content)."""
        content = article.content or article.summary or ""
        if not content:
            return article.title

        # Take first 300 characters
        summary = content[:300]
        if len(content) > 300:
            summary += "..."

        return summary

    def apply_summary_to_article(
        self, article: Article, summary_data: dict[str, Any]
    ) -> Article:
        """Apply summary data to article object."""
        if not summary_data:
            return article

        article.llm_summary = summary_data.get("llm_summary")
        article.llm_key_points = summary_data.get("llm_key_points", [])
        article.llm_tags = summary_data.get("llm_tags", [])

        # Update tags if we have new ones
        if article.llm_tags:
            article.tags = list(set(article.tags + article.llm_tags))[:15]

        return article


# Convenience function
async def summarize_articles(
    articles: list[Article], config: SummarizationConfig | None = None
) -> list[Article]:
    """Summarize list of articles."""
    summarizer = OpenAISummarizer(config)
    summary_data_list = await summarizer.summarize_batch(articles)

    results = []
    for article, summary_data in zip(articles, summary_data_list, strict=False):
        if summary_data:
            updated_article = summarizer.apply_summary_to_article(article, summary_data)
            results.append(updated_article)
        else:
            results.append(article)

    return results
