#!/usr/bin/env python3
"""
Main pipeline script for AI news aggregation.
Runs crawl, processing, and summarization.
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ainews.config import load_config
from ainews.crawler.rss_crawler import crawl_sources
from ainews.processor import process_articles
from ainews.processor.summarizer import SummarizationConfig, summarize_articles
from ainews.storage import save_articles  # We'll implement storage next


async def main(date=None):
    """Run full pipeline for given date."""
    if date is None:
        # Default to yesterday
        date = datetime.now() - timedelta(days=1)
        date = date.replace(hour=0, minute=0, second=0, microsecond=0)

    print(f"Running AI news pipeline for {date.date()}")

    # Load configuration
    config = load_config()
    print(f"Loaded {len([s for s in config.sources if s.enabled])} enabled sources")

    # Filter sources for RSS only (for now)
    rss_sources = [s for s in config.sources if s.enabled and s.type == "rss"]
    print(f"Using {len(rss_sources)} RSS sources")

    # Step 1: Crawl
    print("Crawling RSS feeds...")
    articles = await crawl_sources(rss_sources, max_age_days=1)
    print(f"Crawled {len(articles)} articles")

    if not articles:
        print("No articles found, exiting")
        return []

    # Step 2: Process (deduplicate, categorize, score)
    print("Processing articles...")
    processed_articles, duplicate_articles = process_articles(articles)
    print(
        f"Processed: {len(processed_articles)} unique,\
              {len(duplicate_articles)} duplicates"
    )

    # Step 3: Summarize with OpenAI
    if processed_articles and config.settings.get("enable_summarization", True):
        print("Generating summaries with OpenAI...")
        summarization_config = SummarizationConfig(
            model=config.settings.get("summarization_model", "gpt-3.5-turbo"),
            language="auto",
        )
        processed_articles = await summarize_articles(
            processed_articles, summarization_config
        )
        print(f"Summarized {len(processed_articles)} articles")

    # Step 4: Save results
    output_dir = Path(config.settings.get("output_dir", "./data/processed"))
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"articles_{date.strftime('%Y%m%d')}.json"
    save_articles(processed_articles, str(output_file))
    print(f"Results saved to {output_file}")

    return processed_articles


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AI news pipeline")
    parser.add_argument("--date", type=str, help="Date in YYYY-MM-DD format")
    parser.add_argument(
        "--output", type=str, default="./data/processed", help="Output directory"
    )

    args = parser.parse_args()

    # Parse date
    target_date = None
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(f"Invalid date format: {args.date}. Use YYYY-MM-DD")
            sys.exit(1)

    # Run pipeline
    try:
        articles = asyncio.run(main(target_date))
        print(f"Pipeline completed. Processed {len(articles)} articles.")
    except Exception as e:
        print(f"Pipeline failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
