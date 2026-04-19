"""
Static site generator for AI news aggregator.
"""

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from jinja2 import Environment, FileSystemLoader, select_autoescape
from loguru import logger

from ..models import Article, ArticleCategory


@dataclass
class SiteConfig:
    """Configuration for site generation."""
    # Paths
    output_dir: str = "./data/output"
    template_dir: str = "./src/ainews/generator/templates"
    static_dir: str = "./src/ainews/generator/static"

    # Site metadata
    site_title: str = "AI News Digest"
    site_description: str = "Daily digest of important AI news, research, and developments"
    site_url: str = "https://yourusername.github.io/ainews"
    site_author: str = "AI News Aggregator"

    # Features
    generate_rss: bool = True
    generate_archive: bool = True
    generate_category_pages: bool = True

    # Design
    theme: str = "light"  # "light" or "dark"
    posts_per_page: int = 20

    # Analytics (optional)
    google_analytics_id: Optional[str] = None


class SiteGenerator:
    """Generate static website from articles."""

    def __init__(self, config: SiteConfig = None):
        self.config = config or SiteConfig()
        self.env = None
        self._setup_jinja()

    def _setup_jinja(self):
        """Set up Jinja2 environment."""
        template_path = Path(self.config.template_dir)
        if not template_path.exists():
            template_path.mkdir(parents=True, exist_ok=True)
            self._create_default_templates()

        self.env = Environment(
            loader=FileSystemLoader(self.config.template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

        # Add custom filters
        self.env.filters['date_format'] = self._date_format
        self.env.filters['truncate'] = self._truncate

    def _create_default_templates(self):
        """Create default templates if they don't exist."""
        templates_dir = Path(self.config.template_dir)
        templates_dir.mkdir(parents=True, exist_ok=True)

        # Create base template
        base_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ site_title }}{% endblock %}</title>
    <meta name="description" content="{{ site_description }}">
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="/static/css/style.css">
    {% if google_analytics_id %}
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={{ google_analytics_id }}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());
        gtag('config', '{{ google_analytics_id }}');
    </script>
    {% endif %}
</head>
<body class="bg-gray-50 text-gray-900">
    <nav class="bg-white shadow-lg">
        <div class="container mx-auto px-4 py-3">
            <div class="flex justify-between items-center">
                <div class="flex items-center space-x-2">
                    <i class="fas fa-robot text-blue-600 text-2xl"></i>
                    <a href="/" class="text-xl font-bold text-blue-700">{{ site_title }}</a>
                </div>
                <div class="flex space-x-6">
                    <a href="/" class="text-gray-700 hover:text-blue-600">Today</a>
                    <a href="/archive/" class="text-gray-700 hover:text-blue-600">Archive</a>
                    <a href="/categories/" class="text-gray-700 hover:text-blue-600">Categories</a>
                    <a href="/about/" class="text-gray-700 hover:text-blue-600">About</a>
                </div>
            </div>
        </div>
    </nav>

    <main class="container mx-auto px-4 py-8">
        {% block content %}{% endblock %}
    </main>

    <footer class="bg-white border-t mt-12 py-8">
        <div class="container mx-auto px-4 text-center text-gray-600">
            <p>Generated on {{ generated_date|date_format('%Y-%m-%d %H:%M') }} UTC</p>
            <p class="mt-2">{{ site_description }}</p>
            <div class="mt-4">
                <a href="/rss.xml" class="text-orange-500 hover:text-orange-600 mr-4">
                    <i class="fas fa-rss"></i> RSS Feed
                </a>
                <a href="https://github.com/yourusername/ainews" class="text-gray-700 hover:text-black">
                    <i class="fab fa-github"></i> Source
                </a>
            </div>
        </div>
    </footer>

    <script src="/static/js/main.js"></script>
</body>
</html>"""
        (templates_dir / "base.html").write_text(base_template, encoding='utf-8')

        # Create index template
        index_template = """{% extends "base.html" %}

{% block title %}Today's AI News - {{ site_title }}{% endblock %}

{% block content %}
<div class="mb-8">
    <h1 class="text-3xl font-bold text-gray-900 mb-2">Today's AI News</h1>
    <p class="text-gray-600">{{ date|date_format('%B %d, %Y') }} - {{ articles|length }} articles</p>
</div>

