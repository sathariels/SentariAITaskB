"""
Unit tests for processor modules.
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime

from ..processors.data_cleaner import DataCleaner
from ..processors.deduplicator import Deduplicator
from ..processors.classifier import ReviewClassifier
from ..models.review import Review


class TestDataCleaner(unittest.TestCase):
    """Test cases for DataCleaner class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cleaner = DataCleaner()
    
    def test_clean_text_basic(self):
        """Test basic text cleaning."""
        dirty_text = "  This is a   test\t\nwith extra   whitespace!  "
        clean_text = self.cleaner.clean_text(dirty_text)
        
        self.assertEqual(clean_text, "This is a test with extra whitespace!")
    
    def test_clean_text_html_entities(self):
        """Test HTML entity decoding."""
        html_text = "This &amp; that &lt;tag&gt; &quot;quote&quot;"
        clean_text = self.cleaner.clean_text(html_text)
        
        self.assertIn("&", clean_text)
        self.assertIn("<", clean_text)
        self.assertIn(">", clean_text)
        self.assertIn('"', clean_text)
    
    def test_clean_text_urls(self):
        """Test URL removal."""
        text_with_url = "Check out https://example.com for more info"
        clean_text = self.cleaner.clean_text(text_with_url)
        
        self.assertNotIn("https://example.com", clean_text)
        self.assertIn("Check out", clean_text)
        self.assertIn("for more info", clean_text)
    
    def test_clean_text_emails(self):
        """Test email removal."""
        text_with_email = "Contact us at support@example.com for help"
        clean_text = self.cleaner.clean_text(text_with_email)
        
        self.assertNotIn("support@example.com", clean_text)
        self.assertIn("Contact us at", clean_text)
        self.assertIn("for help", clean_text)
    
    def test_is_valid_review_length(self):
        """Test review length validation."""
        # Too short
        short_review = {'content': 'Bad'}
        self.assertFalse(self.cleaner._is_valid_review(short_review))
        
        # Good length
        good_review = {'content': 'This is a reasonable length review content'}
        self.assertTrue(self.cleaner._is_valid_review(good_review))
        
        # Too long (assuming max_length is 5000)
        long_content = 'x' * 6000
        long_review = {'content': long_content}
        self.assertFalse(self.cleaner._is_valid_review(long_review))
    
    def test_is_spam_detection(self):
        """Test spam detection."""
        spam_text = "CLICK HERE for FREE MONEY!!! Visit www.scam.com"
        self.assertTrue(self.cleaner._is_spam(spam_text))
        
        normal_text = "This app works well for my daily tasks"
        self.assertFalse(self.cleaner._is_spam(normal_text))
    
    def test_normalize_rating(self):
        """Test rating normalization."""
        self.assertEqual(self.cleaner._normalize_rating(3), 3)
        self.assertEqual(self.cleaner._normalize_rating(3.7), 4)
        self.assertEqual(self.cleaner._normalize_rating(0), 1)  # Clamp to minimum
        self.assertEqual(self.cleaner._normalize_rating(6), 5)  # Clamp to maximum
        self.assertIsNone(self.cleaner._normalize_rating(None))
        self.assertIsNone(self.cleaner._normalize_rating("invalid"))
    
    def test_normalize_date(self):
        """Test date normalization."""
        # ISO format should pass through
        iso_date = "2023-01-01T12:00:00"
        self.assertEqual(self.cleaner._normalize_date(iso_date), iso_date)
        
        # Other formats should be converted
        date_formats = [
            "2023-01-01 12:00:00",
            "2023-01-01",
            "01/01/2023"
        ]
        
        for date_str in date_formats:
            result = self.cleaner._normalize_date(date_str)
            self.assertIsNotNone(result)
            self.assertIn("2023-01-01", result)
    
    def test_clean_review_complete(self):
        """Test complete review cleaning process."""
        dirty_review = {
            'review_id': 'test_123',
            'title': '  Great App!  ',
            'content': '  This app is really good https://spam.com and useful  ',
            'rating': 4.7,
            'helpful_count': '10',
            'review_date': '2023-01-01 12:00:00'
        }
        
        cleaned = self.cleaner.clean_review(dirty_review)
        
        self.assertIsNotNone(cleaned)
        self.assertEqual(cleaned['title'], 'Great App!')
        self.assertNotIn('https://spam.com', cleaned['content'])
        self.assertEqual(cleaned['rating'], 5)  # Rounded up
        self.assertEqual(cleaned['helpful_count'], 10)
        self.assertIsNotNone(cleaned['cleaned_at'])


