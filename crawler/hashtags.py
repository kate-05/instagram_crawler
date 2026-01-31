"""Hashtag extraction and analysis."""

import re
from typing import Dict, List, Any, Callable
from collections import Counter


class HashtagExtractor:
    """Extracts and analyzes hashtags from Instagram content."""

    def __init__(self, progress_callback: Callable[[str], None] = None):
        """Initialize the hashtag extractor.

        Args:
            progress_callback: Callback function for progress updates
        """
        self.progress_callback = progress_callback or (lambda x: None)
        # Regex pattern for hashtags (supports Unicode)
        self.hashtag_pattern = re.compile(r'#(\w+)', re.UNICODE)

    def extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text.

        Args:
            text: Text to extract hashtags from

        Returns:
            List of hashtags (without # symbol)
        """
        if not text:
            return []

        matches = self.hashtag_pattern.findall(text)
        # Normalize to lowercase and remove duplicates while preserving order
        seen = set()
        hashtags = []
        for tag in matches:
            tag_lower = tag.lower()
            if tag_lower not in seen:
                seen.add(tag_lower)
                hashtags.append(tag_lower)

        return hashtags

    def extract_from_posts(self, posts: List[Dict[str, Any]]) -> Dict[int, List[str]]:
        """Extract hashtags from multiple posts.

        Args:
            posts: List of post dictionaries with 'id' and 'caption'

        Returns:
            Dictionary mapping post_id to list of hashtags
        """
        self.progress_callback("게시물에서 해시태그 추출 중...")

        results = {}
        total_hashtags = 0

        for post in posts:
            post_id = post.get('id')
            caption = post.get('caption', '')

            hashtags = self.extract_hashtags(caption)
            results[post_id] = hashtags
            total_hashtags += len(hashtags)

        self.progress_callback(f"총 {total_hashtags}개 해시태그 추출됨 ({len(posts)}개 게시물)")
        return results

    def analyze_hashtags(self, hashtags: List[str]) -> Dict[str, Any]:
        """Analyze hashtag usage statistics.

        Args:
            hashtags: List of all hashtags

        Returns:
            Analysis dictionary
        """
        if not hashtags:
            return {
                'total_count': 0,
                'unique_count': 0,
                'top_hashtags': [],
                'frequency_distribution': {}
            }

        counter = Counter(hashtags)

        return {
            'total_count': len(hashtags),
            'unique_count': len(counter),
            'top_hashtags': counter.most_common(20),  # Top 20 hashtags
            'frequency_distribution': dict(counter),
        }

    def get_profile_hashtag_stats(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get comprehensive hashtag statistics for a profile.

        Args:
            posts: List of post dictionaries

        Returns:
            Comprehensive statistics dictionary
        """
        self.progress_callback("해시태그 분석 중...")

        all_hashtags = []
        hashtags_per_post = []

        for post in posts:
            caption = post.get('caption', '')
            hashtags = self.extract_hashtags(caption)
            all_hashtags.extend(hashtags)
            hashtags_per_post.append(len(hashtags))

        analysis = self.analyze_hashtags(all_hashtags)

        # Additional stats
        if hashtags_per_post:
            analysis['avg_hashtags_per_post'] = sum(hashtags_per_post) / len(hashtags_per_post)
            analysis['max_hashtags_in_post'] = max(hashtags_per_post)
            analysis['posts_with_hashtags'] = sum(1 for h in hashtags_per_post if h > 0)
            analysis['posts_without_hashtags'] = sum(1 for h in hashtags_per_post if h == 0)
        else:
            analysis['avg_hashtags_per_post'] = 0
            analysis['max_hashtags_in_post'] = 0
            analysis['posts_with_hashtags'] = 0
            analysis['posts_without_hashtags'] = 0

        self.progress_callback(
            f"해시태그 분석 완료: {analysis['unique_count']}개 고유 해시태그, "
            f"평균 {analysis['avg_hashtags_per_post']:.1f}개/게시물"
        )

        return analysis

    def categorize_hashtags(self, hashtags: List[str]) -> Dict[str, List[str]]:
        """Categorize hashtags by common themes.

        This is a simple categorization based on common patterns.

        Args:
            hashtags: List of hashtags

        Returns:
            Dictionary mapping category to list of hashtags
        """
        categories = {
            'korean': [],
            'english': [],
            'numbers': [],
            'mixed': [],
        }

        korean_pattern = re.compile(r'[\u3131-\u3163\uac00-\ud7a3]')
        number_pattern = re.compile(r'\d')

        for tag in hashtags:
            has_korean = bool(korean_pattern.search(tag))
            has_number = bool(number_pattern.search(tag))
            has_english = bool(re.search(r'[a-zA-Z]', tag))

            if has_korean and not has_english:
                categories['korean'].append(tag)
            elif has_english and not has_korean:
                if has_number:
                    categories['numbers'].append(tag)
                else:
                    categories['english'].append(tag)
            else:
                categories['mixed'].append(tag)

        return categories
