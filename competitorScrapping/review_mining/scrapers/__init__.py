"""
Scrapers module for review mining application.
Contains scrapers for different platforms (Reddit, Play Store, etc.).
"""

from .base_scraper import BaseScraper
from .reddit_scraper import RedditScraper

__all__ = ['BaseScraper', 'RedditScraper']

