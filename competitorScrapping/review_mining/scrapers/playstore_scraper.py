"""
Google Play Store scraper for mining app reviews.
Uses google-play-scraper library to scrape reviews from the Play Store.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import time

try:
    from google_play_scraper import app, reviews, Sort
    GOOGLE_PLAY_SCRAPER_AVAILABLE = True
except ImportError:
    GOOGLE_PLAY_SCRAPER_AVAILABLE = False

from scrapers.base_scraper import BaseScraper


class PlayStoreScraper(BaseScraper):
    """Scraper for Google Play Store reviews."""
    
    def __init__(self):
        """Initialize the Play Store scraper."""
        super().__init__('playstore')
        
        if not GOOGLE_PLAY_SCRAPER_AVAILABLE:
            self.logger.error("google-play-scraper library not installed. Install with: pip install google-play-scraper")
    
    def validate_config(self, app_config: Dict[str, Any]) -> bool:
        """
        Validate the app configuration for Play Store scraping.
        
        Args:
            app_config: App configuration dictionary
            
        Returns:
            True if valid, False otherwise
        """
        if not GOOGLE_PLAY_SCRAPER_AVAILABLE:
            return False
        
        required_fields = ['package_id', 'name']
        return all(field in app_config for field in required_fields)
    
    def scrape_reviews(self, app_config: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Scrape reviews from Google Play Store.
        
        Args:
            app_config: App configuration dictionary
            limit: Maximum number of reviews to scrape
            
        Returns:
            List of review dictionaries
        """
        if not self.validate_config(app_config):
            self.logger.error("Invalid app configuration for Play Store scraping")
            return []
        
        package_id = app_config['package_id']
        app_name = app_config['name']
        
        try:
            # Get app information first
            app_info = self._get_app_info(package_id)
            if not app_info:
                self.logger.error(f"Could not find app with package ID: {package_id}")
                return []
            
            # Scrape reviews
            reviews_data = self._scrape_reviews_data(package_id, limit)
            
            # Convert to standardized format
            standardized_reviews = []
            for review_data in reviews_data:
                standardized_review = self._convert_review_format(review_data, app_name, app_config, app_info)
                if standardized_review:
                    standardized_reviews.append(standardized_review)
            
            self.logger.info(f"Scraped {len(standardized_reviews)} Play Store reviews for {app_name}")
            return standardized_reviews
            
        except Exception as e:
            self.logger.error(f"Error scraping Play Store reviews for {package_id}: {e}")
            return []
    
    def _get_app_info(self, package_id: str) -> Optional[Dict[str, Any]]:
        """Get app information from Play Store."""
        try:
            self._respect_rate_limit()
            app_info = app(package_id)
            return app_info
        except Exception as e:
            self.logger.error(f"Error getting app info for {package_id}: {e}")
            return None
    
    def _scrape_reviews_data(self, package_id: str, limit: int) -> List[Dict[str, Any]]:
        """Scrape reviews data from Play Store."""
        all_reviews = []
        
        try:
            # Scrape reviews in batches
            batch_size = min(200, limit)  # Play Store API limits
            continuation_token = None
            
            while len(all_reviews) < limit:
                self._respect_rate_limit()
                
                remaining = limit - len(all_reviews)
                current_batch_size = min(batch_size, remaining)
                
                try:
                    result, continuation_token = reviews(
                        package_id,
                        lang='en',
                        country='us',
                        sort=Sort.NEWEST,
                        count=current_batch_size,
                        continuation_token=continuation_token
                    )
                    
                    if not result:
                        break
                    
                    all_reviews.extend(result)
                    
                    # If no continuation token, we've reached the end
                    if not continuation_token:
                        break
                    
                except Exception as e:
                    self.logger.error(f"Error in batch scraping: {e}")
                    break
            
        except Exception as e:
            self.logger.error(f"Error scraping reviews for {package_id}: {e}")
        
        return all_reviews[:limit]
    
    def _convert_review_format(self, review_data: Dict[str, Any], app_name: str, 
                             app_config: Dict[str, Any], app_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert Play Store review format to standardized format."""
        try:
            # Extract review date
            review_date = review_data.get('at')
            if review_date:
                review_date = review_date.isoformat() if hasattr(review_date, 'isoformat') else str(review_date)
            
            return self._create_review_dict(
                review_id=f"playstore_{review_data.get('reviewId', '')}",
                app_name=app_name,
                app_id=app_config['package_id'],
                user_id=review_data.get('reviewId', ''),  # Use review ID as user identifier
                username=review_data.get('userName', 'Anonymous'),
                rating=review_data.get('score', 0),
                title=None,  # Play Store reviews don't have titles
                content=review_data.get('content', ''),
                review_date=review_date,
                helpful_count=review_data.get('thumbsUpCount', 0),
                reply_count=0,  # Not available in this API
                verified=True,  # Play Store reviews are verified
                version=review_data.get('appVersion'),
                language='en',  # We're scraping English reviews
                country='us',   # We're scraping US reviews
                source_url=f"https://play.google.com/store/apps/details?id={app_config['package_id']}",
                raw_data={
                    'play_store_data': review_data,
                    'app_info': {
                        'title': app_info.get('title'),
                        'developer': app_info.get('developer'),
                        'category': app_info.get('genre'),
                        'rating': app_info.get('score'),
                        'reviews_count': app_info.get('reviews'),
                        'installs': app_info.get('installs'),
                        'price': app_info.get('price')
                    }
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error converting review format: {e}")
            return None
    
    def get_app_metadata(self, package_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for an app from Play Store.
        
        Args:
            package_id: The app's package ID
            
        Returns:
            App metadata dictionary or None if failed
        """
        if not GOOGLE_PLAY_SCRAPER_AVAILABLE:
            self.logger.error("google-play-scraper library not available")
            return None
        
        try:
            app_info = self._get_app_info(package_id)
            if not app_info:
                return None
            
            return {
                'package_id': package_id,
                'title': app_info.get('title'),
                'description': app_info.get('description'),
                'developer': app_info.get('developer'),
                'category': app_info.get('genre'),
                'rating': app_info.get('score'),
                'reviews_count': app_info.get('reviews'),
                'installs': app_info.get('installs'),
                'price': app_info.get('price'),
                'free': app_info.get('free'),
                'version': app_info.get('version'),
                'updated': app_info.get('updated'),
                'size': app_info.get('size'),
                'screenshots': app_info.get('screenshots', []),
                'url': app_info.get('url'),
                'scraped_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting app metadata for {package_id}: {e}")
            return None
    
    def search_apps(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for apps in Play Store.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of app metadata dictionaries
        """
        if not GOOGLE_PLAY_SCRAPER_AVAILABLE:
            self.logger.error("google-play-scraper library not available")
            return []
        
        try:
            from google_play_scraper import search
            
            self._respect_rate_limit()
            search_results = search(query, n_hits=limit)
            
            apps = []
            for result in search_results:
                app_metadata = {
                    'package_id': result.get('appId'),
                    'title': result.get('title'),
                    'developer': result.get('developer'),
                    'category': result.get('genre'),
                    'rating': result.get('score'),
                    'price': result.get('price'),
                    'free': result.get('free'),
                    'icon': result.get('icon'),
                    'url': result.get('url')
                }
                apps.append(app_metadata)
            
            return apps
            
        except Exception as e:
            self.logger.error(f"Error searching apps: {e}")
            return []
