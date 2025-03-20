import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import config
import sqlite3
from datetime import datetime
import json

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
    Returns a score where higher values indicate better performance.
    """
    mae = np.mean(np.abs(y_true - y_pred))
    return 100 - mae  # Convert MAE to a score where higher is better

def performance_score(
    prompt_name: str,
    test_set: str = 'all',
    binary_threshold: float = 65.0
) -> Dict[str, float]:
    """
    Calculate performance scores for a prompt.
    
    Args:
        prompt_name: Name of the prompt to evaluate
        test_set: Which test set to use ('joe', 'acl', or 'all')
        binary_threshold: Threshold for converting continuous scores (0-100) to binary (default: 65)
                         Used for both LLM responses and Joe scores
    
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
            scores['joe_accuracy'] = calculate_score_accuracy(
                joe_data['joe_score'].values,
                joe_data['score'].values
            )
            # Binary score (accuracy)
            joe_binary_true = (joe_data['joe_score'] >= binary_threshold).astype(int)
            joe_binary_pred = (joe_data['score'] >= binary_threshold).astype(int)
            scores['joe_binary_accuracy'] = calculate_binary_accuracy(
                joe_binary_true.values,
                joe_binary_pred.values
            )
    
    # Calculate ACL score performance
    if test_set in ['acl', 'all']:
        acl_data = df[df['acl_manual_flag'].notna()]
        if len(acl_data) > 0:
            # Binary score (accuracy)
            acl_binary_pred = (acl_data['score'] >= binary_threshold).astype(int)
            scores['acl_accuracy'] = calculate_binary_accuracy(
                acl_data['acl_manual_flag'].values,
                acl_binary_pred.values
            )
    
    return scores

def create_leaderboard(
    prompt_names: List[str],
    binary_threshold: float = 65.0
) -> pd.DataFrame:
    """
    Create a leaderboard comparing multiple prompts.
    
    Args:
        prompt_names: List of prompt names to evaluate
        binary_threshold: Threshold for converting continuous scores (0-100) to binary
    
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
            'joe_accuracy': joe_scores.get('joe_accuracy', np.nan),
            'joe_binary_accuracy': joe_scores.get('joe_binary_accuracy', np.nan),
            'acl_accuracy': acl_scores.get('acl_accuracy', np.nan),
            'combined_accuracy': all_scores.get('joe_binary_accuracy', np.nan) * 0.5 + 
                               all_scores.get('acl_accuracy', np.nan) * 0.5
        }
        results.append(prompt_scores)
    
    # Create DataFrame and sort by combined accuracy
    leaderboard = pd.DataFrame(results)
    leaderboard = leaderboard.sort_values('combined_accuracy', ascending=False)
    
    return leaderboard

def save_leaderboard(leaderboard: pd.DataFrame, output_path: str = "data/leaderboard.csv"):
    """Save leaderboard to CSV file."""
    leaderboard.to_csv(output_path, index=False)
    print(f"Leaderboard saved to {output_path}")
    print("\nPrompt Leaderboard:")
    print(leaderboard.to_string(index=False))

if __name__ == "__main__":
    # Get all unique prompt names from the database
    conn = sqlite3.connect("data/queries.sqlite")
    prompt_names = pd.read_sql_query("SELECT DISTINCT prompt_name FROM queries", conn)['prompt_name'].tolist()
    conn.close()
    
    # Create and save leaderboard
    leaderboard = create_leaderboard(prompt_names)
    save_leaderboard(leaderboard) 