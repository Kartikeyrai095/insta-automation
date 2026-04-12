"""
TrendAgent — Scrapes trending topics from Google Trends RSS feed.
Falls back to Google News RSS top headlines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import feedparser

from config.settings import TRENDS_RSS_URL, TRENDS_GEO
from utils.logger import get_logger
from utils.dedup import filter_duplicates

logger = get_logger("trend")


@dataclass
class TrendItem:
    """A single trending topic."""
    topic: str
    traffic_volume: str = "Unknown"
    source: str = "google_trends"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    related_queries: list[str] = field(default_factory=list)


class TrendAgent:
    """
    Scrapes trending topics from Google Trends RSS.
    Returns a ranked list of unique, non-duplicate topics.
    """

    def __init__(self, geo: str = None, max_topics: int = 10):
        self.geo = geo or TRENDS_GEO
        self.rss_url = f"https://trends.google.com/trending/rss?geo={self.geo}"
        self.max_topics = max_topics

    def run(self) -> list[TrendItem]:
        """
        Fetch trending topics.

        Returns:
            List of TrendItem objects, ranked by relevance.
        """
        logger.info(f"📈 Fetching trends for geo={self.geo}")

        # Try Google Trends RSS first
        trends = self._fetch_google_trends()

        # Fallback to Google News if no trends
        if not trends:
            logger.warning("Google Trends returned no results, falling back to Google News")
            trends = self._fetch_google_news_fallback()

        if not trends:
            logger.error("No trending topics found from any source")
            return []

        # Deduplicate
        topic_strings = [t.topic for t in trends]
        unique_topics = filter_duplicates(topic_strings)

        # Filter the TrendItems to match unique topics
        unique_trends = [t for t in trends if t.topic in unique_topics]

        logger.info(f"✅ Found {len(unique_trends)} unique trending topics")
        for i, trend in enumerate(unique_trends[:5], 1):
            logger.info(f"  #{i}: {trend.topic} ({trend.traffic_volume})")

        return unique_trends[:self.max_topics]

    def _fetch_google_trends(self) -> list[TrendItem]:
        """Fetch from Google Trends RSS."""
        try:
            feed = feedparser.parse(self.rss_url)

            if feed.bozo and not feed.entries:
                logger.warning(f"Feed parse error: {feed.bozo_exception}")
                return []

            trends = []
            for entry in feed.entries:
                topic = entry.get("title", "").strip()
                if not topic:
                    continue

                # Try to extract traffic volume from description
                traffic = "Trending"
                description = entry.get("description", "")
                if description:
                    # Google Trends RSS sometimes includes traffic numbers
                    traffic = description.split(",")[0] if "," in description else description

                # Extract related queries from ht:news_item if available
                related = []
                news_items = entry.get("ht_news_item", [])
                if isinstance(news_items, list):
                    for item in news_items[:3]:
                        if isinstance(item, dict):
                            title = item.get("ht_news_item_title", "")
                            if title:
                                related.append(title)

                trends.append(TrendItem(
                    topic=topic,
                    traffic_volume=traffic[:50],
                    source="google_trends",
                    related_queries=related,
                ))

            logger.info(f"Google Trends RSS returned {len(trends)} entries")
            return trends

        except Exception as e:
            logger.error(f"Error fetching Google Trends: {e}")
            return []

    def _fetch_google_news_fallback(self) -> list[TrendItem]:
        """Fallback: use Google News top headlines as trend proxies."""
        try:
            news_url = f"https://news.google.com/rss?hl=en-IN&gl={self.geo}&ceid={self.geo}:en"
            feed = feedparser.parse(news_url)

            trends = []
            seen = set()

            for entry in feed.entries[:20]:
                title = entry.get("title", "").strip()
                if not title:
                    continue

                # Extract the topic keyword (first meaningful phrase)
                # Google News titles are often: "Headline - Source"
                topic = title.split(" - ")[0].strip()

                # Simple keyword extraction: take first 5 words max
                words = topic.split()[:5]
                topic_key = " ".join(words)

                if topic_key.lower() in seen:
                    continue
                seen.add(topic_key.lower())

                trends.append(TrendItem(
                    topic=topic_key,
                    traffic_volume="News Headline",
                    source="google_news",
                ))

            logger.info(f"Google News fallback returned {len(trends)} topics")
            return trends

        except Exception as e:
            logger.error(f"Error fetching Google News fallback: {e}")
            return []
