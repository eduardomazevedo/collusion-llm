"""
Comprehensive benchmarking analysis for LLM collusion detection.

Evaluates SimpleCapacityV8.1.1 prompt performance across different models and approaches.
Compares against three human evaluation sources: Joe's ratings, ACL's ratings, and human audit.
Produces tables, figures, and YAML statistics for the benchmarking section of the paper.

Output Files Created:
- data/yaml/benchmarking.yaml: Structured statistics for LaTeX \\data{} commands
- data/outputs/tables/model_performance.csv/tex: Model comparison table
- data/outputs/tables/approach_comparison.csv/tex: Approach comparison table  
- data/outputs/tables/human_audit_validation.csv/tex: Human audit validation stages
"""

#%%
import config
import pandas as pd
import numpy as np
import sqlite3
import json
import yaml
from pathlib import Path
from typing import Dict, Optional, Tuple
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))
from modules.utils import extract_score_from_unstructured_response

#%%
# Setup paths
yaml_dir = Path("data/yaml")
yaml_dir.mkdir(parents=True, exist_ok=True)

output_dir = Path("data/outputs")
tables_dir = output_dir / "tables"
figures_dir = output_dir / "figures"
tables_dir.mkdir(parents=True, exist_ok=True)
figures_dir.mkdir(parents=True, exist_ok=True)

#%%
# Constants
PROMPT_NAME = "SimpleCapacityV8.1.1"
THRESHOLD = config.LLM_SCORE_THRESHOLD  # 75
JOE_THRESHOLD = config.JOE_SCORE_THRESHOLD  # 75
ANALYSIS_THRESHOLD = config.ANALYSIS_SCORE_THRESHOLD  # 75

#%%
def load_human_ratings() -> pd.DataFrame:
    """Load and process human ratings data."""
    df = pd.read_csv(config.HUMAN_RATINGS_PATH)
    
    # Create binary labels
    # Joe: score >= 75 is collusive
    df['joe_binary'] = (df['joe_score'] >= JOE_THRESHOLD).astype(float)
    df.loc[df['joe_score'].isna(), 'joe_binary'] = np.nan
    
    # ACL: already binary (1 = collusive, 0 = not)
    df['acl_binary'] = df['acl_manual_flag'].astype(float)
    
    # Combined: Use ACL if available, otherwise Joe
    df['combined_binary'] = df['acl_binary'].fillna(df['joe_binary'])
    
    return df

#%%
def load_human_audit() -> pd.DataFrame:
    """Load and process human audit data."""
    df = pd.read_excel(config.HUMAN_AUDIT_PATH, usecols=["transcript_id", "T/F/N"])
    
    # Convert to binary: T=1, F/N=0
    audit_col = "T/F/N"
    df[audit_col] = df[audit_col].astype("string").str.strip().str.upper().replace("", pd.NA)
    df = df[df[audit_col].notna()].copy()
    df = df[df[audit_col].isin(["T", "F"])].copy()
    assert set(df[audit_col].unique()).issubset({'T', 'F'}), "T/F/N contains values other than T, F"
    df['audit_binary'] = (df[audit_col] == 'T').astype(int)
    
    # Rename for consistency
    df = df.rename(columns={'transcript_id': 'transcriptid'})
    
    return df

#%%
def extract_score_safe(response_str: str) -> Optional[float]:
    """Safely extract score from response string."""
    try:
        # First try JSON parsing
        response_dict = json.loads(response_str)
        if isinstance(response_dict, dict):
            score = response_dict.get('score', None)
            if score is not None:
                return float(score)
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Fall back to robust extraction
    score = extract_score_from_unstructured_response(response_str)
    return float(score) if score is not None else None

