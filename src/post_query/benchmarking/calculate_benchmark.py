#!/usr/bin/env python3
"""
Calculate comprehensive metrics for different LLM approaches against human-reviewed samples.

This script computes precision, recall, F1 scores, and specificity for:
- Non-interactive approaches: single response, average of all responses
- Agentic approaches: repeated high-scoring responses, follow-up analysis

Metrics are calculated for Joe's subsample, ACL's subsample, and pooled sample.
"""

import pandas as pd
import numpy as np
import sqlite3
import json
import argparse
from typing import Dict, List, Tuple, Optional
import config
import os
from modules.utils import extract_score_from_unstructured_response


def calculate_comprehensive_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Calculate comprehensive metrics for binary classification.
    
    Args:
        y_true: True binary labels
        y_pred: Predicted binary labels
        
    Returns:
        Dictionary with metrics: n, precision, recall, f1, specificity, tp, fp, tn, fn
    """
    # Calculate confusion matrix values
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    
    # Sample size
    n = len(y_true)
    
    # Calculate metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    
    # Calculate F1 score
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * (precision * recall) / (precision + recall)
    
    return {
        'n': n,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'specificity': specificity,
        'tp': tp,
        'fp': fp,
        'tn': tn,
        'fn': fn
    }


def load_human_ratings() -> pd.DataFrame:
    """Load human ratings from CSV file."""
    df = pd.read_csv(config.HUMAN_RATINGS_PATH)
    return df


def extract_score_from_response(response_str: str) -> Optional[float]:
    """Extract score from response string, with fallback for unstructured responses."""
    try:
        # First try to parse as JSON
        response_dict = json.loads(response_str)
        if isinstance(response_dict, dict):
            score = response_dict.get('score', None)
            if score is not None:
                return float(score)
        return None
    except (json.JSONDecodeError, ValueError):
        # If JSON parsing fails, use the robust parser from utils
        score = extract_score_from_unstructured_response(response_str)
        return float(score) if score is not None else None


def get_all_llm_responses() -> pd.DataFrame:
    """Load all LLM responses from the queries table."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    query = """
    SELECT 
        query_id,
        prompt_name,
        transcriptid,
        response,
        date,
        model_name,
        LLM_provider
    FROM queries
    ORDER BY date ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Extract scores from responses
    df['score'] = df['response'].apply(extract_score_from_response)
    
    # Remove responses without valid scores
    df = df[df['score'].notna()]
    
    return df


def get_analysis_responses() -> pd.DataFrame:
    """Load analysis responses from the analysis_queries table."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    query = """
    SELECT 
        aq.analysis_query_id,
        aq.reference_query_id,
        aq.prompt_name as analysis_prompt_name,
        aq.response as analysis_response,
        aq.date as analysis_date,
        q.prompt_name as original_prompt_name,
        q.transcriptid,
        q.model_name,
        q.response as original_response
    FROM analysis_queries aq
    JOIN queries q ON aq.reference_query_id = q.query_id
    ORDER BY aq.date ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Extract scores from analysis responses
    df['analysis_score'] = df['analysis_response'].apply(extract_score_from_response)
    
    # Extract scores from original responses
    df['original_score'] = df['original_response'].apply(extract_score_from_response)
    
    # Remove responses without valid analysis scores
    df = df[df['analysis_score'].notna()]
    
    return df


def convert_to_binary(scores: pd.Series, threshold) -> pd.Series:
    """Convert continuous scores to binary using threshold."""
    return (scores >= threshold).astype(int)


def calculate_metrics_for_subsample(
    llm_scores: pd.Series, 
    human_labels: pd.Series,
    threshold: float = config.LLM_SCORE_THRESHOLD
) -> Dict[str, float]:
    """Calculate comprehensive metrics for a subsample."""
    # Convert LLM scores to binary
    llm_binary = convert_to_binary(llm_scores, threshold)
    
    # Calculate comprehensive metrics
    return calculate_comprehensive_metrics(human_labels.values, llm_binary.values)