<div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
    {% for category, count in category_counts.items() %}
    <div class="bg-white rounded-lg shadow p-4">
        <div class="flex justify-between items-center">
            <span class="font-semibold text-gray-700">{{ category|capitalize }}</span>
            <span class="bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded">{{ count }}</span>
        </div>
    </div>
    {% endfor %}
</div>

<div class="space-y-6">
    {% for article in articles %}
    <article class="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow">
        <div class="p-6">
            <div class="flex justify-between items-start mb-3">
                <div>
                    <span class="inline-block bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded mb-2">
                        {{ article.source }}
                    </span>
                    {% for category in article.categories %}
                    <span class="inline-block bg-gray-100 text-gray-800 text-xs font-semibold px-2.5 py-0.5 rounded ml-1">
                        {{ category.value }}
                    </span>
                    {% endfor %}
                </div>
                <span class="text-sm text-gray-500">{{ article.published_at|date_format('%Y-%m-%d') }}</span>
            </div>

            <h2 class="text-xl font-bold text-gray-900 mb-3">
                <a href="{{ article.url }}" target="_blank" class="hover:text-blue-600">{{ article.title }}</a>
            </h2>

            {% if article.llm_summary %}
            <p class="text-gray-700 mb-4">{{ article.llm_summary|truncate(200) }}</p>
            {% elif article.summary %}
            <p class="text-gray-700 mb-4">{{ article.summary|truncate(200) }}</p>
            {% endif %}

            {% if article.llm_key_points %}
            <ul class="mb-4 space-y-1">
                {% for point in article.llm_key_points[:3] %}
                <li class="flex items-start">
                    <i class="fas fa-chevron-right text-blue-500 mt-1 mr-2 text-xs"></i>
                    <span class="text-gray-700">{{ point }}</span>
                </li>
                {% endfor %}
            </ul>
            {% endif %}

            <div class="flex justify-between items-center mt-4 pt-4 border-t">
                <div>
                    {% for tag in article.tags[:5] %}
                    <span class="inline-block bg-gray-50 text-gray-600 text-xs px-2 py-1 rounded mr-1">{{ tag }}</span>
                    {% endfor %}
                </div>
                <a href="{{ article.url }}" target="_blank"
                   class="text-blue-600 hover:text-blue-800 font-medium">
                    Read full article <i class="fas fa-external-link-alt ml-1"></i>
                </a>
            </div>
        </div>
    </article>
    {% endfor %}
</div>

<div class="mt-8 text-center">
    <p class="text-gray-600">Updated daily at 8:00 AM UTC</p>