#%%
def get_llm_scores_by_approach(model_name: str = "gpt-4o-mini", test_transcript_ids: list = None) -> pd.DataFrame:
    """Get LLM scores for different approaches matching manuscript terminology."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    
    # Build query with optional transcript filter
    if test_transcript_ids:
        # Use parameterized query for test transcripts only
        placeholders = ','.join(['?'] * len(test_transcript_ids))
        query = f"""
        SELECT 
            transcriptid,
            response,
            date,
            query_id
        FROM queries
        WHERE prompt_name = ? AND model_name = ?
        AND transcriptid IN ({placeholders})
        ORDER BY transcriptid, date
        """
        params = [PROMPT_NAME, model_name] + test_transcript_ids
    else:
        query = """
        SELECT 
            transcriptid,
            response,
            date,
            query_id
        FROM queries
        WHERE prompt_name = ? AND model_name = ?
        ORDER BY transcriptid, date
        """
        params = (PROMPT_NAME, model_name)
    
    df = pd.read_sql_query(query, conn, params=params)
    
    # Early return if no data
    if len(df) == 0:
        conn.close()
        return pd.DataFrame(columns=['transcriptid', 'llm_flagged_score', 'llm_validation_score', 
                                    'llm_with_followup_score', 'n_queries'])
    
    # Extract scores
    df['score'] = df['response'].apply(extract_score_safe)
    df = df[df['score'].notna()]
    
    # Calculate different approaches using groupby for efficiency
    grouped = df.groupby('transcriptid')
    
    results = []
    for transcriptid, group_df in grouped:
        group_df = group_df.sort_values('date')
        
        # Approach 1: LLM Flagged (first response)
        llm_flagged_score = group_df.iloc[0]['score']
        
        # Approach 2: LLM Validation (average of repeated queries, only for initially flagged)
        if llm_flagged_score >= THRESHOLD and len(group_df) > 1:
            # For high-scoring transcripts with repeated queries
            llm_validation_score = group_df.head(11)['score'].mean()
        else:
            # For low-scoring or single-query transcripts, use the single score
            llm_validation_score = llm_flagged_score
        
        # Get query_id for follow-up analysis lookup
        first_query_id = group_df.iloc[0]['query_id']
        
        results.append({
            'transcriptid': transcriptid,
            'llm_flagged_score': llm_flagged_score,
            'llm_validation_score': llm_validation_score,
            'n_queries': len(group_df),
            'first_query_id': first_query_id
        })
    
    results_df = pd.DataFrame(results)
    
    # Get follow-up analysis scores only for relevant query_ids
    query_ids = results_df['first_query_id'].tolist()
    if query_ids:
        placeholders = ','.join(['?'] * len(query_ids))
        analysis_query = f"""
        SELECT 
            aq.reference_query_id,
            aq.response as analysis_response
        FROM analysis_queries aq
        WHERE aq.prompt_name = 'SimpleExcerptAnalyzer'
        AND aq.reference_query_id IN ({placeholders})
        """
        analysis_df = pd.read_sql_query(analysis_query, conn, params=query_ids)
    else:
        analysis_df = pd.DataFrame(columns=['reference_query_id', 'analysis_response'])
    
    conn.close()
    
    if len(analysis_df) > 0:
        # Extract analysis scores
        analysis_df['analysis_score'] = analysis_df['analysis_response'].apply(extract_score_safe)
        
        # Average analysis scores per reference query
        analysis_avg = analysis_df.groupby('reference_query_id')['analysis_score'].mean().reset_index()
        analysis_avg.columns = ['first_query_id', 'analysis_score']
        
        # Merge with results
        results_df = results_df.merge(analysis_avg, on='first_query_id', how='left')
    else:
        results_df['analysis_score'] = np.nan
    
    # Calculate follow-up validated score (based on validation score, not single)
    results_df['llm_with_followup_score'] = results_df.apply(
        lambda row: 0 if (row['llm_validation_score'] >= THRESHOLD and 
                         pd.notna(row['analysis_score']) and 
                         row['analysis_score'] < ANALYSIS_THRESHOLD) 
                    else row['llm_validation_score'],
        axis=1
    )
    
    return results_df

#%%
def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate classification metrics."""
    # Remove NaN values
    mask = ~(np.isnan(y_true) | np.isnan(y_pred))
    y_true = y_true[mask]
    y_pred = y_pred[mask]
    
    if len(y_true) == 0:
        return {
            'n': 0,
            'precision': np.nan,
            'recall': np.nan,
            'f1': np.nan,
            'specificity': np.nan,
            'tp': 0,
            'fp': 0,
            'tn': 0,
            'fn': 0
        }
    
    # Calculate confusion matrix
    tp = np.sum((y_true == 1) & (y_pred == 1))
    fp = np.sum((y_true == 0) & (y_pred == 1))
    fn = np.sum((y_true == 1) & (y_pred == 0))
    tn = np.sum((y_true == 0) & (y_pred == 0))
    
    # Calculate metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        'n': len(y_true),
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'specificity': specificity,
        'tp': int(tp),
        'fp': int(fp),
        'tn': int(tn),
        'fn': int(fn)
    }

