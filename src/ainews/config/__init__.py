"""
Configuration loading for AI news aggregator.
"""

import typing
from dataclasses import dataclass
from pathlib import Path

import yaml

from ..models import ArticleCategory, CrawlSource


@dataclass
class AppConfig:
    """Application configuration."""

    sources: list[CrawlSource]
    settings: dict[str, typing.Any]


def load_config(config_path: str | Path | None = None) -> AppConfig:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config file. If None, uses default.

    Returns:
        AppConfig object
    """
    if config_path is None:
        # Default to sources.yaml in same directory
        config_path = Path(__file__).parent / "sources.yaml"

    with open(config_path, encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    # Parse sources
    sources = []
    for source_data in config_data.get("sources", []):
        # Map category string to enum
        category_str = source_data.get("category", "").lower()
        category = None
        if category_str:
            for cat in ArticleCategory:
                if cat.value == category_str:
                    category = cat
                    break

        source = CrawlSource(
            name=source_data["name"],
            url=source_data["url"],
            type=source_data["type"],
            enabled=source_data.get("enabled", True),
            priority=source_data.get("priority", 1),
            config=source_data.get("config", {}),
            delay_seconds=source_data.get("delay_seconds", 1.0),
            max_pages=source_data.get("max_pages", 10),
            required_keywords=source_data.get("required_keywords", []),
            excluded_keywords=source_data.get("excluded_keywords", []),
            parser=source_data.get("parser"),
            category=category,
        )
        sources.append(source)

    # Get settings
    settings = config_data.get("settings", {})

    return AppConfig(sources=sources, settings=settings)


def save_config(config: AppConfig, config_path: str | Path | None = None) -> None:
    """
    Save configuration to YAML file.

    Args:
        config: AppConfig object
        config_path: Path to save config
    """
    if config_path is None:
        config_path = Path(__file__).parent / "sources.yaml"

    config_data = {
        "sources": [],
        "settings": config.settings,
    }

    for source in config.sources:
        source_data = {
            "name": source.name,
            "url": source.url,
            "type": source.type,
            "enabled": source.enabled,
            "priority": source.priority,
            "config": source.config,
            "delay_seconds": source.delay_seconds,
            "max_pages": source.max_pages,
            "required_keywords": source.required_keywords,
            "excluded_keywords": source.excluded_keywords,
            "parser": source.parser,
            "category": source.category.value if source.category else None,
        }
        config_data["sources"].append(source_data)

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)