def get_empty_metrics() -> Dict[str, float]:
    """Return empty metrics dictionary."""
    return {
        'joe_n': 0, 'joe_precision': np.nan, 'joe_recall': np.nan, 'joe_f1': np.nan, 'joe_specificity': np.nan,
        'acl_n': 0, 'acl_precision': np.nan, 'acl_recall': np.nan, 'acl_f1': np.nan, 'acl_specificity': np.nan,
        'pooled_n': 0, 'pooled_precision': np.nan, 'pooled_recall': np.nan, 'pooled_f1': np.nan, 'pooled_specificity': np.nan
    }


def process_non_interactive_single(
    llm_responses: pd.DataFrame,
    human_ratings: pd.DataFrame,
    prompt_name: str,
    model_name: str,
    threshold: float = config.LLM_SCORE_THRESHOLD,
    joe_threshold: float = config.JOE_SCORE_THRESHOLD
) -> Dict[str, float]:
    """
    Process non-interactive single response approach.
    Takes the earliest response for each prompt-model-transcript combination.
    """
    # Filter for specific prompt and model
    df = llm_responses[
        (llm_responses['prompt_name'] == prompt_name) & 
        (llm_responses['model_name'] == model_name)
    ].copy()
    
    empty_metrics = get_empty_metrics()
    
    if len(df) == 0:
        return empty_metrics
    
    # Keep only the earliest response per transcript
    df = df.sort_values('date').groupby('transcriptid').first().reset_index()
    
    # Merge with human ratings
    merged = pd.merge(df, human_ratings, on='transcriptid', how='inner')
    
    results = {}
    
    # Joe's subsample
    joe_data = merged[merged['joe_score'].notna()]
    if len(joe_data) > 0:
        joe_binary = convert_to_binary(joe_data['joe_score'], joe_threshold)
        joe_metrics = calculate_metrics_for_subsample(joe_data['score'], joe_binary, threshold)
        results.update({f'joe_{k}': v for k, v in joe_metrics.items()})
    else:
        results.update({k: v for k, v in empty_metrics.items() if k.startswith('joe_')})
    
    # ACL's subsample
    acl_data = merged[merged['acl_manual_flag'].notna()]
    if len(acl_data) > 0:
        acl_metrics = calculate_metrics_for_subsample(
            acl_data['score'], 
            acl_data['acl_manual_flag'], 
            threshold
        )
        results.update({f'acl_{k}': v for k, v in acl_metrics.items()})
    else:
        results.update({k: v for k, v in empty_metrics.items() if k.startswith('acl_')})
    
    # Pooled sample
    pooled_data = merged[(merged['joe_score'].notna()) | (merged['acl_manual_flag'].notna())]
    if len(pooled_data) > 0:
        # Create unified labels
        pooled_labels = []
        pooled_scores = []
        
        for _, row in pooled_data.iterrows():
            # Use ACL label if available, otherwise convert Joe's score
            if pd.notna(row['acl_manual_flag']):
                pooled_labels.append(int(row['acl_manual_flag']))
            else:
                pooled_labels.append(int(row['joe_score'] >= joe_threshold))
            pooled_scores.append(row['score'])
        
        pooled_binary_pred = convert_to_binary(pd.Series(pooled_scores), threshold)
        pooled_metrics = calculate_comprehensive_metrics(
            np.array(pooled_labels), 
            pooled_binary_pred.values
        )
        results.update({f'pooled_{k}': v for k, v in pooled_metrics.items()})
    else:
        results.update({k: v for k, v in empty_metrics.items() if k.startswith('pooled_')})
    
    return results


