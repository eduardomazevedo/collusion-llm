#!/usr/bin/env python3
"""
Calculate F1 scores for different LLM approaches against human-reviewed samples.

This script computes F1 scores for:
- Non-interactive approaches: single response, average of all responses
- Agentic approaches: repeated high-scoring responses, follow-up analysis

F1 scores are calculated for Joe's subsample, ACL's subsample, and pooled sample.
"""

import pandas as pd
import numpy as np
import sqlite3
import json
import argparse
from typing import Dict, List, Tuple, Optional
import config


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
    """Extract score from JSON response string."""
    try:
        response_dict = json.loads(response_str)
        if isinstance(response_dict, dict):
            return response_dict.get('score', None)
        return None
    except:
        return None


def get_all_llm_responses() -> pd.DataFrame:
    """Load all LLM responses from the queries table."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    query = """
    SELECT 
        query_id,
        prompt_name,
        transcript_id,
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
        q.transcript_id,
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


def convert_to_binary(scores: pd.Series, threshold: float = 75.0) -> pd.Series:
    """Convert continuous scores to binary using threshold."""
    return (scores >= threshold).astype(int)


def calculate_metrics_for_subsample(
    llm_scores: pd.Series, 
    human_labels: pd.Series,
    threshold: float = 75.0
) -> Dict[str, float]:
    """Calculate comprehensive metrics for a subsample."""
    # Convert LLM scores to binary
    llm_binary = convert_to_binary(llm_scores, threshold)
    
    # Calculate comprehensive metrics
    return calculate_comprehensive_metrics(human_labels.values, llm_binary.values)


