#!/usr/bin/env python3
"""
Test that all modules can be imported.
"""

import sys
sys.path.insert(0, './src')

modules_to_test = [
    'ainews',
    'ainews.config',
    'ainews.models',
    'ainews.crawler.base',
    'ainews.crawler.rss_crawler',
    'ainews.processor.deduplicator',
    'ainews.processor.categorizer',
    'ainews.processor.summarizer',
    'ainews.generator.site_generator',
    'ainews.storage.database',
]

print("Testing imports...")
for module in modules_to_test:
    try:
        __import__(module)
        print(f"OK {module}")
    except Exception as e:
        print(f"FAIL {module}: {e}")

print("\nTesting configuration load...")
try:
    from ainews.config import load_config
    config = load_config()
    print(f"✓ Config loaded: {len(config.sources)} sources")
except Exception as e:
    print(f"✗ Config load failed: {e}")

print("\nAll tests completed.")