def process_non_interactive_average(
    llm_responses: pd.DataFrame,
    human_ratings: pd.DataFrame,
    prompt_name: str,
    model_name: str,
    threshold: float = config.LLM_SCORE_THRESHOLD,
    joe_threshold: float = config.JOE_SCORE_THRESHOLD
) -> Dict[str, float]:
    """
    Process non-interactive average approach.
    Takes the average of all responses for each prompt-model-transcript combination.
    """
    # Filter for specific prompt and model
    df = llm_responses[
        (llm_responses['prompt_name'] == prompt_name) & 
        (llm_responses['model_name'] == model_name)
    ].copy()
    
    empty_metrics = get_empty_metrics()
    
    if len(df) == 0:
        return empty_metrics
    
    # Average scores per transcript
    avg_scores = df.groupby('transcriptid')['score'].mean().reset_index()
    avg_scores.columns = ['transcriptid', 'avg_score']
    
    # Merge with human ratings
    merged = pd.merge(avg_scores, human_ratings, on='transcriptid', how='inner')
    
    results = {}
    
    # Joe's subsample
    joe_data = merged[merged['joe_score'].notna()]
    if len(joe_data) > 0:
        joe_binary = convert_to_binary(joe_data['joe_score'], joe_threshold)
        joe_metrics = calculate_metrics_for_subsample(joe_data['avg_score'], joe_binary, threshold)
        results.update({f'joe_{k}': v for k, v in joe_metrics.items()})
    else:
        results.update({k: v for k, v in empty_metrics.items() if k.startswith('joe_')})
    
    # ACL's subsample
    acl_data = merged[merged['acl_manual_flag'].notna()]
    if len(acl_data) > 0:
        acl_metrics = calculate_metrics_for_subsample(
            acl_data['avg_score'], 
            acl_data['acl_manual_flag'], 
            threshold
        )
        results.update({f'acl_{k}': v for k, v in acl_metrics.items()})
    else:
        results.update({k: v for k, v in empty_metrics.items() if k.startswith('acl_')})
    
    # Pooled sample
    pooled_data = merged[(merged['joe_score'].notna()) | (merged['acl_manual_flag'].notna())]
    if len(pooled_data) > 0:
        # Create unified labels
        pooled_labels = []
        pooled_scores = []
        
        for _, row in pooled_data.iterrows():
            # Use ACL label if available, otherwise convert Joe's score
            if pd.notna(row['acl_manual_flag']):
                pooled_labels.append(int(row['acl_manual_flag']))
            else:
                pooled_labels.append(int(row['joe_score'] >= joe_threshold))
            pooled_scores.append(row['avg_score'])
        
        pooled_binary_pred = convert_to_binary(pd.Series(pooled_scores), threshold)
        pooled_metrics = calculate_comprehensive_metrics(
            np.array(pooled_labels), 
            pooled_binary_pred.values
        )
        results.update({f'pooled_{k}': v for k, v in pooled_metrics.items()})
    else:
        results.update({k: v for k, v in empty_metrics.items() if k.startswith('pooled_')})
    
    return results


