"""
Deduplication module for review mining.
Removes duplicate and spam reviews using various similarity metrics.
"""

import hashlib
from typing import List, Dict, Any, Set, Tuple
import logging
from difflib import SequenceMatcher
import re

from config.settings import PROCESSING_CONFIG


class Deduplicator:
    """Class for removing duplicate and spam reviews."""
    
    def __init__(self):
        """Initialize the deduplicator."""
        self.logger = logging.getLogger("processor.deduplicator")
        self.similarity_threshold = PROCESSING_CONFIG.get('deduplication_threshold', 0.85)
    
    def deduplicate_reviews(self, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate reviews from a list.
        
        Args:
            reviews: List of review dictionaries
            
        Returns:
            List of deduplicated reviews
        """
        if not reviews:
            return []
        
        self.logger.info(f"Starting deduplication of {len(reviews)} reviews")
        
        # Step 1: Remove exact duplicates by hash
        reviews_after_hash = self._remove_hash_duplicates(reviews)
        
        # Step 2: Remove near-duplicates by content similarity
        reviews_after_similarity = self._remove_similarity_duplicates(reviews_after_hash)
        
        # Step 3: Remove spam reviews
        reviews_after_spam = self._remove_spam_reviews(reviews_after_similarity)
        
        # Step 4: Remove user duplicates (multiple reviews from same user for same app)
        final_reviews = self._remove_user_duplicates(reviews_after_spam)
        
        self.logger.info(f"Deduplication complete: {len(final_reviews)} reviews remaining from {len(reviews)} original")
        
        return final_reviews
    
    def _remove_hash_duplicates(self, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove exact duplicate reviews using content hash."""
        seen_hashes: Set[str] = set()
        unique_reviews = []
        
        for review in reviews:
            content_hash = self._get_content_hash(review)
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_reviews.append(review)
        
        removed_count = len(reviews) - len(unique_reviews)
        self.logger.info(f"Removed {removed_count} exact duplicates")
        
        return unique_reviews
    
    def _remove_similarity_duplicates(self, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove near-duplicate reviews using content similarity."""
        unique_reviews = []
        
        for i, review in enumerate(reviews):
            is_duplicate = False
            
            # Compare with all previously accepted reviews
            for j, unique_review in enumerate(unique_reviews):
                similarity = self._calculate_similarity(review, unique_review)
                
                if similarity >= self.similarity_threshold:
                    # Keep the review with higher quality score
                    if self._get_quality_score(review) > self._get_quality_score(unique_review):
                        # Replace the existing review with the higher quality one
                        unique_reviews[j] = review
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_reviews.append(review)
        
        removed_count = len(reviews) - len(unique_reviews)
        self.logger.info(f"Removed {removed_count} near-duplicate reviews")
        
        return unique_reviews
    
    def _remove_spam_reviews(self, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove spam reviews based on content patterns."""
        non_spam_reviews = []
        
        for review in reviews:
            if not self._is_spam_review(review):
                non_spam_reviews.append(review)
        
        removed_count = len(reviews) - len(non_spam_reviews)
        self.logger.info(f"Removed {removed_count} spam reviews")
        
        return non_spam_reviews
    
    def _remove_user_duplicates(self, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove multiple reviews from the same user for the same app."""
        user_app_reviews: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        
        # Group reviews by user and app
        for review in reviews:
            user_id = review.get('user_id', '')
            app_name = review.get('app_name', '')
            key = (user_id, app_name)
            
            if key not in user_app_reviews:
                user_app_reviews[key] = []
            user_app_reviews[key].append(review)
        
        # Keep only the best review for each user-app combination
        final_reviews = []
        duplicate_count = 0
        
        for key, user_reviews in user_app_reviews.items():
            if len(user_reviews) > 1:
                # Sort by quality score and keep the best one
                best_review = max(user_reviews, key=self._get_quality_score)
                final_reviews.append(best_review)
                duplicate_count += len(user_reviews) - 1
            else:
                final_reviews.append(user_reviews[0])
        
        self.logger.info(f"Removed {duplicate_count} user duplicate reviews")
        
        return final_reviews
    
    def _get_content_hash(self, review: Dict[str, Any]) -> str:
        """Generate a hash for review content."""
        content = review.get('content', '').strip().lower()
        title = review.get('title', '').strip().lower()
        combined = f"{title}|{content}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    def _calculate_similarity(self, review1: Dict[str, Any], review2: Dict[str, Any]) -> float:
        """
        Calculate similarity between two reviews.
        
        Args:
            review1: First review
            review2: Second review
            
        Returns:
            Similarity score between 0 and 1
        """
        content1 = self._normalize_for_comparison(review1.get('content', ''))
        content2 = self._normalize_for_comparison(review2.get('content', ''))
        
        if not content1 or not content2:
            return 0.0
        
        # Use SequenceMatcher for text similarity
        similarity = SequenceMatcher(None, content1, content2).ratio()
        
        # Boost similarity if titles are also similar
        title1 = self._normalize_for_comparison(review1.get('title', ''))
        title2 = self._normalize_for_comparison(review2.get('title', ''))
        
        if title1 and title2:
            title_similarity = SequenceMatcher(None, title1, title2).ratio()
            similarity = (similarity * 0.8) + (title_similarity * 0.2)
        
        return similarity
    
    def _normalize_for_comparison(self, text: str) -> str:
        """Normalize text for similarity comparison."""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation and extra whitespace
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = [word for word in text.split() if word not in stop_words]
        
        return ' '.join(words).strip()
    
    def _get_quality_score(self, review: Dict[str, Any]) -> float:
        """
        Calculate a quality score for a review.
        
        Args:
            review: Review dictionary
            
        Returns:
            Quality score (higher is better)
        """
        score = 0.0
        
        # Content length (longer is generally better, up to a point)
        content_length = len(review.get('content', ''))
        if content_length > 50:
            score += min(content_length / 200.0, 2.0)
        
        # Helpfulness indicators
        helpful_count = review.get('helpful_count', 0)
        score += min(helpful_count / 10.0, 2.0)
        
        # Verified reviews are better
        if review.get('verified', False):
            score += 1.0
        
        # Reviews with titles are often more thoughtful
        if review.get('title'):
            score += 0.5
        
        # Recent reviews might be more relevant
        review_date = review.get('review_date')
        if review_date:
            try:
                from datetime import datetime
                if isinstance(review_date, str):
                    review_dt = datetime.fromisoformat(review_date.replace('Z', '+00:00'))
                    days_old = (datetime.now() - review_dt.replace(tzinfo=None)).days
                    # Prefer reviews less than a year old
                    if days_old < 365:
                        score += (365 - days_old) / 365.0
            except:
                pass
        
        return score
    
    def _is_spam_review(self, review: Dict[str, Any]) -> bool:
        """
        Detect if a review is spam.
        
        Args:
            review: Review dictionary
            
        Returns:
            True if spam, False otherwise
        """
        content = review.get('content', '').lower()
        title = review.get('title', '').lower()
        combined_text = f"{title} {content}"
        
        # Spam patterns
        spam_patterns = [
            r'visit\s+my\s+website',
            r'click\s+here',
            r'make\s+money',
            r'free\s+money',
            r'earn\s+\$\d+',
            r'work\s+from\s+home',
            r'buy\s+now',
            r'limited\s+time',
            r'act\s+fast',
            r'special\s+offer',
            r'http[s]?://',
            r'www\.',
            r'\.com',
            r'whatsapp',
            r'telegram',
            r'contact\s+me',
        ]
        
        spam_count = sum(1 for pattern in spam_patterns if re.search(pattern, combined_text))
        
        # Multiple spam indicators
        if spam_count >= 2:
            return True
        
        # Very short reviews with promotional content
        if len(content) < 20 and spam_count >= 1:
            return True
        
        # Excessive capitalization
        if len(content) > 10:
            caps_ratio = sum(1 for c in content if c.isupper()) / len(content)
            if caps_ratio > 0.7:
                return True
        
        # Excessive repetition
        words = content.split()
        if len(words) > 5:
            unique_words = set(words)
            repetition_ratio = 1 - (len(unique_words) / len(words))
            if repetition_ratio > 0.7:
                return True
        
        return False
    
    def get_deduplication_stats(self, original_reviews: List[Dict[str, Any]], 
                               final_reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics about the deduplication process.
        
        Args:
            original_reviews: Original review list
            final_reviews: Final deduplicated review list
            
        Returns:
            Dictionary with deduplication statistics
        """
        return {
            'original_count': len(original_reviews),
            'final_count': len(final_reviews),
            'removed_count': len(original_reviews) - len(final_reviews),
            'removal_rate': (len(original_reviews) - len(final_reviews)) / len(original_reviews) if original_reviews else 0,
            'similarity_threshold': self.similarity_threshold
        }
