"""
SchedulerAgent — Time-slot awareness and scheduling logic.
Determines which time slot the current run falls into.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from utils.logger import get_logger

logger = get_logger("scheduler")


class TimeSlot:
    """Represents a posting time slot."""
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    OFF_HOURS = "off_hours"


class SchedulerAgent:
    """
    Provides time-slot awareness for the pipeline.
    Can be used to customize content tone or hashtags based on time of day.

    Default schedule (IST):
        Morning:   9:00 AM IST (03:30 UTC)
        Afternoon: 2:00 PM IST (08:30 UTC)
        Evening:   7:00 PM IST (13:30 UTC)
    """

    # IST = UTC + 5:30
    IST = timezone(timedelta(hours=5, minutes=30))

    def __init__(self):
        self.now = datetime.now(self.IST)

    def get_current_slot(self) -> str:
        """
        Determine the current time slot.

        Returns:
            TimeSlot constant string.
        """
        hour = self.now.hour

        if 6 <= hour < 11:
            slot = TimeSlot.MORNING
        elif 11 <= hour < 16:
            slot = TimeSlot.AFTERNOON
        elif 16 <= hour < 22:
            slot = TimeSlot.EVENING
        else:
            slot = TimeSlot.OFF_HOURS

        logger.info(f"⏰ Current time: {self.now.strftime('%I:%M %p IST')} → slot: {slot}")
        return slot

    def get_greeting(self) -> str:
        """Get a time-appropriate greeting for content."""
        slot = self.get_current_slot()
        greetings = {
            TimeSlot.MORNING: "Good morning! ☀️",
            TimeSlot.AFTERNOON: "Good afternoon! 🌤️",
            TimeSlot.EVENING: "Good evening! 🌙",
            TimeSlot.OFF_HOURS: "Hey there! 👋",
        }
        return greetings.get(slot, "Hey there! 👋")

    def get_slot_hashtags(self) -> list[str]:
        """Get time-slot specific hashtags."""
        slot = self.get_current_slot()
        slot_tags = {
            TimeSlot.MORNING: ["#morningnews", "#goodmorning", "#todaysnews"],
            TimeSlot.AFTERNOON: ["#afternoonupdate", "#lunchbreak", "#midday"],
            TimeSlot.EVENING: ["#eveningnews", "#tonight", "#trending"],
            TimeSlot.OFF_HOURS: ["#latenight", "#news", "#update"],
        }
        return slot_tags.get(slot, [])

    def should_run(self) -> bool:
        """
        Check if the current time is within an acceptable posting window.
        Prevents accidental runs during off-hours.
        """
        hour = self.now.hour
        # Allow posting between 6 AM and 11 PM IST
        is_valid = 6 <= hour <= 23
        if not is_valid:
            logger.warning(f"Off-hours ({hour}:xx IST) — skipping")
        return is_valid
