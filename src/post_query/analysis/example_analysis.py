#!/usr/bin/env python3
"""
Example script demonstrating how to use the analysis functionality.

This script shows how to:
1. Analyze queries above a threshold
2. Export results
3. View analysis statistics
"""

import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import config
from modules.queries_db import (
    analyze_queries_above_threshold, 
    export_analysis_to_csv,
    fetch_analysis_with_original_data,
    fetch_queries_by_prompts
)
from modules.llm import LLMQuery

def example_analysis():
    """Example of analyzing high-scoring queries."""
    
    # Configuration
    original_prompt = "SimpleCapacityV8.1.1"  # Replace with your actual prompt name
    analysis_prompt = "SmallExcerptAnalyzer"   # Replace with your analysis prompt name
    score_threshold = 75
    
    print("=== EXAMPLE: Analyzing High-Scoring Queries ===")
    print(f"Original prompt: {original_prompt}")
    print(f"Analysis prompt: {analysis_prompt}")
    print(f"Score threshold: {score_threshold}")
    print()
    
    # Check if we have any queries for the original prompt
    df = fetch_queries_by_prompts([original_prompt])
    if df.empty:
        print(f"No queries found for prompt '{original_prompt}'")
        print("Please run some queries with this prompt first.")
        return
    
    print(f"Found {len(df)} queries for prompt '{original_prompt}'")
    
    # Initialize LLM query instance
    llm_query = LLMQuery()
    
    # Run the analysis
    print("\nStarting analysis...")
    results = analyze_queries_above_threshold(
        prompt_name=original_prompt,
        analysis_prompt_name=analysis_prompt,
        score_threshold=score_threshold,
        llm_query_instance=llm_query
    )
    
    # Print results
    print("\n=== ANALYSIS RESULTS ===")
    print(f"Total queries processed: {results['processed']}")
    print(f"Queries above threshold: {results['above_threshold']}")
    print(f"Successfully analyzed: {results['analyzed']}")
    
    # Export results
    if results['analyzed'] > 0:
        print("\nExporting results to CSV...")
        export_path = export_analysis_to_csv(
            analysis_prompt_name=analysis_prompt,
            include_original=True
        )
        print(f"Results exported to: {export_path}")
        
        # Show some statistics
        analysis_df = fetch_analysis_with_original_data(analysis_prompt)
        print(f"\nAnalysis table now contains {len(analysis_df)} entries")
        
        # Show score distribution
        if 'original_score' in analysis_df.columns:
            scores = analysis_df['original_score'].dropna()
            if len(scores) > 0:
                print(f"Score range: {scores.min()} - {scores.max()}")
                print(f"Average score: {scores.mean():.1f}")
                print(f"Median score: {scores.median():.1f}")

def view_analysis_results(analysis_prompt_name=None):
    """View existing analysis results."""
    
    print("=== VIEWING ANALYSIS RESULTS ===")
    
    # Fetch analysis results
    df = fetch_analysis_with_original_data(analysis_prompt_name)
    
    if df.empty:
        print("No analysis results found.")
        if analysis_prompt_name:
            print(f"No results for analysis prompt: {analysis_prompt_name}")
        return
    
    print(f"Found {len(df)} analysis results")
    
    # Show summary
    print(f"\nAnalysis prompts used: {df['analysis_prompt_name'].unique()}")
    print(f"Original prompts analyzed: {df['original_prompt_name'].unique()}")
    
    # Show score distribution if available
    if 'original_score' in df.columns:
        scores = df['original_score'].dropna()
        if len(scores) > 0:
            print(f"\nScore distribution:")
            print(f"  Range: {scores.min()} - {scores.max()}")
            print(f"  Mean: {scores.mean():.1f}")
            print(f"  Median: {scores.median():.1f}")
            print(f"  Count: {len(scores)}")
    
    # Show recent entries
    print(f"\nMost recent analysis entries:")
    recent = df.sort_values('analysis_date', ascending=False).head(3)
    for _, row in recent.iterrows():
        print(f"  {row['analysis_date']}: {row['original_prompt_name']} -> {row['analysis_prompt_name']} (score: {row.get('original_score', 'N/A')})")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Example analysis functionality')
    parser.add_argument('--action', choices=['analyze', 'view'], default='analyze',
                       help='Action to perform (default: analyze)')
    parser.add_argument('--analysis-prompt', help='Analysis prompt name for viewing results')
    
    args = parser.parse_args()
    
    if args.action == 'analyze':
        example_analysis()
    elif args.action == 'view':
        view_analysis_results(args.analysis_prompt) 