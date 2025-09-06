"""
Export utilities for review mining data.
Handles CSV export, report generation, and data formatting.
"""

import csv
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from config.settings import EXPORT_CONFIG, DATA_PATHS
from models.review import Review, ReviewBatch
from utils.helpers import ensure_directory, safe_filename, format_timestamp


class CSVExporter:
    """Class for exporting review data to CSV format."""
    
    def __init__(self):
        """Initialize the CSV exporter."""
        self.logger = logging.getLogger("exporter.csv")
        self.encoding = EXPORT_CONFIG.get('csv_encoding', 'utf-8')
        self.max_rows_per_file = EXPORT_CONFIG.get('max_rows_per_file', 10000)
    
    def export_reviews(self, reviews: List[Review], filename: str, 
                      output_dir: Optional[str] = None) -> List[str]:
        """
        Export reviews to CSV file(s).
        
        Args:
            reviews: List of Review objects
            filename: Base filename (without extension)
            output_dir: Output directory (default: exports directory)
            
        Returns:
            List of created file paths
        """
        if not reviews:
            self.logger.warning("No reviews to export")
            return []
        
        if output_dir is None:
            output_dir = DATA_PATHS.get('exports', 'data/exports')
        
        ensure_directory(output_dir)
        
        # Convert reviews to dictionaries
        review_dicts = [review.to_dict() for review in reviews]
        
        # Split into chunks if necessary
        file_chunks = self._split_into_chunks(review_dicts)
        created_files = []
        
        for i, chunk in enumerate(file_chunks):
            if len(file_chunks) > 1:
                chunk_filename = f"{filename}_part_{i+1}.csv"
            else:
                chunk_filename = f"{filename}.csv"
            
            file_path = os.path.join(output_dir, safe_filename(chunk_filename))
            self._write_csv_chunk(chunk, file_path)
            created_files.append(file_path)
        
        self.logger.info(f"Exported {len(reviews)} reviews to {len(created_files)} CSV file(s)")
        return created_files
    
    def export_review_batch(self, review_batch: ReviewBatch, 
                           output_dir: Optional[str] = None) -> List[str]:
        """
        Export a ReviewBatch to CSV file(s).
        
        Args:
            review_batch: ReviewBatch object
            output_dir: Output directory
            
        Returns:
            List of created file paths
        """
        timestamp = format_timestamp(format_str='%Y%m%d_%H%M%S')
        filename = f"{review_batch.app_name}_{review_batch.platform}_{timestamp}"
        
        return self.export_reviews(review_batch.reviews, filename, output_dir)
    
    def export_summary_csv(self, review_batches: List[ReviewBatch], 
                          filename: str = "summary", 
                          output_dir: Optional[str] = None) -> str:
        """
        Export a summary CSV of multiple review batches.
        
        Args:
            review_batches: List of ReviewBatch objects
            filename: Filename for summary
            output_dir: Output directory
            
        Returns:
            Path to created file
        """
        if output_dir is None:
            output_dir = DATA_PATHS.get('exports', 'data/exports')
        
        ensure_directory(output_dir)
        
        timestamp = format_timestamp(format_str='%Y%m%d_%H%M%S')
        file_path = os.path.join(output_dir, f"{filename}_{timestamp}.csv")
        
        # Create summary data
        summary_data = []
        for batch in review_batches:
            stats = batch.get_stats()
            summary_data.append({
                'app_name': stats['app_name'],
                'platform': stats['platform'],
                'total_reviews': stats['total_reviews'],
                'high_quality_reviews': stats['high_quality_reviews'],
                'average_rating': round(stats['average_rating'], 2),
                'average_sentiment_score': round(stats['average_sentiment_score'], 3),
                'positive_sentiment_count': stats['sentiment_distribution'].get('positive', 0),
                'negative_sentiment_count': stats['sentiment_distribution'].get('negative', 0),
                'neutral_sentiment_count': stats['sentiment_distribution'].get('neutral', 0),
                'scraped_at': stats['scraped_at']
            })
        
        self._write_csv_chunk(summary_data, file_path)
        self.logger.info(f"Exported summary CSV to {file_path}")
        
        return file_path
    
    def _split_into_chunks(self, data: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Split data into chunks based on max_rows_per_file."""
        if len(data) <= self.max_rows_per_file:
            return [data]
        
        chunks = []
        for i in range(0, len(data), self.max_rows_per_file):
            chunks.append(data[i:i + self.max_rows_per_file])
        
        return chunks
    
    def _write_csv_chunk(self, data: List[Dict[str, Any]], file_path: str):
        """Write a chunk of data to CSV file."""
        if not data:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding=self.encoding) as csvfile:
                fieldnames = data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for row in data:
                    # Handle nested dictionaries and lists
                    cleaned_row = self._clean_row_for_csv(row)
                    writer.writerow(cleaned_row)
                    
        except Exception as e:
            self.logger.error(f"Error writing CSV file {file_path}: {e}")
            raise
    
    def _clean_row_for_csv(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Clean a row for CSV export by handling complex data types."""
        cleaned = {}
        
        for key, value in row.items():
            if isinstance(value, (dict, list)):
                # Convert complex types to JSON strings
                cleaned[key] = json.dumps(value, default=str)
            elif value is None:
                cleaned[key] = ''
            else:
                cleaned[key] = str(value)
        
        return cleaned


class JSONExporter:
    """Class for exporting review data to JSON format."""
    
    def __init__(self):
        """Initialize the JSON exporter."""
        self.logger = logging.getLogger("exporter.json")
    
    def export_reviews(self, reviews: List[Review], filename: str, 
                      output_dir: Optional[str] = None) -> str:
        """
        Export reviews to JSON file.
        
        Args:
            reviews: List of Review objects
            filename: Filename (without extension)
            output_dir: Output directory
            
        Returns:
            Path to created file
        """
        if output_dir is None:
            output_dir = DATA_PATHS.get('exports', 'data/exports')
        
        ensure_directory(output_dir)
        
        file_path = os.path.join(output_dir, f"{safe_filename(filename)}.json")
        
        # Convert reviews to dictionaries
        review_dicts = [review.to_dict() for review in reviews]
        
        export_data = {
            'metadata': {
                'exported_at': datetime.utcnow().isoformat(),
                'total_reviews': len(reviews),
                'export_type': 'reviews'
            },
            'reviews': review_dicts
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Exported {len(reviews)} reviews to JSON: {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"Error exporting to JSON {file_path}: {e}")
            raise
    
    def export_review_batch(self, review_batch: ReviewBatch, 
                           output_dir: Optional[str] = None) -> str:
        """
        Export a ReviewBatch to JSON file.
        
        Args:
            review_batch: ReviewBatch object
            output_dir: Output directory
            
        Returns:
            Path to created file
        """
        timestamp = format_timestamp(format_str='%Y%m%d_%H%M%S')
        filename = f"{review_batch.app_name}_{review_batch.platform}_{timestamp}"
        
        if output_dir is None:
            output_dir = DATA_PATHS.get('exports', 'data/exports')
        
        ensure_directory(output_dir)
        file_path = os.path.join(output_dir, f"{safe_filename(filename)}.json")
        
        # Use the ReviewBatch's save method
        review_batch.save_to_json(file_path)
        
        self.logger.info(f"Exported ReviewBatch to JSON: {file_path}")
        return file_path


class ReportGenerator:
    """Class for generating comprehensive reports."""
    
    def __init__(self):
        """Initialize the report generator."""
        self.logger = logging.getLogger("exporter.report")
        self.csv_exporter = CSVExporter()
        self.json_exporter = JSONExporter()
    
    def generate_comprehensive_report(self, review_batches: List[ReviewBatch], 
                                    report_name: str = "comprehensive_report",
                                    output_dir: Optional[str] = None) -> Dict[str, str]:
        """
        Generate a comprehensive report with multiple formats.
        
        Args:
            review_batches: List of ReviewBatch objects
            report_name: Base name for report files
            output_dir: Output directory
            
        Returns:
            Dictionary mapping format to file path
        """
        if output_dir is None:
            output_dir = DATA_PATHS.get('exports', 'data/exports')
        
        ensure_directory(output_dir)
        
        timestamp = format_timestamp(format_str='%Y%m%d_%H%M%S')
        base_name = f"{report_name}_{timestamp}"
        
        created_files = {}
        
        # Generate summary report
        summary_file = self._generate_summary_report(review_batches, base_name, output_dir)
        created_files['summary'] = summary_file
        
        # Generate detailed CSV files
        csv_files = self._generate_detailed_csv_reports(review_batches, base_name, output_dir)
        created_files['csv_files'] = csv_files
        
        # Generate analysis report
        analysis_file = self._generate_analysis_report(review_batches, base_name, output_dir)
        created_files['analysis'] = analysis_file
        
        self.logger.info(f"Generated comprehensive report: {len(created_files)} files created")
        return created_files
    
    def _generate_summary_report(self, review_batches: List[ReviewBatch], 
                               base_name: str, output_dir: str) -> str:
        """Generate a summary report in JSON format."""
        summary_data = {
            'report_metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'total_batches': len(review_batches),
                'report_type': 'summary'
            },
            'overall_stats': self._calculate_overall_stats(review_batches),
            'batch_summaries': [batch.get_stats() for batch in review_batches]
        }
        
        file_path = os.path.join(output_dir, f"{base_name}_summary.json")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False, default=str)
        
        return file_path
    
    def _generate_detailed_csv_reports(self, review_batches: List[ReviewBatch], 
                                     base_name: str, output_dir: str) -> List[str]:
        """Generate detailed CSV reports for each batch."""
        csv_files = []
        
        for batch in review_batches:
            batch_name = f"{base_name}_{batch.app_name}_{batch.platform}"
            files = self.csv_exporter.export_reviews(
                batch.get_high_quality_reviews(), 
                batch_name, 
                output_dir
            )
            csv_files.extend(files)
        
        return csv_files
    
    def _generate_analysis_report(self, review_batches: List[ReviewBatch], 
                                base_name: str, output_dir: str) -> str:
        """Generate an analysis report with insights."""
        analysis_data = {
            'report_metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'report_type': 'analysis'
            },
            'insights': self._generate_insights(review_batches),
            'category_analysis': self._analyze_categories(review_batches),
            'sentiment_trends': self._analyze_sentiment_trends(review_batches),
            'quality_metrics': self._analyze_quality_metrics(review_batches)
        }
        
        file_path = os.path.join(output_dir, f"{base_name}_analysis.json")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False, default=str)
        
        return file_path
    
    def _calculate_overall_stats(self, review_batches: List[ReviewBatch]) -> Dict[str, Any]:
        """Calculate overall statistics across all batches."""
        total_reviews = sum(len(batch.reviews) for batch in review_batches)
        total_high_quality = sum(len(batch.get_high_quality_reviews()) for batch in review_batches)
        
        all_ratings = []
        all_sentiment_scores = []
        
        for batch in review_batches:
            for review in batch.reviews:
                if review.rating:
                    all_ratings.append(review.rating)
                all_sentiment_scores.append(review.sentiment_score)
        
        return {
            'total_reviews': total_reviews,
            'total_high_quality_reviews': total_high_quality,
            'total_apps': len(set(batch.app_name for batch in review_batches)),
            'total_platforms': len(set(batch.platform for batch in review_batches)),
            'average_rating': sum(all_ratings) / len(all_ratings) if all_ratings else 0,
            'average_sentiment_score': sum(all_sentiment_scores) / len(all_sentiment_scores) if all_sentiment_scores else 0,
            'quality_rate': total_high_quality / total_reviews if total_reviews > 0 else 0
        }
    
    def _generate_insights(self, review_batches: List[ReviewBatch]) -> List[str]:
        """Generate text insights from the data."""
        insights = []
        
        # Find app with highest average rating
        app_ratings = {}
        for batch in review_batches:
            stats = batch.get_stats()
            if stats['average_rating'] > 0:
                app_ratings[batch.app_name] = stats['average_rating']
        
        if app_ratings:
            best_app = max(app_ratings, key=app_ratings.get)
            insights.append(f"Highest rated app: {best_app} ({app_ratings[best_app]:.1f}/5)")
        
        # Find most discussed categories
        category_counts = {}
        for batch in review_batches:
            for review in batch.reviews:
                if review.primary_category and review.primary_category != 'unclassified':
                    category_counts[review.primary_category] = category_counts.get(review.primary_category, 0) + 1
        
        if category_counts:
            top_category = max(category_counts, key=category_counts.get)
            insights.append(f"Most discussed category: {top_category} ({category_counts[top_category]} reviews)")
        
        return insights
    
    def _analyze_categories(self, review_batches: List[ReviewBatch]) -> Dict[str, Any]:
        """Analyze category distributions."""
        category_data = {}
        
        for batch in review_batches:
            for review in batch.reviews:
                if review.primary_category and review.primary_category != 'unclassified':
                    if review.primary_category not in category_data:
                        category_data[review.primary_category] = {
                            'count': 0,
                            'total_sentiment': 0,
                            'ratings': []
                        }
                    
                    category_data[review.primary_category]['count'] += 1
                    category_data[review.primary_category]['total_sentiment'] += review.sentiment_score
                    
                    if review.rating:
                        category_data[review.primary_category]['ratings'].append(review.rating)
        
        # Calculate averages
        for category, data in category_data.items():
            data['average_sentiment'] = data['total_sentiment'] / data['count']
            data['average_rating'] = sum(data['ratings']) / len(data['ratings']) if data['ratings'] else 0
            del data['total_sentiment']  # Remove intermediate calculation
            del data['ratings']  # Remove raw data
        
        return category_data
    
    def _analyze_sentiment_trends(self, review_batches: List[ReviewBatch]) -> Dict[str, Any]:
        """Analyze sentiment trends across platforms and apps."""
        platform_sentiment = {}
        app_sentiment = {}
        
        for batch in review_batches:
            # Platform sentiment
            if batch.platform not in platform_sentiment:
                platform_sentiment[batch.platform] = []
            
            # App sentiment
            if batch.app_name not in app_sentiment:
                app_sentiment[batch.app_name] = []
            
            for review in batch.reviews:
                platform_sentiment[batch.platform].append(review.sentiment_score)
                app_sentiment[batch.app_name].append(review.sentiment_score)
        
        # Calculate averages
        platform_avg = {p: sum(scores)/len(scores) for p, scores in platform_sentiment.items()}
        app_avg = {a: sum(scores)/len(scores) for a, scores in app_sentiment.items()}
        
        return {
            'platform_sentiment_averages': platform_avg,
            'app_sentiment_averages': app_avg
        }
    
    def _analyze_quality_metrics(self, review_batches: List[ReviewBatch]) -> Dict[str, Any]:
        """Analyze quality metrics across batches."""
        total_reviews = 0
        spam_count = 0
        duplicate_count = 0
        high_quality_count = 0
        
        for batch in review_batches:
            total_reviews += len(batch.reviews)
            for review in batch.reviews:
                if review.is_spam:
                    spam_count += 1
                if review.is_duplicate:
                    duplicate_count += 1
                if review.is_high_quality():
                    high_quality_count += 1
        
        return {
            'total_reviews': total_reviews,
            'spam_count': spam_count,
            'duplicate_count': duplicate_count,
            'high_quality_count': high_quality_count,
            'spam_rate': spam_count / total_reviews if total_reviews > 0 else 0,
            'duplicate_rate': duplicate_count / total_reviews if total_reviews > 0 else 0,
            'quality_rate': high_quality_count / total_reviews if total_reviews > 0 else 0
        }
