"""
Central configuration for the Instagram Reel Automation System.
All settings are loaded from environment variables with sensible defaults.
"""

import os
from pathlib import Path

# ─────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"
ASSETS_DIR = BASE_DIR / "assets"
AUDIO_DIR = ASSETS_DIR / "audio"
FONTS_DIR = ASSETS_DIR / "fonts"

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
FONTS_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────
# Control Flags
# ─────────────────────────────────────────────
STOP_FILE = BASE_DIR / "stop.txt"
TOPIC_HISTORY_FILE = BASE_DIR / "topic_history.json"

# ─────────────────────────────────────────────
# Google Gemini API (Content Generation)
# ─────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# ─────────────────────────────────────────────
# Google Veo (AI Video Generation)
# ─────────────────────────────────────────────
VEO_MODEL = os.environ.get("VEO_MODEL", "veo-3.1-generate-preview")
VEO_ENABLED = os.environ.get("VEO_ENABLED", "true").lower() == "true"

# ─────────────────────────────────────────────
# Google Imagen (AI Image Generation)
# ─────────────────────────────────────────────
IMAGEN_MODEL = os.environ.get("IMAGEN_MODEL", "imagen-4.0-generate-001")
IMAGEN_ENABLED = os.environ.get("IMAGEN_ENABLED", "true").lower() == "true"

# ─────────────────────────────────────────────
# Pexels API (Fallback Stock Footage)
# ─────────────────────────────────────────────
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

# ─────────────────────────────────────────────
# Instagram Graph API
# ─────────────────────────────────────────────
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_USER_ID = os.environ.get("INSTAGRAM_USER_ID", "")
INSTAGRAM_API_VERSION = os.environ.get("INSTAGRAM_API_VERSION", "v21.0")
INSTAGRAM_BASE_URL = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}"

# ─────────────────────────────────────────────
# GitHub (for token refresh and control)
# ─────────────────────────────────────────────
GH_TOKEN = os.environ.get("GH_TOKEN", "")
GH_REPO = os.environ.get("GITHUB_REPOSITORY", "")

# ─────────────────────────────────────────────
# Google Trends / Geo Config
# ─────────────────────────────────────────────
TRENDS_GEO = os.environ.get("TRENDS_GEO", "IN")  # India
TRENDS_RSS_URL = f"https://trends.google.com/trending/rss?geo={TRENDS_GEO}"

# ─────────────────────────────────────────────
# Video Specifications
# ─────────────────────────────────────────────
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30
VIDEO_DURATION = 15  # seconds
VIDEO_CODEC = "libx264"
AUDIO_CODEC = "aac"
VIDEO_FORMAT = "mp4"

# ─────────────────────────────────────────────
# Content Settings
# ─────────────────────────────────────────────
MAX_HASHTAGS = 15
MIN_HASHTAGS = 10
MAX_CAPTION_LENGTH = 2200  # Instagram limit
SCRIPT_DURATION_SECONDS = 15
HOOK_MAX_WORDS = 8

# ─────────────────────────────────────────────
# Scheduling & Limits
# ─────────────────────────────────────────────
MAX_POSTS_PER_DAY = 3
MIN_HOURS_BETWEEN_POSTS = 4
DEDUP_WINDOW_DAYS = 7

# ─────────────────────────────────────────────
# Audio Settings
# ─────────────────────────────────────────────
BACKGROUND_AUDIO_VOLUME = 0.08  # 8% volume

# ─────────────────────────────────────────────
# Retry Settings
# ─────────────────────────────────────────────
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5
INSTAGRAM_POLL_INTERVAL = 10  # seconds
INSTAGRAM_POLL_TIMEOUT = 300  # 5 minutes
