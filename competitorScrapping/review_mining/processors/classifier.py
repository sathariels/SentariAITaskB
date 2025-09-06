"""
Review classification module for categorizing reviews by topic/sentiment.
Classifies reviews into categories like UX/UI, Pricing, Performance, etc.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
import logging
from collections import Counter

from config.settings import PROCESSING_CONFIG
from config.apps import REVIEW_CATEGORIES


class ReviewClassifier:
    """Class for classifying reviews into categories."""
    
    def __init__(self):
        """Initialize the review classifier."""
        self.logger = logging.getLogger("processor.classifier")
        self.confidence_threshold = PROCESSING_CONFIG.get('classification_confidence_threshold', 0.7)
        self.categories = REVIEW_CATEGORIES
    
    def classify_reviews(self, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Classify a list of reviews.
        
        Args:
            reviews: List of review dictionaries
            
        Returns:
            List of reviews with classification data added
        """
        classified_reviews = []
        
        for review in reviews:
            classified_review = self.classify_review(review)
            classified_reviews.append(classified_review)
        
        # Log classification statistics
        self._log_classification_stats(classified_reviews)
        
        return classified_reviews
    
    def classify_review(self, review: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify a single review.
        
        Args:
            review: Review dictionary
            
        Returns:
            Review dictionary with classification data added
        """
        # Create a copy to avoid modifying the original
        classified_review = review.copy()
        
        # Get text content for classification
        content = review.get('content', '')
        title = review.get('title', '')
        combined_text = f"{title} {content}".strip()
        
        if not combined_text:
            classified_review.update({
                'primary_category': 'unclassified',
                'category_scores': {},
                'classification_confidence': 0.0,
                'sentiment': 'neutral',
                'sentiment_score': 0.0
            })
            return classified_review
        
        # Classify by category
        category_scores = self._calculate_category_scores(combined_text)
        primary_category, confidence = self._get_primary_category(category_scores)
        
        # Analyze sentiment
        sentiment, sentiment_score = self._analyze_sentiment(combined_text)
        
        # Add classification data
        classified_review.update({
            'primary_category': primary_category,
            'category_scores': category_scores,
            'classification_confidence': confidence,
            'sentiment': sentiment,
            'sentiment_score': sentiment_score,
            'keywords_found': self._extract_keywords(combined_text),
            'classified_at': self._get_current_timestamp()
        })
        
        return classified_review
    
    def _calculate_category_scores(self, text: str) -> Dict[str, float]:
        """
        Calculate scores for each category based on keyword matches.
        
        Args:
            text: Text content to analyze
            
        Returns:
            Dictionary mapping category names to scores
        """
        text_lower = text.lower()
        scores = {}
        
        for category_id, category_data in self.categories.items():
            keywords = category_data.get('keywords', [])
            score = 0.0
            
            for keyword in keywords:
                # Count occurrences of keyword
                keyword_count = len(re.findall(r'\b' + re.escape(keyword.lower()) + r'\b', text_lower))
                
                # Weight by keyword importance (longer keywords get higher weight)
                weight = len(keyword.split()) * 0.5 + 1.0
                score += keyword_count * weight
            
            # Normalize by text length and number of keywords
            if len(text.split()) > 0:
                normalized_score = score / (len(text.split()) * 0.1 + 1)
                scores[category_id] = min(normalized_score, 1.0)  # Cap at 1.0
            else:
                scores[category_id] = 0.0
        
        return scores
    
    def _get_primary_category(self, category_scores: Dict[str, float]) -> Tuple[str, float]:
        """
        Get the primary category and confidence from scores.
        
        Args:
            category_scores: Dictionary of category scores
            
        Returns:
            Tuple of (primary_category, confidence)
        """
        if not category_scores:
            return 'unclassified', 0.0
        
        # Get the category with highest score
        primary_category = max(category_scores, key=category_scores.get)
        max_score = category_scores[primary_category]
        
        # Calculate confidence based on score difference
        sorted_scores = sorted(category_scores.values(), reverse=True)
        
        if len(sorted_scores) < 2 or sorted_scores[0] == 0:
            confidence = max_score
        else:
            # Confidence is higher when there's a clear winner
            score_diff = sorted_scores[0] - sorted_scores[1]
            confidence = min(max_score + score_diff, 1.0)
        
        # If confidence is below threshold, mark as unclassified
        if confidence < self.confidence_threshold:
            return 'unclassified', confidence
        
        return primary_category, confidence
    
    def _analyze_sentiment(self, text: str) -> Tuple[str, float]:
        """
        Analyze sentiment of the text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (sentiment_label, sentiment_score)
        """
        # Enhanced sentiment keywords with weights
        positive_keywords = {
            'excellent': 3, 'amazing': 3, 'outstanding': 3, 'fantastic': 3,
            'great': 2, 'good': 2, 'wonderful': 2, 'awesome': 3, 'love': 2,
            'best': 2, 'perfect': 3, 'brilliant': 2, 'superb': 2,
            'like': 1, 'nice': 1, 'fine': 1, 'okay': 1, 'decent': 1,
            'helpful': 1, 'useful': 1, 'easy': 1, 'smooth': 1, 'fast': 1
        }
        
        negative_keywords = {
            'terrible': 3, 'awful': 3, 'horrible': 3, 'disgusting': 3, 'trash': 3,
            'bad': 2, 'poor': 2, 'worst': 3, 'hate': 2, 'useless': 2,
            'broken': 2, 'buggy': 2, 'slow': 2, 'crash': 2, 'freezes': 2,
            'disappointed': 2, 'frustrated': 2, 'annoying': 1, 'confusing': 1,
            'difficult': 1, 'hard': 1, 'problem': 1, 'issue': 1, 'error': 1
        }
        
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        positive_score = 0
        negative_score = 0
        
        for word in words:
            if word in positive_keywords:
                positive_score += positive_keywords[word]
            elif word in negative_keywords:
                negative_score += negative_keywords[word]
        
        # Calculate net sentiment score
        total_words = len(words)
        if total_words == 0:
            return 'neutral', 0.0
        
        net_score = (positive_score - negative_score) / total_words
        
        # Determine sentiment label
        if net_score > 0.02:
            sentiment = 'positive'
        elif net_score < -0.02:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        # Normalize score to [-1, 1] range
        sentiment_score = max(-1.0, min(1.0, net_score * 10))
        
        return sentiment, sentiment_score
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract relevant keywords found in the text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of found keywords
        """
        text_lower = text.lower()
        found_keywords = []
        
        for category_data in self.categories.values():
            keywords = category_data.get('keywords', [])
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text_lower):
                    found_keywords.append(keyword)
        
        return list(set(found_keywords))  # Remove duplicates
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def _log_classification_stats(self, classified_reviews: List[Dict[str, Any]]):
        """Log classification statistics."""
        if not classified_reviews:
            return
        
        # Count categories
        category_counts = Counter()
        sentiment_counts = Counter()
        confidence_scores = []
        
        for review in classified_reviews:
            category_counts[review.get('primary_category', 'unclassified')] += 1
            sentiment_counts[review.get('sentiment', 'neutral')] += 1
            confidence_scores.append(review.get('classification_confidence', 0))
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        self.logger.info(f"Classification complete for {len(classified_reviews)} reviews")
        self.logger.info(f"Average confidence: {avg_confidence:.3f}")
        self.logger.info(f"Category distribution: {dict(category_counts)}")
        self.logger.info(f"Sentiment distribution: {dict(sentiment_counts)}")
    
    def get_classification_summary(self, classified_reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get summary statistics of classification results.
        
        Args:
            classified_reviews: List of classified reviews
            
        Returns:
            Dictionary with classification summary
        """
        if not classified_reviews:
            return {}
        
        category_counts = Counter()
        sentiment_counts = Counter()
        confidence_scores = []
        
        for review in classified_reviews:
            category_counts[review.get('primary_category', 'unclassified')] += 1
            sentiment_counts[review.get('sentiment', 'neutral')] += 1
            confidence_scores.append(review.get('classification_confidence', 0))
        
        return {
            'total_reviews': len(classified_reviews),
            'category_distribution': dict(category_counts),
            'sentiment_distribution': dict(sentiment_counts),
            'average_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            'high_confidence_count': sum(1 for score in confidence_scores if score >= self.confidence_threshold),
            'unclassified_count': category_counts.get('unclassified', 0),
            'classification_rate': 1 - (category_counts.get('unclassified', 0) / len(classified_reviews))
        }
    
    def get_category_insights(self, classified_reviews: List[Dict[str, Any]], 
                            category: str) -> Dict[str, Any]:
        """
        Get insights for a specific category.
        
        Args:
            classified_reviews: List of classified reviews
            category: Category to analyze
            
        Returns:
            Dictionary with category insights
        """
        category_reviews = [r for r in classified_reviews if r.get('primary_category') == category]
        
        if not category_reviews:
            return {'category': category, 'review_count': 0}
        
        sentiment_counts = Counter(r.get('sentiment', 'neutral') for r in category_reviews)
        avg_rating = sum(r.get('rating', 0) for r in category_reviews) / len(category_reviews)
        avg_sentiment = sum(r.get('sentiment_score', 0) for r in category_reviews) / len(category_reviews)
        
        # Extract common keywords
        all_keywords = []
        for review in category_reviews:
            all_keywords.extend(review.get('keywords_found', []))
        
        common_keywords = Counter(all_keywords).most_common(10)
        
        return {
            'category': category,
            'review_count': len(category_reviews),
            'sentiment_distribution': dict(sentiment_counts),
            'average_rating': avg_rating,
            'average_sentiment_score': avg_sentiment,
            'common_keywords': common_keywords,
            'sample_reviews': [
                {
                    'content': r.get('content', '')[:200] + '...' if len(r.get('content', '')) > 200 else r.get('content', ''),
                    'rating': r.get('rating'),
                    'sentiment': r.get('sentiment')
                }
                for r in category_reviews[:3]
            ]
        }
