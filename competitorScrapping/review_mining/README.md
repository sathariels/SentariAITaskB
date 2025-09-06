# Review Mining Application

A comprehensive system for scraping, processing, and analyzing app reviews from multiple platforms including Reddit and Google Play Store.

## Features

- **Multi-platform scraping**: Reddit discussions and Google Play Store reviews
- **Advanced processing**: Text cleaning, deduplication, and spam detection
- **Intelligent classification**: Automatic categorization by topic (UX/UI, Pricing, Performance, etc.)
- **Sentiment analysis**: Analyze review sentiment and rating patterns
- **Flexible export**: CSV, JSON, and comprehensive reports
- **Configurable targeting**: Easy setup for different apps and competitors

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd review_mining
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up API credentials (optional but recommended):
```bash
# For Reddit API access
export REDDIT_CLIENT_ID="your_reddit_client_id"
export REDDIT_CLIENT_SECRET="your_reddit_client_secret"
export REDDIT_USER_AGENT="ReviewMiner/1.0"
```

## Quick Start

### Command Line Usage

1. **List available apps**:
```bash
python main.py --list-apps
```

2. **Mine reviews for Spotify**:
```bash
python main.py spotify --platforms reddit playstore --limit 200
```

3. **Mine reviews with specific export formats**:
```bash
python main.py netflix --platforms reddit --formats csv report --limit 100
```

### Programmatic Usage

```python
from review_mining import ReviewMiner

# Initialize the miner
miner = ReviewMiner(log_level='INFO')

# Run the full pipeline
results = miner.run_full_pipeline(
    app_name='spotify',
    platforms=['reddit', 'playstore'],
    limit_per_platform=100,
    export_formats=['csv', 'json', 'report']
)

print(f"Processed {results['total_reviews_processed']} reviews")
```

## Project Structure

```
review_mining/
├── config/
│   ├── __init__.py
│   ├── settings.py          # API keys, rate limits, general settings
│   └── apps.py              # Target apps configuration
├── scrapers/
│   ├── __init__.py
│   ├── base_scraper.py      # Abstract base class for scrapers
│   ├── reddit_scraper.py    # Reddit-specific scraping logic
│   └── playstore_scraper.py # Google Play Store scraping logic
├── processors/
│   ├── __init__.py
│   ├── data_cleaner.py      # Text cleaning, normalization
│   ├── deduplicator.py      # Remove duplicates and spam
│   └── classifier.py        # Categorize reviews (UX, Pricing, etc.)
├── models/
│   ├── __init__.py
│   └── review.py            # Review data model/schema
├── utils/
│   ├── __init__.py
│   ├── helpers.py           # Common utility functions
│   └── export.py            # CSV export and data formatting
├── data/
│   ├── raw/                 # Raw scraped data
│   ├── processed/           # Cleaned and deduplicated data
│   └── exports/             # Final CSV outputs and reports
├── tests/
│   ├── __init__.py
│   ├── test_scrapers.py
│   └── test_processors.py
├── requirements.txt
├── main.py                  # Main orchestration script
└── README.md
```

## Configuration

### Adding New Apps

Edit `config/apps.py` to add new target apps:

```python
TARGET_APPS = {
    'mobile_apps': {
        'your_app': {
            'name': 'Your App Name',
            'package_id': 'com.yourcompany.yourapp',
            'category': 'productivity',
            'platforms': ['android', 'ios'],
            'keywords': ['your app', 'productivity', 'task management'],
            'competitors': ['competitor1', 'competitor2']
        }
    }
}
```

### Customizing Processing

Modify settings in `config/settings.py`:

```python
PROCESSING_CONFIG = {
    'min_review_length': 10,
    'max_review_length': 5000,
    'deduplication_threshold': 0.85,
    'classification_confidence_threshold': 0.7
}
```

### API Configuration

Set up API credentials in environment variables or `config/settings.py`:

- **Reddit API**: Required for comprehensive Reddit scraping
- **Google Play Store**: Uses `google-play-scraper` (no API key needed)

## Data Processing Pipeline

