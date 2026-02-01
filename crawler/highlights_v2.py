"""Highlights crawler using instagrapi (alternative to instaloader)."""

import time
from typing import Dict, List, Any, Callable, Tuple, Optional
from datetime import datetime

from config import REQUEST_DELAY


class HighlightsCrawlerV2:
    """Crawls Instagram Highlights using instagrapi.

    Note: Requires login to access highlights.
    """

    def __init__(self, client=None, progress_callback: Callable[[str], None] = None):
        """Initialize the highlights crawler.

        Args:
            client: instagrapi Client instance (must be logged in)
            progress_callback: Callback function for progress updates
        """
        self.client = client
        self.progress_callback = progress_callback or (lambda x: None)

    def set_client(self, client):
        """Set the instagrapi client."""
        self.client = client

    def get_highlights(self, user_id: int,
                       stop_flag: Callable[[], bool] = None) -> List[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
        """Get all highlights from a user.

        Args:
            user_id: Instagram user ID
            stop_flag: Function that returns True if crawling should stop

        Returns:
            List of tuples (highlight_info, list of items)
        """
        if not self.client:
            self.progress_callback("instagrapi 클라이언트가 설정되지 않았습니다")
            return []

        self.progress_callback("하이라이트 가져오는 중...")

        highlights_data = []

        try:
            highlights = self.client.user_highlights(user_id)

            if not highlights:
                self.progress_callback("하이라이트가 없습니다")
                return []

            self.progress_callback(f"하이라이트 {len(highlights)}개 발견")

            for highlight in highlights:
                if stop_flag and stop_flag():
                    self.progress_callback("하이라이트 수집 중단됨")
                    break

                try:
                    # Highlight metadata
                    highlight_info = {
                        'highlight_id': str(highlight.pk),
                        'title': highlight.title or '',
                        'cover_url': str(highlight.cover_media.thumbnail_url) if highlight.cover_media else None,
                        'item_count': highlight.media_count or 0,
                    }

                    # Get highlight items
                    items = []
                    try:
                        highlight_medias = self.client.highlight_info(highlight.pk).items
                        for item in highlight_medias:
                            if stop_flag and stop_flag():
                                break

                            try:
                                item_data = {
                                    'media_id': str(item.pk),
                                    'media_type': 'video' if item.media_type == 2 else 'image',
                                    'media_url': str(item.video_url) if item.video_url else str(item.thumbnail_url),
                                    'thumbnail_url': str(item.thumbnail_url) if item.thumbnail_url else None,
                                    'posted_at': item.taken_at.isoformat() if item.taken_at else None,
                                }
                                items.append(item_data)
                            except Exception as e:
                                self.progress_callback(f"하이라이트 아이템 처리 오류: {str(e)}")
                                continue

                            time.sleep(REQUEST_DELAY * 0.3)
                    except Exception as e:
                        self.progress_callback(f"하이라이트 아이템 로드 오류: {str(e)}")

                    highlight_info['item_count'] = len(items)
                    highlights_data.append((highlight_info, items))

                    self.progress_callback(
                        f"하이라이트 '{highlight_info['title']}' 수집됨 ({len(items)}개 아이템)"
                    )

                except Exception as e:
                    self.progress_callback(f"하이라이트 처리 오류: {str(e)}")
                    continue

                time.sleep(REQUEST_DELAY)

            self.progress_callback(f"총 {len(highlights_data)}개 하이라이트 수집 완료")
            return highlights_data

        except Exception as e:
            self.progress_callback(f"하이라이트 수집 오류: {str(e)}")
            return highlights_data


class StoriesCrawlerV2:
    """Crawls Instagram Stories using instagrapi.

    Note: Requires login to access stories.
    """

    def __init__(self, client=None, progress_callback: Callable[[str], None] = None):
        """Initialize the stories crawler.

        Args:
            client: instagrapi Client instance (must be logged in)
            progress_callback: Callback function for progress updates
        """
        self.client = client
        self.progress_callback = progress_callback or (lambda x: None)

    def set_client(self, client):
        """Set the instagrapi client."""
        self.client = client

    def get_stories(self, user_id: int,
                    stop_flag: Callable[[], bool] = None) -> List[Dict[str, Any]]:
        """Get current stories from a user.

        Args:
            user_id: Instagram user ID
            stop_flag: Function that returns True if crawling should stop

        Returns:
            List of story dictionaries
        """
        if not self.client:
            self.progress_callback("instagrapi 클라이언트가 설정되지 않았습니다")
            return []

        self.progress_callback("스토리 가져오는 중...")

        stories = []

        try:
            story_items = self.client.user_stories(user_id)

            if not story_items:
                self.progress_callback("현재 스토리가 없습니다")
                return []

            for item in story_items:
                if stop_flag and stop_flag():
                    self.progress_callback("스토리 수집 중단됨")
                    break

                try:
                    story_data = {
                        'media_id': str(item.pk),
                        'media_type': 'video' if item.media_type == 2 else 'image',
                        'media_url': str(item.video_url) if item.video_url else str(item.thumbnail_url),
                        'thumbnail_url': str(item.thumbnail_url) if item.thumbnail_url else None,
                        'posted_at': item.taken_at.isoformat() if item.taken_at else None,
                        'expires_at': None,  # instagrapi doesn't provide this directly
                    }
                    stories.append(story_data)
                except Exception as e:
                    self.progress_callback(f"스토리 아이템 처리 오류: {str(e)}")
                    continue

                time.sleep(REQUEST_DELAY * 0.5)

            self.progress_callback(f"총 {len(stories)}개 스토리 수집 완료")
            return stories

        except Exception as e:
            self.progress_callback(f"스토리 수집 오류: {str(e)}")
            return stories
