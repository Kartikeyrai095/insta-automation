"""
ControlAgent — STOP/START/PAUSE mechanism.
Reads a control flag file to determine whether the pipeline should execute.
"""

from datetime import datetime, timezone
from pathlib import Path

from config.settings import STOP_FILE, MAX_POSTS_PER_DAY, TOPIC_HISTORY_FILE
from utils.logger import get_logger

logger = get_logger("control")


class ControlStatus:
    """Result of a control check."""

    def __init__(self, should_run: bool, reason: str):
        self.should_run = should_run
        self.reason = reason

    def __repr__(self) -> str:
        status = "RUN" if self.should_run else "HALT"
        return f"ControlStatus({status}: {self.reason})"


class ControlAgent:
    """
    Manages the STOP/START/PAUSE mechanism for the automation pipeline.

    Control flags (in stop.txt):
        - "START" or empty/missing → proceed with execution
        - "STOP"  → halt execution entirely
        - "PAUSE" → skip this run only
    """

    def __init__(self):
        self.stop_file = STOP_FILE

    def check(self) -> ControlStatus:
        """
        Check all control conditions.

        Returns:
            ControlStatus indicating whether the pipeline should run.
        """
        # 1. Check stop.txt flag
        flag_status = self._check_flag()
        if not flag_status.should_run:
            return flag_status

        # 2. Check daily post limit
        limit_status = self._check_daily_limit()
        if not limit_status.should_run:
            return limit_status

        logger.info("✅ All control checks passed — pipeline may proceed")
        return ControlStatus(True, "All checks passed")

    def _check_flag(self) -> ControlStatus:
        """Check the stop.txt control flag."""
        if not self.stop_file.exists():
            logger.info("No stop.txt found — defaulting to START")
            return ControlStatus(True, "No control file found, default START")

        try:
            content = self.stop_file.read_text(encoding="utf-8").strip().upper()
        except IOError as e:
            logger.error(f"Could not read stop.txt: {e}")
            return ControlStatus(True, f"Could not read stop.txt ({e}), defaulting to START")

        if content == "STOP":
            logger.warning("🛑 STOP flag detected — halting execution")
            return ControlStatus(False, "STOP flag is active")

        if content == "PAUSE":
            logger.info("⏸️ PAUSE flag detected — skipping this run only")
            return ControlStatus(False, "PAUSE flag is active (single skip)")

        # START or any other value → proceed
        logger.info(f"Control flag: '{content}' — proceeding")
        return ControlStatus(True, f"Control flag is '{content}'")

    def _check_daily_limit(self) -> ControlStatus:
        """Check if we've exceeded the daily post limit."""
        try:
            import json

            if not TOPIC_HISTORY_FILE.exists():
                return ControlStatus(True, "No post history yet")

            with open(TOPIC_HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)

            today = datetime.now(timezone.utc).date()
            today_posts = sum(
                1 for entry in history
                if datetime.fromisoformat(entry.get("timestamp", "2000-01-01")).date() == today
            )

            if today_posts >= MAX_POSTS_PER_DAY:
                logger.warning(
                    f"Daily post limit reached ({today_posts}/{MAX_POSTS_PER_DAY})"
                )
                return ControlStatus(
                    False,
                    f"Daily limit reached: {today_posts}/{MAX_POSTS_PER_DAY} posts today",
                )

            logger.info(f"Daily limit OK: {today_posts}/{MAX_POSTS_PER_DAY} posts today")
            return ControlStatus(True, f"{today_posts}/{MAX_POSTS_PER_DAY} posts today")

        except Exception as e:
            logger.error(f"Error checking daily limit: {e}")
            return ControlStatus(True, f"Could not check limit ({e}), proceeding")

    @staticmethod
    def set_flag(flag: str = "START") -> None:
        """Set the control flag. Useful for testing."""
        STOP_FILE.write_text(flag.upper(), encoding="utf-8")
        logger.info(f"Control flag set to: {flag.upper()}")
