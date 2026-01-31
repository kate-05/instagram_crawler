"""SQLite database table definitions for Instagram Crawler."""

import sqlite3
from pathlib import Path

# SQL statements for creating tables

CREATE_PROFILES_TABLE = """
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    full_name TEXT,
    biography TEXT,
    follower_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    post_count INTEGER DEFAULT 0,
    is_private BOOLEAN DEFAULT 0,
    profile_pic_url TEXT,
    external_url TEXT,
    is_verified BOOLEAN DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_POSTS_TABLE = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    shortcode TEXT UNIQUE NOT NULL,
    post_url TEXT,
    post_type TEXT DEFAULT 'image',
    caption TEXT,
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    media_url TEXT,
    thumbnail_url TEXT,
    is_video BOOLEAN DEFAULT 0,
    video_duration REAL,
    posted_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);
"""

CREATE_STORIES_TABLE = """
CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    media_id TEXT UNIQUE,
    media_type TEXT DEFAULT 'image',
    media_url TEXT,
    thumbnail_url TEXT,
    posted_at DATETIME,
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);
"""

CREATE_HIGHLIGHTS_TABLE = """
CREATE TABLE IF NOT EXISTS highlights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    highlight_id TEXT UNIQUE,
    title TEXT,
    cover_url TEXT,
    item_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);
"""

CREATE_HIGHLIGHT_ITEMS_TABLE = """
CREATE TABLE IF NOT EXISTS highlight_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    highlight_id INTEGER NOT NULL,
    media_id TEXT,
    media_type TEXT DEFAULT 'image',
    media_url TEXT,
    thumbnail_url TEXT,
    posted_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (highlight_id) REFERENCES highlights(id) ON DELETE CASCADE
);
"""

CREATE_COMMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    parent_id INTEGER,
    comment_id TEXT,
    username TEXT,
    text TEXT,
    like_count INTEGER DEFAULT 0,
    posted_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES comments(id) ON DELETE CASCADE
);
"""

CREATE_HASHTAGS_TABLE = """
CREATE TABLE IF NOT EXISTS hashtags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);
"""

# Create indexes for better query performance
CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_posts_profile_id ON posts(profile_id);",
    "CREATE INDEX IF NOT EXISTS idx_posts_shortcode ON posts(shortcode);",
    "CREATE INDEX IF NOT EXISTS idx_stories_profile_id ON stories(profile_id);",
    "CREATE INDEX IF NOT EXISTS idx_highlights_profile_id ON highlights(profile_id);",
    "CREATE INDEX IF NOT EXISTS idx_highlight_items_highlight_id ON highlight_items(highlight_id);",
    "CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id);",
    "CREATE INDEX IF NOT EXISTS idx_comments_parent_id ON comments(parent_id);",
    "CREATE INDEX IF NOT EXISTS idx_hashtags_post_id ON hashtags(post_id);",
    "CREATE INDEX IF NOT EXISTS idx_hashtags_tag ON hashtags(tag);",
    "CREATE INDEX IF NOT EXISTS idx_profiles_username ON profiles(username);",
]


def init_database(db_path: Path) -> sqlite3.Connection:
    """Initialize the SQLite database with all required tables.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        sqlite3.Connection: Database connection object
    """
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Enable dict-like row access

    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")

    cursor = conn.cursor()

    # Create tables
    cursor.execute(CREATE_PROFILES_TABLE)
    cursor.execute(CREATE_POSTS_TABLE)
    cursor.execute(CREATE_STORIES_TABLE)
    cursor.execute(CREATE_HIGHLIGHTS_TABLE)
    cursor.execute(CREATE_HIGHLIGHT_ITEMS_TABLE)
    cursor.execute(CREATE_COMMENTS_TABLE)
    cursor.execute(CREATE_HASHTAGS_TABLE)

    # Create indexes
    for index_sql in CREATE_INDEXES:
        cursor.execute(index_sql)

    conn.commit()

    return conn


def get_table_info(conn: sqlite3.Connection, table_name: str) -> list:
    """Get column information for a table.

    Args:
        conn: Database connection
        table_name: Name of the table

    Returns:
        List of column information tuples
    """
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    return cursor.fetchall()