def process_agentic_repeated_high(
    llm_responses: pd.DataFrame,
    human_ratings: pd.DataFrame,
    prompt_name: str,
    model_name: str,
    threshold: float = config.LLM_SCORE_THRESHOLD,
    joe_threshold: float = config.JOE_SCORE_THRESHOLD
) -> Dict[str, float]:
    """
    Process agentic repeated high-scoring approach.
    Average scores from repeated responses only for transcripts that scored >= threshold initially.
    Only applicable for models that start with "gpt-4o-mini".
    """
    empty_metrics = get_empty_metrics()
    
    # Check if model is eligible
    # This is based on the fact that we ran the big batch using gpt-4o-mini and only re-ran those that scored high then
    if not model_name.startswith('gpt-4o-mini'):
        return empty_metrics
    
    # Filter for specific prompt and model
    df = llm_responses[
        (llm_responses['prompt_name'] == prompt_name) & 
        (llm_responses['model_name'] == model_name)
    ].copy()
    
    if len(df) == 0:
        return empty_metrics
    
    # Get first response per transcript
    first_responses = df.sort_values('date').groupby('transcriptid').first().reset_index()
    
    # Identify high-scoring transcripts
    high_scoring_transcripts = first_responses[first_responses['score'] >= threshold]['transcriptid'].tolist()
    
    # For high-scoring transcripts, average all responses
    # For others, use the first response
    final_scores = []
    
    for transcriptid in df['transcriptid'].unique():
        transcript_df = df[df['transcriptid'] == transcriptid]
        
        if transcriptid in high_scoring_transcripts:
            # Average all responses for high-scoring transcripts
            avg_score = transcript_df['score'].mean()
        else:
            # Use first response for others
            avg_score = transcript_df.sort_values('date').iloc[0]['score']
        
        final_scores.append({
            'transcriptid': transcriptid,
            'final_score': avg_score
        })
    
    final_scores_df = pd.DataFrame(final_scores)
    
    # Merge with human ratings
    merged = pd.merge(final_scores_df, human_ratings, on='transcriptid', how='inner')
    
    results = {}
    
    # Joe's subsample
    joe_data = merged[merged['joe_score'].notna()]
    if len(joe_data) > 0:
        joe_binary = convert_to_binary(joe_data['joe_score'], joe_threshold)
        joe_metrics = calculate_metrics_for_subsample(joe_data['final_score'], joe_binary, threshold)
        results.update({f'joe_{k}': v for k, v in joe_metrics.items()})
    else:
        results.update({k: v for k, v in empty_metrics.items() if k.startswith('joe_')})
    
    # ACL's subsample
    acl_data = merged[merged['acl_manual_flag'].notna()]
    if len(acl_data) > 0:
        acl_metrics = calculate_metrics_for_subsample(
            acl_data['final_score'], 
            acl_data['acl_manual_flag'], 
            threshold
        )
        results.update({f'acl_{k}': v for k, v in acl_metrics.items()})
    else:
        results.update({k: v for k, v in empty_metrics.items() if k.startswith('acl_')})
    
    # Pooled sample
    pooled_data = merged[(merged['joe_score'].notna()) | (merged['acl_manual_flag'].notna())]
    if len(pooled_data) > 0:
        # Create unified labels
        pooled_labels = []
        pooled_scores = []
        
        for _, row in pooled_data.iterrows():
            # Use ACL label if available, otherwise convert Joe's score
            if pd.notna(row['acl_manual_flag']):
                pooled_labels.append(int(row['acl_manual_flag']))
            else:
                pooled_labels.append(int(row['joe_score'] >= joe_threshold))
            pooled_scores.append(row['final_score'])
        
        pooled_binary_pred = convert_to_binary(pd.Series(pooled_scores), threshold)
        pooled_metrics = calculate_comprehensive_metrics(
            np.array(pooled_labels), 
            pooled_binary_pred.values
        )
        results.update({f'pooled_{k}': v for k, v in pooled_metrics.items()})
    else:
        results.update({k: v for k, v in empty_metrics.items() if k.startswith('pooled_')})
    
    return results