#%%
def evaluate_model_performance(model_name: str, human_ratings: pd.DataFrame, human_audit: pd.DataFrame) -> Dict:
    """Evaluate a model's performance across different approaches and test sets."""
    
    # Get test transcript IDs to filter queries
    test_ids = human_ratings['transcriptid'].tolist()
    audit_ids = human_audit['transcriptid'].tolist()
    all_test_ids = list(set(test_ids + audit_ids))
    
    # Get LLM scores for different approaches (only for test transcripts)
    llm_scores = get_llm_scores_by_approach(model_name, test_transcript_ids=all_test_ids)
    
    # Merge with human ratings
    merged = llm_scores.merge(human_ratings[['transcriptid', 'joe_binary', 'acl_binary', 'combined_binary']], 
                              on='transcriptid', how='inner')
    
    # Merge with human audit
    merged_audit = llm_scores.merge(human_audit[['transcriptid', 'audit_binary']], 
                                    on='transcriptid', how='inner')
    
    results = {}
    
    # Evaluate each approach
    approaches = [
        ('llm_flagged', 'llm_flagged_score'),
        ('llm_validation', 'llm_validation_score'),
        ('llm_with_followup', 'llm_with_followup_score')
    ]
    
    for approach_name, score_col in approaches:
        # Convert scores to binary predictions
        merged[f'{approach_name}_pred'] = (merged[score_col] >= THRESHOLD).astype(int)
        merged_audit[f'{approach_name}_pred'] = (merged_audit[score_col] >= THRESHOLD).astype(int)
        
        # Calculate metrics for each test set
        joe_metrics = calculate_metrics(
            merged[merged['joe_binary'].notna()]['joe_binary'].values,
            merged[merged['joe_binary'].notna()][f'{approach_name}_pred'].values
        )
        
        acl_metrics = calculate_metrics(
            merged[merged['acl_binary'].notna()]['acl_binary'].values,
            merged[merged['acl_binary'].notna()][f'{approach_name}_pred'].values
        )
        
        combined_metrics = calculate_metrics(
            merged[merged['combined_binary'].notna()]['combined_binary'].values,
            merged[merged['combined_binary'].notna()][f'{approach_name}_pred'].values
        )
        
        audit_metrics = calculate_metrics(
            merged_audit['audit_binary'].values,
            merged_audit[f'{approach_name}_pred'].values
        ) if len(merged_audit) > 0 else {k: np.nan for k in ['n', 'precision', 'recall', 'f1', 'specificity', 'tp', 'fp', 'tn', 'fn']}
        
        results[approach_name] = {
            'joe': joe_metrics,
            'acl': acl_metrics,
            'combined': combined_metrics,
            'audit': audit_metrics
        }
    
    return results

#%%
# Load data
print("Loading human evaluation data...")
human_ratings = load_human_ratings()
human_audit = load_human_audit()

print(f"Loaded {len(human_ratings)} human ratings")
print(f"  - Joe's ratings: {human_ratings['joe_binary'].notna().sum()}")
print(f"  - ACL's ratings: {human_ratings['acl_binary'].notna().sum()}")
print(f"Loaded {len(human_audit)} human audit ratings")
print(f"  - True positives: {(human_audit['audit_binary'] == 1).sum()}")
print(f"  - False positives: {(human_audit['audit_binary'] == 0).sum()}")

