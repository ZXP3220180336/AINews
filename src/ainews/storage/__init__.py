"""
Storage utilities for articles.
"""

from .database import ArticleStorage, load_articles, save_articles

__all__ = ["ArticleStorage", "save_articles", "load_articles"]
