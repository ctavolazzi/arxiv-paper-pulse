"""Beehiiv RSS feed reader for fetching and parsing newsletter articles."""
import feedparser
import ssl
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from . import config
from .utils import get_unique_id

# Handle SSL certificate issues (common on macOS)
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context


class BeehiivReader:
    """Reads and manages Beehiiv RSS feeds."""

    def __init__(self, feed_url: str):
        """
        Initialize Beehiiv reader.

        Args:
            feed_url: URL of the Beehiiv RSS feed
        """
        self.feed_url = feed_url
        self._ensure_directories()

    def _ensure_directories(self):
        """Create data directories if they don't exist."""
        beehiiv_dir = Path(config.BEEHIIV_DATA_DIR)
        beehiiv_dir.mkdir(parents=True, exist_ok=True)

    def fetch_feed(self, force_refresh: bool = False) -> Dict:
        """
        Fetch and parse the RSS feed.

        Args:
            force_refresh: If True, always fetch fresh data

        Returns:
            Dictionary with feed metadata and articles
        """
        feed = feedparser.parse(self.feed_url)

        if feed.bozo:
            raise ValueError(f"Failed to parse RSS feed: {feed.bozo_exception}")

        feed_info = feed.feed

        # Extract feed metadata
        feed_data = {
            "feed_url": self.feed_url,
            "title": feed_info.get("title", "Unknown"),
            "description": feed_info.get("subtitle") or feed_info.get("description", ""),
            "link": feed_info.get("link", ""),
            "language": feed_info.get("language", ""),
            "updated": feed_info.get("updated") or feed_info.get("published", ""),
            "categories": [tag.term for tag in feed_info.tags] if "tags" in feed_info else [],
            "image_url": feed_info.image.get("href") if "image" in feed_info and isinstance(feed_info.image, dict) else None,
            "articles": []
        }

        # Extract articles
        for entry in feed.entries:
            article = {
                "title": entry.get("title", "Untitled"),
                "link": entry.get("link", ""),
                "published": entry.get("published") or entry.get("updated", ""),
                "summary": entry.get("summary", ""),
                "content": entry.get("content", [{}])[0].get("value", "") if entry.get("content") else "",
                "author": entry.get("author", ""),
                "tags": [tag.term for tag in entry.tags] if "tags" in entry else [],
                "id": entry.get("id") or entry.get("link", ""),
                "feed_url": self.feed_url
            }
            feed_data["articles"].append(article)

        # Save to file
        if not force_refresh:
            self._save_feed_data(feed_data)

        return feed_data

    def _create_file_path(self, directory: Path, prefix: str) -> Path:
        """Create a timestamped file path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return directory / f"{prefix}_{timestamp}.json"

    def _save_feed_data(self, feed_data: Dict):
        """Save feed data to JSON file."""
        beehiiv_dir = Path(config.BEEHIIV_DATA_DIR)
        file_path = self._create_file_path(beehiiv_dir, "beehiiv_feed")
        with open(file_path, "w") as f:
            json.dump(feed_data, f, indent=2)
        print(f"Saved Beehiiv feed data to {file_path}")

    def get_latest_articles(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get the latest articles from the feed.

        Args:
            limit: Maximum number of articles to return

        Returns:
            List of article dictionaries
        """
        feed_data = self.fetch_feed()
        articles = feed_data.get("articles", [])

        if limit:
            articles = articles[:limit]

        return articles

    def get_article_by_id(self, article_id: str) -> Optional[Dict]:
        """
        Get a specific article by ID.

        Args:
            article_id: Article ID or link

        Returns:
            Article dictionary or None if not found
        """
        feed_data = self.fetch_feed()

        for article in feed_data.get("articles", []):
            if article.get("id") == article_id or article.get("link") == article_id:
                return article

        return None

    def get_feed_info(self) -> Dict:
        """
        Get feed metadata without fetching articles.

        Returns:
            Dictionary with feed information
        """
        feed = feedparser.parse(self.feed_url)

        if feed.bozo:
            raise ValueError(f"Failed to parse RSS feed: {feed.bozo_exception}")

        feed_info = feed.feed

        return {
            "feed_url": self.feed_url,
            "title": feed_info.get("title", "Unknown"),
            "description": feed_info.get("subtitle") or feed_info.get("description", ""),
            "link": feed_info.get("link", ""),
            "language": feed_info.get("language", ""),
            "updated": feed_info.get("updated") or feed_info.get("published", ""),
            "categories": [tag.term for tag in feed_info.tags] if "tags" in feed_info else [],
            "image_url": feed_info.image.get("href") if "image" in feed_info and isinstance(feed_info.image, dict) else None,
            "article_count": len(feed.entries)
        }


def get_stored_articles() -> List[Dict]:
    """
    Get all articles from stored feed files.

    Returns:
        List of all articles across all stored feeds
    """
    beehiiv_dir = Path(config.BEEHIIV_DATA_DIR)

    if not beehiiv_dir.exists():
        return []

    all_articles = []
    feed_files = sorted(beehiiv_dir.glob("beehiiv_feed_*.json"), reverse=True)

    for feed_file in feed_files:
        try:
            with open(feed_file, "r") as f:
                feed_data = json.load(f)
                articles = feed_data.get("articles", [])
                all_articles.extend(articles)
        except Exception as e:
            print(f"Error reading {feed_file}: {e}")

    return all_articles
