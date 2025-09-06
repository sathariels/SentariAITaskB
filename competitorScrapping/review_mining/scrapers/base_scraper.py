"""
Abstract base class for all scrapers.
Defines the common interface and functionality for scraping different platforms.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import time
import logging
import random
import requests
from datetime import datetime

from config.settings import SCRAPING_CONFIG, RATE_LIMITS


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""
    
    def __init__(self, platform: str):
        """
        Initialize the base scraper.
        
        Args:
            platform: The platform name (e.g., 'reddit', 'playstore')
        """
        self.platform = platform
        self.logger = logging.getLogger(f"scraper.{platform}")
        self.session = requests.Session()
        self.rate_limit_config = RATE_LIMITS.get(platform, {})
        self.last_request_time = 0
        
        # Set up session with user agent rotation
        self._setup_session()
    
    def _setup_session(self):
        """Setup the requests session with headers and configuration."""
        user_agents = SCRAPING_CONFIG.get('user_agents', [])
        if user_agents:
            user_agent = random.choice(user_agents)
            self.session.headers.update({'User-Agent': user_agent})
        
        self.session.timeout = SCRAPING_CONFIG.get('timeout', 30)
    
    def _respect_rate_limit(self):
        """Ensure rate limiting is respected."""
        delay = self.rate_limit_config.get('delay_between_requests', 1.0)
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < delay:
            sleep_time = delay - time_since_last
            self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Optional[requests.Response]:
        """
        Make a rate-limited HTTP request with retry logic.
        
        Args:
            url: The URL to request
            params: Query parameters
            headers: Additional headers
            
        Returns:
            Response object or None if failed
        """
        self._respect_rate_limit()
        
        max_retries = SCRAPING_CONFIG.get('max_retries', 3)
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, headers=request_headers)
                response.raise_for_status()
                return response
            
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.logger.error(f"Request failed after {max_retries} attempts: {url}")
                    return None
    
    @abstractmethod
    def scrape_reviews(self, app_config: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Scrape reviews for a given app.
        
        Args:
            app_config: Configuration for the app to scrape
            limit: Maximum number of reviews to scrape
            
        Returns:
            List of review dictionaries
        """
        pass
    
    @abstractmethod
    def validate_config(self, app_config: Dict[str, Any]) -> bool:
        """
        Validate the app configuration for this scraper.
        
        Args:
            app_config: Configuration to validate
            
        Returns:
            True if valid, False otherwise
        """
        pass
    
    def get_scraper_info(self) -> Dict[str, Any]:
        """
        Get information about this scraper.
        
        Returns:
            Dictionary with scraper metadata
        """
        return {
            'platform': self.platform,
            'rate_limit': self.rate_limit_config,
            'last_request_time': self.last_request_time,
            'session_info': {
                'user_agent': self.session.headers.get('User-Agent'),
                'timeout': self.session.timeout
            }
        }
    
    def _create_review_dict(self, **kwargs) -> Dict[str, Any]:
        """
        Create a standardized review dictionary.
        
        Returns:
            Standardized review dictionary
        """
        return {
            'platform': self.platform,
            'scraped_at': datetime.utcnow().isoformat(),
            'review_id': kwargs.get('review_id'),
            'app_name': kwargs.get('app_name'),
            'app_id': kwargs.get('app_id'),
            'user_id': kwargs.get('user_id'),
            'username': kwargs.get('username'),
            'rating': kwargs.get('rating'),
            'title': kwargs.get('title'),
            'content': kwargs.get('content'),
            'review_date': kwargs.get('review_date'),
            'helpful_count': kwargs.get('helpful_count', 0),
            'reply_count': kwargs.get('reply_count', 0),
            'verified': kwargs.get('verified', False),
            'version': kwargs.get('version'),
            'language': kwargs.get('language'),
            'country': kwargs.get('country'),
            'device': kwargs.get('device'),
            'source_url': kwargs.get('source_url'),
            'raw_data': kwargs.get('raw_data', {})
        }
