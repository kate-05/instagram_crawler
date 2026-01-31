"""Comments crawler using instaloader."""

import time
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional

import instaloader

from config import REQUEST_DELAY, MAX_COMMENTS_PER_POST


class CommentsCrawler:
    """Crawls Instagram comments using instaloader."""

    def __init__(self, loader: instaloader.Instaloader = None,
                 progress_callback: Callable[[str], None] = None,
                 max_comments: int = None):
        """Initialize the comments crawler.

        Args:
            loader: Instaloader instance (shared for session)
            progress_callback: Callback function for progress updates
            max_comments: Maximum comments per post
        """
        self.loader = loader or instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=True,
            save_metadata=False,
            compress_json=False,
            quiet=True
        )
        self.progress_callback = progress_callback or (lambda x: None)
        self.max_comments = max_comments or MAX_COMMENTS_PER_POST

    def _comment_node_to_dict(self, node: Dict, post_id: int, parent_id: str = None) -> Optional[Dict[str, Any]]:
        """Convert comment node from post._node to dictionary.

        Args:
            node: Comment node dictionary from post._node
            post_id: Database post ID
            parent_id: Parent comment ID for replies

        Returns:
            Comment dictionary or None if invalid
        """
        try:
            comment_id = str(node.get('id', ''))
            if not comment_id:
                return None

            # Parse timestamp
            posted_at = None
            if 'created_at' in node:
                posted_at = datetime.fromtimestamp(node['created_at']).isoformat()

            return {
                'post_id': post_id,
                'comment_id': comment_id,
                'username': node.get('owner', {}).get('username', ''),
                'text': node.get('text', ''),
                'like_count': node.get('edge_liked_by', {}).get('count', 0),
                'posted_at': posted_at,
                'parent_id': parent_id,
            }
        except Exception:
            return None

    def _comment_to_dict(self, comment, post_id: int) -> Dict[str, Any]:
        """Convert instaloader comment object to dictionary.

        Args:
            comment: Instaloader comment object
            post_id: Database post ID

        Returns:
            Comment dictionary
        """
        return {
            'post_id': post_id,
            'comment_id': str(comment.id) if hasattr(comment, 'id') else None,
            'username': comment.owner.username if hasattr(comment, 'owner') else None,
            'text': comment.text if hasattr(comment, 'text') else '',
            'like_count': comment.likes_count if hasattr(comment, 'likes_count') else 0,
            'posted_at': comment.created_at_utc.isoformat() if hasattr(comment, 'created_at_utc') and comment.created_at_utc else None,
            'parent_id': None,
        }

    def _extract_comments_from_node(self, post, post_id: int, limit: int) -> List[Dict[str, Any]]:
        """Extract comments directly from post._node structure.

        Instagram embeds initial comments in the post data under
        'edge_media_to_parent_comment' or 'edge_media_to_comment'.

        Args:
            post: Instaloader Post object
            post_id: Database post ID
            limit: Maximum comments to extract

        Returns:
            List of comment dictionaries
        """
        comments = []

        if not hasattr(post, '_node'):
            return comments

        node = post._node

        # Try different edge keys
        edge_keys = ['edge_media_to_parent_comment', 'edge_media_to_comment']

        for edge_key in edge_keys:
            if edge_key not in node:
                continue

            edges_data = node[edge_key]
            if not isinstance(edges_data, dict):
                continue

            edges = edges_data.get('edges', [])

            for edge in edges:
                if len(comments) >= limit:
                    break

                comment_node = edge.get('node', {})
                comment_data = self._comment_node_to_dict(comment_node, post_id)

                if comment_data and comment_data['comment_id']:
                    comments.append(comment_data)

                    # Extract replies if available
                    replies_edge = comment_node.get('edge_threaded_comments', {})
                    reply_edges = replies_edge.get('edges', [])

                    for reply_edge in reply_edges:
                        if len(comments) >= limit:
                            break

                        reply_node = reply_edge.get('node', {})
                        reply_data = self._comment_node_to_dict(
                            reply_node, post_id, parent_id=comment_data['comment_id']
                        )

                        if reply_data and reply_data['comment_id']:
                            comments.append(reply_data)

            # If we found comments with this key, don't try other keys
            if comments:
                break

        return comments

    def get_comments(self, shortcode: str, post_id: int,
                     max_comments: int = None,
                     stop_flag: Callable[[], bool] = None) -> List[Dict[str, Any]]:
        """Get comments for a post.

        Uses two methods:
        1. Extract from post._node (embedded comments, no extra API call)
        2. Fallback to post.get_comments() if method 1 fails

        Args:
            shortcode: Post shortcode
            post_id: Database post ID
            max_comments: Maximum comments to fetch
            stop_flag: Function that returns True if crawling should stop

        Returns:
            List of comment dictionaries
        """
        limit = max_comments or self.max_comments
        comments = []

        try:
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)

            # Check if post has comments
            if post.comments == 0:
                return []

            self.progress_callback(f"댓글 수집 중 ({shortcode}): 예상 {post.comments}개")

            # Method 1: Extract from post._node (embedded comments)
            comments = self._extract_comments_from_node(post, post_id, limit)

            if comments:
                self.progress_callback(f"댓글 {len(comments)}개 수집됨 ({shortcode}) [embedded]")
                return comments

            # Method 2: Fallback to get_comments() API
            self.progress_callback(f"댓글 API 호출 중 ({shortcode})...")
            count = 0

            try:
                for comment in post.get_comments():
                    if stop_flag and stop_flag():
                        break

                    if limit and count >= limit:
                        break

                    try:
                        comment_data = self._comment_to_dict(comment, post_id)
                        if comment_data['comment_id']:
                            comments.append(comment_data)
                            count += 1

                        # Handle replies if available
                        if hasattr(comment, 'answers'):
                            try:
                                for reply in comment.answers:
                                    if limit and count >= limit:
                                        break

                                    reply_data = self._comment_to_dict(reply, post_id)
                                    if reply_data['comment_id']:
                                        reply_data['parent_id'] = comment_data['comment_id']
                                        comments.append(reply_data)
                                        count += 1
                            except Exception:
                                pass

                    except Exception as e:
                        self.progress_callback(f"댓글 처리 오류: {str(e)}")
                        continue

                    time.sleep(REQUEST_DELAY * 0.3)

            except instaloader.exceptions.ConnectionException as e:
                # API method failed, return what we have from embedded
                if "fail" in str(e).lower():
                    self.progress_callback(f"댓글 API 차단됨, embedded 댓글만 사용 ({shortcode})")

            self.progress_callback(f"댓글 {len(comments)}개 수집됨 ({shortcode})")
            return comments

        except instaloader.exceptions.LoginRequiredException:
            self.progress_callback(f"댓글 접근에 로그인이 필요합니다 ({shortcode})")
            return []
        except instaloader.exceptions.QueryReturnedBadRequestException:
            self.progress_callback(f"댓글 수집 실패 - 요청 오류 ({shortcode})")
            return []
        except instaloader.exceptions.ConnectionException as e:
            self.progress_callback(f"연결 오류 ({shortcode}): {str(e)}")
            return comments
        except Exception as e:
            self.progress_callback(f"댓글 수집 오류 ({shortcode}): {str(e)}")
            return comments

    def get_comments_for_posts(self, posts: List[Dict[str, Any]],
                               max_comments_per_post: int = None,
                               stop_flag: Callable[[], bool] = None,
                               progress_callback: Callable[[int, int, str], None] = None) -> Dict[int, List[Dict[str, Any]]]:
        """Get comments for multiple posts.

        Args:
            posts: List of post dictionaries (must have 'id' and 'shortcode')
            max_comments_per_post: Maximum comments per post
            stop_flag: Function that returns True if crawling should stop
            progress_callback: Callback with (current, total, status) parameters

        Returns:
            Dictionary mapping post_id to list of comments
        """
        results = {}
        total = len(posts)

        for i, post in enumerate(posts):
            if stop_flag and stop_flag():
                self.progress_callback("댓글 수집 중단됨")
                break

            post_id = post['id']
            shortcode = post['shortcode']

            comments = self.get_comments(
                shortcode, post_id,
                max_comments=max_comments_per_post,
                stop_flag=stop_flag
            )

            results[post_id] = comments

            if progress_callback:
                status = f"{len(comments)}개 댓글" if comments else "댓글 없음"
                progress_callback(i + 1, total, f"{shortcode} ({status})")

            time.sleep(REQUEST_DELAY)

        return results

    def get_comment_count(self, shortcode: str) -> int:
        """Get the number of comments for a post.

        Args:
            shortcode: Post shortcode

        Returns:
            Number of comments
        """
        try:
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            return post.comments
        except Exception:
            return 0
