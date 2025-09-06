"""
Helper utilities for the review mining application.
Contains common utility functions used across the application.
"""

import os
import json
import logging
import hashlib
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import time
import functools
import csv


def setup_logging(log_level: str = 'INFO', log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR')
        log_file: Optional log file path
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger('review_mining')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def ensure_directory(directory: str) -> str:
    """
    Ensure a directory exists, create it if it doesn't.
    
    Args:
        directory: Directory path
        
    Returns:
        Directory path
    """
    os.makedirs(directory, exist_ok=True)
    return directory


def safe_filename(filename: str) -> str:
    """
    Create a safe filename by removing/replacing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Safe filename
    """
    invalid_chars = '<>:"/\\|?*'
    safe_name = filename
    
    for char in invalid_chars:
        safe_name = safe_name.replace(char, '_')
    
    # Replace multiple underscores with single underscore
    safe_name = '_'.join(filter(None, safe_name.split('_')))
    
    # Limit length
    if len(safe_name) > 200:
        safe_name = safe_name[:200]
    
    return safe_name


def generate_hash(data: Union[str, Dict, List]) -> str:
    """
    Generate a hash for data.
    
    Args:
        data: Data to hash
        
    Returns:
        Hash string
    """
    if isinstance(data, (dict, list)):
        data_str = json.dumps(data, sort_keys=True)
    else:
        data_str = str(data)
    
    return hashlib.md5(data_str.encode('utf-8')).hexdigest()


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of specified size.
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    Flatten a nested dictionary.
    
    Args:
        d: Dictionary to flatten
        parent_key: Parent key prefix
        sep: Separator for nested keys
        
    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def retry_with_backoff(max_retries: int = 3, backoff_factor: float = 1.0, 
                      exceptions: tuple = (Exception,)):
    """
    Decorator for retrying function calls with exponential backoff.
    
    Args:
        max_retries: Maximum number of retries
        backoff_factor: Backoff multiplication factor
        exceptions: Tuple of exceptions to catch
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        raise e
                    
                    wait_time = backoff_factor * (2 ** attempt)
                    time.sleep(wait_time)
            
        return wrapper
    return decorator


def rate_limit(calls_per_second: float):
    """
    Decorator for rate limiting function calls.
    
    Args:
        calls_per_second: Maximum calls per second
        
    Returns:
        Decorator function
    """
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator


def format_timestamp(timestamp: Optional[str] = None, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Format a timestamp string.
    
    Args:
        timestamp: ISO timestamp string (default: current time)
        format_str: Format string
        
    Returns:
        Formatted timestamp
    """
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            dt = dt.replace(tzinfo=None)  # Remove timezone for formatting
        except ValueError:
            dt = datetime.now()
    else:
        dt = datetime.now()
    
    return dt.strftime(format_str)


def parse_date_range(date_str: str) -> tuple[datetime, datetime]:
    """
    Parse a date range string into start and end dates.
    
    Args:
        date_str: Date range string (e.g., "2023-01-01:2023-12-31", "last_7_days", "last_month")
        
    Returns:
        Tuple of (start_date, end_date)
    """
    now = datetime.now()
    
    if ':' in date_str:
        # Explicit date range
        start_str, end_str = date_str.split(':')
        start_date = datetime.fromisoformat(start_str)
        end_date = datetime.fromisoformat(end_str)
    elif date_str == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    elif date_str == 'yesterday':
        yesterday = now - timedelta(days=1)
        start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif date_str.startswith('last_') and date_str.endswith('_days'):
        days = int(date_str.replace('last_', '').replace('_days', ''))
        start_date = now - timedelta(days=days)
        end_date = now
    elif date_str == 'last_week':
        start_date = now - timedelta(weeks=1)
        end_date = now
    elif date_str == 'last_month':
        start_date = now - timedelta(days=30)
        end_date = now
    else:
        # Single date
        start_date = datetime.fromisoformat(date_str)
        end_date = start_date + timedelta(days=1)
    
    return start_date, end_date


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate text similarity using simple metrics.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Similarity score between 0 and 1
    """
    if not text1 or not text2:
        return 0.0
    
    # Simple Jaccard similarity using words
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0


def clean_text_simple(text: str) -> str:
    """
    Simple text cleaning utility.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Basic cleaning
    import re
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?;:()\-\'\"@#]', '', text)
    
    return text.strip()


def load_json_file(filepath: str) -> Dict[str, Any]:
    """
    Load a JSON file safely.
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        Dictionary data or empty dict if failed
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.warning(f"Failed to load JSON file {filepath}: {e}")
        return {}


def save_json_file(data: Dict[str, Any], filepath: str):
    """
    Save data to JSON file safely.
    
    Args:
        data: Data to save
        filepath: Path to save file
    """
    ensure_directory(os.path.dirname(filepath))
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    except Exception as e:
        logging.error(f"Failed to save JSON file {filepath}: {e}")
        raise


def load_csv_file(filepath: str) -> List[Dict[str, Any]]:
    """
    Load a CSV file into a list of dictionaries.
    
    Args:
        filepath: Path to CSV file
        
    Returns:
        List of row dictionaries
    """
    try:
        with open(filepath, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        logging.warning(f"CSV file not found: {filepath}")
        return []
    except Exception as e:
        logging.error(f"Failed to load CSV file {filepath}: {e}")
        return []


def get_file_size(filepath: str) -> int:
    """
    Get file size in bytes.
    
    Args:
        filepath: Path to file
        
    Returns:
        File size in bytes, 0 if file doesn't exist
    """
    try:
        return os.path.getsize(filepath)
    except OSError:
        return 0


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    
    while size_bytes >= 1024.0 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def get_memory_usage() -> Dict[str, float]:
    """
    Get current memory usage statistics.
    
    Returns:
        Dictionary with memory usage info
    """
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
            'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
            'percent': process.memory_percent()
        }
    except ImportError:
        return {'error': 'psutil not available'}
    except Exception as e:
        return {'error': str(e)}


def profile_execution_time(func):
    """
    Decorator to profile function execution time.
    
    Args:
        func: Function to profile
        
    Returns:
        Wrapped function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        logging.info(f"{func.__name__} executed in {execution_time:.3f} seconds")
        
        return result
    return wrapper

