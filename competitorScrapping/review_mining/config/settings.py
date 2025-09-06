"""
Configuration settings for the review mining application.
Contains API keys, rate limits, and general application settings.
"""

import os
from typing import Dict, Any

# API Configuration
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID', 'Wj2cbO3SZ4ntQI39RISUVw')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET', 'GVZW7MJg5nFhYkZ2n8J9cy82iJbv_A')
REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT', 'ReviewMiner/1.0')

# Rate Limiting Settings
RATE_LIMITS = {
    'reddit': {
        'requests_per_minute': 60,
        'requests_per_hour': 3600,
        'delay_between_requests': 1.0  # seconds
    },
    'playstore': {
        'requests_per_minute': 30,
        'requests_per_hour': 1800,
        'delay_between_requests': 2.0  # seconds
    }
}

# Scraping Configuration
SCRAPING_CONFIG = {
    'max_retries': 3,
    'timeout': 30,  # seconds
    'user_agents': [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    ]
}

# Data Processing Configuration
PROCESSING_CONFIG = {
    'min_review_length': 5,  # characters (lowered from 10)
    'max_review_length': 5000,  # characters
    'languages': ['en'],  # supported languages
    'deduplication_threshold': 0.90,  # similarity threshold for duplicate detection (raised to be less strict)
    'classification_confidence_threshold': 0.3  # lowered to accept more classifications
}

# Export Configuration
EXPORT_CONFIG = {
    'csv_encoding': 'utf-8',
    'date_format': '%Y-%m-%d %H:%M:%S',
    'max_rows_per_file': 10000
}

# Logging Configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': 'logs/review_mining.log'
}

# File Paths
DATA_PATHS = {
    'raw': 'data/raw',
    'processed': 'data/processed',
    'exports': 'data/exports',
    'logs': 'logs'
}
