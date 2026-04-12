"""
Topic deduplication utility.
Prevents the system from posting about the same topic within a configurable window.
Uses fuzzy matching to catch near-duplicate topics.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

from config.settings import TOPIC_HISTORY_FILE, DEDUP_WINDOW_DAYS
from utils.logger import get_logger

logger = get_logger("dedup")


def load_history() -> list[dict]:
    """Load topic history from JSON file."""
    if not TOPIC_HISTORY_FILE.exists():
        return []

    try:
        with open(TOPIC_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        logger.warning("Could not read topic history, starting fresh")
        return []


def save_history(history: list[dict]) -> None:
    """Save topic history to JSON file."""
    try:
        with open(TOPIC_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, default=str)
        logger.info(f"Saved {len(history)} topics to history")
    except IOError as e:
        logger.error(f"Failed to save topic history: {e}")


def is_similar(topic_a: str, topic_b: str, threshold: float = 0.65) -> bool:
    """
    Check if two topics are similar using fuzzy matching.

    Args:
        topic_a: First topic string.
        topic_b: Second topic string.
        threshold: Similarity ratio threshold (0.0 to 1.0).

    Returns:
        True if topics are considered similar.
    """
    # Normalize strings
    a = topic_a.lower().strip()
    b = topic_b.lower().strip()

    # Exact match
    if a == b:
        return True

    # Check if one contains the other
    if a in b or b in a:
        return True

    # Fuzzy ratio check
    ratio = SequenceMatcher(None, a, b).ratio()
    return ratio >= threshold


def is_duplicate(topic: str) -> bool:
    """
    Check if a topic has been used within the dedup window.

    Args:
        topic: Topic string to check.

    Returns:
        True if topic is a duplicate (should be skipped).
    """
    history = load_history()
    cutoff = datetime.now(timezone.utc) - timedelta(days=DEDUP_WINDOW_DAYS)

    for entry in history:
        entry_time = datetime.fromisoformat(entry["timestamp"])
        if entry_time.tzinfo is None:
            entry_time = entry_time.replace(tzinfo=timezone.utc)

        if entry_time < cutoff:
            continue

        if is_similar(topic, entry["topic"]):
            logger.info(f"Duplicate detected: '{topic}' ≈ '{entry['topic']}'")
            return True

    return False


def record_topic(topic: str) -> None:
    """
    Record a topic as used.

    Args:
        topic: Topic string to record.
    """
    history = load_history()

    history.append({
        "topic": topic,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Prune entries older than window
    cutoff = datetime.now(timezone.utc) - timedelta(days=DEDUP_WINDOW_DAYS * 2)
    history = [
        entry for entry in history
        if datetime.fromisoformat(entry["timestamp"]).replace(tzinfo=timezone.utc) > cutoff
    ]

    save_history(history)


def filter_duplicates(topics: list[str]) -> list[str]:
    """
    Filter out duplicate topics from a list.

    Args:
        topics: List of topic strings.

    Returns:
        Filtered list with duplicates removed.
    """
    unique = []
    for topic in topics:
        if not is_duplicate(topic):
            # Also check against already-accepted topics in this batch
            is_batch_dup = any(is_similar(topic, u) for u in unique)
            if not is_batch_dup:
                unique.append(topic)

    logger.info(f"Filtered {len(topics)} topics → {len(unique)} unique")
    return unique
