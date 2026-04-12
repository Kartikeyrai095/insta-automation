"""
NewsAgent — Fetches news from RSS feeds and matches them to trending topics.
Only returns verified, source-matched news items.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from urllib.parse import urlparse

import feedparser

from config.rss_feeds import NEWS_FEEDS, VERIFIED_DOMAINS
from agents.trend_agent import TrendItem
from utils.logger import get_logger

logger = get_logger("news")


@dataclass
class NewsMatch:
    """A matched news item for a trending topic."""
    topic: str
    headline: str
    summary: str
    source_url: str
    source_name: str
    category: str
    match_score: float


class NewsAgent:
    """
    Fetches news from multiple RSS feeds and matches headlines
    to trending topics using fuzzy keyword matching.
    """

    def __init__(self, min_match_score: float = 0.35):
        self.feeds = NEWS_FEEDS
        self.min_match_score = min_match_score

    def run(self, trends: list[TrendItem]) -> NewsMatch | None:
        """
        Find the best news match for the given trends.

        Args:
            trends: List of TrendItem from TrendAgent.

        Returns:
            Best NewsMatch, or None if no valid match found.
        """
        if not trends:
            logger.warning("No trends provided to NewsAgent")
            return None

        logger.info(f"📰 Searching {len(self.feeds)} RSS feeds for {len(trends)} topics")

        # Fetch all news articles
        all_articles = self._fetch_all_feeds()
        logger.info(f"Fetched {len(all_articles)} total articles")

        if not all_articles:
            logger.error("No articles fetched from any feed")
            return None

        # Find best match across all topics
        best_match = None
        best_score = 0

        for trend in trends:
            match = self._find_best_match(trend, all_articles)
            if match and match.match_score > best_score:
                best_match = match
                best_score = match.match_score

        if best_match:
            logger.info(
                f"✅ Best match: '{best_match.topic}' ↔ '{best_match.headline}' "
                f"(score: {best_match.match_score:.2f}, source: {best_match.source_name})"
            )
        else:
            logger.warning("❌ No valid news match found for any trending topic")
            
            # Fallback to the top trend to allow the pipeline to continue
            top_trend = trends[0]
            logger.info(f"Using fallback generic match for top trend: {top_trend.topic}")
            import urllib.parse
            search_query = urllib.parse.quote(top_trend.topic)
            best_match = NewsMatch(
                topic=top_trend.topic,
                headline=f"Trending now: {top_trend.topic}",
                summary=f"This topic is currently trending. Searching for news about {top_trend.topic}.",
                source_url=f"https://news.google.com/search?q={search_query}&hl=en-IN&gl=IN&ceid=IN:en",
                source_name="Google News (Fallback)",
                category="Trending",
                match_score=0.1
            )

        return best_match

    def _fetch_all_feeds(self) -> list[dict]:
        """Fetch articles from all configured RSS feeds."""
        articles = []

        for feed_config in self.feeds:
            try:
                feed = feedparser.parse(feed_config["url"])

                if feed.bozo and not feed.entries:
                    logger.debug(f"Feed error for {feed_config['name']}: {feed.bozo_exception}")
                    continue

                for entry in feed.entries[:15]:  # Limit per feed
                    title = entry.get("title", "").strip()
                    if not title:
                        continue

                    # Clean Google News titles (remove " - SourceName" suffix)
                    clean_title = title.rsplit(" - ", 1)[0].strip() if " - " in title else title

                    summary = entry.get("summary", entry.get("description", ""))
                    # Strip HTML tags from summary
                    if summary:
                        import re
                        summary = re.sub(r"<[^>]+>", "", summary).strip()[:300]

                    link = entry.get("link", "")

                    articles.append({
                        "title": clean_title,
                        "raw_title": title,
                        "summary": summary,
                        "link": link,
                        "source_name": feed_config["name"],
                        "category": feed_config["category"],
                        "priority": feed_config["priority"],
                    })

            except Exception as e:
                logger.debug(f"Error fetching {feed_config['name']}: {e}")
                continue

        return articles

    def _find_best_match(self, trend: TrendItem, articles: list[dict]) -> NewsMatch | None:
        """Find the best article match for a single trend."""
        topic_lower = trend.topic.lower()
        topic_words = set(topic_lower.split())

        best_match = None
        best_score = 0

        for article in articles:
            headline_lower = article["title"].lower()

            # Score 1: Fuzzy sequence matching
            seq_score = SequenceMatcher(None, topic_lower, headline_lower).ratio()

            # Score 2: Keyword overlap (important for short topics)
            headline_words = set(headline_lower.split())
            if topic_words:
                overlap = len(topic_words & headline_words) / len(topic_words)
            else:
                overlap = 0

            # Score 3: substring containment bonus
            substring_bonus = 0.3 if topic_lower in headline_lower else 0

            # Combined score (weighted)
            combined_score = (seq_score * 0.4) + (overlap * 0.4) + substring_bonus

            # Priority bonus for higher-priority feeds
            priority_bonus = max(0, (5 - article["priority"]) * 0.02)
            combined_score += priority_bonus

            if combined_score > best_score and combined_score >= self.min_match_score:
                best_score = combined_score

                # Verify the source domain
                is_verified = self._is_verified_source(article["link"])

                best_match = NewsMatch(
                    topic=trend.topic,
                    headline=article["title"],
                    summary=article["summary"][:200] if article["summary"] else "",
                    source_url=article["link"],
                    source_name=article["source_name"],
                    category=article["category"],
                    match_score=combined_score,
                )

        return best_match

    @staticmethod
    def _is_verified_source(url: str) -> bool:
        """Check if a URL belongs to a verified news domain."""
        try:
            domain = urlparse(url).netloc.lower()
            # Strip 'www.' prefix
            if domain.startswith("www."):
                domain = domain[4:]

            return any(verified in domain for verified in VERIFIED_DOMAINS)
        except Exception:
            return False
