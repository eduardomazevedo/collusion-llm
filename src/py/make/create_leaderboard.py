import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import config
import sqlite3
from datetime import datetime
import json
import argparse
import os
import sys


def load_human_ratings() -> pd.DataFrame:
    """Load human ratings from CSV file."""
    df = pd.read_csv("data/human-ratings.csv")
    # Rename column to match database
    df = df.rename(columns={'transcriptid': 'transcript_id'})
    return df

def load_llm_responses(prompt_name: str) -> pd.DataFrame:
    """Load LLM responses for a specific prompt from the database."""
    conn = sqlite3.connect("data/queries.sqlite")
    query = """
    SELECT transcript_id, response, date
    FROM queries
    WHERE prompt_name = ?
    ORDER BY date DESC
    """
    df = pd.read_sql_query(query, conn, params=(prompt_name,))
    conn.close()
    
    # Parse JSON response to get scores
    def extract_score(response):
        try:
            response_dict = json.loads(response)
            if isinstance(response_dict, dict):
                return response_dict.get('score', np.nan)
            return np.nan
        except:
            return np.nan
    
    df['score'] = df['response'].apply(extract_score)
    return df

def calculate_binary_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate accuracy for binary predictions."""
    return np.mean(y_true == y_pred)

def calculate_score_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculate accuracy for continuous predictions (0-100 scale).
    Converts MAE to a score where higher is better.
    """
    mae = np.mean(np.abs(y_true - y_pred))
    return 100 - mae  # Convert MAE to a score where higher is better