#%%
# Get list of models to evaluate
conn = sqlite3.connect(config.DATABASE_PATH)
cursor = conn.cursor()
cursor.execute(f"SELECT DISTINCT model_name FROM queries WHERE prompt_name = '{PROMPT_NAME}'")
available_models = [row[0] for row in cursor.fetchall()]
conn.close()

print(f"\nAvailable models for {PROMPT_NAME}: {available_models}")

#%%
# Evaluate each model
all_results = {}
for model_name in available_models:
    print(f"\nEvaluating {model_name}...")
    all_results[model_name] = evaluate_model_performance(model_name, human_ratings, human_audit)

#%%
# Create Combined Benchmarking Table with Two Panels
print("\nCreating Combined Benchmarking Table...")

# Panel A: Approach Comparison (using gpt-4o-mini)
primary_model = "gpt-4o-mini"
panel_a_data = []

if primary_model in all_results:
    for approach_name in ['llm_flagged', 'llm_validation', 'llm_with_followup']:
        results = all_results[primary_model][approach_name]
        
        approach_display = {
            'llm_flagged': 'LLM Flagged',
            'llm_validation': 'LLM Validation',
            'llm_with_followup': 'LLM with Follow-up Analysis'
        }[approach_name]
        
        panel_a_data.append({
            'Approach': approach_display,
            'Joe F1': f"{results['joe']['f1']:.3f}" if pd.notna(results['joe']['f1']) else "—",
            'ACL F1': f"{results['acl']['f1']:.3f}" if pd.notna(results['acl']['f1']) else "—",
            'Combined F1': f"{results['combined']['f1']:.3f}" if pd.notna(results['combined']['f1']) else "—",
            'Audit F1': f"{results['audit']['f1']:.3f}" if pd.notna(results['audit']['f1']) else "—"
        })

panel_a_df = pd.DataFrame(panel_a_data)

# Panel B: Model Comparison (using LLM Flagged approach)
panel_b_data = []

for model_name in available_models:
    results = all_results[model_name]['llm_flagged']
    
    panel_b_data.append({
        'Model': model_name,
        'Joe F1': f"{results['joe']['f1']:.3f}" if pd.notna(results['joe']['f1']) else "—",
        'ACL F1': f"{results['acl']['f1']:.3f}" if pd.notna(results['acl']['f1']) else "—",
        'Combined F1': f"{results['combined']['f1']:.3f}" if pd.notna(results['combined']['f1']) else "—"
    })

panel_b_df = pd.DataFrame(panel_b_data)
# Sort by Combined F1 score
panel_b_df['sort_key'] = panel_b_df['Combined F1'].apply(lambda x: float(x) if x != "—" else -1)
panel_b_df = panel_b_df.sort_values('sort_key', ascending=False).drop('sort_key', axis=1)

# Add panel indicators
panel_a_df.insert(0, 'Panel', 'A')
panel_b_df.insert(0, 'Panel', 'B')

# Combine panels
combined_df = pd.concat([panel_a_df, panel_b_df], ignore_index=True)

# Save as CSV
combined_df.to_csv(tables_dir / "benchmarking_combined.csv", index=False)

# Create cleaner CSV structure for combined table
combined_csv_data = []

# Add Panel A data
for _, row in panel_a_df.iterrows():
    combined_csv_data.append({
        'Panel': 'A: Approaches',
        'Method': row['Approach'],
        'Joe F1': row['Joe F1'],
        'ACL F1': row['ACL F1'],
        'Combined F1': row['Combined F1'],
        'Audit F1': row['Audit F1']
    })

# Add Panel B data  
for _, row in panel_b_df.iterrows():
    combined_csv_data.append({
        'Panel': 'B: Models',
        'Method': row['Model'],
        'Joe F1': row['Joe F1'],
        'ACL F1': row['ACL F1'],
        'Combined F1': row['Combined F1'],
        'Audit F1': '—'  # Models don't have audit scores - only gpt-4o-mini was used in production
    })

