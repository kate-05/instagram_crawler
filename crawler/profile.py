"""Profile information crawler using instaloader."""

import time
import re
from typing import Dict, Any, Optional, Callable
from datetime import datetime

import instaloader

from config import PROFILE_REQUEST_DELAY, SESSION_DIR


class ProfileCrawler:
    """Crawls Instagram profile information using instaloader."""

    def __init__(self, loader: instaloader.Instaloader = None,
                 progress_callback: Callable[[str], None] = None):
        """Initialize the profile crawler.

        Args:
            loader: Instaloader instance (shared for session)
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
        self._is_logged_in = False

    def login(self, username: str, password: str) -> bool:
        """Login to Instagram.

        Args:
            username: Instagram username
            password: Instagram password

        Returns:
            True if login successful
        """
        try:
            self.loader.login(username, password)
            self._is_logged_in = True
            self.progress_callback(f"로그인 성공: {username}")
            return True
        except instaloader.exceptions.BadCredentialsException:
            self.progress_callback("로그인 실패: 잘못된 인증 정보")
            return False
        except instaloader.exceptions.TwoFactorAuthRequiredException:
            self.progress_callback("로그인 실패: 2단계 인증이 필요합니다")
            return False
        except Exception as e:
            self.progress_callback(f"로그인 오류: {str(e)}")
            return False

    def load_session(self, username: str) -> bool:
        """Load saved session from file.

        Args:
            username: Session username

        Returns:
            True if session loaded successfully
        """
        try:
            session_file = SESSION_DIR / f"{username}_session"
            if session_file.exists():
                self.loader.load_session_from_file(username, str(session_file))
                self._is_logged_in = True
                self.progress_callback(f"세션 로드됨: {username}")
                return True
            return False
        except Exception as e:
            self.progress_callback(f"세션 로드 실패: {str(e)}")
            return False

    def save_session(self, username: str) -> bool:
        """Save current session to file.

        Args:
            username: Session username

        Returns:
            True if session saved successfully
        """
        try:
            SESSION_DIR.mkdir(parents=True, exist_ok=True)
            session_file = SESSION_DIR / f"{username}_session"
            self.loader.save_session_to_file(str(session_file))
            self.progress_callback(f"세션 저장됨: {username}")
            return True
        except Exception as e:
            self.progress_callback(f"세션 저장 실패: {str(e)}")
            return False

    def logout(self):
        """Logout from Instagram."""
        self._is_logged_in = False
        self.loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True
        )

    @property
    def is_logged_in(self) -> bool:
        """Check if logged in."""
        return self._is_logged_in

    def extract_username(self, url_or_username: str) -> Optional[str]:
        """Extract username from Instagram URL or return as-is if already username.

        Args:
            url_or_username: Instagram URL or username

        Returns:
            Username or None if invalid
        """
        url_or_username = url_or_username.strip()

        # Remove trailing slashes
        url_or_username = url_or_username.rstrip('/')

        # Check if it's a URL
        patterns = [
            r'instagram\.com/([^/\?]+)',
            r'instagr\.am/([^/\?]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url_or_username)
            if match:
                username = match.group(1)
                # Skip common non-username paths
                if username in ['p', 'reel', 'reels', 'stories', 'explore', 'accounts']:
                    return None
                return username

        # If not a URL, assume it's a username
        # Remove @ if present
        if url_or_username.startswith('@'):
            url_or_username = url_or_username[1:]

        # Basic validation
        if re.match(r'^[a-zA-Z0-9._]+$', url_or_username):
            return url_or_username

        return None

    def get_profile_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Get profile information.

        Args:
            username: Instagram username

        Returns:
            Profile info dictionary or None
        """
        self.progress_callback(f"프로필 정보 가져오는 중: {username}")

        try:
            profile = instaloader.Profile.from_username(self.loader.context, username)

            profile_info = {
                'username': profile.username,
                'full_name': profile.full_name,
                'biography': profile.biography,
                'follower_count': profile.followers,
                'following_count': profile.followees,
                'post_count': profile.mediacount,
                'is_private': profile.is_private,
                'is_verified': profile.is_verified,
                'profile_pic_url': profile.profile_pic_url,
                'external_url': profile.external_url,
                'userid': profile.userid,
            }

            self.progress_callback(
                f"프로필 발견: {profile_info['full_name'] or username} "
                f"(게시물: {profile_info['post_count']}, "
                f"팔로워: {profile_info['follower_count']})"
            )

            time.sleep(PROFILE_REQUEST_DELAY)

            return profile_info

        except instaloader.exceptions.ProfileNotExistsException:
            self.progress_callback(f"프로필을 찾을 수 없습니다: {username}")
            return None
        except instaloader.exceptions.PrivateProfileNotFollowedException:
            self.progress_callback(f"비공개 계정입니다: {username}")
            return {
                'username': username,
                'is_private': True,
                'full_name': None,
                'biography': None,
                'follower_count': 0,
                'following_count': 0,
                'post_count': 0,
                'is_verified': False,
                'profile_pic_url': None,
                'external_url': None,
            }
        except instaloader.exceptions.LoginRequiredException:
            self.progress_callback("로그인이 필요합니다")
            return None
        except instaloader.exceptions.ConnectionException as e:
            self.progress_callback(f"연결 오류: {str(e)}")
            return None
        except Exception as e:
            self.progress_callback(f"프로필 정보 가져오기 실패: {str(e)}")
            return None

    def get_profile(self, username: str) -> Optional[instaloader.Profile]:
        """Get instaloader Profile object.

        Args:
            username: Instagram username

        Returns:
            Profile object or None
        """
        try:
            return instaloader.Profile.from_username(self.loader.context, username)
        except Exception:
            return None
