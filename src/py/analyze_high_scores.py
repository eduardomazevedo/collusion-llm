#!/usr/bin/env python3
"""
Script to analyze queries above a certain score threshold.

This script demonstrates how to use the analysis functionality to:
1. Find queries from a specific prompt that have scores above a threshold
2. Extract excerpts from those responses
3. Analyze the excerpts using a new analysis prompt
4. Store the analysis results in a separate table

Usage:
    python src/py/analyze_high_scores.py <original_prompt_name> <analysis_prompt_name> [score_threshold]
"""

import sys
import os
import argparse
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import config
from modules.queries_db import analyze_queries_above_threshold, export_analysis_to_csv
from modules.llm import LLMQuery

def main():
    parser = argparse.ArgumentParser(description='Analyze queries above a score threshold')
    parser.add_argument('original_prompt', help='Name of the original prompt used to create entries')
    parser.add_argument('analysis_prompt', help='Name of the analysis prompt to use for analyzing outputs')
    parser.add_argument('--threshold', type=int, default=75, help='Score threshold (default: 75)')
    parser.add_argument('--export', action='store_true', help='Export results to CSV after analysis')
    parser.add_argument('--export-path', help='Custom path for CSV export')
    
    args = parser.parse_args()
    
    print(f"Starting analysis of queries with score >= {args.threshold}")
    print(f"Original prompt: {args.original_prompt}")
    print(f"Analysis prompt: {args.analysis_prompt}")
    print("-" * 50)
    
    # Initialize LLM query instance
    llm_query = LLMQuery()
    
    # Run the analysis
    results = analyze_queries_above_threshold(
        prompt_name=args.original_prompt,
        analysis_prompt_name=args.analysis_prompt,
        score_threshold=args.threshold,
        llm_query_instance=llm_query
    )
    
    print("\n" + "=" * 50)
    print("ANALYSIS SUMMARY")
    print("=" * 50)
    print(f"Total queries processed: {results['processed']}")
    print(f"Queries above threshold ({args.threshold}): {results['above_threshold']}")
    print(f"Successfully analyzed: {results['analyzed']}")
    
    # Export results if requested
    if args.export:
        print("\nExporting results to CSV...")
        export_path = export_analysis_to_csv(
            output_path=args.export_path,
            analysis_prompt_name=args.analysis_prompt,
            include_original=True
        )
        print(f"Results exported to: {export_path}")

if __name__ == "__main__":
    main() 