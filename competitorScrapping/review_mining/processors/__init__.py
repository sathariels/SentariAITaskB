"""
Processors module for review mining application.
Contains data processing, cleaning, deduplication, and classification functionality.
"""

from .data_cleaner import DataCleaner
from .deduplicator import Deduplicator
from .classifier import ReviewClassifier

__all__ = ['DataCleaner', 'Deduplicator', 'ReviewClassifier']