def process_non_interactive_single(
    llm_responses: pd.DataFrame,
    human_ratings: pd.DataFrame,
    prompt_name: str,
    model_name: str,
    threshold: float = 75.0
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
    
    # Initialize empty metrics
    empty_metrics = {
        'joe_n': 0, 'joe_precision': np.nan, 'joe_recall': np.nan, 'joe_f1': np.nan, 'joe_specificity': np.nan,
        'acl_n': 0, 'acl_precision': np.nan, 'acl_recall': np.nan, 'acl_f1': np.nan, 'acl_specificity': np.nan,
        'pooled_n': 0, 'pooled_precision': np.nan, 'pooled_recall': np.nan, 'pooled_f1': np.nan, 'pooled_specificity': np.nan
    }
    
    if len(df) == 0:
        return empty_metrics
    
    # Keep only the earliest response per transcript
    df = df.sort_values('date').groupby('transcript_id').first().reset_index()
    
    # Merge with human ratings
    merged = pd.merge(df, human_ratings, left_on='transcript_id', right_on='transcriptid', how='inner')
    
    results = {}
    
    # Joe's subsample
    joe_data = merged[merged['joe_score'].notna()]
    if len(joe_data) > 0:
        joe_binary = convert_to_binary(joe_data['joe_score'], threshold)
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
                pooled_labels.append(int(row['joe_score'] >= threshold))
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
    threshold: float = 75.0
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
    
    # Initialize empty metrics
    empty_metrics = {
        'joe_n': 0, 'joe_precision': np.nan, 'joe_recall': np.nan, 'joe_f1': np.nan, 'joe_specificity': np.nan,
        'acl_n': 0, 'acl_precision': np.nan, 'acl_recall': np.nan, 'acl_f1': np.nan, 'acl_specificity': np.nan,
        'pooled_n': 0, 'pooled_precision': np.nan, 'pooled_recall': np.nan, 'pooled_f1': np.nan, 'pooled_specificity': np.nan
    }
    
    if len(df) == 0:
        return empty_metrics
    
    # Average scores per transcript
    avg_scores = df.groupby('transcript_id')['score'].mean().reset_index()
    avg_scores.columns = ['transcript_id', 'avg_score']
    
    # Merge with human ratings
    merged = pd.merge(avg_scores, human_ratings, left_on='transcript_id', right_on='transcriptid', how='inner')
    
    results = {}
    
    # Joe's subsample
    joe_data = merged[merged['joe_score'].notna()]
    if len(joe_data) > 0:
        joe_binary = convert_to_binary(joe_data['joe_score'], threshold)
        results['joe_f1'] = calculate_f1_for_subsample(joe_data['avg_score'], joe_binary, threshold)
    else:
        results['joe_f1'] = np.nan
    
    # ACL's subsample
    acl_data = merged[merged['acl_manual_flag'].notna()]
    if len(acl_data) > 0:
        results['acl_f1'] = calculate_f1_for_subsample(
            acl_data['avg_score'], 
            acl_data['acl_manual_flag'], 
            threshold
        )
    else:
        results['acl_f1'] = np.nan
    
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
                pooled_labels.append(int(row['joe_score'] >= threshold))
            pooled_scores.append(row['avg_score'])
        
        pooled_binary_pred = convert_to_binary(pd.Series(pooled_scores), threshold)
        results['pooled_f1'] = calculate_f1_score(
            np.array(pooled_labels), 
            pooled_binary_pred.values
        )
    else:
        results['pooled_f1'] = np.nan
    
    return results


def process_agentic_repeated_high(
    llm_responses: pd.DataFrame,
    human_ratings: pd.DataFrame,
    prompt_name: str,
    model_name: str,
    threshold: float = 75.0
) -> Dict[str, float]:
    """
    Process agentic repeated high-scoring approach.
    Average scores from repeated responses only for transcripts that scored >= threshold initially.
    Only applicable for models that start with "gpt-4o-mini".
    """
    # Check if model is eligible
    if not model_name.startswith('gpt-4o-mini'):
        return {'joe_f1': np.nan, 'acl_f1': np.nan, 'pooled_f1': np.nan}
    
    # Filter for specific prompt and model
    df = llm_responses[
        (llm_responses['prompt_name'] == prompt_name) & 
        (llm_responses['model_name'] == model_name)
    ].copy()
    
    if len(df) == 0:
        return {'joe_f1': np.nan, 'acl_f1': np.nan, 'pooled_f1': np.nan}
    
    # Get first response per transcript
    first_responses = df.sort_values('date').groupby('transcript_id').first().reset_index()
    
    # Identify high-scoring transcripts
    high_scoring_transcripts = first_responses[first_responses['score'] >= threshold]['transcript_id'].tolist()
    
    # For high-scoring transcripts, average all responses
    # For others, use the first response
    final_scores = []
    
    for transcript_id in df['transcript_id'].unique():
        transcript_df = df[df['transcript_id'] == transcript_id]
        
        if transcript_id in high_scoring_transcripts:
            # Average all responses for high-scoring transcripts
            avg_score = transcript_df['score'].mean()
        else:
            # Use first response for others
            avg_score = transcript_df.sort_values('date').iloc[0]['score']
        
        final_scores.append({
            'transcript_id': transcript_id,
            'final_score': avg_score
        })
    
    final_scores_df = pd.DataFrame(final_scores)
    
    # Merge with human ratings
    merged = pd.merge(final_scores_df, human_ratings, left_on='transcript_id', right_on='transcriptid', how='inner')
    
    results = {}
    
    # Joe's subsample
    joe_data = merged[merged['joe_score'].notna()]
    if len(joe_data) > 0:
        joe_binary = convert_to_binary(joe_data['joe_score'], threshold)
        results['joe_f1'] = calculate_f1_for_subsample(joe_data['final_score'], joe_binary, threshold)
    else:
        results['joe_f1'] = np.nan
    
    # ACL's subsample
    acl_data = merged[merged['acl_manual_flag'].notna()]
    if len(acl_data) > 0:
        results['acl_f1'] = calculate_f1_for_subsample(
            acl_data['final_score'], 
            acl_data['acl_manual_flag'], 
            threshold
        )
    else:
        results['acl_f1'] = np.nan
    
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
                pooled_labels.append(int(row['joe_score'] >= threshold))
            pooled_scores.append(row['final_score'])
        
        pooled_binary_pred = convert_to_binary(pd.Series(pooled_scores), threshold)
        results['pooled_f1'] = calculate_f1_score(
            np.array(pooled_labels), 
            pooled_binary_pred.values
        )
    else:
        results['pooled_f1'] = np.nan
    
    return results


def process_agentic_analysis(
    analysis_responses: pd.DataFrame,
    human_ratings: pd.DataFrame,
    original_prompt_name: str,
    model_name: str,
    threshold: float = 75.0
) -> Dict[str, float]:
    """
    Process agentic analysis approach.
    Uses scores from follow-up analysis queries.
    """
    # Filter for specific original prompt and model
    df = analysis_responses[
        (analysis_responses['original_prompt_name'] == original_prompt_name) & 
        (analysis_responses['model_name'] == model_name)
    ].copy()
    
    if len(df) == 0:
        return {'joe_f1': np.nan, 'acl_f1': np.nan, 'pooled_f1': np.nan}
    
    # Average analysis scores per transcript
    avg_scores = df.groupby('transcript_id')['analysis_score'].mean().reset_index()
    avg_scores.columns = ['transcript_id', 'analysis_avg_score']
    
    # Merge with human ratings
    merged = pd.merge(avg_scores, human_ratings, left_on='transcript_id', right_on='transcriptid', how='inner')
    
    results = {}
    
    # Joe's subsample
    joe_data = merged[merged['joe_score'].notna()]
    if len(joe_data) > 0:
        joe_binary = convert_to_binary(joe_data['joe_score'], threshold)
        results['joe_f1'] = calculate_f1_for_subsample(joe_data['analysis_avg_score'], joe_binary, threshold)
    else:
        results['joe_f1'] = np.nan
    
    # ACL's subsample
    acl_data = merged[merged['acl_manual_flag'].notna()]
    if len(acl_data) > 0:
        results['acl_f1'] = calculate_f1_for_subsample(
            acl_data['analysis_avg_score'], 
            acl_data['acl_manual_flag'], 
            threshold
        )
    else:
        results['acl_f1'] = np.nan
    
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
                pooled_labels.append(int(row['joe_score'] >= threshold))
            pooled_scores.append(row['analysis_avg_score'])
        
        pooled_binary_pred = convert_to_binary(pd.Series(pooled_scores), threshold)
        results['pooled_f1'] = calculate_f1_score(
            np.array(pooled_labels), 
            pooled_binary_pred.values
        )
    else:
        results['pooled_f1'] = np.nan
    
    return results


def process_agentic_analysis_filtered(
    analysis_responses: pd.DataFrame,
    human_ratings: pd.DataFrame,
    original_prompt_name: str,
    model_name: str,
    threshold: float = 75.0
) -> Dict[str, float]:
    """
    Process agentic analysis filtered approach.
    Uses original query scores but only for transcripts where analysis score >= threshold.
    """
    # Filter for specific original prompt and model
    df = analysis_responses[
        (analysis_responses['original_prompt_name'] == original_prompt_name) & 
        (analysis_responses['model_name'] == model_name)
    ].copy()
    
    if len(df) == 0:
        return {'joe_f1': np.nan, 'acl_f1': np.nan, 'pooled_f1': np.nan}
    
    # Filter to only keep transcripts where analysis score >= threshold
    high_analysis_df = df[df['analysis_score'] >= threshold]
    
    if len(high_analysis_df) == 0:
        return {'joe_f1': np.nan, 'acl_f1': np.nan, 'pooled_f1': np.nan}
    
    # Average original scores per transcript (in case of multiple analyses)
    avg_original_scores = high_analysis_df.groupby('transcript_id')['original_score'].mean().reset_index()
    avg_original_scores.columns = ['transcript_id', 'filtered_original_score']
    
    # Merge with human ratings
    merged = pd.merge(avg_original_scores, human_ratings, left_on='transcript_id', right_on='transcriptid', how='inner')
    
    results = {}
    
    # Joe's subsample
    joe_data = merged[merged['joe_score'].notna()]
    if len(joe_data) > 0:
        joe_binary = convert_to_binary(joe_data['joe_score'], threshold)
        results['joe_f1'] = calculate_f1_for_subsample(joe_data['filtered_original_score'], joe_binary, threshold)
    else:
        results['joe_f1'] = np.nan
    
    # ACL's subsample
    acl_data = merged[merged['acl_manual_flag'].notna()]
    if len(acl_data) > 0:
        results['acl_f1'] = calculate_f1_for_subsample(
            acl_data['filtered_original_score'], 
            acl_data['acl_manual_flag'], 
            threshold
        )
    else:
        results['acl_f1'] = np.nan
    
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
                pooled_labels.append(int(row['joe_score'] >= threshold))
            pooled_scores.append(row['filtered_original_score'])
        
        pooled_binary_pred = convert_to_binary(pd.Series(pooled_scores), threshold)
        results['pooled_f1'] = calculate_f1_score(
            np.array(pooled_labels), 
            pooled_binary_pred.values
        )
    else:
        results['pooled_f1'] = np.nan
    
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
    parser = argparse.ArgumentParser(description='Calculate F1 scores for LLM approaches')
    parser.add_argument('--prompt', type=str, help='Specific prompt name to analyze (default: all prompts)')
    parser.add_argument('--threshold', type=float, default=75.0, help='Threshold for binary conversion (default: 75.0)')
    parser.add_argument('--output', type=str, default='data/f1_scores.csv', help='Output CSV file path')
    
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
    llm_responses = llm_responses[llm_responses['transcript_id'].isin(test_transcript_ids)]
    
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
            llm_responses, human_ratings, prompt_name, model_name, args.threshold
        )
        results.append({
            'model': model_name,
            'prompt': prompt_name,
            'approach': 'non-interactive-single',
            'followup': 'none',
            'joe_f1': single_results['joe_f1'],
            'acl_f1': single_results['acl_f1'],
            'pooled_f1': single_results['pooled_f1']
        })
        
        # Non-interactive average
        avg_results = process_non_interactive_average(
            llm_responses, human_ratings, prompt_name, model_name, args.threshold
        )
        results.append({
            'model': model_name,
            'prompt': prompt_name,
            'approach': 'non-interactive-average',
            'followup': 'none',
            'joe_f1': avg_results['joe_f1'],
            'acl_f1': avg_results['acl_f1'],
            'pooled_f1': avg_results['pooled_f1']
        })
        
        # Agentic repeated high-scoring (only for gpt-4o-mini models)
        if model_name.startswith('gpt-4o-mini'):
            repeated_results = process_agentic_repeated_high(
                llm_responses, human_ratings, prompt_name, model_name, args.threshold
            )
            results.append({
                'model': model_name,
                'prompt': prompt_name,
                'approach': 'agentic-repeated-high',
                'followup': 'none',
                'joe_f1': repeated_results['joe_f1'],
                'acl_f1': repeated_results['acl_f1'],
                'pooled_f1': repeated_results['pooled_f1']
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
                    filtered_analysis, human_ratings, prompt_name, model_name, args.threshold
                )
                results.append({
                    'model': model_name,
                    'prompt': prompt_name,
                    'approach': 'agentic-analysis',
                    'followup': analysis_prompt,
                    'joe_f1': analysis_results['joe_f1'],
                    'acl_f1': analysis_results['acl_f1'],
                    'pooled_f1': analysis_results['pooled_f1']
                })
                
                # Agentic analysis filtered (original scores filtered by analysis threshold)
                filtered_results = process_agentic_analysis_filtered(
                    filtered_analysis, human_ratings, prompt_name, model_name, args.threshold
                )
                results.append({
                    'model': model_name,
                    'prompt': prompt_name,
                    'approach': 'agentic-analysis-filtered',
                    'followup': analysis_prompt,
                    'joe_f1': filtered_results['joe_f1'],
                    'acl_f1': filtered_results['acl_f1'],
                    'pooled_f1': filtered_results['pooled_f1']
                })
    
    # Create DataFrame and save
    results_df = pd.DataFrame(results)
    
    # Sort by pooled F1 score (descending)
    results_df = results_df.sort_values('pooled_f1', ascending=False, na_position='last')
    
    # Format F1 scores to 3 decimal places
    for col in ['joe_f1', 'acl_f1', 'pooled_f1']:
        results_df[col] = results_df[col].round(3)
    
    # Save to CSV
    results_df.to_csv(args.output, index=False)
    print(f"\nResults saved to {args.output}")
    
    # Print summary
    print("\nTop 10 results by pooled F1 score:")
    print(results_df.head(10).to_string(index=False))


if __name__ == '__main__':
    main()