def process_agentic_analysis(
    analysis_responses: pd.DataFrame,
    human_ratings: pd.DataFrame,
    original_prompt_name: str,
    model_name: str,
    threshold: float = config.LLM_SCORE_THRESHOLD,
    joe_threshold: float = config.JOE_SCORE_THRESHOLD,
    analysis_threshold: float = config.ANALYSIS_SCORE_THRESHOLD
) -> Dict[str, float]:
    """
    Process agentic analysis approach.
    Uses corrected scores: original scores validated by analysis, with false positives set to 0.
    Evaluates on full test set.
    """
    # First, get ALL original LLM responses for this prompt/model
    conn = sqlite3.connect(config.DATABASE_PATH)
    query = """
    SELECT 
        transcriptid,
        response,
        date
    FROM queries
    WHERE prompt_name = ? AND model_name = ?
    ORDER BY date ASC
    """
    all_responses = pd.read_sql_query(query, conn, params=(original_prompt_name, model_name))
    conn.close()
    
    # Extract scores and keep earliest per transcript
    all_responses['original_score'] = all_responses['response'].apply(extract_score_from_response)
    all_responses = all_responses[all_responses['original_score'].notna()]
    all_responses = all_responses.sort_values('date').groupby('transcriptid').first().reset_index()
    
    # Get analysis results for this prompt/model
    analysis_df = analysis_responses[
        (analysis_responses['original_prompt_name'] == original_prompt_name) & 
        (analysis_responses['model_name'] == model_name)
    ].copy()
    
    # Average analysis scores per transcript
    if len(analysis_df) > 0:
        avg_analysis = analysis_df.groupby('transcriptid')['analysis_score'].mean().reset_index()
        avg_analysis.columns = ['transcriptid', 'analysis_avg_score']
    else:
        avg_analysis = pd.DataFrame(columns=['transcriptid', 'analysis_avg_score'])
    
    # Merge original scores with analysis scores
    merged_scores = pd.merge(
        all_responses[['transcriptid', 'original_score']], 
        avg_analysis, 
        on='transcriptid', 
        how='left'
    )
    
    # Apply correction logic
    corrected_scores = []
    for _, row in merged_scores.iterrows():
        original = row['original_score']
        analysis = row['analysis_avg_score']
        
        if pd.notna(analysis):
            # Has analysis: validate the original high score
            if original >= threshold and analysis < analysis_threshold:
                # False positive detected by analysis
                corrected_score = 0
            else:
                # Either validated high score or was low to begin with
                corrected_score = original
        else:
            # No analysis (original was <threshold): keep original
            corrected_score = original
            
        corrected_scores.append({
            'transcriptid': row['transcriptid'],
            'corrected_score': corrected_score
        })
    
    corrected_df = pd.DataFrame(corrected_scores)
    
    # Merge with human ratings to get test set
    merged = pd.merge(corrected_df, human_ratings, on='transcriptid', how='inner')
    
    empty_metrics = get_empty_metrics()
    
    if len(merged) == 0:
        return empty_metrics
    
    results = {}
    
    # Joe's subsample
    joe_data = merged[merged['joe_score'].notna()]
    if len(joe_data) > 0:
        joe_binary = convert_to_binary(joe_data['joe_score'], joe_threshold)
        joe_metrics = calculate_metrics_for_subsample(joe_data['corrected_score'], joe_binary, threshold)
        results.update({f'joe_{k}': v for k, v in joe_metrics.items()})
    else:
        results.update({k: v for k, v in empty_metrics.items() if k.startswith('joe_')})
    
    # ACL's subsample
    acl_data = merged[merged['acl_manual_flag'].notna()]
    if len(acl_data) > 0:
        acl_metrics = calculate_metrics_for_subsample(
            acl_data['corrected_score'], 
            acl_data['acl_manual_flag'], 
            threshold
        )
        results.update({f'acl_{k}': v for k, v in acl_metrics.items()})
    else:
        results.update({k: v for k, v in empty_metrics.items() if k.startswith('acl_')})
    
    # Pooled sample
    pooled_data = merged[(merged['joe_score'].notna()) | (merged['acl_manual_flag'].notna())]
    if len(pooled_data) > 0:
        # Create unified labels
        pooled_labels = []
        pooled_scores = []
        
        for _, row in pooled_data.iterrows():
            # Use ACL label if available, otherwise convert Joe's score
            if pd.notna(row['acl_manual_flag']):
                pooled_labels.append(int(row['acl_manual_flag']))
            else:
                pooled_labels.append(int(row['joe_score'] >= joe_threshold))
            pooled_scores.append(row['corrected_score'])
        
        pooled_binary_pred = convert_to_binary(pd.Series(pooled_scores), threshold)
        pooled_metrics = calculate_comprehensive_metrics(
            np.array(pooled_labels), 
            pooled_binary_pred.values
        )
        results.update({f'pooled_{k}': v for k, v in pooled_metrics.items()})
    else:
        results.update({k: v for k, v in empty_metrics.items() if k.startswith('pooled_')})
    
    return results


