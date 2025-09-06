"""
Reddit scraper for mining app reviews and discussions.
Uses Reddit API (PRAW) to scrape relevant subreddits for app mentions and reviews.
"""

import praw
from typing import List, Dict, Any, Optional
import re
from datetime import datetime

from scrapers.base_scraper import BaseScraper
from config.settings import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
from config.apps import get_subreddits_for_category


class RedditScraper(BaseScraper):
    """Scraper for Reddit reviews and discussions."""
    
    def __init__(self):
        """Initialize the Reddit scraper."""
        super().__init__('reddit')
        self.reddit = None
        self._setup_reddit_client()
    
    def _setup_reddit_client(self):
        """Setup the Reddit API client."""
        try:
            if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
                self.logger.warning("Reddit API credentials not found. Some features may be limited.")
                return
            
            self.reddit = praw.Reddit(
                client_id=REDDIT_CLIENT_ID,
                client_secret=REDDIT_CLIENT_SECRET,
                user_agent=REDDIT_USER_AGENT,
                ratelimit_seconds=60
            )
            
            # Test the connection
            self.reddit.user.me()
            self.logger.info("Reddit API client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Reddit API client: {e}")
            self.reddit = None
    
    def validate_config(self, app_config: Dict[str, Any]) -> bool:
        """
        Validate the app configuration for Reddit scraping.
        
        Args:
            app_config: App configuration dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['name', 'keywords']
        return all(field in app_config for field in required_fields)
    
    def scrape_reviews(self, app_config: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Scrape Reddit posts and comments mentioning the app.
        
        Args:
            app_config: App configuration dictionary
            limit: Maximum number of posts/comments to scrape
            
        Returns:
            List of review/mention dictionaries
        """
        if not self.validate_config(app_config):
            self.logger.error("Invalid app configuration for Reddit scraping")
            return []
        
        if not self.reddit:
            self.logger.error("Reddit API client not available")
            return []
        
        reviews = []
        app_name = app_config['name']
        keywords = app_config.get('keywords', [])
        category = app_config.get('category', '')
        
        # Get relevant subreddits
        subreddits = self._get_relevant_subreddits(app_config, category)
        
        for subreddit_name in subreddits:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                posts = self._search_subreddit(subreddit, keywords, limit // len(subreddits))
                
                for post in posts:
                    # Process post
                    post_review = self._extract_post_data(post, app_name, app_config)
                    if post_review:
                        reviews.append(post_review)
                    
                    # Process comments
                    comment_reviews = self._extract_comments_data(post, app_name, app_config, limit=5)
                    reviews.extend(comment_reviews)
                    
                    if len(reviews) >= limit:
                        break
                
            except Exception as e:
                self.logger.error(f"Error scraping subreddit {subreddit_name}: {e}")
                continue
        
        self.logger.info(f"Scraped {len(reviews)} Reddit posts/comments for {app_name}")
        return reviews[:limit]
    
    def _get_relevant_subreddits(self, app_config: Dict[str, Any], category: str) -> List[str]:
        """Get list of relevant subreddits to search."""
        subreddits = set()
        
        # Add category-specific subreddits
        category_subreddits = get_subreddits_for_category(category)
        subreddits.update(category_subreddits)
        
        # Add app-specific subreddits if they exist
        app_name = app_config['name'].lower()
        subreddits.add(app_name)
        
        # Add general review subreddits
        general_subreddits = ['apps', 'AppHookup', 'androidapps', 'iosgaming', 'software']
        subreddits.update(general_subreddits)
        
        return list(subreddits)
    
    def _search_subreddit(self, subreddit, keywords: List[str], limit: int = 50):
        """Search a subreddit for posts containing keywords."""
        posts = []
        
        try:
            # Search by keywords
            for keyword in keywords:
                search_results = subreddit.search(keyword, limit=limit//len(keywords), sort='relevance')
                posts.extend(search_results)
            
            # Also get hot posts and filter by keywords
            hot_posts = subreddit.hot(limit=limit//2)
            for post in hot_posts:
                if any(keyword.lower() in post.title.lower() or 
                      keyword.lower() in post.selftext.lower() 
                      for keyword in keywords):
                    posts.append(post)
            
        except Exception as e:
            self.logger.error(f"Error searching subreddit: {e}")
        
        return posts[:limit]
    
    def _extract_post_data(self, post, app_name: str, app_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract review data from a Reddit post."""
        try:
            # Check if post is relevant
            if not self._is_relevant_post(post, app_config.get('keywords', [])):
                return None
            
            sentiment_score = self._analyze_sentiment_simple(post.title + ' ' + post.selftext)
            
            return self._create_review_dict(
                review_id=f"reddit_post_{post.id}",
                app_name=app_name,
                user_id=str(post.author) if post.author else 'deleted',
                username=str(post.author) if post.author else 'deleted',
                rating=self._convert_sentiment_to_rating(sentiment_score),
                title=post.title,
                content=post.selftext,
                review_date=datetime.fromtimestamp(post.created_utc).isoformat(),
                helpful_count=post.score,
                reply_count=post.num_comments,
                source_url=f"https://reddit.com{post.permalink}",
                raw_data={
                    'subreddit': str(post.subreddit),
                    'upvote_ratio': post.upvote_ratio,
                    'gilded': post.gilded,
                    'sentiment_score': sentiment_score,
                    'post_type': 'submission'
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting post data: {e}")
            return None
    
    def _extract_comments_data(self, post, app_name: str, app_config: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        """Extract review data from Reddit comments."""
        comments_data = []
        keywords = app_config.get('keywords', [])
        
        try:
            post.comments.replace_more(limit=0)  # Don't load "more comments"
            
            for comment in post.comments.list()[:limit]:
                if self._is_relevant_comment(comment, keywords):
                    sentiment_score = self._analyze_sentiment_simple(comment.body)
                    
                    comment_data = self._create_review_dict(
                        review_id=f"reddit_comment_{comment.id}",
                        app_name=app_name,
                        user_id=str(comment.author) if comment.author else 'deleted',
                        username=str(comment.author) if comment.author else 'deleted',
                        rating=self._convert_sentiment_to_rating(sentiment_score),
                        title=f"Comment on: {post.title[:50]}...",
                        content=comment.body,
                        review_date=datetime.fromtimestamp(comment.created_utc).isoformat(),
                        helpful_count=comment.score,
                        reply_count=len(comment.replies) if comment.replies else 0,
                        source_url=f"https://reddit.com{comment.permalink}",
                        raw_data={
                            'subreddit': str(comment.subreddit),
                            'parent_post_id': post.id,
                            'sentiment_score': sentiment_score,
                            'post_type': 'comment'
                        }
                    )
                    comments_data.append(comment_data)
        
        except Exception as e:
            self.logger.error(f"Error extracting comments data: {e}")
        
        return comments_data
    
    def _is_relevant_post(self, post, keywords: List[str]) -> bool:
        """Check if a post is relevant based on keywords."""
        text = (post.title + ' ' + post.selftext).lower()
        return any(keyword.lower() in text for keyword in keywords)
    
    def _is_relevant_comment(self, comment, keywords: List[str]) -> bool:
        """Check if a comment is relevant based on keywords."""
        text = comment.body.lower()
        return any(keyword.lower() in text for keyword in keywords) and len(comment.body) > 20
    
    def _analyze_sentiment_simple(self, text: str) -> float:
        """
        Simple sentiment analysis based on positive/negative keywords.
        Returns a score between -1 (negative) and 1 (positive).
        """
        positive_words = ['good', 'great', 'excellent', 'amazing', 'love', 'best', 'perfect', 'awesome', 'fantastic']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'worst', 'horrible', 'disgusting', 'useless', 'broken']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total_words = len(text.split())
        if total_words == 0:
            return 0
        
        sentiment = (positive_count - negative_count) / max(total_words, 1)
        return max(-1, min(1, sentiment * 10))  # Scale and clamp between -1 and 1
    
    def _convert_sentiment_to_rating(self, sentiment_score: float) -> int:
        """Convert sentiment score to 1-5 star rating."""
        if sentiment_score >= 0.5:
            return 5
        elif sentiment_score >= 0.2:
            return 4
        elif sentiment_score >= -0.2:
            return 3
        elif sentiment_score >= -0.5:
            return 2
        else:
            return 1
    
    def get_available_subreddits(self, app_config: Dict[str, Any]) -> List[str]:
        """Get list of available subreddits for an app."""
        category = app_config.get('category', '')
        return self._get_relevant_subreddits(app_config, category)
