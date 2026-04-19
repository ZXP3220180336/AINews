"""
Storage utilities for articles (JSON file-based).
"""

import json
import pickle
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

from ..models import Article


class ArticleStorage:
    """Simple file-based storage for articles."""

    def __init__(self, base_dir: Path | str = "./data"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_articles(self, articles: list[Article], filename: str) -> Path:
        """
        Save articles to JSON file.

        Args:
            articles: List of articles
            filename: Output filename (without path)

        Returns:
            Path to saved file
        """
        output_path = self.base_dir / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert articles to dicts
        articles_data = []
        for article in articles:
            article_dict = asdict(article)

            # Convert datetime objects to ISO format strings
            for key, value in article_dict.items():
                if isinstance(value, datetime):
                    article_dict[key] = value.isoformat()
                elif (
                    isinstance(value, list) and value and isinstance(value[0], datetime)
                ):
                    article_dict[key] = [
                        v.isoformat() if isinstance(v, datetime) else v for v in value
                    ]

            # Handle ArticleCategory enums
            if "categories" in article_dict:
                article_dict["categories"] = [cat.value for cat in article.categories]

            articles_data.append(article_dict)

        # Save as JSON
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(articles_data, f, ensure_ascii=False, indent=2)

        return output_path

    def load_articles(self, filename: str) -> list[Article]:
        """
        Load articles from JSON file.

        Args:
            filename: Input filename (without path)

        Returns:
            List of articles
        """
        input_path = self.base_dir / filename
        if not input_path.exists():
            return []

        with open(input_path, encoding="utf-8") as f:
            articles_data = json.load(f)

        articles = []
        for article_dict in articles_data:
            # Convert string dates back to datetime
            for key in ["published_at", "crawled_at", "updated_at"]:
                if key in article_dict and article_dict[key]:
                    try:
                        article_dict[key] = datetime.fromisoformat(article_dict[key])
                    except ValueError, TypeError:
                        # Keep as string if parsing fails
                        pass

            # Convert category strings back to ArticleCategory enums
            if "categories" in article_dict:
                from ..models import ArticleCategory

                categories = []
                for cat_str in article_dict["categories"]:
                    try:
                        category = ArticleCategory(cat_str)
                        categories.append(category)
                    except ValueError:
                        # Unknown category, skip
                        pass
                article_dict["categories"] = categories

            # Create Article object
            try:
                # Filter out None values for fields that can't be None
                required_fields = ["title", "url", "source", "published_at"]
                for field in required_fields:
                    if field not in article_dict or article_dict[field] is None:
                        raise ValueError(f"Missing required field: {field}")

                article = Article(**article_dict)
                articles.append(article)
            except Exception as e:
                print(f"Failed to load article: {e}")
                continue

        return articles

    def save_pickle(self, articles: list[Article], filename: str) -> Path:
        """Save articles using pickle (preserves Python objects)."""
        output_path = self.base_dir / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "wb") as f:
            pickle.dump(articles, f)

        return output_path

    def load_pickle(self, filename: str) -> list[Article]:
        """Load articles from pickle file."""
        input_path = self.base_dir / filename
        if not input_path.exists():
            return []

        with open(input_path, "rb") as f:
            articles = pickle.load(f)

        return articles

    def list_article_files(self, pattern: str = "articles_*.json") -> list[Path]:
        """List article files matching pattern."""
        return sorted(self.base_dir.glob(pattern))

    def get_latest_articles(self, days: int = 7) -> list[Article]:
        """Get articles from the last N days."""
        all_articles = []
        for filepath in self.list_article_files():
            try:
                articles = self.load_articles(filepath.name)
                all_articles.extend(articles)
            except Exception as e:
                print(f"Failed to load {filepath}: {e}")
                continue

        # Filter by date
        cutoff = datetime.now() - timedelta(days=days)
        recent_articles = [a for a in all_articles if a.published_at >= cutoff]

        return recent_articles


# Convenience functions
def save_articles(articles: list[Article], filepath: str) -> Path:
    """Save articles to JSON file."""
    storage = ArticleStorage(Path(filepath).parent)
    return storage.save_articles(articles, Path(filepath).name)


def load_articles(filepath: str) -> list[Article]:
    """Load articles from JSON file."""
    storage = ArticleStorage(Path(filepath).parent)
    return storage.load_articles(Path(filepath).name)