def get_unique_prompt_model_combinations(llm_responses: pd.DataFrame) -> List[Tuple[str, str]]:
    """Get unique combinations of prompt_name and model_name that have responses."""
    combinations = llm_responses[['prompt_name', 'model_name']].drop_duplicates()
    return [(row['prompt_name'], row['model_name']) for _, row in combinations.iterrows()]


def get_analysis_prompt_names(analysis_responses: pd.DataFrame, prompt_name: str, model_name: str) -> List[str]:
    """Get unique analysis prompt names for a given original prompt and model."""
    df = analysis_responses[
        (analysis_responses['original_prompt_name'] == prompt_name) & 
        (analysis_responses['model_name'] == model_name)
    ]
    return df['analysis_prompt_name'].unique().tolist()


def main():
    parser = argparse.ArgumentParser(description='Calculate comprehensive metrics for LLM approaches')
    parser.add_argument('--prompt', type=str, help='Specific prompt name to analyze (default: all prompts)')
    parser.add_argument('--threshold', type=float, default=config.LLM_SCORE_THRESHOLD, help='Threshold for LLM score binary conversion')
    parser.add_argument('--joe-threshold', dest='joe_threshold', type=float, default=config.JOE_SCORE_THRESHOLD, help='Threshold for Joe\'s score binary conversion')
    parser.add_argument('--analysis-threshold', dest='analysis_threshold', type=float, default=config.ANALYSIS_SCORE_THRESHOLD, help='Threshold for analysis score validation')
    parser.add_argument('--output', type=str, default=config.BENCHMARKING_PATH, help='Output CSV file path')
    parser.add_argument('--detailed', action='store_true', help='Print detailed metrics including confusion matrices')
    
    args = parser.parse_args()
    
    print("Loading data...")
    human_ratings = load_human_ratings()
    llm_responses = get_all_llm_responses()
    analysis_responses = get_analysis_responses()
    
    # Get test transcript IDs (those with human ratings)
    test_transcript_ids = human_ratings[
        (human_ratings['joe_score'].notna()) | (human_ratings['acl_manual_flag'].notna())
    ]['transcriptid'].unique()
    
    # Filter LLM responses to only test transcripts
    llm_responses = llm_responses[llm_responses['transcriptid'].isin(test_transcript_ids)]
    
    print(f"Found {len(llm_responses)} LLM responses for test transcripts")
    print(f"Found {len(analysis_responses)} analysis responses")
    
    # Get unique prompt-model combinations
    combinations = get_unique_prompt_model_combinations(llm_responses)
    
    # Filter by specific prompt if requested
    if args.prompt:
        combinations = [(p, m) for p, m in combinations if p == args.prompt]
        print(f"Filtering for prompt: {args.prompt}")
    
    print(f"Processing {len(combinations)} prompt-model combinations...")
    
    results = []
    
    for prompt_name, model_name in combinations:
        print(f"\nProcessing {prompt_name} with {model_name}...")
        
        # Non-interactive single
        single_results = process_non_interactive_single(
            llm_responses, human_ratings, prompt_name, model_name, args.threshold, args.joe_threshold
        )
        results.append({
            'model': model_name,
            'prompt': prompt_name,
            'approach': 'non-interactive-single',
            'followup': 'none',
            **single_results
        })
        
        # Non-interactive average
        avg_results = process_non_interactive_average(
            llm_responses, human_ratings, prompt_name, model_name, args.threshold, args.joe_threshold
        )
        results.append({
            'model': model_name,
            'prompt': prompt_name,
            'approach': 'non-interactive-average',
            'followup': 'none',
            **avg_results
        })
        
        # Agentic repeated high-scoring (only for gpt-4o-mini models)
        if model_name.startswith('gpt-4o-mini'):
            repeated_results = process_agentic_repeated_high(
                llm_responses, human_ratings, prompt_name, model_name, args.threshold, args.joe_threshold
            )
            results.append({
                'model': model_name,
                'prompt': prompt_name,
                'approach': 'agentic-repeated-high',
                'followup': 'none',
                **repeated_results
            })
        
        # Agentic analysis (check for analysis prompts)
        analysis_prompts = get_analysis_prompt_names(analysis_responses, prompt_name, model_name)
        
        if analysis_prompts:
            # Process each analysis prompt separately
            for analysis_prompt in analysis_prompts:
                # Filter analysis responses for this specific analysis prompt
                filtered_analysis = analysis_responses[
                    analysis_responses['analysis_prompt_name'] == analysis_prompt
                ]
                
                analysis_results = process_agentic_analysis(
                    filtered_analysis, human_ratings, prompt_name, model_name, args.threshold, args.joe_threshold, args.analysis_threshold
                )
                results.append({
                    'model': model_name,
                    'prompt': prompt_name,
                    'approach': 'agentic-analysis',
                    'followup': analysis_prompt,
                    **analysis_results
                })
    
    # Create DataFrame and save
    results_df = pd.DataFrame(results)
    
    # Sort by pooled F1 score (descending)
    results_df = results_df.sort_values('pooled_f1', ascending=False, na_position='last')
    
    # Format numeric columns to 3 decimal places
    numeric_cols = [col for col in results_df.columns if any(metric in col for metric in ['precision', 'recall', 'f1', 'specificity'])]
    for col in numeric_cols:
        results_df[col] = results_df[col].round(3)
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Save to CSV
    results_df.to_csv(args.output, index=False)
    print(f"\nResults saved to {args.output}")
    
    # Print summary
    if args.detailed:
        print("\nDetailed results for top 5 approaches by pooled F1 score:")
        for idx, row in results_df.head(5).iterrows():
            print(f"\n{'='*60}")
            print(f"Model: {row['model']}")
            print(f"Prompt: {row['prompt']}")
            print(f"Approach: {row['approach']}")
            print(f"Followup: {row['followup']}")
            print(f"\nJoe's Sample (n={int(row['joe_n']) if not pd.isna(row['joe_n']) else 0}):")
            if row['joe_n'] > 0:
                print(f"  Precision: {row['joe_precision']:.3f}")
                print(f"  Recall: {row['joe_recall']:.3f}")
                print(f"  F1: {row['joe_f1']:.3f}")
                print(f"  Specificity: {row['joe_specificity']:.3f}")
            else:
                print("  No data")
            
            print(f"\nACL's Sample (n={int(row['acl_n']) if not pd.isna(row['acl_n']) else 0}):")
            if row['acl_n'] > 0:
                print(f"  Precision: {row['acl_precision']:.3f}")
                print(f"  Recall: {row['acl_recall']:.3f}")
                print(f"  F1: {row['acl_f1']:.3f}")
                print(f"  Specificity: {row['acl_specificity']:.3f}")
            else:
                print("  No data")
            
            print(f"\nPooled Sample (n={int(row['pooled_n']) if not pd.isna(row['pooled_n']) else 0}):")
            if row['pooled_n'] > 0:
                print(f"  Precision: {row['pooled_precision']:.3f}")
                print(f"  Recall: {row['pooled_recall']:.3f}")
                print(f"  F1: {row['pooled_f1']:.3f}")
                print(f"  Specificity: {row['pooled_specificity']:.3f}")
            else:
                print("  No data")
    else:
        # Simple summary table
        print("\nTop 10 results by pooled F1 score:")
        display_cols = ['model', 'prompt', 'approach', 'followup', 
                       'pooled_n', 'pooled_precision', 'pooled_recall', 'pooled_f1']
        print(results_df[display_cols].head(10).to_string(index=False))


if __name__ == '__main__':
    main()