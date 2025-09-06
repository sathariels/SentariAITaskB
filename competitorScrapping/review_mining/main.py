#!/usr/bin/env python3
"""
Main orchestration script for the review mining application.
Coordinates scraping, processing, and exporting of app reviews.
"""

import argparse
import sys
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import LOGGING_CONFIG, DATA_PATHS
from config.apps import TARGET_APPS, get_app_config
from scrapers import RedditScraper
from processors import DataCleaner, Deduplicator, ReviewClassifier
from models.review import Review, ReviewBatch
from utils.helpers import setup_logging, ensure_directory, profile_execution_time
from utils.export import CSVExporter, JSONExporter, ReportGenerator


class ReviewMiner:
    """Main orchestrator for review mining operations."""
    
    def __init__(self, log_level: str = 'INFO'):
        """
        Initialize the review miner.
        
        Args:
            log_level: Logging level
        """
        # Setup logging
        log_file = LOGGING_CONFIG.get('file', 'logs/review_mining.log')
        ensure_directory('logs')
        self.logger = setup_logging(log_level, log_file)
        
        # Initialize components
        self.scrapers = {
            'reddit': RedditScraper()
        }
        
        self.processors = {
            'cleaner': DataCleaner(),
            'deduplicator': Deduplicator(),
            'classifier': ReviewClassifier()
        }
        
        self.exporters = {
            'csv': CSVExporter(),
            'json': JSONExporter(),
            'report': ReportGenerator()
        }
        
        # Ensure data directories exist
        for path in DATA_PATHS.values():
            ensure_directory(path)
        
        self.logger.info("Review mining system initialized")
    
    @profile_execution_time
    def scrape_app_reviews(self, app_name: str, platforms: List[str], 
                          limit_per_platform: int = 100) -> List[ReviewBatch]:
        """
        Scrape reviews for a specific app across platforms.
        
        Args:
            app_name: Name of the app to scrape
            platforms: List of platforms to scrape from
            limit_per_platform: Maximum reviews per platform
            
        Returns:
            List of ReviewBatch objects
        """
        self.logger.info(f"Starting review scraping for {app_name} on platforms: {platforms}")
        
        app_config = get_app_config(app_name)
        if not app_config:
            self.logger.error(f"No configuration found for app: {app_name}")
            return []
        
        review_batches = []
        
        for platform in platforms:
            if platform not in self.scrapers:
                self.logger.warning(f"Scraper not available for platform: {platform}")
                continue
            
            try:
                scraper = self.scrapers[platform]
                
                # Validate configuration for this scraper
                if not scraper.validate_config(app_config):
                    self.logger.warning(f"Invalid config for {app_name} on {platform}")
                    continue
                
                self.logger.info(f"Scraping {app_name} reviews from {platform}")
                
                # Scrape reviews
                review_dicts = scraper.scrape_reviews(app_config, limit_per_platform)
                
                if not review_dicts:
                    self.logger.warning(f"No reviews found for {app_name} on {platform}")
                    continue
                
                # Convert to Review objects
                reviews = []
                for review_dict in review_dicts:
                    try:
                        review = Review.from_dict(review_dict)
                        reviews.append(review)
                    except Exception as e:
                        self.logger.error(f"Error creating Review object: {e}")
                        continue
                
                # Create ReviewBatch
                batch = ReviewBatch(
                    reviews=reviews,
                    app_name=app_name,
                    platform=platform
                )
                
                review_batches.append(batch)
                self.logger.info(f"Scraped {len(reviews)} reviews from {platform}")
                
            except Exception as e:
                self.logger.error(f"Error scraping {platform} for {app_name}: {e}")
                continue
        
        self.logger.info(f"Completed scraping for {app_name}: {len(review_batches)} batches created")
        return review_batches
    
    @profile_execution_time
    def process_review_batches(self, review_batches: List[ReviewBatch]) -> List[ReviewBatch]:
        """
        Process review batches through cleaning, deduplication, and classification.
        
        Args:
            review_batches: List of ReviewBatch objects
            
        Returns:
            List of processed ReviewBatch objects
        """
        self.logger.info(f"Starting processing of {len(review_batches)} review batches")
        
        processed_batches = []
        
        for batch in review_batches:
            try:
                self.logger.info(f"Processing batch: {batch.app_name} - {batch.platform}")
                
                # Convert Review objects to dictionaries for processing
                review_dicts = [review.to_dict() for review in batch.reviews]
                
                # Step 1: Clean reviews
                self.logger.info("Cleaning reviews...")
                cleaned_dicts = self.processors['cleaner'].clean_reviews(review_dicts)
                
                # Step 2: Deduplicate reviews
                self.logger.info("Deduplicating reviews...")
                deduplicated_dicts = self.processors['deduplicator'].deduplicate_reviews(cleaned_dicts)
                
                # Step 3: Classify reviews
                self.logger.info("Classifying reviews...")
                classified_dicts = self.processors['classifier'].classify_reviews(deduplicated_dicts)
                
                # Convert back to Review objects and update
                processed_reviews = []
                for review_dict in classified_dicts:
                    try:
                        review = Review.from_dict(review_dict)
                        processed_reviews.append(review)
                    except Exception as e:
                        self.logger.error(f"Error creating processed Review object: {e}")
                        continue
                
                # Create processed batch
                processed_batch = ReviewBatch(
                    reviews=processed_reviews,
                    app_name=batch.app_name,
                    platform=batch.platform,
                    scraped_at=batch.scraped_at,
                    total_scraped=batch.total_scraped
                )
                
                processed_batch.total_processed = len(processed_reviews)
                processed_batch.processing_stats = {
                    'original_count': len(review_dicts),
                    'cleaned_count': len(cleaned_dicts),
                    'deduplicated_count': len(deduplicated_dicts),
                    'classified_count': len(classified_dicts),
                    'final_count': len(processed_reviews)
                }
                
                processed_batches.append(processed_batch)
                
                self.logger.info(f"Processed batch: {len(processed_reviews)} final reviews from {len(review_dicts)} original")
                
            except Exception as e:
                self.logger.error(f"Error processing batch {batch.app_name}-{batch.platform}: {e}")
                continue
        
        self.logger.info(f"Completed processing: {len(processed_batches)} batches processed")
        return processed_batches
    
    @profile_execution_time
    def export_results(self, review_batches: List[ReviewBatch], 
                      formats: List[str] = None, output_dir: str = None) -> Dict[str, List[str]]:
        """
        Export processed review batches in specified formats.
        
        Args:
            review_batches: List of processed ReviewBatch objects
            formats: List of export formats ('csv', 'json', 'report')
            output_dir: Output directory (defaults to configured exports directory)
            
        Returns:
            Dictionary mapping format to list of created files
        """
        if formats is None:
            formats = ['csv', 'json']
        
        if output_dir is None:
            output_dir = DATA_PATHS.get('exports', 'data/exports')
        
        self.logger.info(f"Exporting results in formats: {formats}")
        
        exported_files = {}
        
        try:
            # Export individual batches
            for format_name in formats:
                if format_name == 'csv':
                    csv_files = []
                    for batch in review_batches:
                        files = self.exporters['csv'].export_review_batch(batch, output_dir)
                        csv_files.extend(files)
                    exported_files['csv'] = csv_files
                
                elif format_name == 'json':
                    json_files = []
                    for batch in review_batches:
                        file_path = self.exporters['json'].export_review_batch(batch, output_dir)
                        json_files.append(file_path)
                    exported_files['json'] = json_files
                
                elif format_name == 'report':
                    report_files = self.exporters['report'].generate_comprehensive_report(
                        review_batches, output_dir=output_dir
                    )
                    exported_files['report'] = list(report_files.values())
            
            self.logger.info(f"Export completed: {sum(len(files) for files in exported_files.values())} files created")
            
        except Exception as e:
            self.logger.error(f"Error during export: {e}")
        
        return exported_files
    
    def run_full_pipeline(self, app_name: str, platforms: List[str], 
                         limit_per_platform: int = 100, 
                         export_formats: List[str] = None) -> Dict[str, Any]:
        """
        Run the complete review mining pipeline.
        
        Args:
            app_name: Name of the app to mine reviews for
            platforms: List of platforms to scrape
            limit_per_platform: Maximum reviews per platform
            export_formats: List of export formats
            
        Returns:
            Dictionary with pipeline results
        """
        if export_formats is None:
            export_formats = ['csv', 'json', 'report']
        
        self.logger.info(f"Starting full pipeline for {app_name}")
        start_time = datetime.now()
        
        try:
            # Step 1: Scrape reviews
            review_batches = self.scrape_app_reviews(app_name, platforms, limit_per_platform)
            
            if not review_batches:
                self.logger.error("No reviews scraped, aborting pipeline")
                return {'success': False, 'error': 'No reviews scraped'}
            
            # Step 2: Process reviews
            processed_batches = self.process_review_batches(review_batches)
            
            if not processed_batches:
                self.logger.error("No reviews processed, aborting pipeline")
                return {'success': False, 'error': 'No reviews processed'}
            
            # Step 3: Export results
            exported_files = self.export_results(processed_batches, export_formats)
            
            # Calculate summary statistics
            total_original = sum(batch.total_scraped for batch in processed_batches)
            total_processed = sum(batch.total_processed for batch in processed_batches)
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            results = {
                'success': True,
                'app_name': app_name,
                'platforms': platforms,
                'execution_time_seconds': execution_time,
                'total_reviews_scraped': total_original,
                'total_reviews_processed': total_processed,
                'processing_rate': total_processed / total_original if total_original > 0 else 0,
                'batches_created': len(processed_batches),
                'exported_files': exported_files,
                'batch_summaries': [batch.get_stats() for batch in processed_batches]
            }
            
            self.logger.info(f"Pipeline completed successfully: {total_processed}/{total_original} reviews processed in {execution_time:.2f}s")
            return results
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            return {'success': False, 'error': str(e)}