class TestDeduplicator(unittest.TestCase):
    """Test cases for Deduplicator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.deduplicator = Deduplicator()
    
    def test_get_content_hash(self):
        """Test content hash generation."""
        review1 = {'content': 'This is a test', 'title': 'Test'}
        review2 = {'content': 'This is a test', 'title': 'Test'}
        review3 = {'content': 'Different content', 'title': 'Test'}
        
        hash1 = self.deduplicator._get_content_hash(review1)
        hash2 = self.deduplicator._get_content_hash(review2)
        hash3 = self.deduplicator._get_content_hash(review3)
        
        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)
    
    def test_calculate_similarity(self):
        """Test similarity calculation."""
        review1 = {'content': 'This app is really good and useful'}
        review2 = {'content': 'This app is really good and helpful'}
        review3 = {'content': 'Completely different review content'}
        
        similarity_high = self.deduplicator._calculate_similarity(review1, review2)
        similarity_low = self.deduplicator._calculate_similarity(review1, review3)
        
        self.assertGreater(similarity_high, similarity_low)
        self.assertGreater(similarity_high, 0.5)  # Should be quite similar
        self.assertLess(similarity_low, 0.5)    # Should be less similar
    
    def test_normalize_for_comparison(self):
        """Test text normalization for comparison."""
        text = "This is a TEST with punctuation!!! And, extra words."
        normalized = self.deduplicator._normalize_for_comparison(text)
        
        self.assertNotIn('!!!', normalized)
        self.assertNotIn(',', normalized)
        self.assertEqual(normalized.lower(), normalized)
    
    def test_get_quality_score(self):
        """Test quality score calculation."""
        high_quality = {
            'content': 'This is a detailed review with lots of helpful information about the app features',
            'helpful_count': 15,
            'verified': True,
            'title': 'Detailed Review',
            'review_date': datetime.now().isoformat()
        }
        
        low_quality = {
            'content': 'Bad',
            'helpful_count': 0,
            'verified': False,
            'title': None,
            'review_date': None
        }
        
        high_score = self.deduplicator._get_quality_score(high_quality)
        low_score = self.deduplicator._get_quality_score(low_quality)
        
        self.assertGreater(high_score, low_score)
    
    def test_is_spam_review(self):
        """Test spam review detection."""
        spam_review = {
            'content': 'Visit my website www.spam.com for free money!',
            'title': 'Make money fast!'
        }
        
        normal_review = {
            'content': 'This app works well for organizing my tasks',
            'title': 'Good productivity app'
        }
        
        self.assertTrue(self.deduplicator._is_spam_review(spam_review))
        self.assertFalse(self.deduplicator._is_spam_review(normal_review))
    
    def test_remove_hash_duplicates(self):
        """Test exact duplicate removal."""
        reviews = [
            {'content': 'Same content', 'title': 'Same title'},
            {'content': 'Same content', 'title': 'Same title'},  # Duplicate
            {'content': 'Different content', 'title': 'Different title'}
        ]
        
        unique_reviews = self.deduplicator._remove_hash_duplicates(reviews)
        
        self.assertEqual(len(unique_reviews), 2)
    
    def test_deduplicate_reviews_complete(self):
        """Test complete deduplication process."""
        reviews = [
            {'review_id': '1', 'user_id': 'user1', 'app_name': 'TestApp', 'content': 'Great app!', 'helpful_count': 10},
            {'review_id': '2', 'user_id': 'user1', 'app_name': 'TestApp', 'content': 'Great app!', 'helpful_count': 5},  # Duplicate
            {'review_id': '3', 'user_id': 'user2', 'app_name': 'TestApp', 'content': 'This app is great!', 'helpful_count': 8},  # Similar
            {'review_id': '4', 'user_id': 'user3', 'app_name': 'TestApp', 'content': 'Visit www.spam.com', 'helpful_count': 0},  # Spam
            {'review_id': '5', 'user_id': 'user4', 'app_name': 'TestApp', 'content': 'Completely different review', 'helpful_count': 3}
        ]
        
        deduplicated = self.deduplicator.deduplicate_reviews(reviews)
        
        self.assertLess(len(deduplicated), len(reviews))
        
        # Check that spam was removed
        contents = [r['content'] for r in deduplicated]
        self.assertNotIn('Visit www.spam.com', ' '.join(contents))


class TestReviewClassifier(unittest.TestCase):
    """Test cases for ReviewClassifier class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.classifier = ReviewClassifier()
    
    def test_calculate_category_scores(self):
        """Test category score calculation."""
        text = "The interface is confusing and the price is too expensive"
        scores = self.classifier._calculate_category_scores(text)
        
        self.assertIn('ux_ui', scores)
        self.assertIn('pricing', scores)
        
        # Should have higher scores for relevant categories
        self.assertGreater(scores.get('ux_ui', 0), 0)
        self.assertGreater(scores.get('pricing', 0), 0)
    
    def test_get_primary_category(self):
        """Test primary category selection."""
        scores = {
            'ux_ui': 0.8,
            'pricing': 0.3,
            'performance': 0.1
        }
        
        primary, confidence = self.classifier._get_primary_category(scores)
        
        self.assertEqual(primary, 'ux_ui')
        self.assertGreater(confidence, 0.5)
    
    def test_analyze_sentiment(self):
        """Test sentiment analysis."""
        positive_text = "This app is excellent and amazing!"
        negative_text = "This app is terrible and awful!"
        neutral_text = "This app exists and does things."
        
        pos_sentiment, pos_score = self.classifier._analyze_sentiment(positive_text)
        neg_sentiment, neg_score = self.classifier._analyze_sentiment(negative_text)
        neu_sentiment, neu_score = self.classifier._analyze_sentiment(neutral_text)
        
        self.assertEqual(pos_sentiment, 'positive')
        self.assertEqual(neg_sentiment, 'negative')
        self.assertEqual(neu_sentiment, 'neutral')
        
        self.assertGreater(pos_score, 0)
        self.assertLess(neg_score, 0)
        self.assertAlmostEqual(neu_score, 0, places=1)
    
    def test_extract_keywords(self):
        """Test keyword extraction."""
        text = "The user interface is confusing and the price is expensive"
        keywords = self.classifier._extract_keywords(text)
        
        self.assertIn('interface', keywords)
        self.assertIn('price', keywords)
    
    def test_classify_review_complete(self):
        """Test complete review classification."""
        review = {
            'content': 'The app interface is really confusing and hard to use',
            'title': 'Poor UX Design',
            'rating': 2
        }
        
        classified = self.classifier.classify_review(review)
        
        self.assertIn('primary_category', classified)
        self.assertIn('category_scores', classified)
        self.assertIn('classification_confidence', classified)
        self.assertIn('sentiment', classified)
        self.assertIn('sentiment_score', classified)
        
        # Should be classified as UX-related
        self.assertEqual(classified['primary_category'], 'ux_ui')
        self.assertEqual(classified['sentiment'], 'negative')
    
    def test_classify_empty_content(self):
        """Test classification with empty content."""
        review = {
            'content': '',
            'title': ''
        }
        
        classified = self.classifier.classify_review(review)
        
        self.assertEqual(classified['primary_category'], 'unclassified')
        self.assertEqual(classified['sentiment'], 'neutral')
        self.assertEqual(classified['classification_confidence'], 0.0)
    
    def test_get_classification_summary(self):
        """Test classification summary generation."""
        classified_reviews = [
            {'primary_category': 'ux_ui', 'sentiment': 'negative', 'classification_confidence': 0.8},
            {'primary_category': 'pricing', 'sentiment': 'positive', 'classification_confidence': 0.9},
            {'primary_category': 'ux_ui', 'sentiment': 'neutral', 'classification_confidence': 0.7},
            {'primary_category': 'unclassified', 'sentiment': 'neutral', 'classification_confidence': 0.2}
        ]
        
        summary = self.classifier.get_classification_summary(classified_reviews)
        
        self.assertEqual(summary['total_reviews'], 4)
        self.assertEqual(summary['category_distribution']['ux_ui'], 2)
        self.assertEqual(summary['category_distribution']['pricing'], 1)
        self.assertEqual(summary['unclassified_count'], 1)
        self.assertEqual(summary['high_confidence_count'], 3)  # >= 0.7 threshold
    
    def test_get_category_insights(self):
        """Test category insights generation."""
        classified_reviews = [
            {
                'primary_category': 'ux_ui', 
                'sentiment': 'negative', 
                'sentiment_score': -0.5,
                'rating': 2,
                'content': 'Interface is confusing',
                'keywords_found': ['interface', 'confusing']
            },
            {
                'primary_category': 'ux_ui', 
                'sentiment': 'positive', 
                'sentiment_score': 0.7,
                'rating': 5,
                'content': 'Great design',
                'keywords_found': ['design']
            }
        ]
        
        insights = self.classifier.get_category_insights(classified_reviews, 'ux_ui')
        
        self.assertEqual(insights['category'], 'ux_ui')
        self.assertEqual(insights['review_count'], 2)
        self.assertEqual(insights['average_rating'], 3.5)
        self.assertIn('interface', [kw[0] for kw in insights['common_keywords']])


