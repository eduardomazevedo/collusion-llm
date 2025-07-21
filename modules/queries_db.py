import config
import sqlite3
from datetime import datetime, timezone
import pandas as pd
import json
from modules.utils import extract_invalid_response

# Open a persistent connection when the module loads
conn = sqlite3.connect(config.DATABASE_PATH)
cursor = conn.cursor()

def create_analysis_table():
    """Create the analysis table if it doesn't exist."""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_queries (
            analysis_query_id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_query_id INTEGER NOT NULL,
            prompt_name TEXT NOT NULL,
            date TEXT NOT NULL,
            response TEXT NOT NULL,
            LLM_provider TEXT,
            model_name TEXT,
            call_type TEXT,
            temperature REAL,
            max_response INTEGER,
            input_tokens INTEGER,
            output_tokens INTEGER,
            FOREIGN KEY (reference_query_id) REFERENCES queries (query_id)
        )
    ''')
    conn.commit()

def insert_analysis_result(
    reference_query_id: int,
    prompt_name: str,
    response: str,
    llm_provider: str,
    model_name: str,
    call_type: str,
    temperature: float,
    max_response: int,
    input_tokens: int,
    output_tokens: int
):
    """
    Insert a new analysis result into the analysis_queries table.
    
    Args:
        reference_query_id: ID of the original query from the queries table
        prompt_name: Name of the analysis prompt used
        response: The LLM response
        llm_provider: The LLM provider (e.g. "openai")
        model_name: The model name (e.g. "o4-mini-2025-04-16")
        call_type: Type of call ("single" or "batch")
        temperature: Temperature setting used
        max_response: Maximum response tokens
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens used
    """
    # Ensure the analysis table exists
    create_analysis_table()
    
    cursor.execute(
        """
        INSERT INTO analysis_queries (
            reference_query_id, prompt_name, date, response,
            LLM_provider, model_name, call_type,
            temperature, max_response, input_tokens, output_tokens
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            reference_query_id, prompt_name, datetime.now(timezone.utc).isoformat(), response,
            llm_provider, model_name, call_type,
            temperature, max_response, input_tokens, output_tokens
        ),
    )
    conn.commit()

def insert_query_result(
    prompt_name: str,
    transcriptid: int,
    response: str,
    llm_provider: str,
    model_name: str,
    call_type: str,
    temperature: float,
    max_response: int,
    input_tokens: int,
    output_tokens: int
):
    """
    Insert a new query result into the database using an open connection.
    
    Args:
        prompt_name: Name of the prompt used
        transcriptid: ID of the transcript
        response: The LLM response
        llm_provider: The LLM provider (e.g. "openai")
        model_name: The model name (e.g. "o4-mini-2025-04-16")
        call_type: Type of call ("single" or "batch")
        temperature: Temperature setting used
        max_response: Maximum response tokens
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens used
    """
    cursor.execute(
        """
        INSERT INTO queries (
            prompt_name, transcriptid, date, response,
            LLM_provider, model_name, call_type,
            temperature, max_response, input_tokens, output_tokens
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            prompt_name, transcriptid, datetime.now(timezone.utc).isoformat(), response,
            llm_provider, model_name, call_type,
            temperature, max_response, input_tokens, output_tokens
        ),
    )
    conn.commit()

def fetch_all_queries():
    """Fetch all query results and return a pandas DataFrame."""
    cursor.execute("SELECT * FROM queries")
    
    rows = cursor.fetchall()
    columns = [
        'query_id', 'prompt_name', 'transcriptid', 'date', 'response',
        'LLM_provider', 'model_name', 'call_type',
        'temperature', 'max_response', 'input_tokens', 'output_tokens'
    ]
    return pd.DataFrame(rows, columns=columns)

def fetch_queries_by_prompts(prompt_names: list[str]):
    """
    Fetch query results for specific prompt names and return a pandas DataFrame.
    
    Args:
        prompt_names: List of prompt names to filter by
    """
    placeholders = ','.join(['?'] * len(prompt_names))
    cursor.execute(f"SELECT * FROM queries WHERE prompt_name IN ({placeholders})", prompt_names)
    
    rows = cursor.fetchall()
    columns = [
        'query_id', 'prompt_name', 'transcriptid', 'date', 'response',
        'LLM_provider', 'model_name', 'call_type',
        'temperature', 'max_response', 'input_tokens', 'output_tokens'
    ]
    return pd.DataFrame(rows, columns=columns)

def get_latest_queries(df: pd.DataFrame = None):
    """
    Get the latest query result for each transcript from the given DataFrame.
    If no DataFrame is provided, uses all queries.
    
    Args:
        df: Optional DataFrame to filter from. If None, uses all queries.
    """
    if df is None:
        df = fetch_all_queries()
    
    # Convert date column to datetime for proper sorting
    df['date'] = pd.to_datetime(df['date'])
    
    # Sort by date in descending order and keep first occurrence (latest) for each transcript
    return df.sort_values('date', ascending=False).drop_duplicates(subset=['transcriptid', 'prompt_name'], keep='first')

def export_to_csv(output_path: str = None, prompt_names: list[str] = None, latest_only: bool = False):
    """
    Export the queries database to a CSV file with optional filtering.
    
    Args:
        output_path: Path where to save the CSV file. If None, uses a default path
                    in the output directory with timestamp.
        prompt_names: Optional list of prompt names to filter by. If None, exports all queries.
        latest_only: If True, only exports the latest query result for each transcript.
    
    Returns:
        Path to the exported CSV file
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"data/outputs/visualize_db_{timestamp}.csv"
    
    # Fetch queries based on filters
    if prompt_names:
        df = fetch_queries_by_prompts(prompt_names)
    else:
        df = fetch_all_queries()
    
    # Get latest entries if requested
    if latest_only:
        df = get_latest_queries(df)
    
    # Create output directory if it doesn't exist
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save to CSV
    df.to_csv(output_path, index=False)
    print(f"Exported {len(df)} queries to {output_path}")
    
    return output_path

def close_db():
    """Close the database connection. Call this when shutting down."""
    conn.close()

def extract_score_from_response(response: str) -> int:
    """
    Extract score from a response string, handling both valid JSON and invalid formats.
    
    Args:
        response: The response string from the database
        
    Returns:
        int: The extracted score, or None if not found
    """
    try:
        # Try to parse as valid JSON first
        response_dict = json.loads(response)
        if isinstance(response_dict, dict):
            return response_dict.get('score')
    except json.JSONDecodeError:
        # If JSON parsing fails, try to extract using helper function
        try:
            extracted = extract_invalid_response(response, ['score'])
            return extracted.get('score')
        except:
            pass
    
    return None

def extract_excerpts_from_response(response: str) -> str:
    """
    Extract excerpts from a response string, handling both valid JSON and invalid formats.
    
    Args:
        response: The response string from the database
        
    Returns:
        str: The extracted excerpts as a string, or empty string if not found
    """
    try:
        # Try to parse as valid JSON first
        response_dict = json.loads(response)
        if isinstance(response_dict, dict):
            excerpts = response_dict.get('excerpts', [])
            if isinstance(excerpts, list):
                return '; '.join(excerpts)
            return str(excerpts)
    except json.JSONDecodeError:
        # If JSON parsing fails, try to extract using helper function
        try:
            extracted = extract_invalid_response(response, ['excerpts'])
            return extracted.get('excerpts', '')
        except:
            pass
    
    return ''

def analyze_queries_above_threshold(
    prompt_name: str,
    analysis_prompt_name: str,
    score_threshold: int,
    llm_query_instance=None
):
    """
    Analyze queries above a certain score threshold using a new analysis prompt.
    
    Args:
        prompt_name: Name of the original prompt used to create entries
        analysis_prompt_name: Name of the new prompt to analyze the outputs
        score_threshold: Minimum score threshold (default: 75)
        llm_query_instance: Optional LLMQuery instance, will create one if not provided
        
    Returns:
        dict: Results of the analysis process
    """
    from modules.llm import LLMQuery
    
    # Create LLM query instance if not provided
    if llm_query_instance is None:
        llm_query_instance = LLMQuery()
    
    # Fetch all queries for the given prompt name
    df = fetch_queries_by_prompts([prompt_name])
    
    if df.empty:
        print(f"No queries found for prompt '{prompt_name}'")
        return {"processed": 0, "above_threshold": 0, "analyzed": 0}
    
    print(f"Found {len(df)} queries for prompt '{prompt_name}'")
    
    # Extract scores and filter above threshold
    df['score'] = df['response'].apply(extract_score_from_response)
    above_threshold_df = df[df['score'] >= score_threshold].copy()
    
    print(f"Found {len(above_threshold_df)} queries with score >= {score_threshold}")
    
    if above_threshold_df.empty:
        print("No queries above threshold to analyze")
        return {"processed": len(df), "above_threshold": 0, "analyzed": 0}
    
    # Process each query above threshold
    analyzed_count = 0
    for _, row in above_threshold_df.iterrows():
        try:
            # Extract excerpts for analysis
            excerpts = extract_excerpts_from_response(row['response'])
            
            if not excerpts.strip():
                print(f"Warning: No excerpts found for query_id {row['query_id']}")
                continue
            
            # Generate analysis using the analysis prompt
            analysis_response, token_info = llm_query_instance.generate_response(
                analysis_prompt_name, excerpts
            )
            
            # Save analysis result to database
            insert_analysis_result(
                reference_query_id=row['query_id'],
                prompt_name=analysis_prompt_name,
                response=analysis_response,
                llm_provider=llm_query_instance.provider,
                model_name=llm_query_instance.model,
                call_type="single",
                temperature=llm_query_instance.temperature,
                max_response=llm_query_instance.max_tokens,
                input_tokens=token_info['input_tokens'],
                output_tokens=token_info['output_tokens']
            )
            
            analyzed_count += 1
            print(f"✓ Analyzed query_id {row['query_id']} (score: {row['score']})")
            
        except Exception as e:
            print(f"Error analyzing query_id {row['query_id']}: {e}")
    
    print(f"\nAnalysis complete: {analyzed_count}/{len(above_threshold_df)} queries analyzed")
    
    return {
        "processed": len(df),
        "above_threshold": len(above_threshold_df),
        "analyzed": analyzed_count
    }

def fetch_analysis_results(analysis_prompt_name: str = None):
    """
    Fetch analysis results from the analysis_queries table.
    
    Args:
        analysis_prompt_name: Optional prompt name to filter by
        
    Returns:
        pandas.DataFrame: Analysis results
    """
    # Ensure the analysis table exists
    create_analysis_table()
    
    if analysis_prompt_name:
        cursor.execute("SELECT * FROM analysis_queries WHERE prompt_name = ?", (analysis_prompt_name,))
    else:
        cursor.execute("SELECT * FROM analysis_queries")
    
    rows = cursor.fetchall()
    columns = [
        'analysis_query_id', 'reference_query_id', 'prompt_name', 'date', 'response',
        'LLM_provider', 'model_name', 'call_type',
        'temperature', 'max_response', 'input_tokens', 'output_tokens'
    ]
    return pd.DataFrame(rows, columns=columns)

def fetch_analysis_with_original_data(analysis_prompt_name: str = None):
    """
    Fetch analysis results joined with original query data.
    
    Args:
        analysis_prompt_name: Optional prompt name to filter by
        
    Returns:
        pandas.DataFrame: Analysis results with original query data
    """
    # Ensure the analysis table exists
    create_analysis_table()
    
    if analysis_prompt_name:
        cursor.execute("""
            SELECT 
                a.analysis_query_id,
                a.reference_query_id,
                a.prompt_name as analysis_prompt_name,
                a.date as analysis_date,
                a.response as analysis_response,
                a.LLM_provider as analysis_llm_provider,
                a.model_name as analysis_model_name,
                q.prompt_name as original_prompt_name,
                q.transcriptid,
                q.date as original_date,
                q.response as original_response
            FROM analysis_queries a
            JOIN queries q ON a.reference_query_id = q.query_id
            WHERE a.prompt_name = ?
        """, (analysis_prompt_name,))
    else:
        cursor.execute("""
            SELECT 
                a.analysis_query_id,
                a.reference_query_id,
                a.prompt_name as analysis_prompt_name,
                a.date as analysis_date,
                a.response as analysis_response,
                a.LLM_provider as analysis_llm_provider,
                a.model_name as analysis_model_name,
                q.prompt_name as original_prompt_name,
                q.transcriptid,
                q.date as original_date,
                q.response as original_response
            FROM analysis_queries a
            JOIN queries q ON a.reference_query_id = q.query_id
        """)
    
    rows = cursor.fetchall()
    columns = [
        'analysis_query_id', 'reference_query_id', 'analysis_prompt_name', 'analysis_date',
        'analysis_response', 'analysis_llm_provider', 'analysis_model_name',
        'original_prompt_name', 'transcriptid', 'original_date', 'original_response'
    ]
    df = pd.DataFrame(rows, columns=columns)
    
    # Add score column by extracting from original response
    df['original_score'] = df['original_response'].apply(extract_score_from_response)
    
    return df

def export_analysis_to_csv(output_path: str = None, analysis_prompt_name: str = None, include_original: bool = True):
    """
    Export analysis results to a CSV file.
    
    Args:
        output_path: Path where to save the CSV file. If None, uses a default path
                    in the output directory with timestamp.
        analysis_prompt_name: Optional analysis prompt name to filter by
        include_original: If True, includes original query data in the export
    
    Returns:
        Path to the exported CSV file
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prompt_suffix = f"_{analysis_prompt_name}" if analysis_prompt_name else ""
        output_path = f"data/outputs/analysis_results{prompt_suffix}_{timestamp}.csv"
    
    # Fetch analysis data
    if include_original:
        df = fetch_analysis_with_original_data(analysis_prompt_name)
    else:
        df = fetch_analysis_results(analysis_prompt_name)
    
    # Create output directory if it doesn't exist
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save to CSV
    df.to_csv(output_path, index=False)
    print(f"Exported {len(df)} analysis results to {output_path}")
    
    return output_path