</div>
{% endblock %}"""
        (templates_dir / "index.html").write_text(index_template, encoding='utf-8')

        # Create RSS template
        rss_template = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
    <title>{{ site_title }}</title>
    <link>{{ site_url }}</link>
    <description>{{ site_description }}</description>
    <language>en</language>
    <atom:link href="{{ site_url }}/rss.xml" rel="self" type="application/rss+xml"/>
    <lastBuildDate>{{ generated_date|rss_date }}</lastBuildDate>

    {% for article in articles %}
    <item>
        <title>{{ article.title }}</title>
        <link>{{ article.url }}</link>
        <description><![CDATA[
            <strong>Source:</strong> {{ article.source }}<br/>
            <strong>Published:</strong> {{ article.published_at|date_format('%Y-%m-%d') }}<br/>
            {% if article.llm_summary %}
            {{ article.llm_summary }}
            {% elif article.summary %}
            {{ article.summary }}
            {% endif %}
        ]]></description>
        <pubDate>{{ article.published_at|rss_date }}</pubDate>
        <guid>{{ article.url }}</guid>
        {% for category in article.categories %}
        <category>{{ category.value }}</category>
        {% endfor %}
    </item>
    {% endfor %}
</channel>
</rss>"""
        (templates_dir / "rss.xml").write_text(rss_template, encoding='utf-8')

        logger.info("Created default templates")

    def _date_format(self, value, format_str='%Y-%m-%d'):
        """Jinja filter to format dates."""
        if isinstance(value, str):
            from dateutil.parser import parse
            value = parse(value)
        return value.strftime(format_str)

    def _truncate(self, text, length=100):
        """Jinja filter to truncate text."""
        if not text:
            return ""
        if len(text) <= length:
            return text
        return text[:length] + "..."

    def _copy_static_files(self):
        """Copy static files to output directory."""
        static_src = Path(self.config.static_dir)
        static_dest = Path(self.config.output_dir) / "static"

        if static_src.exists():
            if static_dest.exists():
                shutil.rmtree(static_dest)
            shutil.copytree(static_src, static_dest)
            logger.info(f"Copied static files to {static_dest}")
        else:
            # Create minimal static files
            static_dest.mkdir(parents=True, exist_ok=True)
            css_dir = static_dest / "css"
            css_dir.mkdir(exist_ok=True)

            # Create minimal CSS
            css_content = """/* Minimal styles - Tailwind does most of the work */
.article-card {
    transition: transform 0.2s ease-in-out;
}
.article-card:hover {
    transform: translateY(-2px);
}
.category-badge {
    transition: background-color 0.2s;
}
"""
            (css_dir / "style.css").write_text(css_content, encoding='utf-8')

            # Create minimal JS
            js_dir = static_dest / "js"
            js_dir.mkdir(exist_ok=True)
            js_content = """// Simple interactivity
document.addEventListener('DOMContentLoaded', function() {
    // Add click tracking for external links
    document.querySelectorAll('a[href^="http"]').forEach(link => {
        if (!link.href.includes(window.location.hostname)) {
            link.addEventListener('click', function() {
                console.log('External link clicked:', this.href);
            });
        }
    });
});
"""
            (js_dir / "main.js").write_text(js_content, encoding='utf-8')

    def generate(self, articles: List[Article], date: datetime = None) -> Path:
        """
        Generate static site for given articles.

        Args:
            articles: List of articles to include
            date: Date for the site (defaults to today)

        Returns:
            Path to output directory
        """
        if date is None:
            date = datetime.now()

        logger.info(f"Generating site for {date.date()} with {len(articles)} articles")

        # Prepare output directory
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Copy static files
        self._copy_static_files()

        # Prepare context
        context = self._prepare_context(articles, date)

        # Render templates
        self._render_templates(context, output_path)

        # Generate RSS feed if enabled
        if self.config.generate_rss:
            self._generate_rss_feed(articles, context, output_path)

        # Generate archive if enabled
        if self.config.generate_archive:
            self._update_archive(articles, date, output_path)

        logger.info(f"Site generated at {output_path.absolute()}")
        return output_path

    def _prepare_context(self, articles: List[Article], date: datetime) -> Dict[str, Any]:
        """Prepare template context."""
        # Sort articles by importance
        articles_sorted = sorted(articles, key=lambda a: a.importance_score, reverse=True)

        # Count by category
        category_counts = {}
        for article in articles:
            for category in article.categories:
                category_counts[category.value] = category_counts.get(category.value, 0) + 1

        return {
            "articles": articles_sorted,
            "date": date,
            "category_counts": category_counts,
            "site_title": self.config.site_title,
            "site_description": self.config.site_description,
            "site_url": self.config.site_url,
            "site_author": self.config.site_author,
            "google_analytics_id": self.config.google_analytics_id,
            "generated_date": datetime.now(),
        }

    def _render_templates(self, context: Dict[str, Any], output_path: Path):
        """Render Jinja2 templates."""
        # Render index.html
        template = self.env.get_template("index.html")
        html = template.render(**context)
        (output_path / "index.html").write_text(html, encoding='utf-8')

        # Create about page
        about_template = self.env.get_template("base.html")
        about_html = about_template.render(
            **context,
            title="About - " + self.config.site_title,
            content=f"""
            <div class="max-w-3xl mx-auto">
                <h1 class="text-3xl font-bold mb-6">About {self.config.site_title}</h1>
                <div class="prose prose-lg">
                    <p>This is an automated daily digest of important AI news, research papers, and developments in artificial intelligence.</p>
                    <p>The site is updated every morning at 8:00 AM UTC, aggregating content from various sources including:</p>
                    <ul>
                        <li>Research papers (arXiv, Google AI, OpenAI, Anthropic)</li>
                        <li>Tech news (TechCrunch, VentureBeat, MIT Technology Review)</li>
                        <li>Community discussions (Reddit r/MachineLearning, Hacker News)</li>
                        <li>Chinese sources (机器之心, 雷锋网, 知乎)</li>
                    </ul>
                    <p>Articles are automatically categorized, deduplicated, and summarized using AI.</p>
                    <p>This project is open source. You can find the code on <a href="https://github.com/yourusername/ainews" class="text-blue-600">GitHub</a>.</p>
                </div>
            </div>
            """
        )
        (output_path / "about.html").write_text(about_html, encoding='utf-8')

        logger.info("Rendered HTML templates")

    def _generate_rss_feed(self, articles: List[Article], context: Dict[str, Any], output_path: Path):
        """Generate RSS feed."""
        # Add RSS date filter
        import email.utils
        def rss_date_filter(date_val):
            if isinstance(date_val, str):
                from dateutil.parser import parse
                date_val = parse(date_val)
            return email.utils.formatdate(date_val.timestamp())

        self.env.filters['rss_date'] = rss_date_filter

        # Render RSS
        rss_template = self.env.get_template("rss.xml")
        rss_content = rss_template.render(**context)
        (output_path / "rss.xml").write_text(rss_content, encoding='utf-8')

        logger.info("Generated RSS feed")

    def _update_archive(self, articles: List[Article], date: datetime, output_path: Path):
        """Update archive index and add daily page."""
        archive_dir = output_path / "archive"
        archive_dir.mkdir(exist_ok=True)

        # Create daily archive page
        daily_context = self._prepare_context(articles, date)
        daily_context["is_archive"] = True

        template = self.env.get_template("index.html")
        daily_html = template.render(**daily_context)
        daily_path = archive_dir / f"{date.strftime('%Y-%m-%d')}.html"
        daily_path.write_text(daily_html, encoding='utf-8')

        # Update archive index (list of dates)
        archive_index_path = output_path / "archive" / "index.html"
        if archive_index_path.exists():
            # In a real implementation, we would read and update the index
            # For now, we'll just create a simple index
            pass

        # Create simple archive index
        archive_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Archive - {self.config.site_title}</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-50">
    <div class="container mx-auto px-4 py-8">
        <h1 class="text-3xl font-bold mb-6">Archive</h1>
        <p class="mb-6">Past editions of the AI News Digest.</p>
        <div class="bg-white rounded-lg shadow p-6">
            <h2 class="text-xl font-semibold mb-4">{date.strftime('%B %d, %Y')}</h2>
            <p class="mb-4">{len(articles)} articles</p>
            <a href="{date.strftime('%Y-%m-%d')}.html" class="text-blue-600 hover:text-blue-800">
                View this edition →
            </a>
        </div>
    </div>
