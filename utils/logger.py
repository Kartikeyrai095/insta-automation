"""
Structured logger for the Instagram Reel Automation System.
Outputs JSON-formatted logs to both console and log files.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from config.settings import LOGS_DIR


class JSONFormatter(logging.Formatter):
    """Format log records as JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "agent": getattr(record, "agent", "system"),
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "data"):
            log_entry["data"] = record.data

        if record.exc_info and record.exc_info[0] is not None:
            log_entry["error"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def get_logger(agent_name: str = "system") -> logging.Logger:
    """
    Get a configured logger for a specific agent.

    Args:
        agent_name: Name of the agent (used in log output).

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(f"insta_automation.{agent_name}")

    # Avoid duplicate handlers if logger already configured
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Console handler (INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter(
        f"%(asctime)s | {agent_name:>15s} | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    # File handler (DEBUG and above) — per-run log file
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"run_{run_id}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def log_with_data(logger: logging.Logger, level: int, message: str, data: dict = None):
    """Log a message with optional structured data."""
    extra = {"data": data} if data else {}
    logger.log(level, message, extra=extra)
