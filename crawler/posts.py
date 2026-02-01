"""Posts crawler using instaloader."""

import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

import instaloader

from config import POST_REQUEST_DELAY, RATE_LIMIT_WAIT, MAX_RETRIES


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

        Uses _node data directly to avoid additional API calls.

        Args:
            post: Instaloader Post object

        Returns:
            Post data dictionary
        """
        post_type = self._determine_post_type(post)
        node = post._node if hasattr(post, '_node') else {}

        # Extract data from _node to avoid API calls
        shortcode = node.get('shortcode', post.shortcode)
        caption = ''
        if 'edge_media_to_caption' in node:
            edges = node['edge_media_to_caption'].get('edges', [])
            if edges:
                caption = edges[0].get('node', {}).get('text', '')

        # Get counts from node
        like_count = node.get('edge_liked_by', {}).get('count', 0)
        if not like_count:
            like_count = node.get('edge_media_preview_like', {}).get('count', 0)

        comment_count = node.get('edge_media_to_comment', {}).get('count', 0)
        if not comment_count:
            comment_count = node.get('edge_media_preview_comment', {}).get('count', 0)
            if not comment_count:
                comment_count = node.get('edge_media_to_parent_comment', {}).get('count', 0)

        # Video info
        is_video = node.get('is_video', False)
        view_count = node.get('video_view_count', 0) if is_video else 0
        video_duration = node.get('video_duration') if is_video else None

        # Media URLs
        display_url = node.get('display_url', '')
        video_url = node.get('video_url', '') if is_video else ''
        thumbnail_url = node.get('thumbnail_src', display_url)

        # Timestamp
        posted_at = None
        if 'taken_at_timestamp' in node:
            posted_at = datetime.fromtimestamp(node['taken_at_timestamp']).isoformat()

        return {
            'shortcode': shortcode,
            'post_type': post_type,
            'caption': caption,
            'like_count': like_count,
            'comment_count': comment_count,
            'view_count': view_count,
            'media_url': video_url if is_video else display_url,
            'thumbnail_url': thumbnail_url,
            'is_video': is_video,
            'video_duration': video_duration,
            'posted_at': posted_at,
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
        retry_count = 0

        # Try to get post iterator with retries
        post_iterator = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                post_iterator = profile.get_posts()
                # Try to get first item to verify connection
                break
            except instaloader.exceptions.ConnectionException as e:
                error_msg = str(e)
                if "401" in error_msg or "wait" in error_msg.lower():
                    if attempt < MAX_RETRIES:
                        self.progress_callback(f"Rate limit 감지. {RATE_LIMIT_WAIT}초 대기 후 재시도 ({attempt+1}/{MAX_RETRIES})...")
                        time.sleep(RATE_LIMIT_WAIT)
                        continue
                raise

        if post_iterator is None:
            self.progress_callback("게시물 목록을 가져올 수 없습니다")
            return []

        try:

            while True:
                # Check stop flag
                if stop_flag and stop_flag():
                    self.progress_callback("게시물 수집 중단됨")
                    break

                # Check max posts
                if max_posts and count >= max_posts:
                    break

                try:
                    post = next(post_iterator)
                    retry_count = 0  # Reset retry count on success

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
                            self.progress_callback(f"최대 재시도 횟수 초과. 수집된 {len(posts)}개 반환")
                            break
                    raise

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