def calculate_binary_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Calculate binary classification metrics.
    
    Args:
        y_true: True labels
        y_pred: Predicted labels
    
    Returns:
        Dictionary containing accuracy, precision, and recall for both positive and negative cases
    """
    # Calculate metrics for positive class (1)
    tp = np.sum((y_true == 1) & (y_pred == 1))
    fp = np.sum((y_true == 0) & (y_pred == 1))
    fn = np.sum((y_true == 1) & (y_pred == 0))
    
    pos_precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    pos_recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    
    # Calculate metrics for negative class (0)
    tn = np.sum((y_true == 0) & (y_pred == 0))
    fn = np.sum((y_true == 1) & (y_pred == 0))
    fp = np.sum((y_true == 0) & (y_pred == 1))
    
    neg_precision = tn / (tn + fn) if (tn + fn) > 0 else 0
    neg_recall = tn / (tn + fp) if (tn + fp) > 0 else 0
    
    # Overall accuracy
    accuracy = np.mean(y_true == y_pred)
    
    return {
        'accuracy': accuracy,
        'pos_precision': pos_precision,
        'pos_recall': pos_recall,
        'neg_precision': neg_precision,
        'neg_recall': neg_recall
    }

def performance_score(
    prompt_name: str,
    test_set: str = 'all',
    binary_threshold: float = 75.0
) -> Dict[str, float]:
    """
    Calculate performance scores for a prompt.
    
    Args:
        prompt_name: Name of the prompt to evaluate
        test_set: Which test set to use ('joe', 'acl', or 'all')
        binary_threshold: Threshold for converting continuous scores (0-100) to binary
    
    Returns:
        Dictionary containing performance scores for different metrics
    """
    # Load data
    human_ratings = load_human_ratings()
    llm_responses = load_llm_responses(prompt_name)
    
    # Merge human ratings with LLM responses
    df = pd.merge(human_ratings, llm_responses, on='transcript_id', how='inner')
    
    scores = {}
    
    # Calculate Joe score performance
    if test_set in ['joe', 'all']:
        joe_data = df[df['joe_score'].notna()]
        if len(joe_data) > 0:
            # Continuous score (converted from MAE to accuracy)
            scores['joe_continuous_accuracy'] = calculate_score_accuracy(
                joe_data['joe_score'].values,
                joe_data['score'].values
            )
            # Binary score (accuracy)
            joe_binary_true = (joe_data['joe_score'] >= binary_threshold).astype(int)
            joe_binary_pred = (joe_data['score'] >= binary_threshold).astype(int)
            joe_metrics = calculate_binary_metrics(joe_binary_true.values, joe_binary_pred.values)
            scores.update({f'joe_{k}': v for k, v in joe_metrics.items()})
    
    # Calculate ACL score performance
    if test_set in ['acl', 'all']:
        acl_data = df[df['acl_manual_flag'].notna()]
        if len(acl_data) > 0:
            # Binary score (accuracy)
            acl_binary_pred = (acl_data['score'] >= binary_threshold).astype(int)
            acl_metrics = calculate_binary_metrics(
                acl_data['acl_manual_flag'].values,
                acl_binary_pred.values
            )
            scores.update({f'acl_{k}': v for k, v in acl_metrics.items()})
    
    return scores

def create_leaderboard(
    prompt_names: List[str],
    binary_threshold: float = 65.0,
    sort_by: str = 'combined_accuracy'
) -> pd.DataFrame:
    """
    Create a leaderboard comparing multiple prompts.
    
    Args:
        prompt_names: List of prompt names to evaluate
        binary_threshold: Threshold for converting continuous scores (0-100) to binary
        sort_by: Metric to sort the leaderboard by
    
    Returns:
        DataFrame containing performance scores for all prompts
    """
    results = []
    
    for prompt in prompt_names:
        # Calculate scores for each test set
        joe_scores = performance_score(prompt, test_set='joe', binary_threshold=binary_threshold)
        acl_scores = performance_score(prompt, test_set='acl', binary_threshold=binary_threshold)
        all_scores = performance_score(prompt, test_set='all', binary_threshold=binary_threshold)
        
        # Combine scores
        prompt_scores = {
            'prompt_name': prompt,
            'joe_continuous_accuracy': joe_scores.get('joe_continuous_accuracy', np.nan),
            'joe_binary_accuracy': joe_scores.get('joe_accuracy', np.nan),
            'joe_pos_precision': joe_scores.get('joe_pos_precision', np.nan),
            'joe_pos_recall': joe_scores.get('joe_pos_recall', np.nan),
            'joe_neg_precision': joe_scores.get('joe_neg_precision', np.nan),
            'joe_neg_recall': joe_scores.get('joe_neg_recall', np.nan),
            'acl_accuracy': acl_scores.get('acl_accuracy', np.nan),
            'acl_pos_precision': acl_scores.get('acl_pos_precision', np.nan),
            'acl_pos_recall': acl_scores.get('acl_pos_recall', np.nan),
            'acl_neg_precision': acl_scores.get('acl_neg_precision', np.nan),
            'acl_neg_recall': acl_scores.get('acl_neg_recall', np.nan),
            'combined_accuracy': all_scores.get('joe_accuracy', np.nan) * 0.5 + 
                               all_scores.get('acl_accuracy', np.nan) * 0.5
        }
        results.append(prompt_scores)
    
    # Create DataFrame and sort by specified metric
    leaderboard = pd.DataFrame(results)
    
    # Validate sort metric
    if sort_by not in leaderboard.columns:
        raise ValueError(f"Invalid sort metric: {sort_by}. Available metrics: {', '.join(leaderboard.columns)}")
    
    leaderboard = leaderboard.sort_values(sort_by, ascending=False)
    
    return leaderboard

def save_leaderboard(leaderboard: pd.DataFrame, output_path: str = "data/leaderboard.csv"):
    """Save leaderboard to CSV file."""
    # Format all numeric columns to 3 decimal places
    numeric_columns = leaderboard.select_dtypes(include=[np.float64]).columns
    leaderboard[numeric_columns] = leaderboard[numeric_columns].round(3)
    
    leaderboard.to_csv(output_path, index=False)
    print(f"Leaderboard saved to {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Create or update the leaderboard.')
    parser.add_argument('--threshold', type=float, default=65.0,
                      help='Threshold for converting continuous scores (0-100) to binary')
    parser.add_argument('--sort', type=str, default='combined_accuracy',
                      help='Metric to sort the leaderboard by')
    args = parser.parse_args()
    
    # Get all unique prompts from the database
    conn = sqlite3.connect("data/queries.sqlite")
    prompt_names = pd.read_sql_query("SELECT DISTINCT prompt_name FROM queries", conn)['prompt_name'].tolist()
    conn.close()
    
    # Create leaderboard
    leaderboard = create_leaderboard(
        prompt_names=prompt_names,
        binary_threshold=args.threshold,
        sort_by=args.sort
    )
    
    # Save to CSV
    save_leaderboard(leaderboard)
    print(f"Leaderboard updated and sorted by {args.sort}")

if __name__ == '__main__':
    main() 