"""Crawler modules for Instagram data collection."""

from crawler.profile import ProfileCrawler
from crawler.posts import PostsCrawler
from crawler.reels import ReelsCrawler
from crawler.stories import StoriesCrawler
from crawler.highlights import HighlightsCrawler
from crawler.comments import CommentsCrawler
from crawler.hashtags import HashtagExtractor

__all__ = [
    'ProfileCrawler',
    'PostsCrawler',
    'ReelsCrawler',
    'StoriesCrawler',
    'HighlightsCrawler',
    'CommentsCrawler',
    'HashtagExtractor'
]
