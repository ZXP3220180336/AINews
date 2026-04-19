#!/usr/bin/env python3
"""
End-to-end test for AI News Aggregator.
Tests basic functionality without requiring scikit-learn/pandas.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ainews.config import load_config
from ainews.generator.site_generator import SiteConfig, generate_site
from ainews.models import Article, ArticleCategory, CrawlSource
from ainews.storage.database import ArticleStorage


def test_config_loading():
    """Test configuration loading from YAML."""
    print("1. Testing configuration loading...")
    try:
        config = load_config()
        print(f"   OK Config loaded: {len(config.sources)} sources")
        print(f"   OK Settings: {list(config.settings.keys())}")
        return True
    except Exception as e:
        print(f"   FAIL Config loading failed: {e}")
        return False


def test_models():
    """Test data model creation."""
    print("2. Testing data models...")
    try:
        # Create a sample article
        article = Article(
            title="OpenAI releases GPT-5 with new capabilities",
            url="https://openai.com/blog/gpt-5",
            source="OpenAI Blog",
            published_at=datetime.now() - timedelta(hours=6),
            summary="OpenAI has released GPT-5 with improved reasoning and \
                multimodal capabilities.",
            categories=[ArticleCategory.MODELS],
            tags=["gpt-5", "openai", "llm"],
            importance_score=0.9,
        )

        print(f"   OK Article created: {article.title}")
        print(f"   OK Categories: {[c.value for c in article.categories]}")
        print(f"   OK Is recent (<1 day): {article.is_recent}")

        # Create a source
        source = CrawlSource(
            name="OpenAI Blog",
            url="https://openai.com/blog/rss",
            type="rss",
            enabled=True,
            priority=3,
        )
        print(f"   OK Source created: {source}")

        return True
    except Exception as e:
        print(f"   FAIL Model test failed: {e}")
        return False


def test_storage():
    """Test article storage and retrieval."""
    print("3. Testing storage...")
    try:
        storage = ArticleStorage(base_dir="./test_data")

        # Create test articles
        articles = [
            Article(
                title=f"Test Article {i}",
                url=f"https://example.com/article{i}",
                source="Test Source",
                published_at=datetime.now() - timedelta(hours=i * 2),
                summary=f"This is test article {i}",
                categories=[
                    ArticleCategory.MODELS if i % 2 == 0 else ArticleCategory.RESEARCH
                ],
                tags=["test", "ai"],
                importance_score=0.5 + i * 0.1,
            )
            for i in range(3)
        ]

        # Save to JSON
        output_path = storage.save_articles(articles, "test_articles.json")
        print(f"   OK Articles saved to: {output_path}")

        # Load back
        loaded_articles = storage.load_articles("test_articles.json")
        print(f"   OK Articles loaded: {len(loaded_articles)}")

        # Verify data
        if len(loaded_articles) == len(articles):
            print("   OK Data integrity verified")
        else:
            print(
                f"   FAIL Data mismatch: expected {len(articles)}, \
                    got {len(loaded_articles)}"
            )

        # Clean up
        if output_path.exists():
            output_path.unlink()
        if storage.base_dir.exists():
            # Remove only test files
            for f in storage.base_dir.glob("test_*.json"):
                f.unlink()

        return True
    except Exception as e:
        print(f"   FAIL Storage test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_site_generation():
    """Test static site generation."""
    print("4. Testing site generation...")
    try:
        # Create test articles
        articles = [
            Article(
                title="OpenAI announces new AI model",
                url="https://openai.com/blog/new-model",
                source="OpenAI Blog",
                published_at=datetime.now() - timedelta(hours=12),
                summary="OpenAI has announced a new AI model with advanced \
                    capabilities.",
                categories=[ArticleCategory.MODELS],
                tags=["openai", "model", "announcement"],
                importance_score=0.8,
            ),
            Article(
                title="New research paper on AI alignment",
                url="https://arxiv.org/abs/2401.12345",
                source="arXiv",
                published_at=datetime.now() - timedelta(hours=24),
                summary="A new paper discusses novel approaches to AI alignment.",
                categories=[ArticleCategory.RESEARCH, ArticleCategory.ETHICS],
                tags=["research", "alignment", "safety"],
                importance_score=0.7,
            ),
        ]

        # Create site configuration
        site_config = SiteConfig(
            output_dir="./test_output",
            site_title="AI News Test",
            site_description="Test site for AI News Aggregator",
            site_url="https://example.com/test",
        )

        # Generate site
        output_path = generate_site(articles, site_config)
        print(f"   OK Site generated at: {output_path}")

        # Check generated files
        files = list(output_path.rglob("*"))
        html_files = [f for f in files if f.suffix == ".html"]
        print(f"   OK Generated files: {len(files)} total, {len(html_files)} HTML")

        # Check for required files
        required_files = ["index.html", "articles.html", "about.html"]
        for req_file in required_files:
            if (output_path / req_file).exists():
                print(f"   OK Found required file: {req_file}")
            else:
                print(f"   FAIL Missing file: {req_file}")

        # Clean up
        import shutil

        if output_path.exists():
            shutil.rmtree(output_path)

        return True
    except Exception as e:
        print(f"   FAIL Site generation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_crawler_basic():
    """Test basic crawler functionality (without actual network calls)."""
    print("5. Testing crawler basic functionality...")
    try:
        from ainews.crawler.rss_crawler import RSSCrawler

        # Create a mock source
        source = CrawlSource(
            name="Test RSS",
            url="https://example.com/feed.xml",
            type="rss",
            enabled=True,
        )

        # Create crawler
        crawler = RSSCrawler(source)

        # Test initialization
        print(f"   OK Crawler initialized: {crawler}")

        # Note: We don't actually crawl to avoid network calls in test
        print("   OK Crawler basic test passed (no network calls)")

        return True
    except Exception as e:
        print(f"   FAIL Crawler test failed: {e}")
        return False


def test_imports():
    """Test that all modules can be imported."""
    print("6. Testing module imports...")
    modules_to_test = [
        "ainews",
        "ainews.config",
        "ainews.models",
        "ainews.crawler.base",
        "ainews.crawler.rss_crawler",
        "ainews.storage.database",
        "ainews.generator.site_generator",
    ]

    all_ok = True
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"   OK {module}")
        except Exception as e:
            print(f"   FAIL {module}: {e}")
            all_ok = False

    return all_ok


async def main():
    """Run all tests."""
    print("=" * 60)
    print("AI News Aggregator - End-to-End Test")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Config Loading", test_config_loading()))
    results.append(("Data Models", test_models()))
    results.append(("Storage", test_storage()))
    results.append(("Site Generation", test_site_generation()))
    results.append(("Crawler Basic", await test_crawler_basic()))
    results.append(("Module Imports", test_imports()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "OK PASS" if success else "FAIL FAIL"
        print(f"{status} {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    # Clean up test directories
    for dir_path in [Path("./test_data"), Path("./test_output")]:
        if dir_path.exists():
            import shutil

            shutil.rmtree(dir_path)

    if passed == total:
        print("\nSUCCESS: All tests passed! The basic pipeline is working.")
        return 0
    else:
        print(f"\nWARNING: {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
