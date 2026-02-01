"""Reels crawler using instaloader."""

import time
from typing import Dict, List, Any, Callable

import instaloader

from config import POST_REQUEST_DELAY, RATE_LIMIT_WAIT, MAX_RETRIES


class ReelsCrawler:
    """Crawls Instagram Reels using instaloader."""

    def __init__(self, loader: instaloader.Instaloader = None,
                 progress_callback: Callable[[str], None] = None):
        """Initialize the reels crawler.

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

    def _reel_to_dict(self, post: instaloader.Post) -> Dict[str, Any]:
        """Convert Reel Post object to dictionary.

        Uses _node data directly to avoid additional API calls.

        Args:
            post: Instaloader Post object

        Returns:
            Reel data dictionary
        """
        from datetime import datetime

        node = post._node if hasattr(post, '_node') else {}

        # Extract data from _node
        shortcode = node.get('shortcode', post.shortcode)
        caption = ''
        if 'edge_media_to_caption' in node:
            edges = node['edge_media_to_caption'].get('edges', [])
            if edges:
                caption = edges[0].get('node', {}).get('text', '')

        like_count = node.get('edge_liked_by', {}).get('count', 0)
        if not like_count:
            like_count = node.get('edge_media_preview_like', {}).get('count', 0)

        comment_count = node.get('edge_media_to_comment', {}).get('count', 0)
        if not comment_count:
            comment_count = node.get('edge_media_preview_comment', {}).get('count', 0)

        view_count = node.get('video_view_count', 0)
        video_duration = node.get('video_duration')
        display_url = node.get('display_url', '')
        video_url = node.get('video_url', '')

        posted_at = None
        if 'taken_at_timestamp' in node:
            posted_at = datetime.fromtimestamp(node['taken_at_timestamp']).isoformat()

        return {
            'shortcode': shortcode,
            'post_type': 'reel',
            'caption': caption,
            'like_count': like_count,
            'comment_count': comment_count,
            'view_count': view_count,
            'media_url': video_url or display_url,
            'thumbnail_url': display_url,
            'is_video': True,
            'video_duration': video_duration,
            'posted_at': posted_at,
        }

    def get_reels(self, profile: instaloader.Profile,
                  max_reels: int = None,
                  stop_flag: Callable[[], bool] = None) -> List[Dict[str, Any]]:
        """Get reels from a profile.

        Note: Instaloader doesn't have a direct method to get only reels,
        so we filter posts that are reels based on product_type.

        Args:
            profile: Instaloader Profile object
            max_reels: Maximum number of reels to fetch (None for all)
            stop_flag: Function that returns True if crawling should stop

        Returns:
            List of reel dictionaries
        """
        self.progress_callback(f"릴스 가져오는 중: {profile.username}")

        reels = []
        count = 0
        total_checked = 0
        retry_count = 0

        try:
            post_iterator = profile.get_posts()

            while True:
                # Check stop flag
                if stop_flag and stop_flag():
                    self.progress_callback("릴스 수집 중단됨")
                    break

                try:
                    post = next(post_iterator)
                    retry_count = 0  # Reset on success
                    total_checked += 1

                    # Check if it's a reel (product_type is in _node)
                    is_reel = False
                    if post.is_video:
                        product_type = None
                        if hasattr(post, '_node'):
                            product_type = post._node.get('product_type')
                        if product_type == 'clips':
                            is_reel = True

                    if is_reel:
                        try:
                            reel_data = self._reel_to_dict(post)
                            reels.append(reel_data)
                            count += 1

                            if count % 5 == 0:
                                self.progress_callback(f"릴스 {count}개 수집됨...")

                            # Check max reels
                            if max_reels and count >= max_reels:
                                break

                        except Exception as e:
                            self.progress_callback(f"릴스 처리 오류 ({post.shortcode}): {str(e)}")
                            continue

                    time.sleep(POST_REQUEST_DELAY)

                    # Limit total posts to check to avoid infinite loop
                    if total_checked >= 500 and (not max_reels or count < max_reels):
                        self.progress_callback(f"최근 500개 게시물에서 릴스 검색 완료")
                        break

                except StopIteration:
                    break
                except instaloader.exceptions.ConnectionException as e:
                    error_msg = str(e)
                    if "401" in error_msg or "wait" in error_msg.lower():
                        retry_count += 1
                        if retry_count <= MAX_RETRIES:
                            self.progress_callback(f"Rate limit 감지. {RATE_LIMIT_WAIT}초 대기 후 재시도 ({retry_count}/{MAX_RETRIES})...")
                            time.sleep(RATE_LIMIT_WAIT)
                            continue
                        else:
                            self.progress_callback(f"최대 재시도 횟수 초과. 수집된 {len(reels)}개 반환")
                            break
                    raise

            self.progress_callback(f"총 {len(reels)}개 릴스 수집 완료")
            return reels

        except instaloader.exceptions.PrivateProfileNotFollowedException:
            self.progress_callback("비공개 계정입니다")
            return []
        except instaloader.exceptions.LoginRequiredException:
            self.progress_callback("로그인이 필요합니다")
            return []
        except Exception as e:
            self.progress_callback(f"릴스 수집 오류: {str(e)}")
            return reels

    def get_reels_from_posts(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter reels from a list of posts.

        Args:
            posts: List of post dictionaries

        Returns:
            List of reel dictionaries
        """
        return [post for post in posts if post.get('post_type') == 'reel']