combined_csv_df = pd.DataFrame(combined_csv_data)
combined_csv_df.to_csv(tables_dir / "benchmarking_combined.csv", index=False)

# Create LaTeX table with panels
latex_str = "\\begin{tabular}{lrrrr}\n"
latex_str += "\\toprule\n"

# Panel A
latex_str += "\\multicolumn{5}{l}{\\textbf{Panel A: Approach Comparison (gpt-4o-mini)}} \\\\\n"
latex_str += "\\midrule\n"
latex_str += "Approach & Joe F1 & ACL F1 & Combined F1 & Audit F1 \\\\\n"
latex_str += "\\midrule\n"
for _, row in panel_a_df.iterrows():
    latex_str += f"{row['Approach']} & {row['Joe F1']} & {row['ACL F1']} & {row['Combined F1']} & {row['Audit F1']} \\\\\n"

# Panel B
latex_str += "\\midrule\n"
latex_str += "\\multicolumn{5}{l}{\\textbf{Panel B: Model Comparison (LLM Flagged approach)}} \\\\\n"
latex_str += "\\midrule\n"
latex_str += "Model & Joe F1 & ACL F1 & Combined F1 & \\\\\n"
latex_str += "\\midrule\n"
for _, row in panel_b_df.iterrows():
    latex_str += f"{row['Model']} & {row['Joe F1']} & {row['ACL F1']} & {row['Combined F1']} & \\\\\n"

latex_str += "\\bottomrule\n"
latex_str += "\\end{tabular}"

# Save LaTeX
with open(tables_dir / "benchmarking_combined.tex", 'w') as f:
    f.write(latex_str)

# Save description
with open(tables_dir / "benchmarking_combined.txt", 'w') as f:
    f.write("Combined benchmarking table with Panel A showing approach comparison and Panel B showing model comparison.\n")
    f.write("Generated by: src/post_query/analysis/benchmarking_analysis.py")

print("Combined table saved to data/outputs/tables/benchmarking_combined.csv")

#%%
# Keep approach comparison table for backward compatibility  
print("\nCreating approach comparison table...")

# Use gpt-4o-mini as the primary model (most data available)
if primary_model in all_results:
    approach_data = []
    
    for approach_name in ['llm_flagged', 'llm_validation', 'llm_with_followup']:
        results = all_results[primary_model][approach_name]
        
        approach_display = {
            'llm_flagged': 'LLM Flagged',
            'llm_validation': 'LLM Validation',
            'llm_with_followup': 'LLM with Follow-up Analysis'
        }[approach_name]
        
        approach_data.append({
            'Approach': approach_display,
            'Joe F1': results['joe']['f1'],
            'Joe Prec': results['joe']['precision'],
            'Joe Rec': results['joe']['recall'],
            'ACL F1': results['acl']['f1'],
            'ACL Prec': results['acl']['precision'],
            'ACL Rec': results['acl']['recall'],
            'Audit F1': results['audit']['f1'],
            'Audit Prec': results['audit']['precision'],
            'Audit Rec': results['audit']['recall'],
            'Combined F1': results['combined']['f1']
        })
    
    approach_df = pd.DataFrame(approach_data)
    
    # Format numeric columns
    for col in approach_df.columns:
        if col != 'Approach':
            approach_df[col] = approach_df[col].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "—")
    
    # Save full version as CSV
    approach_df.to_csv(tables_dir / "approach_comparison_full.csv", index=False)
    
    # Create simplified version with just F1 scores for main text
    approach_simple = approach_df[['Approach', 'Joe F1', 'ACL F1', 'Audit F1', 'Combined F1']].copy()
    approach_simple.to_csv(tables_dir / "approach_comparison.csv", index=False)
    
    # Save full LaTeX for appendix
    latex_table_full = approach_df.to_latex(index=False, escape=False, column_format='l' + 'r'*10)
    with open(tables_dir / "approach_comparison_full.tex", 'w') as f:
        f.write(latex_table_full)
    
    # Save simplified LaTeX for main text
    latex_table = approach_simple.to_latex(index=False, escape=False, column_format='lrrrr')
    with open(tables_dir / "approach_comparison.tex", 'w') as f:
        f.write(latex_table)
    
    # Save description
    with open(tables_dir / "approach_comparison.txt", 'w') as f:
        f.write(f"Comparison of different scoring approaches for {primary_model}.\n")
        f.write("Generated by: src/post_query/analysis/benchmarking_analysis.py")
    
    print("Table 2 saved to data/outputs/tables/approach_comparison.csv")

