"""
Review data model and schema definitions.
Defines the structure and validation for review data.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
import json


@dataclass
class Review:
    """Data model for a review."""
    
    # Core identifiers
    review_id: str
    platform: str
    app_name: str
    
    # Content
    content: str
    title: Optional[str] = None
    rating: Optional[int] = None
    
    # User information
    user_id: Optional[str] = None
    username: Optional[str] = None
    verified: bool = False
    
    # Timestamps
    review_date: Optional[str] = None
    scraped_at: Optional[str] = None
    processed_at: Optional[str] = None
    
    # Engagement metrics
    helpful_count: int = 0
    reply_count: int = 0
    
    # Technical metadata
    app_id: Optional[str] = None
    version: Optional[str] = None
    language: Optional[str] = None
    country: Optional[str] = None
    device: Optional[str] = None
    source_url: Optional[str] = None
    
    # Processing results
    cleaned_content: Optional[str] = None
    primary_category: Optional[str] = None
    category_scores: Dict[str, float] = field(default_factory=dict)
    classification_confidence: float = 0.0
    sentiment: Optional[str] = None
    sentiment_score: float = 0.0
    keywords_found: List[str] = field(default_factory=list)
    
    # Quality metrics
    is_duplicate: bool = False
    is_spam: bool = False
    quality_score: float = 0.0
    
    # Raw data
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        # Validate required fields
        if not self.review_id:
            raise ValueError("review_id is required")
        if not self.platform:
            raise ValueError("platform is required")
        if not self.app_name:
            raise ValueError("app_name is required")
        
        # Set default timestamps
        current_time = datetime.utcnow().isoformat()
        if not self.scraped_at:
            self.scraped_at = current_time
        
        # Validate rating
        if self.rating is not None:
            if not isinstance(self.rating, int) or not (1 <= self.rating <= 5):
                raise ValueError("rating must be an integer between 1 and 5")
        
        # Validate sentiment
        if self.sentiment is not None:
            if self.sentiment not in ['positive', 'negative', 'neutral']:
                raise ValueError("sentiment must be 'positive', 'negative', or 'neutral'")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Review':
        """
        Create a Review instance from a dictionary.
        
        Args:
            data: Dictionary containing review data
            
        Returns:
            Review instance
        """
        # Extract known fields
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        review_data = {k: v for k, v in data.items() if k in known_fields}
        
        # Handle special cases for default factory fields
        if 'category_scores' not in review_data:
            review_data['category_scores'] = {}
        if 'keywords_found' not in review_data:
            review_data['keywords_found'] = []
        if 'raw_data' not in review_data:
            review_data['raw_data'] = {}
        
        return cls(**review_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the Review instance to a dictionary.
        
        Returns:
            Dictionary representation of the review
        """
        data = {}
        for field_name, field_def in self.__dataclass_fields__.items():
            value = getattr(self, field_name)
            data[field_name] = value
        return data
    
    def to_json(self) -> str:
        """
        Convert the Review instance to JSON string.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=2, default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Review':
        """
        Create a Review instance from JSON string.
        
        Args:
            json_str: JSON string containing review data
            
        Returns:
            Review instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def update_processing_results(self, 
                                cleaned_content: Optional[str] = None,
                                primary_category: Optional[str] = None,
                                category_scores: Optional[Dict[str, float]] = None,
                                classification_confidence: Optional[float] = None,
                                sentiment: Optional[str] = None,
                                sentiment_score: Optional[float] = None,
                                keywords_found: Optional[List[str]] = None,
                                is_duplicate: Optional[bool] = None,
                                is_spam: Optional[bool] = None,
                                quality_score: Optional[float] = None):
        """
        Update processing results for the review.
        
        Args:
            cleaned_content: Cleaned content text
            primary_category: Primary classification category
            category_scores: Category confidence scores
            classification_confidence: Classification confidence
            sentiment: Sentiment label
            sentiment_score: Sentiment score
            keywords_found: List of found keywords
            is_duplicate: Whether review is duplicate
            is_spam: Whether review is spam
            quality_score: Quality score
        """
        if cleaned_content is not None:
            self.cleaned_content = cleaned_content
        if primary_category is not None:
            self.primary_category = primary_category
        if category_scores is not None:
            self.category_scores = category_scores
        if classification_confidence is not None:
            self.classification_confidence = classification_confidence
        if sentiment is not None:
            self.sentiment = sentiment
        if sentiment_score is not None:
            self.sentiment_score = sentiment_score
        if keywords_found is not None:
            self.keywords_found = keywords_found
        if is_duplicate is not None:
            self.is_duplicate = is_duplicate
        if is_spam is not None:
            self.is_spam = is_spam
        if quality_score is not None:
            self.quality_score = quality_score
        
        # Update processed timestamp
        self.processed_at = datetime.utcnow().isoformat()
    
    def get_display_content(self) -> str:
        """
        Get the best available content for display.
        
        Returns:
            Cleaned content if available, otherwise original content
        """
        return self.cleaned_content if self.cleaned_content else self.content
    
    def is_processed(self) -> bool:
        """
        Check if the review has been processed.
        
        Returns:
            True if processed, False otherwise
        """
        return self.processed_at is not None
    
    def is_high_quality(self, min_quality_score: float = 0.5) -> bool:
        """
        Check if the review meets quality criteria.
        
        Args:
            min_quality_score: Minimum quality score threshold
            
        Returns:
            True if high quality, False otherwise
        """
        return (not self.is_spam and 
                not self.is_duplicate and 
                self.quality_score >= min_quality_score and
                len(self.content) >= 20)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the review.
        
        Returns:
            Dictionary with review summary
        """
        content_preview = self.get_display_content()[:100] + "..." if len(self.get_display_content()) > 100 else self.get_display_content()
        
        return {
            'review_id': self.review_id,
            'platform': self.platform,
            'app_name': self.app_name,
            'rating': self.rating,
            'sentiment': self.sentiment,
            'primary_category': self.primary_category,
            'content_preview': content_preview,
            'review_date': self.review_date,
            'is_high_quality': self.is_high_quality(),
            'helpful_count': self.helpful_count
        }


@dataclass
class ReviewBatch:
    """Container for a batch of reviews with metadata."""
    
    reviews: List[Review]
    app_name: str
    platform: str
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    total_scraped: int = 0
    total_processed: int = 0
    processing_stats: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization setup."""
        if not self.total_scraped:
            self.total_scraped = len(self.reviews)
    
    def add_review(self, review: Review):
        """
        Add a review to the batch.
        
        Args:
            review: Review to add
        """
        self.reviews.append(review)
        self.total_scraped = len(self.reviews)
    
    def get_processed_reviews(self) -> List[Review]:
        """
        Get only the processed reviews.
        
        Returns:
            List of processed reviews
        """
        return [review for review in self.reviews if review.is_processed()]
    
    def get_high_quality_reviews(self, min_quality_score: float = 0.5) -> List[Review]:
        """
        Get only high quality reviews.
        
        Args:
            min_quality_score: Minimum quality score threshold
            
        Returns:
            List of high quality reviews
        """
        return [review for review in self.reviews if review.is_high_quality(min_quality_score)]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics for the review batch.
        
        Returns:
            Dictionary with batch statistics
        """
        processed_reviews = self.get_processed_reviews()
        high_quality_reviews = self.get_high_quality_reviews()
        
        # Category distribution
        category_counts = {}
        sentiment_counts = {}
        rating_counts = {}
        
        for review in processed_reviews:
            # Categories
            category = review.primary_category or 'unclassified'
            category_counts[category] = category_counts.get(category, 0) + 1
            
            # Sentiment
            sentiment = review.sentiment or 'neutral'
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
            
            # Ratings
            if review.rating:
                rating_counts[review.rating] = rating_counts.get(review.rating, 0) + 1
        
        return {
            'app_name': self.app_name,
            'platform': self.platform,
            'total_reviews': len(self.reviews),
            'processed_reviews': len(processed_reviews),
            'high_quality_reviews': len(high_quality_reviews),
            'spam_reviews': sum(1 for r in self.reviews if r.is_spam),
            'duplicate_reviews': sum(1 for r in self.reviews if r.is_duplicate),
            'category_distribution': category_counts,
            'sentiment_distribution': sentiment_counts,
            'rating_distribution': rating_counts,
            'average_rating': sum(r.rating for r in processed_reviews if r.rating) / len([r for r in processed_reviews if r.rating]) if any(r.rating for r in processed_reviews) else 0,
            'average_sentiment_score': sum(r.sentiment_score for r in processed_reviews) / len(processed_reviews) if processed_reviews else 0,
            'scraped_at': self.scraped_at,
            'processing_stats': self.processing_stats
        }
    
    def to_dict_list(self) -> List[Dict[str, Any]]:
        """
        Convert all reviews to a list of dictionaries.
        
        Returns:
            List of review dictionaries
        """
        return [review.to_dict() for review in self.reviews]
    
    def save_to_json(self, filepath: str):
        """
        Save the review batch to a JSON file.
        
        Args:
            filepath: Path to save the JSON file
        """
        data = {
            'metadata': {
                'app_name': self.app_name,
                'platform': self.platform,
                'scraped_at': self.scraped_at,
                'total_scraped': self.total_scraped,
                'total_processed': self.total_processed,
                'processing_stats': self.processing_stats
            },
            'reviews': self.to_dict_list()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    @classmethod
    def load_from_json(cls, filepath: str) -> 'ReviewBatch':
        """
        Load a review batch from a JSON file.
        
        Args:
            filepath: Path to the JSON file
            
        Returns:
            ReviewBatch instance
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        metadata = data.get('metadata', {})
        review_dicts = data.get('reviews', [])
        
        reviews = [Review.from_dict(review_dict) for review_dict in review_dicts]
        
        return cls(
            reviews=reviews,
            app_name=metadata.get('app_name', ''),
            platform=metadata.get('platform', ''),
            scraped_at=metadata.get('scraped_at', ''),
            total_scraped=metadata.get('total_scraped', len(reviews)),
            total_processed=metadata.get('total_processed', 0),
            processing_stats=metadata.get('processing_stats', {})
        )

