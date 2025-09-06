"""
Data cleaning and normalization module for review mining.
Handles text cleaning, language detection, and data validation.
"""

import re
import html
import unicodedata
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from config.settings import PROCESSING_CONFIG


class DataCleaner:
    """Class for cleaning and normalizing review data."""
    
    def __init__(self):
        """Initialize the data cleaner."""
        self.logger = logging.getLogger("processor.data_cleaner")
        self.min_length = PROCESSING_CONFIG.get('min_review_length', 10)
        self.max_length = PROCESSING_CONFIG.get('max_review_length', 5000)
        self.supported_languages = PROCESSING_CONFIG.get('languages', ['en'])
    
    def clean_reviews(self, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Clean a list of review dictionaries.
        
        Args:
            reviews: List of review dictionaries
            
        Returns:
            List of cleaned review dictionaries
        """
        cleaned_reviews = []
        
        for review in reviews:
            cleaned_review = self.clean_review(review)
            if cleaned_review:
                cleaned_reviews.append(cleaned_review)
        
        self.logger.info(f"Cleaned {len(cleaned_reviews)} out of {len(reviews)} reviews")
        return cleaned_reviews
    
    def clean_review(self, review: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Clean a single review dictionary.
        
        Args:
            review: Review dictionary
            
        Returns:
            Cleaned review dictionary or None if invalid
        """
        try:
            # Create a copy to avoid modifying the original
            cleaned_review = review.copy()
            
            # Clean text fields
            cleaned_review['title'] = self.clean_text(review.get('title', ''))
            cleaned_review['content'] = self.clean_text(review.get('content', ''))
            
            # Validate review content
            if not self._is_valid_review(cleaned_review):
                return None
            
            # Normalize other fields
            cleaned_review['rating'] = self._normalize_rating(review.get('rating'))
            cleaned_review['review_date'] = self._normalize_date(review.get('review_date'))
            cleaned_review['helpful_count'] = self._normalize_count(review.get('helpful_count'))
            cleaned_review['reply_count'] = self._normalize_count(review.get('reply_count'))
            
            # Add cleaning metadata
            cleaned_review['cleaned_at'] = datetime.utcnow().isoformat()
            cleaned_review['original_length'] = len(review.get('content', ''))
            cleaned_review['cleaned_length'] = len(cleaned_review.get('content', ''))
            
            return cleaned_review
            
        except Exception as e:
            self.logger.error(f"Error cleaning review {review.get('review_id', 'unknown')}: {e}")
            return None
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text content.
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Normalize Unicode characters
        text = unicodedata.normalize('NFKC', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters
        text = ''.join(char for char in text if unicodedata.category(char) != 'Cc')
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+\.\S+', '', text)
        
        # Remove excessive punctuation
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        text = re.sub(r'[.]{3,}', '...', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?;:()\-\'\"@#]', '', text)
        
        # Trim whitespace
        text = text.strip()
        
        return text
    
    def _is_valid_review(self, review: Dict[str, Any]) -> bool:
        """
        Validate if a review meets quality criteria.
        
        Args:
            review: Review dictionary
            
        Returns:
            True if valid, False otherwise
        """
        content = review.get('content', '')
        
        # Check minimum length
        if len(content) < self.min_length:
            return False
        
        # Check maximum length
        if len(content) > self.max_length:
            return False
        
        # Check if content is not just punctuation or numbers
        alphanumeric_count = sum(1 for char in content if char.isalnum())
        if alphanumeric_count < 5:
            return False
        
        # Check for spam patterns
        if self._is_spam(content):
            return False
        
        # Check language (basic check)
        if not self._is_supported_language(content):
            return False
        
        return True
    
    def _is_spam(self, text: str) -> bool:
        """
        Basic spam detection.
        
        Args:
            text: Text to check
            
        Returns:
            True if likely spam, False otherwise
        """
        spam_patterns = [
            r'(.)\1{10,}',  # Repeated characters
            r'[A-Z]{20,}',  # Excessive caps
            r'www\.',       # URLs
            r'bit\.ly',     # Short URLs
            r'click here',  # Click bait
            r'free money',  # Common spam phrases
            r'buy now',
            r'limited time',
        ]
        
        text_lower = text.lower()
        for pattern in spam_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def _is_supported_language(self, text: str) -> bool:
        """
        Basic language detection (English only for now).
        
        Args:
            text: Text to check
            
        Returns:
            True if supported language, False otherwise
        """
        # Simple English detection - check for common English words
        english_words = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
        text_lower = text.lower()
        english_word_count = sum(1 for word in english_words if word in text_lower)
        
        # If we find at least 2 common English words, assume it's English
        return english_word_count >= 2
    
    def _normalize_rating(self, rating: Any) -> Optional[int]:
        """
        Normalize rating to integer between 1-5.
        
        Args:
            rating: Raw rating value
            
        Returns:
            Normalized rating or None if invalid
        """
        if rating is None:
            return None
        
        try:
            rating_float = float(rating)
            # Clamp between 1 and 5
            normalized = max(1, min(5, round(rating_float)))
            return int(normalized)
        except (ValueError, TypeError):
            return None
    
    def _normalize_date(self, date_str: Any) -> Optional[str]:
        """
        Normalize date to ISO format.
        
        Args:
            date_str: Raw date string
            
        Returns:
            ISO formatted date string or None if invalid
        """
        if not date_str:
            return None
        
        if isinstance(date_str, str):
            # If already in ISO format, return as is
            if re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', date_str):
                return date_str
            
            # Try to parse common date formats
            date_formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%d/%m/%Y',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%SZ'
            ]
            
            for fmt in date_formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
        
        return None
    
    def _normalize_count(self, count: Any) -> int:
        """
        Normalize count values to non-negative integers.
        
        Args:
            count: Raw count value
            
        Returns:
            Normalized count
        """
        if count is None:
            return 0
        
        try:
            count_int = int(float(count))
            return max(0, count_int)
        except (ValueError, TypeError):
            return 0
    
    def get_cleaning_stats(self, original_reviews: List[Dict[str, Any]], 
                          cleaned_reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics about the cleaning process.
        
        Args:
            original_reviews: Original review list
            cleaned_reviews: Cleaned review list
            
        Returns:
            Dictionary with cleaning statistics
        """
        return {
            'original_count': len(original_reviews),
            'cleaned_count': len(cleaned_reviews),
            'removed_count': len(original_reviews) - len(cleaned_reviews),
            'removal_rate': (len(original_reviews) - len(cleaned_reviews)) / len(original_reviews) if original_reviews else 0,
            'average_length_reduction': self._calculate_average_length_reduction(original_reviews, cleaned_reviews)
        }
    
    def _calculate_average_length_reduction(self, original_reviews: List[Dict[str, Any]], 
                                          cleaned_reviews: List[Dict[str, Any]]) -> float:
        """Calculate average length reduction from cleaning."""
        if not cleaned_reviews:
            return 0
        
        # Match cleaned reviews with originals by review_id
        length_reductions = []
        original_dict = {r.get('review_id'): r for r in original_reviews}
        
        for cleaned in cleaned_reviews:
            review_id = cleaned.get('review_id')
            if review_id in original_dict:
                original_len = len(original_dict[review_id].get('content', ''))
                cleaned_len = len(cleaned.get('content', ''))
                if original_len > 0:
                    reduction = (original_len - cleaned_len) / original_len
                    length_reductions.append(reduction)
        
        return sum(length_reductions) / len(length_reductions) if length_reductions else 0