#%%
# Create Table 3: Human Audit Validation Stages
print("\nCreating Table 3: Human Audit Validation Stages...")

if primary_model in all_results:
    audit_stages_data = []
    
    for approach_name in ['llm_flagged', 'llm_validation', 'llm_with_followup']:
        results = all_results[primary_model][approach_name]['audit']
        
        approach_display = {
            'llm_flagged': 'LLM Flagged',
            'llm_validation': 'LLM Validation',
            'llm_with_followup': 'LLM with Follow-up Analysis'
        }[approach_name]
        
        if results['n'] > 0:
            audit_stages_data.append({
                'Stage': approach_display,
                'Flagged': results['tp'] + results['fp'],
                'True Positives': results['tp'],
                'False Positives': results['fp'],
                'Precision': f"{results['precision']:.3f}",
                'Recall': f"{results['recall']:.3f}"
            })
    
    audit_stages_df = pd.DataFrame(audit_stages_data)
    
    # Save as CSV
    audit_stages_df.to_csv(tables_dir / "human_audit_validation.csv", index=False)
    
    # Save as LaTeX
    latex_table = audit_stages_df.to_latex(index=False, escape=False, column_format='lrrrrr')
    with open(tables_dir / "human_audit_validation.tex", 'w') as f:
        f.write(latex_table)
    
    # Save description
    with open(tables_dir / "human_audit_validation.txt", 'w') as f:
        f.write("Human audit performance at different validation stages.\n")
        f.write("Generated by: src/post_query/analysis/benchmarking_analysis.py")
    
    print("Table 3 saved to data/outputs/tables/human_audit_validation.csv")

#%%
# Create YAML summary statistics
print("\nCreating YAML summary statistics...")

# Find best performing model and approach
best_f1 = 0
best_model = None
best_approach = None

for model_name, model_results in all_results.items():
    for approach_name, approach_results in model_results.items():
        current_f1 = approach_results['combined']['f1']
        if pd.notna(current_f1) and current_f1 > best_f1:
            best_f1 = current_f1
            best_model = model_name
            best_approach = approach_name

# Get detailed stats for best configuration
if best_model and best_approach:
    best_results = all_results[best_model][best_approach]

# Calculate summary statistics
summary_stats = {
    'test_set': {
        'total_transcripts': int(len(human_ratings)),
        'joe_rated': int(human_ratings['joe_binary'].notna().sum()),
        'acl_rated': int(human_ratings['acl_binary'].notna().sum()),
        'combined_rated': int(human_ratings['combined_binary'].notna().sum()),
        'human_audit': int(len(human_audit)),
        'human_audit_true': int((human_audit['audit_binary'] == 1).sum()),
        'human_audit_false': int((human_audit['audit_binary'] == 0).sum())
    },
    
    'model_comparison': {
        'models_tested': len(available_models),
        'best_model': best_model if best_model else "N/A",
        'worst_model': panel_b_df.iloc[-1]['Model'] if len(panel_b_df) > 0 else "N/A"
    }
}

# Add best performance metrics if available
if best_model and best_approach:
    summary_stats['best_performance'] = {
        'model': best_model,
        'approach': best_approach,
        'f1_score': float(best_results['combined']['f1']),
        'precision': float(best_results['combined']['precision']),
        'recall': float(best_results['combined']['recall']),
        'specificity': float(best_results['combined']['specificity'])
    }