class TestProcessorIntegration(unittest.TestCase):
    """Integration tests for processors."""
    
    def test_full_processing_pipeline(self):
        """Test complete processing pipeline."""
        # Create test reviews
        raw_reviews = [
            {
                'review_id': '1',
                'content': '  This app has terrible UI design and is too expensive!!!  ',
                'title': 'Bad App',
                'rating': 1,
                'user_id': 'user1',
                'app_name': 'TestApp'
            },
            {
                'review_id': '2', 
                'content': '  This app has terrible UI design and is too expensive!!!  ',  # Duplicate
                'title': 'Bad App',
                'rating': 1,
                'user_id': 'user2',
                'app_name': 'TestApp'
            },
            {
                'review_id': '3',
                'content': 'Great interface and reasonable pricing. Love it!',
                'title': 'Excellent App',
                'rating': 5,
                'user_id': 'user3',
                'app_name': 'TestApp'
            }
        ]
        
        # Process through pipeline
        cleaner = DataCleaner()
        deduplicator = Deduplicator()
        classifier = ReviewClassifier()
        
        # Step 1: Clean
        cleaned_reviews = []
        for review in raw_reviews:
            cleaned = cleaner.clean_review(review)
            if cleaned:
                cleaned_reviews.append(cleaned)
        
        # Step 2: Deduplicate
        deduplicated_reviews = deduplicator.deduplicate_reviews(cleaned_reviews)
        
        # Step 3: Classify
        classified_reviews = classifier.classify_reviews(deduplicated_reviews)
        
        # Verify results
        self.assertLess(len(classified_reviews), len(raw_reviews))  # Duplicates removed
        
        for review in classified_reviews:
            self.assertIn('primary_category', review)
            self.assertIn('sentiment', review)
            self.assertNotIn('!!!', review['content'])  # Cleaned
    
    def test_review_model_integration(self):
        """Test integration with Review model."""
        # Create Review objects
        review_data = {
            'review_id': 'test_123',
            'platform': 'test',
            'app_name': 'TestApp',
            'content': 'The interface design is confusing',
            'rating': 2
        }
        
        review = Review.from_dict(review_data)
        
        # Process with classifier
        classifier = ReviewClassifier()
        classified_dict = classifier.classify_review(review.to_dict())
        
        # Update Review object
        review.update_processing_results(
            primary_category=classified_dict['primary_category'],
            sentiment=classified_dict['sentiment'],
            sentiment_score=classified_dict['sentiment_score']
        )
        
        self.assertTrue(review.is_processed())
        self.assertEqual(review.primary_category, 'ux_ui')
        self.assertEqual(review.sentiment, 'negative')


if __name__ == '__main__':
    unittest.main()