</body>
</html>"""
        archive_index_path.write_text(archive_html, encoding='utf-8')

        logger.info(f"Updated archive for {date.date()}")

    def generate_category_pages(self, articles: List[Article], output_path: Path):
        """Generate category index pages."""
        if not self.config.generate_category_pages:
            return

        # Group articles by category
        articles_by_category = {}
        for article in articles:
            for category in article.categories:
                articles_by_category.setdefault(category.value, []).append(article)

        # Create category directory
        category_dir = output_path / "categories"
        category_dir.mkdir(exist_ok=True)

        # Generate category pages
        for category, cat_articles in articles_by_category.items():
            context = self._prepare_context(cat_articles, datetime.now())
            context["category"] = category
            context["title"] = f"{category.capitalize()} - {self.config.site_title}"

            template = self.env.get_template("index.html")
            html = template.render(**context)
            (category_dir / f"{category}.html").write_text(html, encoding='utf-8')

        # Generate category index
        categories_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Categories - {self.config.site_title}</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-50">
    <div class="container mx-auto px-4 py-8">
        <h1 class="text-3xl font-bold mb-6">Categories</h1>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {"".join(f'''
            <div class="bg-white rounded-lg shadow p-6">
                <h2 class="text-xl font-semibold mb-2">{cat.capitalize()}</h2>
                <p class="text-gray-600 mb-4">{len(articles)} articles</p>
                <a href="{cat}.html" class="text-blue-600 hover:text-blue-800">
                    Browse {cat} articles →
                </a>
            </div>
            ''' for cat, articles in articles_by_category.items())}
        </div>
    </div>
</body>
</html>"""
        (category_dir / "index.html").write_text(categories_html, encoding='utf-8')

        logger.info(f"Generated {len(articles_by_category)} category pages")


# Convenience function
def generate_site(articles: List[Article], config: SiteConfig = None) -> Path:
    """Generate site with default settings."""
    generator = SiteGenerator(config)
    return generator.generate(articles)