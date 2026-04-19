"""
Article categorization and tagging.
"""

import re
from dataclasses import dataclass

from ..models import Article, ArticleCategory


@dataclass
class CategorizationConfig:
    """Configuration for categorization."""

    # Keywords for each category
    category_keywords: dict[ArticleCategory, list[str]] | None = None

    # Minimum confidence for auto-categorization
    min_confidence: float = 0.3

    # Use LLM for categorization (if available)
    use_llm: bool = False

    # Fallback to source category if no match
    use_source_category: bool = True


class Categorizer:
    """Categorize articles based on content and metadata."""

    # Default keywords for each category
    DEFAULT_KEYWORDS = {
        ArticleCategory.MODELS: [
            "model",
            "llm",
            "gpt",
            "gemini",
            "claude",
            "llama",
            "mistral",
            "transformer",
            "multimodal",
            "foundation model",
            "large language model",
            "参数",
            "模型",
            "大模型",
            "语言模型",
            "GPT",
            "LLM",
        ],
        ArticleCategory.AGENTS: [
            "agent",
            "autonomous",
            "auto-gpt",
            "babyagi",
            "langchain",
            "workflow",
            "orchestration",
            "reasoning",
            "planning",
            "智能体",
            "代理",
            "自动化",
            "自主",
            "Agent",
        ],
        ArticleCategory.RESEARCH: [
            "research",
            "paper",
            "arxiv",
            "preprint",
            "conference",
            "publication",
            "study",
            "experiment",
            "methodology",
            "研究",
            "论文",
            "学术",
            "实验",
            "arXiv",
            "预印本",
        ],
        ArticleCategory.BUSINESS: [
            "business",
            "company",
            "startup",
            "funding",
            "investment",
            "venture",
            "acquisition",
            "merger",
            "partnership",
            "product",
            "launch",
            "market",
            "industry",
            "商业",
            "公司",
            "融资",
            "投资",
            "创业",
            "收购",
            "产品发布",
        ],
        ArticleCategory.TOOLS: [
            "tool",
            "library",
            "framework",
            "platform",
            "sdk",
            "api",
            "github",
            "open source",
            "software",
            "package",
            "module",
            "工具",
            "库",
            "框架",
            "平台",
            "开源",
            "GitHub",
            "SDK",
        ],
        ArticleCategory.ETHICS: [
            "ethics",
            "safety",
            "alignment",
            "bias",
            "fairness",
            "transparency",
            "accountability",
            "regulation",
            "governance",
            "风险",
            "安全",
            "对齐",
            "偏见",
            "公平",
            "透明度",
            "监管",
        ],
        ArticleCategory.POLICY: [
            "policy",
            "regulation",
            "law",
            "government",
            "compliance",
            "standard",
            "guideline",
            "legislation",
            "bill",
            "act",
            "政策",
            "法规",
            "法律",
            "政府",
            "合规",
            "标准",
            "立法",
        ],
    }

    def __init__(self, config: CategorizationConfig | None = None):
        self.config = config or CategorizationConfig()

        # Use provided keywords or defaults
        if self.config.category_keywords is None:
            self.config.category_keywords = self.DEFAULT_KEYWORDS

        # Compile regex patterns for each category
        self._patterns = {}
        for category, keywords in self.config.category_keywords.items():
            # Create case-insensitive pattern
            pattern = r"\b(" + "|".join(re.escape(kw) for kw in keywords) + r")\b"
            self._patterns[category] = re.compile(pattern, re.IGNORECASE)

    def categorize(self, article: Article) -> list[ArticleCategory]:
        """
        Categorize an article.

        Args:
            article: Article to categorize

        Returns:
            List of categories (sorted by confidence)
        """
        categories = []

        # 1. Check if article already has categories from source
        if article.categories and self.config.use_source_category:
            categories.extend(article.categories)

        # 2. Auto-categorize based on content
        auto_categories = self._auto_categorize(article)
        categories.extend(auto_categories)

        # 3. Deduplicate and sort by confidence
        unique_categories = []
        seen = set()
        for cat in categories:
            if cat not in seen:
                unique_categories.append(cat)
                seen.add(cat)

        # If no categories found, use OTHER
        if not unique_categories:
            unique_categories = [ArticleCategory.OTHER]

        return unique_categories

    def _auto_categorize(self, article: Article) -> list[ArticleCategory]:
        """Auto-categorize article based on content."""
        # Combine title, summary, and content for analysis
        text = self._get_analysis_text(article)

        # Count keyword matches for each category
        scores = {}
        for category, pattern in self._patterns.items():
            matches = pattern.findall(text)
            score = len(matches) / max(1, len(text.split()))  # Normalize by word count
            if score >= self.config.min_confidence:
                scores[category] = score

        # Sort by score descending
        sorted_categories = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Return top categories (max 3)
        top_categories = [cat for cat, score in sorted_categories[:3]]
        return top_categories

    def _get_analysis_text(self, article: Article) -> str:
        """Get text for analysis (title + summary + content)."""
        parts = []

        if article.title:
            parts.append(article.title)

        if article.summary:
            parts.append(article.summary)

        if article.content:
            # Use first 5000 chars of content to avoid excessive processing
            content = article.content[:5000]
            parts.append(content)

        return " ".join(parts)

    def extract_tags(self, article: Article, max_tags: int = 10) -> list[str]:
        """
        Extract tags from article content.

        Args:
            article: Article to tag
            max_tags: Maximum number of tags to return

        Returns:
            List of tags
        """
        text = self._get_analysis_text(article)

        # Simple approach: extract words that appear multiple times
        # (excluding stop words and very short words)
        words = re.findall(r"\b\w{3,}\b", text.lower())

        # Count frequencies
        from collections import Counter

        word_counts = Counter(words)

        # Filter out common English/Chinese stop words
        stop_words = self._get_stop_words()
        filtered_counts = {
            word: count
            for word, count in word_counts.items()
            if word not in stop_words and count >= 2
        }

        # Sort by frequency
        sorted_words = sorted(filtered_counts.items(), key=lambda x: x[1], reverse=True)

        # Take top tags
        tags = [word for word, count in sorted_words[:max_tags]]

        # Also include any existing tags
        tags.extend(article.tags)

        # Deduplicate
        return list(set(tags))

    def _get_stop_words(self) -> set:
        """Get stop words for English and Chinese."""
        # Basic stop words
        english_stop = {
            "the",
            "and",
            "for",
            "are",
            "but",
            "not",
            "you",
            "all",
            "any",
            "can",
            "her",
            "was",
            "one",
            "our",
            "out",
            "day",
            "get",
            "has",
            "him",
            "his",
            "how",
            "man",
            "new",
            "now",
            "old",
            "see",
            "two",
            "who",
            "boy",
            "did",
            "its",
            "let",
            "put",
            "say",
            "she",
            "too",
            "use",
            "way",
            "why",
            "yes",
            "yet",
        }

        chinese_stop = {
            "的",
            "了",
            "在",
            "是",
            "我",
            "有",
            "和",
            "就",
            "不",
            "人",
            "都",
            "一",
            "一个",
            "上",
            "也",
            "很",
            "到",
            "说",
            "要",
            "去",
            "你",
            "会",
            "着",
            "没有",
            "看",
            "好",
            "自己",
            "这",
            "那",
            "什么",
            "我们",
            "他们",
            "这个",
            "那个",
            "这些",
            "那些",
        }

        return english_stop | chinese_stop

    def calculate_importance(self, article: Article) -> float:
        """
        Calculate importance score for article (0-1).

        Factors:
        - Source priority
        - Category importance
        - Content length
        - Presence of key entities
        """
        score = 0.0

        # 1. Source priority (if available from config)
        # Default: research sources > business sources > others
        if any(kw in article.source.lower() for kw in ["arxiv", "research", "paper"]):
            score += 0.3
        elif any(
            kw in article.source.lower() for kw in ["tech", "venture", "business"]
        ):
            score += 0.2
        else:
            score += 0.1

        # 2. Category importance
        category_weights = {
            ArticleCategory.MODELS: 1.0,
            ArticleCategory.AGENTS: 0.9,
            ArticleCategory.RESEARCH: 0.8,
            ArticleCategory.BUSINESS: 0.7,
            ArticleCategory.TOOLS: 0.6,
            ArticleCategory.ETHICS: 0.5,
            ArticleCategory.POLICY: 0.5,
            ArticleCategory.OTHER: 0.3,
        }

        if article.categories:
            max_cat_weight = max(
                category_weights.get(cat, 0.3) for cat in article.categories
            )
            score += max_cat_weight * 0.3
        else:
            score += 0.1

        # 3. Content length (normalized)
        if article.content:
            content_length = len(article.content)
            # Normalize: 0-1000 chars = 0.1, 1000-5000 = 0.2, 5000+ = 0.3
            if content_length > 5000:
                score += 0.3
            elif content_length > 1000:
                score += 0.2
            else:
                score += 0.1

        # 4. Has summary
        if article.summary and len(article.summary) > 50:
            score += 0.1

        # 5. Has multiple categories
        if len(article.categories) > 1:
            score += 0.1

        # Cap at 1.0
        return min(score, 1.0)


# Global instance for convenience
_default_categorizer = Categorizer()


def categorize_article(article: Article) -> list[ArticleCategory]:
    """Convenience function to categorize an article."""
    return _default_categorizer.categorize(article)


def extract_tags(article: Article, max_tags: int = 10) -> list[str]:
    """Convenience function to extract tags."""
    return _default_categorizer.extract_tags(article, max_tags)


def calculate_importance(article: Article) -> float:
    """Convenience function to calculate importance score."""
    return _default_categorizer.calculate_importance(article)
