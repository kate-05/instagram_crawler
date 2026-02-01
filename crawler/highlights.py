"""Highlights crawler using instaloader."""

import time
from typing import Dict, List, Any, Callable, Tuple
from datetime import datetime

import instaloader

from config import REQUEST_DELAY


class HighlightsCrawler:
    """Crawls Instagram Highlights using instaloader.

    Note: Requires login to access highlights.
    """

    def __init__(self, loader: instaloader.Instaloader = None,
                 progress_callback: Callable[[str], None] = None):
        """Initialize the highlights crawler.

        Args:
            loader: Instaloader instance (must be logged in)
            progress_callback: Callback function for progress updates
        """
        self.loader = loader or instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True
        )
        self.progress_callback = progress_callback or (lambda x: None)

    def _highlight_item_to_dict(self, item: instaloader.StoryItem) -> Dict[str, Any]:
        """Convert highlight item to dictionary.

        Args:
            item: Instaloader StoryItem object

        Returns:
            Highlight item dictionary
        """
        return {
            'media_id': str(item.mediaid),
            'media_type': 'video' if item.is_video else 'image',
            'media_url': item.video_url if item.is_video else item.url,
            'thumbnail_url': item.url,
            'posted_at': item.date_utc.isoformat() if item.date_utc else None,
        }

    def get_highlights(self, profile: instaloader.Profile,
                       stop_flag: Callable[[], bool] = None) -> List[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
        """Get all highlights from a profile.

        Note: Requires login.

        Args:
            profile: Instaloader Profile object
            stop_flag: Function that returns True if crawling should stop

        Returns:
            List of tuples (highlight_info, list of items)
        """
        self.progress_callback(f"하이라이트 가져오는 중: {profile.username}")

        highlights_data = []

        try:
            try:
                highlights = list(self.loader.get_highlights(profile))
            except KeyError as e:
                self.progress_callback(f"하이라이트 API 응답 오류 (Instagram API 변경 가능성): {e}")
                return []
            except TypeError as e:
                self.progress_callback(f"하이라이트 데이터 형식 오류: {e}")
                return []

            if not highlights:
                self.progress_callback("하이라이트가 없습니다")
                return []

            for highlight in highlights:
                if stop_flag and stop_flag():
                    self.progress_callback("하이라이트 수집 중단됨")
                    break

                try:
                    # Highlight metadata
                    highlight_info = {
                        'highlight_id': str(highlight.unique_id),
                        'title': highlight.title,
                        'cover_url': highlight.cover_url if hasattr(highlight, 'cover_url') else None,
                        'item_count': 0,  # Will be updated after getting items
                    }

                    # Get highlight items
                    items = []
                    for item in highlight.get_items():
                        if stop_flag and stop_flag():
                            break

                        try:
                            item_data = self._highlight_item_to_dict(item)
                            items.append(item_data)
                        except Exception as e:
                            self.progress_callback(f"하이라이트 아이템 처리 오류: {str(e)}")
                            continue

                        time.sleep(REQUEST_DELAY * 0.5)  # Shorter delay for items

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

        except instaloader.exceptions.LoginRequiredException:
            self.progress_callback("하이라이트 접근에 로그인이 필요합니다")
            return []
        except instaloader.exceptions.PrivateProfileNotFollowedException:
            self.progress_callback("비공개 계정의 하이라이트에 접근할 수 없습니다")
            return []
        except Exception as e:
            self.progress_callback(f"하이라이트 수집 오류: {str(e)}")
            return highlights_data

    def get_highlight_by_id(self, highlight_id: str,
                            stop_flag: Callable[[], bool] = None) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Get a specific highlight by ID.

        Args:
            highlight_id: Highlight unique ID
            stop_flag: Function that returns True if crawling should stop

        Returns:
            Tuple of (highlight_info, list of items)
        """
        # Note: Instaloader doesn't directly support getting a single highlight by ID
        # This would require implementing a custom approach
        self.progress_callback("개별 하이라이트 가져오기는 현재 지원되지 않습니다")
        return ({}, [])
