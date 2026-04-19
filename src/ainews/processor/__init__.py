"""
Article processing pipeline: deduplication, categorization, tagging.
"""

from .categorizer import (
    CategorizationConfig,
    Categorizer,
    calculate_importance,
    categorize_article,
    extract_tags,
)
from .deduplicator import DeduplicationConfig, Deduplicator


class ProcessingPipeline:
    """Complete processing pipeline for articles."""

    def __init__(
        self,
        deduplication_config: DeduplicationConfig | None = None,
        categorization_config: CategorizationConfig | None = None,
    ):
        self.deduplicator = Deduplicator(deduplication_config)
        self.categorizer = Categorizer(categorization_config)

    def process(self, articles: list) -> tuple:
        """
        Process articles through full pipeline.

        Args:
            articles: List of articles to process

        Returns:
            Tuple of (processed_articles, duplicate_articles)
        """
        # Step 1: Deduplication
        unique_articles, duplicate_articles = self.deduplicator.deduplicate(articles)

        # Step 2: Categorization and tagging
        processed_articles = []
        for article in unique_articles:
            # Categorize
            categories = self.categorizer.categorize(article)
            article.categories = categories

            # Extract tags
            tags = self.categorizer.extract_tags(article)
            article.tags = tags

            # Calculate importance
            importance = self.categorizer.calculate_importance(article)
            article.importance_score = importance

            processed_articles.append(article)

        return processed_articles, duplicate_articles


# Convenience functions
def process_articles(articles: list) -> tuple:
    """Process articles using default pipeline."""
    pipeline = ProcessingPipeline()
    return pipeline.process(articles)
