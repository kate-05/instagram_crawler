"""Configuration settings for Instagram Crawler."""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Database settings
DATABASE_NAME = "instagram_crawler.db"
DATABASE_PATH = BASE_DIR / DATABASE_NAME

# Progress file
PROGRESS_FILE = "crawl_progress.json"
PROGRESS_PATH = BASE_DIR / PROGRESS_FILE

# Session settings
SESSION_DIR = BASE_DIR / "sessions"

# Rate limiting (seconds between requests)
REQUEST_DELAY = 3.0  # Delay between individual requests
PROFILE_REQUEST_DELAY = 5.0  # Delay after profile info requests
POST_REQUEST_DELAY = 2.5  # Delay between post requests
RATE_LIMIT_WAIT = 60  # Wait time when rate limited (seconds)
MAX_RETRIES = 3  # Maximum retry attempts for rate-limited requests

# Comment settings
MAX_COMMENTS_PER_POST = 100  # Maximum comments to fetch per post

# Export settings
EXPORT_DIR = BASE_DIR / "exports"

# GUI settings
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 700
APPEARANCE_MODE = "dark"  # "dark", "light", or "system"
COLOR_THEME = "blue"  # "blue", "green", "dark-blue"

# Access code settings (for distribution control)
# Format: "CODE": "YYYY-MM-DD" (expiry date)
ACCESS_CODES = {
    "KATE2026Q1": "2026-03-31",  # 1분기 수강생
    "KATE2026Q2": "2026-06-30",  # 2분기 수강생
    "KATE2026Q3": "2026-09-30",  # 3분기 수강생
    "KATE2026Q4": "2026-12-31",  # 4분기 수강생
}

# Status constants
class Status:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    UNAVAILABLE = "unavailable"
    PRIVATE = "private"
    FAILED = "failed"


# Crawling steps
class CrawlStep:
    PROFILE_INFO = "profile_info"
    POST_LIST = "post_list"
    POST_DETAILS = "post_details"
    REELS = "reels"
    STORIES = "stories"
    HIGHLIGHTS = "highlights"
    COMMENTS = "comments"
    HASHTAGS = "hashtags"

    @classmethod
    def all_steps(cls):
        return [
            cls.PROFILE_INFO,
            cls.POST_LIST,
            cls.POST_DETAILS,
            cls.REELS,
            cls.STORIES,
            cls.HIGHLIGHTS,
            cls.COMMENTS,
            cls.HASHTAGS
        ]

    @classmethod
    def login_required_steps(cls):
        """Steps that require login."""
        return [cls.STORIES, cls.HIGHLIGHTS]
