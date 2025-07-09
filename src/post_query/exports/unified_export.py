#!/usr/bin/env python3
"""
Unified export script for collusion detection project data.

This script consolidates functionality from multiple export scripts:
- export_queries.py: Export query results from database
- export_analysis.py: Export analysis results from database
- export_companies.py: Export company metadata
- export_token_sizes.py: Export token size calculations
- make_visualizer.py: Create Excel visualization files

Usage:
    python unified_export.py --type queries --format csv
    python unified_export.py --type analysis --include-original
    python unified_export.py --type companies
    python unified_export.py --type tokens --incremental
    python unified_export.py --type visualizer --input high_scores.csv
    python unified_export.py --type all --output-dir exports/
"""

import argparse
import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys
from pathlib import Path
import json
from typing import List, Optional, Dict, Any
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

import config
from modules.queries_db import (
    fetch_all_queries,
    fetch_queries_by_prompts,
    get_latest_queries,
    fetch_analysis_results,
    fetch_analysis_with_original_data
)
from modules import capiq
from modules.utils import transcript_token_size

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class UnifiedExporter:
    """Handles all export operations for the project."""
    
    def __init__(self, output_dir: str = None):
        """Initialize exporter with output directory."""
        self.output_dir = output_dir or os.path.join(config.OUTPUT_DIR, 'exports')
        os.makedirs(self.output_dir, exist_ok=True)
        
    def generate_filename(self, base_name: str, format: str = 'csv') -> str:
        """Generate filename with timestamp."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return os.path.join(self.output_dir, f"{base_name}_{timestamp}.{format}")
    
    def export_queries(self, output_path: str = None, prompts: List[str] = None, 
                      latest_only: bool = False, format: str = 'csv') -> str:
        """
        Export query results from database.
        
        Args:
            output_path: Custom output path
            prompts: List of prompt names to filter by
            latest_only: Only export latest query per transcript
            format: Output format (csv or excel)
            
        Returns:
            Path to exported file
        """
        logging.info("Exporting query results...")
        
        # Get data from database
        df = fetch_all_queries()
        
        # Filter by prompts if specified
        if prompts:
            df = df[df['prompt_name'].isin(prompts)]
            logging.info(f"Filtered to {len(df)} results for prompts: {prompts}")
        
        # Keep only latest per transcript if requested
        if latest_only:
            df = df.sort_values('created_at').groupby(['transcriptid', 'prompt_name']).last().reset_index()
            logging.info(f"Kept latest queries only: {len(df)} results")
        
        # Set output path
        if not output_path:
            base_name = f"queries_{'_'.join(prompts) if prompts else 'all'}"
            output_path = self.generate_filename(base_name, format)
        
        # Export based on format
        if format == 'excel':
            df.to_excel(output_path, index=False, sheet_name='Queries')
        else:
            df.to_csv(output_path, index=False)
        
        logging.info(f"Exported {len(df)} query results to {output_path}")
        return output_path
    
    def export_analysis(self, output_path: str = None, analysis_prompt: str = None,
                       include_original: bool = True, format: str = 'csv') -> str:
        """
        Export analysis query results.
        
        Args:
            output_path: Custom output path
            analysis_prompt: Filter by analysis prompt name
            include_original: Include original query data
            format: Output format
            
        Returns:
            Path to exported file
        """
        logging.info("Exporting analysis results...")
        
        # Get data based on whether to include original
        if include_original:
            df = fetch_analysis_with_original_data()
        else:
            df = fetch_analysis_results()
        
        # Filter by analysis prompt if specified
        if analysis_prompt:
            if include_original:
                df = df[df['analysis_prompt_name'] == analysis_prompt]
            else:
                df = df[df['prompt_name'] == analysis_prompt]
            logging.info(f"Filtered to {len(df)} results for prompt: {analysis_prompt}")
        
        # Set output path
        if not output_path:
            base_name = f"analysis_{analysis_prompt if analysis_prompt else 'all'}"
            output_path = self.generate_filename(base_name, format)
        
        # Export based on format
        if format == 'excel':
            df.to_excel(output_path, index=False, sheet_name='Analysis')
        else:
            df.to_csv(output_path, index=False)
        
        logging.info(f"Exported {len(df)} analysis results to {output_path}")
        return output_path
    
    def export_companies(self, output_path: str = None) -> str:
        """
        Export company and transcript metadata.
        
        Args:
            output_path: Custom output path
            
        Returns:
            Path to exported file
        """
        logging.info("Exporting company metadata...")
        
        # Read transcript details
        transcript_detail_path = os.path.join(config.DATA_DIR, 'datasets', 'transcript_detail.feather')
        df = pd.read_feather(transcript_detail_path)
        
        # Select and rename columns
        df = df[['companyid', 'companyname', 'transcriptid', 'headline']]
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['transcriptid'])
        
        # Count unique companies
        unique_companies = df['companyid'].nunique()
        logging.info(f"Found {unique_companies} unique companies with {len(df)} transcripts")
        
        # Set output path
        if not output_path:
            output_path = os.path.join(config.DATA_DIR, 'datasets', 'companies_transcripts.csv')
        
        # Save without header
        df.to_csv(output_path, index=False, header=False)
        
        logging.info(f"Exported company metadata to {output_path}")
        return output_path
    
    def export_token_sizes(self, output_path: str = None, incremental: bool = True) -> str:
        """
        Export token sizes for all transcripts.
        
        Args:
            output_path: Custom output path
            incremental: Skip already processed transcripts
            
        Returns:
            Path to exported file
        """
        logging.info("Calculating and exporting token sizes...")
        
        # Set output path
        if not output_path:
            output_path = os.path.join(config.DATA_DIR, 'intermediaries', 'transcript_tokens.csv')
        
        # Load existing data if incremental
        existing_data = {}
        if incremental and os.path.exists(output_path):
            try:
                existing_df = pd.read_csv(output_path)
                existing_data = dict(zip(existing_df['transcriptid'], existing_df['token_count']))
                logging.info(f"Loaded {len(existing_data)} existing token calculations")
            except Exception as e:
                logging.warning(f"Could not load existing data: {e}")
        
        # Get all transcript IDs
        transcript_detail_path = os.path.join(config.DATA_DIR, 'datasets', 'transcript_detail.feather')
        df = pd.read_feather(transcript_detail_path)
        all_transcript_ids = df['transcriptid'].unique()
        
        # Filter to unprocessed if incremental
        if incremental:
            transcript_ids = [tid for tid in all_transcript_ids if tid not in existing_data]
            logging.info(f"Processing {len(transcript_ids)} new transcripts")
        else:
            transcript_ids = all_transcript_ids
        
        # Process transcripts
        results = []
        failed_count = 0
        
        for i, transcriptid in enumerate(transcript_ids):
            if i % 100 == 0 and i > 0:
                logging.info(f"Processed {i}/{len(transcript_ids)} transcripts")
                # Save intermediate results
                if incremental:
                    self._save_token_results(results, existing_data, output_path)
                    results = []
            
            try:
                # Get token size for transcript
                token_size = transcript_token_size(transcriptid)
                
                if token_size is not None:
                    results.append({
                        'transcriptid': transcriptid,
                        'token_count': token_size
                    })
                else:
                    failed_count += 1
                    
            except Exception as e:
                logging.warning(f"Failed to process transcript {transcriptid}: {e}")
                failed_count += 1
        
        # Save final results
        if results or not incremental:
            self._save_token_results(results, existing_data if incremental else {}, output_path)
        
        logging.info(f"Completed token calculation. Failed: {failed_count}")
        return output_path
    
    def _save_token_results(self, new_results: List[Dict], existing_data: Dict, output_path: str):
        """Helper to save token calculation results."""
        # Combine with existing data
        all_data = existing_data.copy()
        for result in new_results:
            all_data[result['transcriptid']] = result['token_count']
        
        # Convert to dataframe and save
        df = pd.DataFrame([
            {'transcriptid': tid, 'token_count': size}
            for tid, size in all_data.items()
        ])
        df.sort_values('transcriptid', inplace=True)
        df.to_csv(output_path, index=False)
    
    def create_visualizer(self, input_path: str = None, output_path: str = None) -> str:
        """
        Create Excel visualization file with full transcript content.
        
        Args:
            input_path: Path to high scores CSV
            output_path: Custom output path
            
        Returns:
            Path to exported file
        """
        logging.info("Creating visualization Excel file...")
        
        # Set paths
        if not input_path:
            input_path = os.path.join(config.DATA_DIR, 'outputs', 'analysis', 'high_scores.csv')
        if not output_path:
            output_path = os.path.join(config.DATA_DIR, 'outputs', 'analysis', 'high_scores_transcripts.xlsx')
        
        # Read high scores
        df = pd.read_csv(input_path)
        logging.info(f"Processing {len(df)} high-scoring transcripts")
        
        # Get unique transcript IDs
        transcript_ids = df['transcriptid'].unique().tolist()
        
        # Fetch transcripts in batches
        batch_size = 50
        all_transcripts = {}
        
        for i in range(0, len(transcript_ids), batch_size):
            batch_ids = transcript_ids[i:i+batch_size]
            logging.info(f"Fetching batch {i//batch_size + 1}/{(len(transcript_ids)-1)//batch_size + 1}")
            
            try:
                batch_transcripts = capiq.get_transcripts(batch_ids)
                all_transcripts.update(batch_transcripts)
            except Exception as e:
                logging.error(f"Failed to fetch batch: {e}")
        
        # Add transcript content to dataframe
        df['full_transcript'] = df['transcriptid'].map(lambda x: json.dumps(all_transcripts.get(x, {})))
        
        # Load company metadata
        companies_path = os.path.join(config.DATA_DIR, 'datasets', 'companies_transcripts.csv')
        companies_df = pd.read_csv(companies_path, names=['companyid', 'companyname', 'transcriptid', 'headline'])
        
        # Merge with company data
        df = df.merge(
            companies_df[['companyname', 'transcriptid', 'headline']],
            left_on='transcriptid',
            right_on='transcriptid',
            how='left'
        )
        
        # Reorder columns
        column_order = ['transcriptid', 'companyname', 'headline', 'score', 'reasoning', 'excerpts', 'full_transcript']
        df = df[[col for col in column_order if col in df.columns]]
        
        # Save to Excel
        df.to_excel(output_path, index=False, sheet_name='High Scores')
        
        logging.info(f"Created visualization file: {output_path}")
        return output_path
    
    def export_all(self, include_tokens: bool = False, include_visualizer: bool = False) -> Dict[str, str]:
        """
        Export all data types.
        
        Args:
            include_tokens: Include token size calculation (slow)
            include_visualizer: Include visualization file creation
            
        Returns:
            Dictionary mapping export type to file path
        """
        results = {}
        
        # Export queries
        results['queries'] = self.export_queries()
        
        # Export analysis
        results['analysis'] = self.export_analysis()
        
        # Export companies
        results['companies'] = self.export_companies()
        
        # Export token sizes if requested
        if include_tokens:
            results['tokens'] = self.export_token_sizes()
        
        # Create visualizer if requested
        if include_visualizer:
            results['visualizer'] = self.create_visualizer()
        
        return results


def main():
    """Main entry point for unified export script."""
    parser = argparse.ArgumentParser(
        description='Unified export script for collusion detection project',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--type',
        choices=['queries', 'analysis', 'companies', 'tokens', 'visualizer', 'all'],
        required=True,
        help='Type of data to export'
    )
    
    parser.add_argument(
        '--format',
        choices=['csv', 'excel'],
        default='csv',
        help='Output format (default: csv)'
    )
    
    parser.add_argument(
        '--output',
        help='Custom output path'
    )
    
    parser.add_argument(
        '--output-dir',
        help='Output directory for exports'
    )
    
    # Query-specific options
    parser.add_argument(
        '--prompts',
        nargs='+',
        help='Filter by prompt names (for queries export)'
    )
    
    parser.add_argument(
        '--latest-only',
        action='store_true',
        help='Only export latest query per transcript (for queries export)'
    )
    
    # Analysis-specific options
    parser.add_argument(
        '--analysis-prompt',
        help='Filter by analysis prompt name'
    )
    
    parser.add_argument(
        '--include-original',
        action='store_true',
        default=True,
        help='Include original query data with analysis (default: True)'
    )
    
    # Token-specific options
    parser.add_argument(
        '--incremental',
        action='store_true',
        default=True,
        help='Skip already processed transcripts for token calculation (default: True)'
    )
    
    # Visualizer-specific options
    parser.add_argument(
        '--input',
        help='Input file for visualizer (default: high_scores.csv)'
    )
    
    # All export options
    parser.add_argument(
        '--include-tokens',
        action='store_true',
        help='Include token calculation when exporting all (slow)'
    )
    
    parser.add_argument(
        '--include-visualizer',
        action='store_true',
        help='Include visualizer creation when exporting all'
    )
    
    args = parser.parse_args()
    
    # Initialize exporter
    exporter = UnifiedExporter(output_dir=args.output_dir)
    
    try:
        # Handle different export types
        if args.type == 'queries':
            output_path = exporter.export_queries(
                output_path=args.output,
                prompts=args.prompts,
                latest_only=args.latest_only,
                format=args.format
            )
            print(f"Exported queries to: {output_path}")
            
        elif args.type == 'analysis':
            output_path = exporter.export_analysis(
                output_path=args.output,
                analysis_prompt=args.analysis_prompt,
                include_original=args.include_original,
                format=args.format
            )
            print(f"Exported analysis to: {output_path}")
            
        elif args.type == 'companies':
            output_path = exporter.export_companies(output_path=args.output)
            print(f"Exported companies to: {output_path}")
            
        elif args.type == 'tokens':
            output_path = exporter.export_token_sizes(
                output_path=args.output,
                incremental=args.incremental
            )
            print(f"Exported token sizes to: {output_path}")
            
        elif args.type == 'visualizer':
            output_path = exporter.create_visualizer(
                input_path=args.input,
                output_path=args.output
            )
            print(f"Created visualizer at: {output_path}")
            
        elif args.type == 'all':
            results = exporter.export_all(
                include_tokens=args.include_tokens,
                include_visualizer=args.include_visualizer
            )
            print("\nExported all data:")
            for export_type, path in results.items():
                print(f"  {export_type}: {path}")
        
        return 0
        
    except Exception as e:
        logging.error(f"Export failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())