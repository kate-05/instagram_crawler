"""Stories crawler using instaloader."""

import time
from typing import Dict, List, Any, Callable
from datetime import datetime

import instaloader

from config import REQUEST_DELAY


class StoriesCrawler:
    """Crawls Instagram Stories using instaloader.

    Note: Requires login to access stories.
    """

    def __init__(self, loader: instaloader.Instaloader = None,
                 progress_callback: Callable[[str], None] = None):
        """Initialize the stories crawler.

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

    def _story_item_to_dict(self, item: instaloader.StoryItem) -> Dict[str, Any]:
        """Convert StoryItem to dictionary.

        Args:
            item: Instaloader StoryItem object

        Returns:
            Story item dictionary
        """
        return {
            'media_id': str(item.mediaid),
            'media_type': 'video' if item.is_video else 'image',
            'media_url': item.video_url if item.is_video else item.url,
            'thumbnail_url': item.url,
            'posted_at': item.date_utc.isoformat() if item.date_utc else None,
            'expires_at': item.expiring_utc.isoformat() if hasattr(item, 'expiring_utc') and item.expiring_utc else None,
        }

    def get_stories(self, profile: instaloader.Profile,
                    stop_flag: Callable[[], bool] = None) -> List[Dict[str, Any]]:
        """Get current stories from a profile.

        Note: Requires login. Stories are ephemeral (24 hours).

        Args:
            profile: Instaloader Profile object
            stop_flag: Function that returns True if crawling should stop

        Returns:
            List of story dictionaries
        """
        self.progress_callback(f"스토리 가져오는 중: {profile.username}")

        stories = []

        try:
            # Get stories for the profile
            try:
                story_items = list(self.loader.get_stories(userids=[profile.userid]))
            except KeyError as e:
                self.progress_callback(f"스토리 API 응답 오류 (Instagram API 변경 가능성): {e}")
                return []
            except TypeError as e:
                self.progress_callback(f"스토리 데이터 형식 오류: {e}")
                return []

            if not story_items:
                self.progress_callback("현재 스토리가 없습니다")
                return []

            for story in story_items:
                if stop_flag and stop_flag():
                    self.progress_callback("스토리 수집 중단됨")
                    break

                for item in story.get_items():
                    if stop_flag and stop_flag():
                        break

                    try:
                        story_data = self._story_item_to_dict(item)
                        stories.append(story_data)
                    except Exception as e:
                        self.progress_callback(f"스토리 아이템 처리 오류: {str(e)}")
                        continue

                    time.sleep(REQUEST_DELAY)

            self.progress_callback(f"총 {len(stories)}개 스토리 수집 완료")
            return stories

        except instaloader.exceptions.LoginRequiredException:
            self.progress_callback("스토리 접근에 로그인이 필요합니다")
            return []
        except instaloader.exceptions.PrivateProfileNotFollowedException:
            self.progress_callback("비공개 계정의 스토리에 접근할 수 없습니다")
            return []
        except Exception as e:
            self.progress_callback(f"스토리 수집 오류: {str(e)}")
            return stories

    def check_has_stories(self, profile: instaloader.Profile) -> bool:
        """Check if a profile has active stories.

        Args:
            profile: Instaloader Profile object

        Returns:
            True if profile has stories
        """
        try:
            # This requires being logged in
            return profile.has_highlight_reels
        except Exception:
            return False
