"""Database manager for CRUD operations and progress tracking."""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from database.models import init_database
from config import DATABASE_PATH, Status


class DatabaseManager:
    """Manages all database operations for the Instagram Crawler."""

    def __init__(self, db_path: Path = DATABASE_PATH):
        """Initialize the database manager.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn = init_database(db_path)

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    # ==================== Profile Operations ====================

    def add_profile(self, username: str, full_name: str = None,
                    biography: str = None, follower_count: int = 0,
                    following_count: int = 0, post_count: int = 0,
                    is_private: bool = False, profile_pic_url: str = None,
                    external_url: str = None, is_verified: bool = False) -> Optional[int]:
        """Add a new profile to the database.

        Args:
            username: Instagram username
            full_name: Display name
            biography: Bio text
            follower_count: Number of followers
            following_count: Number of following
            post_count: Number of posts
            is_private: Whether the account is private
            profile_pic_url: Profile picture URL
            external_url: External website URL
            is_verified: Whether the account is verified

        Returns:
            Profile ID if successful, None if profile already exists
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO profiles (username, full_name, biography, follower_count,
                                      following_count, post_count, is_private,
                                      profile_pic_url, external_url, is_verified, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (username, full_name, biography, follower_count, following_count,
                  post_count, is_private, profile_pic_url, external_url, is_verified,
                  Status.PENDING))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_profile(self, profile_id: int = None, username: str = None) -> Optional[Dict[str, Any]]:
        """Get profile information by ID or username.

        Args:
            profile_id: Profile ID
            username: Instagram username

        Returns:
            Profile data as dictionary or None
        """
        cursor = self.conn.cursor()
        if profile_id:
            cursor.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
        elif username:
            cursor.execute("SELECT * FROM profiles WHERE username = ?", (username,))
        else:
            return None
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_profiles(self) -> List[Dict[str, Any]]:
        """Get all profiles from the database.

        Returns:
            List of profile dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM profiles ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def update_profile(self, profile_id: int, **kwargs) -> bool:
        """Update profile information.

        Args:
            profile_id: Profile ID
            **kwargs: Fields to update

        Returns:
            True if updated successfully
        """
        if not kwargs:
            return False

        # Add updated_at timestamp
        kwargs['updated_at'] = datetime.now().isoformat()

        updates = [f"{key} = ?" for key in kwargs.keys()]
        params = list(kwargs.values())
        params.append(profile_id)

        cursor = self.conn.cursor()
        cursor.execute(f"""
            UPDATE profiles SET {', '.join(updates)} WHERE id = ?
        """, params)
        self.conn.commit()
        return cursor.rowcount > 0

    def update_profile_status(self, profile_id: int, status: str) -> bool:
        """Update profile crawling status.

        Args:
            profile_id: Profile ID
            status: New status

        Returns:
            True if updated successfully
        """
        return self.update_profile(profile_id, status=status)

    def delete_profile(self, profile_id: int) -> bool:
        """Delete a profile and all associated data.

        Args:
            profile_id: Profile ID

        Returns:
            True if deleted successfully
        """
        cursor = self.conn.cursor()
        # Cascade delete will handle related tables
        cursor.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # ==================== Post Operations ====================

    def add_post(self, profile_id: int, shortcode: str, post_type: str = 'image',
                 caption: str = None, like_count: int = 0, comment_count: int = 0,
                 view_count: int = 0, media_url: str = None, thumbnail_url: str = None,
                 is_video: bool = False, video_duration: float = None,
                 posted_at: str = None, post_url: str = None) -> Optional[int]:
        """Add a new post to the database.

        Args:
            profile_id: Parent profile ID
            shortcode: Post shortcode (unique identifier)
            post_type: Type of post (image/video/carousel/reel)
            caption: Post caption
            like_count: Number of likes
            comment_count: Number of comments
            view_count: Number of views (for videos)
            media_url: Main media URL
            thumbnail_url: Thumbnail URL
            is_video: Whether it's a video
            video_duration: Duration in seconds
            posted_at: Post timestamp
            post_url: Instagram post URL

        Returns:
            Post ID if successful, None if post already exists
        """
        # Generate post_url from shortcode if not provided
        if not post_url and shortcode:
            post_url = f"https://www.instagram.com/p/{shortcode}/"

        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO posts (profile_id, shortcode, post_url, post_type, caption,
                                   like_count, comment_count, view_count, media_url,
                                   thumbnail_url, is_video, video_duration, posted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (profile_id, shortcode, post_url, post_type, caption, like_count,
                  comment_count, view_count, media_url, thumbnail_url,
                  is_video, video_duration, posted_at))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def add_posts_batch(self, posts: List[Dict[str, Any]]) -> int:
        """Add multiple posts in a batch.

        Args:
            posts: List of post dictionaries

        Returns:
            Number of posts added
        """
        cursor = self.conn.cursor()
        added = 0
        for post in posts:
            # Generate post_url from shortcode if not provided
            shortcode = post['shortcode']
            post_url = post.get('post_url') or f"https://www.instagram.com/p/{shortcode}/"

            try:
                cursor.execute("""
                    INSERT INTO posts (profile_id, shortcode, post_url, post_type, caption,
                                       like_count, comment_count, view_count, media_url,
                                       thumbnail_url, is_video, video_duration, posted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (post['profile_id'], shortcode, post_url, post.get('post_type', 'image'),
                      post.get('caption'), post.get('like_count', 0),
                      post.get('comment_count', 0), post.get('view_count', 0),
                      post.get('media_url'), post.get('thumbnail_url'),
                      post.get('is_video', False), post.get('video_duration'),
                      post.get('posted_at')))
                added += 1
            except sqlite3.IntegrityError:
                pass
        self.conn.commit()
        return added

    def get_post(self, post_id: int = None, shortcode: str = None) -> Optional[Dict[str, Any]]:
        """Get post by ID or shortcode.

        Args:
            post_id: Post ID
            shortcode: Post shortcode

        Returns:
            Post data as dictionary or None
        """
        cursor = self.conn.cursor()
        if post_id:
            cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
        elif shortcode:
            cursor.execute("SELECT * FROM posts WHERE shortcode = ?", (shortcode,))
        else:
            return None
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_profile_posts(self, profile_id: int, post_type: str = None,
                          offset: int = 0, limit: int = None) -> List[Dict[str, Any]]:
        """Get all posts for a profile.

        Args:
            profile_id: Profile ID
            post_type: Filter by post type
            offset: Starting index
            limit: Maximum number of posts to return

        Returns:
            List of post dictionaries
        """
        cursor = self.conn.cursor()
        query = "SELECT * FROM posts WHERE profile_id = ?"
        params = [profile_id]

        if post_type:
            query += " AND post_type = ?"
            params.append(post_type)

        query += " ORDER BY posted_at DESC"

        if limit:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_post_count(self, profile_id: int, post_type: str = None) -> int:
        """Get the number of posts for a profile.

        Args:
            profile_id: Profile ID
            post_type: Filter by post type

        Returns:
            Number of posts
        """
        cursor = self.conn.cursor()
        if post_type:
            cursor.execute("""
                SELECT COUNT(*) as count FROM posts
                WHERE profile_id = ? AND post_type = ?
            """, (profile_id, post_type))
        else:
            cursor.execute("""
                SELECT COUNT(*) as count FROM posts WHERE profile_id = ?
            """, (profile_id,))
        return cursor.fetchone()['count']

    def update_post(self, post_id: int, **kwargs) -> bool:
        """Update post information.

        Args:
            post_id: Post ID
            **kwargs: Fields to update

        Returns:
            True if updated successfully
        """
        if not kwargs:
            return False

        updates = [f"{key} = ?" for key in kwargs.keys()]
        params = list(kwargs.values())
        params.append(post_id)

        cursor = self.conn.cursor()
        cursor.execute(f"""
            UPDATE posts SET {', '.join(updates)} WHERE id = ?
        """, params)
        self.conn.commit()
        return cursor.rowcount > 0

    # ==================== Story Operations ====================

    def add_story(self, profile_id: int, media_id: str, media_type: str = 'image',
                  media_url: str = None, thumbnail_url: str = None,
                  posted_at: str = None, expires_at: str = None) -> Optional[int]:
        """Add a story to the database.

        Args:
            profile_id: Profile ID
            media_id: Unique media identifier
            media_type: Type (image/video)
            media_url: Media URL
            thumbnail_url: Thumbnail URL
            posted_at: Post timestamp
            expires_at: Expiry timestamp

        Returns:
            Story ID if successful
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO stories (profile_id, media_id, media_type, media_url,
                                     thumbnail_url, posted_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (profile_id, media_id, media_type, media_url, thumbnail_url,
                  posted_at, expires_at))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_profile_stories(self, profile_id: int) -> List[Dict[str, Any]]:
        """Get all stories for a profile.

        Args:
            profile_id: Profile ID

        Returns:
            List of story dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM stories WHERE profile_id = ?
            ORDER BY posted_at DESC
        """, (profile_id,))
        return [dict(row) for row in cursor.fetchall()]

    # ==================== Highlight Operations ====================

    def add_highlight(self, profile_id: int, highlight_id: str, title: str,
                      cover_url: str = None, item_count: int = 0) -> Optional[int]:
        """Add a highlight to the database.

        Args:
            profile_id: Profile ID
            highlight_id: Instagram highlight ID
            title: Highlight title
            cover_url: Cover image URL
            item_count: Number of items

        Returns:
            Highlight database ID if successful
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO highlights (profile_id, highlight_id, title, cover_url, item_count)
                VALUES (?, ?, ?, ?, ?)
            """, (profile_id, highlight_id, title, cover_url, item_count))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def add_highlight_item(self, highlight_id: int, media_id: str,
                           media_type: str = 'image', media_url: str = None,
                           thumbnail_url: str = None, posted_at: str = None) -> Optional[int]:
        """Add a highlight item.

        Args:
            highlight_id: Highlight database ID
            media_id: Media identifier
            media_type: Type (image/video)
            media_url: Media URL
            thumbnail_url: Thumbnail URL
            posted_at: Post timestamp

        Returns:
            Item ID if successful
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO highlight_items (highlight_id, media_id, media_type,
                                             media_url, thumbnail_url, posted_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (highlight_id, media_id, media_type, media_url, thumbnail_url, posted_at))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_profile_highlights(self, profile_id: int) -> List[Dict[str, Any]]:
        """Get all highlights for a profile.

        Args:
            profile_id: Profile ID

        Returns:
            List of highlight dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM highlights WHERE profile_id = ?
            ORDER BY created_at DESC
        """, (profile_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_highlight_items(self, highlight_id: int) -> List[Dict[str, Any]]:
        """Get all items for a highlight.

        Args:
            highlight_id: Highlight database ID

        Returns:
            List of highlight item dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM highlight_items WHERE highlight_id = ?
            ORDER BY posted_at DESC
        """, (highlight_id,))
        return [dict(row) for row in cursor.fetchall()]

    # ==================== Comment Operations ====================

    def add_comment(self, post_id: int, comment_id: str, username: str,
                    text: str, like_count: int = 0, posted_at: str = None,
                    parent_id: int = None) -> Optional[int]:
        """Add a comment for a post.

        Args:
            post_id: Post ID
            comment_id: Instagram comment ID
            username: Comment author
            text: Comment text
            like_count: Number of likes
            posted_at: Timestamp
            parent_id: Parent comment ID for replies

        Returns:
            Comment database ID if successful
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO comments (post_id, comment_id, username, text,
                                      like_count, posted_at, parent_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (post_id, comment_id, username, text, like_count, posted_at, parent_id))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def add_comments_batch(self, comments: List[Dict[str, Any]]) -> int:
        """Add multiple comments in a batch.

        Args:
            comments: List of comment dictionaries

        Returns:
            Number of comments added
        """
        cursor = self.conn.cursor()
        added = 0
        for comment in comments:
            try:
                cursor.execute("""
                    INSERT INTO comments (post_id, comment_id, username, text,
                                          like_count, posted_at, parent_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (comment['post_id'], comment.get('comment_id'),
                      comment.get('username'), comment.get('text'),
                      comment.get('like_count', 0), comment.get('posted_at'),
                      comment.get('parent_id')))
                added += 1
            except sqlite3.IntegrityError:
                pass
        self.conn.commit()
        return added

    def get_post_comments(self, post_id: int, include_replies: bool = True) -> List[Dict[str, Any]]:
        """Get all comments for a post.

        Args:
            post_id: Post ID
            include_replies: Whether to include replies

        Returns:
            List of comment dictionaries
        """
        cursor = self.conn.cursor()
        if include_replies:
            cursor.execute("""
                SELECT * FROM comments WHERE post_id = ?
                ORDER BY posted_at DESC
            """, (post_id,))
        else:
            cursor.execute("""
                SELECT * FROM comments WHERE post_id = ? AND parent_id IS NULL
                ORDER BY posted_at DESC
            """, (post_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_comment_count(self, post_id: int) -> int:
        """Get the number of comments for a post.

        Args:
            post_id: Post ID

        Returns:
            Number of comments
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count FROM comments WHERE post_id = ?
        """, (post_id,))
        return cursor.fetchone()['count']

    # ==================== Hashtag Operations ====================

    def add_hashtag(self, post_id: int, tag: str) -> Optional[int]:
        """Add a hashtag for a post.

        Args:
            post_id: Post ID
            tag: Hashtag (without #)

        Returns:
            Hashtag ID if successful
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO hashtags (post_id, tag) VALUES (?, ?)
            """, (post_id, tag.lower().strip()))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def add_hashtags_batch(self, post_id: int, tags: List[str]) -> int:
        """Add multiple hashtags for a post.

        Args:
            post_id: Post ID
            tags: List of hashtags

        Returns:
            Number of hashtags added
        """
        cursor = self.conn.cursor()
        added = 0
        for tag in tags:
            try:
                cursor.execute("""
                    INSERT INTO hashtags (post_id, tag) VALUES (?, ?)
                """, (post_id, tag.lower().strip()))
                added += 1
            except sqlite3.IntegrityError:
                pass
        self.conn.commit()
        return added

    def get_post_hashtags(self, post_id: int) -> List[str]:
        """Get all hashtags for a post.

        Args:
            post_id: Post ID

        Returns:
            List of hashtag strings
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT tag FROM hashtags WHERE post_id = ?", (post_id,))
        return [row['tag'] for row in cursor.fetchall()]

    def get_profile_hashtags(self, profile_id: int) -> List[Dict[str, Any]]:
        """Get hashtag statistics for a profile.

        Args:
            profile_id: Profile ID

        Returns:
            List of dictionaries with tag and count
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT h.tag, COUNT(*) as count
            FROM hashtags h
            JOIN posts p ON h.post_id = p.id
            WHERE p.profile_id = ?
            GROUP BY h.tag
            ORDER BY count DESC
        """, (profile_id,))
        return [dict(row) for row in cursor.fetchall()]

    # ==================== Statistics ====================

    def get_profile_stats(self, profile_id: int) -> Dict[str, Any]:
        """Get statistics for a profile.

        Args:
            profile_id: Profile ID

        Returns:
            Statistics dictionary
        """
        cursor = self.conn.cursor()

        # Total posts
        cursor.execute("""
            SELECT COUNT(*) as total FROM posts WHERE profile_id = ?
        """, (profile_id,))
        total_posts = cursor.fetchone()['total']

        # Posts by type
        cursor.execute("""
            SELECT post_type, COUNT(*) as count FROM posts
            WHERE profile_id = ?
            GROUP BY post_type
        """, (profile_id,))
        posts_by_type = {row['post_type']: row['count'] for row in cursor.fetchall()}

        # Total comments
        cursor.execute("""
            SELECT COUNT(*) as count FROM comments c
            JOIN posts p ON c.post_id = p.id
            WHERE p.profile_id = ?
        """, (profile_id,))
        total_comments = cursor.fetchone()['count']

        # Total stories
        cursor.execute("""
            SELECT COUNT(*) as count FROM stories WHERE profile_id = ?
        """, (profile_id,))
        total_stories = cursor.fetchone()['count']

        # Total highlights
        cursor.execute("""
            SELECT COUNT(*) as count FROM highlights WHERE profile_id = ?
        """, (profile_id,))
        total_highlights = cursor.fetchone()['count']

        # Unique hashtags
        cursor.execute("""
            SELECT COUNT(DISTINCT h.tag) as count FROM hashtags h
            JOIN posts p ON h.post_id = p.id
            WHERE p.profile_id = ?
        """, (profile_id,))
        unique_hashtags = cursor.fetchone()['count']

        return {
            'total_posts': total_posts,
            'posts_by_type': posts_by_type,
            'total_comments': total_comments,
            'total_stories': total_stories,
            'total_highlights': total_highlights,
            'unique_hashtags': unique_hashtags
        }
