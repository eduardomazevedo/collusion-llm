#!/usr/bin/env python3
"""
Script to export analysis results to CSV without running analysis again.

Usage:
    python src/py/export_analysis.py [--analysis-prompt NAME] [--output PATH]
"""

import sys
import os
import argparse
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import config
from modules.queries_db import export_analysis_to_csv, fetch_analysis_with_original_data

def main():
    parser = argparse.ArgumentParser(description='Export analysis results to CSV')
    parser.add_argument('--analysis-prompt', help='Analysis prompt name to filter by')
    parser.add_argument('--output', help='Custom output path for CSV file')
    parser.add_argument('--include-original', action='store_true', default=True,
                       help='Include original query data in export (default: True)')
    
    args = parser.parse_args()
    
    print("Exporting analysis results to CSV...")
    
    # Export the results
    export_path = export_analysis_to_csv(
        output_path=args.output,
        analysis_prompt_name=args.analysis_prompt,
        include_original=args.include_original
    )
    
    print(f"Results exported to: {export_path}")
    
    # Show some statistics
    df = fetch_analysis_with_original_data(args.analysis_prompt)
    print(f"\nExport summary:")
    print(f"  Total analysis entries: {len(df)}")
    if args.analysis_prompt:
        print(f"  Analysis prompt: {args.analysis_prompt}")
    else:
        print(f"  Analysis prompts found: {df['analysis_prompt_name'].unique()}")
    
    if 'original_score' in df.columns:
        scores = df['original_score'].dropna()
        if len(scores) > 0:
            print(f"  Score range: {scores.min()} - {scores.max()}")
            print(f"  Average score: {scores.mean():.1f}")

if __name__ == "__main__":
    main() 