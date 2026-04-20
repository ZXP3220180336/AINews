#!/usr/bin/env python3
"""
Generate static site from processed articles.
"""

import datetime as datetime_
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ainews.config import load_config
from ainews.generator.site_generator import SiteConfig, generate_site
from ainews.storage import load_articles  # We'll implement storage next


def main(date=None):
    """Generate site for given date."""
    if date is None:
        # Default to yesterday
        date = datetime_.datetime.now() - datetime_.timedelta(days=1)
        date = date.replace(hour=0, minute=0, second=0, microsecond=0)

    print(f"Generating site for {date.date()}")

    # Load configuration
    config = load_config()

    # Load articles for the date
    input_dir = Path(config.settings.get("output_dir", "./data/processed"))
    input_file = input_dir / f"articles_{date.strftime('%Y%m%d')}.json"

    if not input_file.exists():
        print(f"No articles found for {date.date()}")
        # Try to load any recent articles
        recent_files = sorted(input_dir.glob("articles_*.json"), reverse=True)
        if recent_files:
            input_file = recent_files[0]
            print(f"Using most recent file: {input_file.name}")
        else:
            print("No article files found")
            return None

    # Load articles
    print(f"Loading articles from {input_file}")
    articles = load_articles(str(input_file))

    if not articles:
        print("No articles to display")
        # Create placeholder message

        from ainews.models import Article, ArticleCategory

        articles = [
            Article(
                title="No news articles available for this date",
                url="https://github.com/yourusername/ainews",
                source="AI News Aggregator",
                published_at=datetime_.datetime.now(),
                summary="The daily crawl may have failed or no articles were found. \
                    Check back tomorrow.",
                categories=[ArticleCategory.OTHER],
                tags=["update", "status"],
            )
        ]

    # Generate site
    site_config = SiteConfig(
        output_dir="./data/output",
        site_title=config.settings.get("site_title", "AI News Digest"),
        site_description=config.settings.get(
            "site_description", "Daily AI news aggregator"
        ),
        site_url=config.settings.get(
            "site_url", "https://yourusername.github.io/ainews"
        ),
    )

    output_path = generate_site(articles, site_config)
    print(f"Site generated at: {output_path}")

    # Create a simple index of all generated files
    index_file = output_path / "file_index.txt"
    with open(index_file, "w") as f:
        for file_path in output_path.rglob("*"):
            if file_path.is_file():
                f.write(f"{file_path.relative_to(output_path)}\n")

    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate static site")
    parser.add_argument("--date", type=str, help="Date in YYYY-MM-DD format")
    parser.add_argument("--input", type=str, help="Input JSON file with articles")

    args = parser.parse_args()

    # Parse date
    target_date = None
    if args.date:
        try:
            target_date = datetime_.datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(f"Invalid date format: {args.date}. Use YYYY-MM-DD")
            sys.exit(1)

    try:
        output_path = main(target_date)
        if output_path:
            print(f"Site generation successful. Files in {output_path}")
        else:
            print("Site generation failed")
            sys.exit(1)
    except Exception as e:
        print(f"Site generation failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
