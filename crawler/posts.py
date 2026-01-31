"""Posts crawler using instaloader."""

import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

import instaloader

from config import POST_REQUEST_DELAY


class PostsCrawler:
    """Crawls Instagram posts using instaloader."""

    def __init__(self, loader: instaloader.Instaloader = None,
                 progress_callback: Callable[[str], None] = None):
        """Initialize the posts crawler.

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

    def _determine_post_type(self, post: instaloader.Post) -> str:
        """Determine the type of post.

        Args:
            post: Instaloader Post object

        Returns:
            Post type string
        """
        if post.typename == 'GraphSidecar':
            return 'carousel'
        elif post.is_video:
            # Check if it's a reel (product_type is in _node)
            product_type = None
            if hasattr(post, '_node'):
                product_type = post._node.get('product_type')
            if product_type == 'clips':
                return 'reel'
            return 'video'
        else:
            return 'image'

    def _post_to_dict(self, post: instaloader.Post) -> Dict[str, Any]:
        """Convert Post object to dictionary.

        Args:
            post: Instaloader Post object

        Returns:
            Post data dictionary
        """
        post_type = self._determine_post_type(post)

        return {
            'shortcode': post.shortcode,
            'post_type': post_type,
            'caption': post.caption if post.caption else '',
            'like_count': post.likes,
            'comment_count': post.comments,
            'view_count': post.video_view_count if post.is_video else 0,
            'media_url': post.video_url if post.is_video else post.url,
            'thumbnail_url': post.url,
            'is_video': post.is_video,
            'video_duration': post.video_duration if post.is_video else None,
            'posted_at': post.date_utc.isoformat() if post.date_utc else None,
        }

    def get_posts(self, profile: instaloader.Profile,
                  max_posts: int = None,
                  stop_flag: Callable[[], bool] = None) -> List[Dict[str, Any]]:
        """Get all posts from a profile.

        Args:
            profile: Instaloader Profile object
            max_posts: Maximum number of posts to fetch (None for all)
            stop_flag: Function that returns True if crawling should stop

        Returns:
            List of post dictionaries
        """
        self.progress_callback(f"게시물 목록 가져오는 중: {profile.username}")

        posts = []
        count = 0

        try:
            for post in profile.get_posts():
                # Check stop flag
                if stop_flag and stop_flag():
                    self.progress_callback("게시물 수집 중단됨")
                    break

                # Check max posts
                if max_posts and count >= max_posts:
                    break

                try:
                    post_data = self._post_to_dict(post)
                    posts.append(post_data)
                    count += 1

                    if count % 10 == 0:
                        self.progress_callback(f"게시물 {count}개 수집됨...")

                    time.sleep(POST_REQUEST_DELAY)

                except Exception as e:
                    self.progress_callback(f"게시물 처리 오류 ({post.shortcode}): {str(e)}")
                    continue

            self.progress_callback(f"총 {len(posts)}개 게시물 수집 완료")
            return posts

        except instaloader.exceptions.PrivateProfileNotFollowedException:
            self.progress_callback("비공개 계정입니다")
            return []
        except instaloader.exceptions.LoginRequiredException:
            self.progress_callback("로그인이 필요합니다")
            return []
        except Exception as e:
            self.progress_callback(f"게시물 수집 오류: {str(e)}")
            return posts

    def get_post_details(self, shortcode: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a single post.

        Args:
            shortcode: Post shortcode

        Returns:
            Post details dictionary or None
        """
        try:
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            return self._post_to_dict(post)
        except Exception as e:
            self.progress_callback(f"게시물 상세정보 가져오기 실패 ({shortcode}): {str(e)}")
            return None

    def get_carousel_items(self, shortcode: str) -> List[Dict[str, Any]]:
        """Get all items from a carousel post.

        Args:
            shortcode: Post shortcode

        Returns:
            List of media item dictionaries
        """
        items = []
        try:
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)

            if post.typename == 'GraphSidecar':
                for node in post.get_sidecar_nodes():
                    item = {
                        'is_video': node.is_video,
                        'media_url': node.video_url if node.is_video else node.display_url,
                        'thumbnail_url': node.display_url,
                    }
                    items.append(item)
            else:
                # Single item
                items.append({
                    'is_video': post.is_video,
                    'media_url': post.video_url if post.is_video else post.url,
                    'thumbnail_url': post.url,
                })

        except Exception as e:
            self.progress_callback(f"캐러셀 아이템 가져오기 실패 ({shortcode}): {str(e)}")

        return items