1. **Scraping**: Collect reviews from configured platforms
2. **Cleaning**: Remove HTML, normalize text, filter spam
3. **Deduplication**: Remove exact and near-duplicate reviews
4. **Classification**: Categorize by topic and analyze sentiment
5. **Export**: Generate CSV files and comprehensive reports

## Review Categories

The system automatically classifies reviews into categories:

- **UX/UI**: User experience and interface feedback
- **Pricing**: Cost and billing-related comments
- **Performance**: Speed, reliability, and technical issues
- **Features**: Functionality and feature requests
- **Customer Service**: Support and service quality
- **Content Quality**: Content and catalog feedback

## Export Formats

### CSV Export
- Individual files per app/platform combination
- Structured data with all review fields
- Suitable for spreadsheet analysis

### JSON Export
- Complete data with nested structures
- Preserves all metadata and processing results
- Machine-readable format

### Comprehensive Reports
- Summary statistics and insights
- Category analysis and sentiment trends
- Executive-friendly overview format

## API Reference

### Core Classes

#### ReviewMiner
Main orchestrator class for the entire pipeline.

```python
miner = ReviewMiner(log_level='INFO')
results = miner.run_full_pipeline(app_name, platforms, limit_per_platform)
```

#### Review
Data model representing a single review.

```python
review = Review.from_dict(review_data)
review.update_processing_results(sentiment='positive', primary_category='ux_ui')
```

#### ReviewBatch
Container for multiple reviews with batch-level metadata.

```python
batch = ReviewBatch(reviews, app_name='Spotify', platform='reddit')
stats = batch.get_stats()
```

### Scrapers

#### RedditScraper
Scrapes Reddit posts and comments mentioning target apps.

```python
scraper = RedditScraper()
reviews = scraper.scrape_reviews(app_config, limit=100)
```

#### PlayStoreScraper
Scrapes Google Play Store reviews.

```python
scraper = PlayStoreScraper()
reviews = scraper.scrape_reviews(app_config, limit=100)
```

### Processors

#### DataCleaner
Cleans and normalizes review text.

```python
cleaner = DataCleaner()
cleaned_reviews = cleaner.clean_reviews(raw_reviews)
```

#### Deduplicator
Removes duplicate and spam reviews.

```python
deduplicator = Deduplicator()
unique_reviews = deduplicator.deduplicate_reviews(reviews)
```

#### ReviewClassifier
Classifies reviews by category and sentiment.

```python
classifier = ReviewClassifier()
classified_reviews = classifier.classify_reviews(reviews)
```

## Testing

Run the test suite:

```bash
python -m pytest tests/
```

Run specific test modules:

```bash
python -m pytest tests/test_scrapers.py
python -m pytest tests/test_processors.py
```

## Performance Considerations

- **Rate Limiting**: Automatic rate limiting for API compliance
- **Memory Management**: Batch processing for large datasets
- **Retry Logic**: Robust error handling and retry mechanisms
- **Concurrent Processing**: Parallel processing where applicable

## Troubleshooting

### Common Issues

1. **Reddit API Errors**:
   - Ensure API credentials are set correctly
   - Check rate limits and quotas
   - Verify user agent string format

2. **Google Play Store Issues**:
   - Install `google-play-scraper`: `pip install google-play-scraper`
   - Some apps may have restricted review access
   - Rate limiting may cause temporary blocks

3. **Memory Issues**:
   - Reduce `limit_per_platform` for large datasets
   - Process apps individually rather than in batch
   - Monitor memory usage with `psutil`

### Logging

The application logs to both console and file. Check logs for detailed error information:

```bash
tail -f logs/review_mining.log
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Run tests: `python -m pytest`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with Python 3.7+
- Uses PRAW for Reddit API access
- Uses google-play-scraper for Play Store data
- Text processing with standard Python libraries

## Roadmap

- [ ] Add support for App Store reviews (iOS)
- [ ] Implement advanced NLP models for better classification
- [ ] Add real-time monitoring and alerts
- [ ] Create web dashboard for results visualization
- [ ] Add support for Twitter/X mentions
- [ ] Implement comparative analysis features