def main():
    """Main function with CLI interface."""
    parser = argparse.ArgumentParser(description='Review Mining Application')
    
    parser.add_argument('app_name', nargs='?', help='Name of the app to mine reviews for')
    parser.add_argument('--platforms', nargs='+', default=['reddit'],
                       help='Platforms to scrape from (default: reddit)')
    parser.add_argument('--limit', type=int, default=100,
                       help='Maximum reviews per platform (default: 100)')
    parser.add_argument('--formats', nargs='+', default=['csv', 'json', 'report'],
                       help='Export formats (default: csv json report)')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    parser.add_argument('--list-apps', action='store_true',
                       help='List available apps and exit')
    
    args = parser.parse_args()
    
    # List available apps
    if args.list_apps:
        print("Available apps:")
        for category, apps in TARGET_APPS.items():
            print(f"\n{category.title()}:")
            for app_name, config in apps.items():
                print(f"  - {app_name}: {config['name']}")
        return 0
    
    # Initialize review miner
    try:
        miner = ReviewMiner(log_level=args.log_level)
    except Exception as e:
        print(f"Failed to initialize review miner: {e}")
        return 1
    
    # Run pipeline
    try:
        results = miner.run_full_pipeline(
            app_name=args.app_name,
            platforms=args.platforms,
            limit_per_platform=args.limit,
            export_formats=args.formats
        )
        
        if results['success']:
            print(f"\n✅ Pipeline completed successfully!")
            print(f"App: {results['app_name']}")
            print(f"Reviews processed: {results['total_reviews_processed']}/{results['total_reviews_scraped']}")
            print(f"Execution time: {results['execution_time_seconds']:.2f} seconds")
            print(f"Files created: {sum(len(files) for files in results['exported_files'].values())}")
            return 0
        else:
            print(f"\n❌ Pipeline failed: {results['error']}")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Pipeline interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