# Add approach comparison for primary model
if primary_model in all_results:
    summary_stats['approach_comparison'] = {
        'llm_flagged_f1': float(all_results[primary_model]['llm_flagged']['combined']['f1']),
        'llm_validation_f1': float(all_results[primary_model]['llm_validation']['combined']['f1']),
        'llm_with_followup_f1': float(all_results[primary_model]['llm_with_followup']['combined']['f1']) if pd.notna(all_results[primary_model]['llm_with_followup']['combined']['f1']) else 0.0
    }
    
    # Calculate improvement
    min_f1 = min(summary_stats['approach_comparison'].values())
    max_f1 = max(summary_stats['approach_comparison'].values())
    if min_f1 > 0:
        summary_stats['approach_comparison']['improvement_pct'] = float((max_f1 - min_f1) / min_f1 * 100)
    else:
        summary_stats['approach_comparison']['improvement_pct'] = 0.0

# Add human audit performance
if primary_model in all_results:
    audit_flagged = all_results[primary_model]['llm_flagged']['audit']
    audit_with_followup = all_results[primary_model]['llm_with_followup']['audit']
    
    if audit_flagged['n'] > 0:
        summary_stats['human_audit_performance'] = {
            'flagged_precision': float(audit_flagged['precision']),
            'flagged_recall': float(audit_flagged['recall']),
            'with_followup_precision': float(audit_with_followup['precision']) if pd.notna(audit_with_followup['precision']) else float(audit_flagged['precision']),
            'with_followup_recall': float(audit_with_followup['recall']) if pd.notna(audit_with_followup['recall']) else float(audit_flagged['recall']),
            'false_positives_removed': int(audit_flagged['fp'] - audit_with_followup['fp']) if pd.notna(audit_with_followup['fp']) else 0
        }

# Save YAML
yaml_path = yaml_dir / "benchmarking.yaml"
with open(yaml_path, 'w') as f:
    yaml.dump(summary_stats, f, default_flow_style=False, sort_keys=False)

print(f"Summary statistics saved to {yaml_path}")

#%%
# Print summary
print("\n" + "="*60)
print("BENCHMARKING ANALYSIS COMPLETE")
print("="*60)
print(f"\nTest Set Overview:")
print(f"  Total transcripts: {summary_stats['test_set']['total_transcripts']}")
print(f"  Joe's ratings: {summary_stats['test_set']['joe_rated']}")
print(f"  ACL's ratings: {summary_stats['test_set']['acl_rated']}")
print(f"  Human audit: {summary_stats['test_set']['human_audit']}")

if 'best_performance' in summary_stats:
    print(f"\nBest Performance:")
    print(f"  Model: {summary_stats['best_performance']['model']}")
    print(f"  Approach: {summary_stats['best_performance']['approach']}")
    print(f"  F1 Score: {summary_stats['best_performance']['f1_score']:.3f}")
    print(f"  Precision: {summary_stats['best_performance']['precision']:.3f}")
    print(f"  Recall: {summary_stats['best_performance']['recall']:.3f}")

if 'approach_comparison' in summary_stats:
    print(f"\nApproach Comparison ({primary_model}):")
    print(f"  LLM Flagged F1: {summary_stats['approach_comparison']['llm_flagged_f1']:.3f}")
    print(f"  LLM Validation F1: {summary_stats['approach_comparison']['llm_validation_f1']:.3f}")
    print(f"  LLM with Follow-up F1: {summary_stats['approach_comparison']['llm_with_followup_f1']:.3f}")
    if 'improvement_pct' in summary_stats['approach_comparison']:
        print(f"  Improvement: {summary_stats['approach_comparison']['improvement_pct']:.1f}%")

print("\nOutput files created:")
print("  - data/outputs/tables/model_performance.csv")
print("  - data/outputs/tables/approach_comparison.csv")
print("  - data/outputs/tables/human_audit_validation.csv")
print("  - data/yaml/benchmarking.yaml")
