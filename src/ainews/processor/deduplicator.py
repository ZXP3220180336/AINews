"""
Article deduplication using URL, title, and content similarity.
"""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..models import Article


@dataclass
class DeduplicationConfig:
    """Configuration for deduplication."""

    # Similarity thresholds
    url_similarity_threshold: float = 0.9
    title_similarity_threshold: float = 0.8
    content_similarity_threshold: float = 0.7

    # Methods to use
    use_url: bool = True
    use_title: bool = True
    use_content: bool = True

    # Content similarity method: "tfidf" or "embeddings"
    content_similarity_method: str = "embeddings"

    # Embeddings model (if using embeddings)
    embeddings_model: str = "all-MiniLM-L6-v2"

    # Maximum articles to process at once (for memory)
    batch_size: int = 100


class Deduplicator:
    """Deduplicate articles using multiple similarity measures."""

    def __init__(self, config: DeduplicationConfig | None = None):
        self.config = config or DeduplicationConfig()

        # Lazy load embeddings model
        self._embeddings_model = None
        self._vectorizer = None

    def deduplicate(
        self, articles: list[Article]
    ) -> tuple[list[Article], list[Article]]:
        """
        Deduplicate articles, keeping only unique ones.

        Args:
            articles: List of articles to deduplicate

        Returns:
            Tuple of (unique_articles, duplicate_articles)
        """
        if not articles:
            return [], []

        logger.info(f"Deduplicating {len(articles)} articles")

        # Group by source for faster comparison
        articles_by_source = {}
        for article in articles:
            articles_by_source.setdefault(article.source, []).append(article)

        # Process each source group
        all_unique = []
        all_duplicates = []

        for _source, source_articles in articles_by_source.items():
            unique, duplicates = self._deduplicate_group(source_articles)
            all_unique.extend(unique)
            all_duplicates.extend(duplicates)

        logger.info(
            f"Found {len(all_unique)} unique and \
                {len(all_duplicates)} duplicate articles"
        )
        return all_unique, all_duplicates

    def _deduplicate_group(
        self, articles: list[Article]
    ) -> tuple[list[Article], list[Article]]:
        """Deduplicate articles from the same source."""
        if len(articles) <= 1:
            return articles, []

        # Sort by importance (most important first)
        articles.sort(key=lambda a: a.importance_score, reverse=True)

        unique = []
        duplicates = []

        # Compare each article with already selected unique articles
        for article in articles:
            is_duplicate = False

            for unique_article in unique:
                if self._are_duplicates(article, unique_article):
                    is_duplicate = True
                    duplicates.append(article)
                    logger.debug(
                        f"Duplicate found: {article.title} -> {unique_article.title}"
                    )
                    break

            if not is_duplicate:
                unique.append(article)

        return unique, duplicates

    def _are_duplicates(self, article1: Article, article2: Article) -> bool:
        """Check if two articles are duplicates."""
        # URL similarity (exact or near-exact)
        if self.config.use_url:
            url_sim = self._url_similarity(article1.url, article2.url)
            if url_sim >= self.config.url_similarity_threshold:
                return True

        # Title similarity
        if self.config.use_title:
            title_sim = self._text_similarity(article1.title, article2.title)
            if title_sim >= self.config.title_similarity_threshold:
                return True

        # Content similarity
        if self.config.use_content and article1.content and article2.content:
            content_sim = self._content_similarity(article1.content, article2.content)
            if content_sim >= self.config.content_similarity_threshold:
                return True

        return False

    def _url_similarity(self, url1: str, url2: str) -> float:
        """Calculate URL similarity."""
        # Normalize URLs
        url1 = self._normalize_url(url1)
        url2 = self._normalize_url(url2)

        if url1 == url2:
            return 1.0

        # Use sequence similarity for URLs
        return SequenceMatcher(None, url1, url2).ratio()

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison."""
        # Remove protocol, www, trailing slashes, query params, fragments
        url = re.sub(r"^https?://(www\.)?", "", url)
        url = re.sub(r"/$", "", url)
        url = re.sub(r"\?.*$", "", url)
        url = re.sub(r"#.*$", "", url)
        url = url.lower()
        return url

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using sequence matching."""
        if not text1 or not text2:
            return 0.0

        # Simple preprocessing
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()

        if text1 == text2:
            return 1.0

        return SequenceMatcher(None, text1, text2).ratio()

    def _content_similarity(self, content1: str, content2: str) -> float:
        """Calculate content similarity using TF-IDF or embeddings."""
        if not content1 or not content2:
            return 0.0

        # Truncate content to avoid memory issues
        max_length = 10000
        if len(content1) > max_length:
            content1 = content1[:max_length]
        if len(content2) > max_length:
            content2 = content2[:max_length]

        if self.config.content_similarity_method == "embeddings":
            return self._embeddings_similarity(content1, content2)
        else:
            return self._tfidf_similarity(content1, content2)

    def _tfidf_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity using TF-IDF vectors."""
        if self._vectorizer is None:
            self._vectorizer = TfidfVectorizer(
                stop_words="english", max_features=1000, ngram_range=(1, 2)
            )

        try:
            vectors = self._vectorizer.fit_transform([text1, text2])
            similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]  # type: ignore
            return float(similarity)
        except Exception:
            # Fallback to simple text similarity
            return self._text_similarity(text1, text2)

    def _embeddings_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity using sentence embeddings."""
        if self._embeddings_model is None:
            self._embeddings_model = SentenceTransformer(self.config.embeddings_model)

        try:
            embeddings = self._embeddings_model.encode([text1, text2])
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]  # type: ignore
            return float(similarity)
        except Exception as e:
            logger.warning(f"Embeddings similarity failed: {e}")
            # Fallback to TF-IDF
            return self._tfidf_similarity(text1, text2)

    def find_clusters(
        self, articles: list[Article], threshold: float = 0.6
    ) -> list[list[Article]]:
        """
        Find clusters of similar articles.

        Args:
            articles: List of articles
            threshold: Similarity threshold for clustering

        Returns:
            List of clusters (each cluster is list of similar articles)
        """
        if len(articles) <= 1:
            return [articles] if articles else []

        # Compute pairwise similarity matrix
        n = len(articles)
        similarity_matrix = np.eye(n)

        for i in range(n):
            for j in range(i + 1, n):
                sim = self._content_similarity(articles[i].content, articles[j].content)  # type: ignore
                similarity_matrix[i][j] = sim
                similarity_matrix[j][i] = sim

        # Simple clustering: connect if similarity > threshold
        clusters = []
        assigned = set()

        for i in range(n):
            if i in assigned:
                continue

            cluster = [articles[i]]
            assigned.add(i)

            for j in range(i + 1, n):
                if j not in assigned and similarity_matrix[i][j] >= threshold:
                    cluster.append(articles[j])
                    assigned.add(j)

            clusters.append(cluster)

        return clusters


# Global logger
import logging

logger = logging.getLogger(__name__)
