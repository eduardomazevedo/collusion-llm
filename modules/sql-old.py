import sqlite3
import numpy as np
import pandas as pd

def get_max_iteration(db_path, table_name, prompt_name):
    """
    Get the max iteration number for a given prompt.
    
    Args:
    - db_path (str): Path to the SQLite database.
    - table_name (str): Name of the table to check for existing columns.
    - prompt_name (str): Name of the prompt.
    
    Returns:
    - int: The max iteration number.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [info[1] for info in cursor.fetchall()]
    
    max_iteration = 0
    for column in columns:
        if column.startswith(prompt_name):
            try:
                iteration = int(column.split('_')[-1])
                if iteration > max_iteration:
                    max_iteration = iteration
            except ValueError:
                continue
    
    conn.close()
    return max_iteration

def add_columns_for_prompt(db_path, table_name, prompt_name, variables):
    """
    Add columns to the database for the variables that the prompt will output.
    
    Args:
    - db_path (str): Path to the SQLite database.
    - table_name (str): Name of the table to add columns to.
    - prompt_name (str): Name of the prompt.
    - variables (list): List of variable names that the prompt will output.
    """
    iteration = get_max_iteration(db_path, table_name, prompt_name) + 1
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for var in variables:
        column_name = f"{prompt_name}_{var}_{iteration}"
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT")
    
    conn.commit()
    conn.close()

def populate_columns_from_response(db_path, table_name, prompt_name, response_dict):
    """
    Populate the new columns in the database with the variables from the response dictionary.
    
    Args:
    - db_path (str): Path to the SQLite database.
    - table_name (str): Name of the table to populate columns in.
    - prompt_name (str): Name of the prompt.
    - response_dict (dict): Dictionary containing the response data.
    """
    iteration = get_max_iteration(db_path, table_name, prompt_name)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for transcript_id, response in response_dict.items():
        for var, value in response.items():
            column_name = f"{prompt_name}_{var}_{iteration}"
            cursor.execute(f"""
                UPDATE {table_name}
                SET {column_name} = ?
                WHERE transcriptid = ?
            """, (value, transcript_id))
    
    conn.commit()
    conn.close()

def get_transcript_ids(db_path, table_name):
    """
    Get a list of transcript id values from the database.
    
    Args:
    - db_path (str): Path to the SQLite database.
    - table_name (str): Name of the table to query.
    
    Returns:
    - list: List of transcript id values.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = f'SELECT transcriptid FROM "{table_name}"'
    cursor.execute(query)
    transcript_ids = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return transcript_ids

def remove_columns(db_path, table_name, columns_to_remove):
    """
    Remove specific columns from the database table.
    
    Args:
    - db_path (str): Path to the SQLite database.
    - table_name (str): Name of the table to modify.
    - columns_to_remove (list): List of column names to remove.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get the current columns in the table
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [info[1] for info in cursor.fetchall()]
    
    # Filter out the columns to remove
    columns_to_keep = [col for col in columns if col not in columns_to_remove]
    
    # Create a new table with the desired schema
    columns_str = ", ".join(columns_to_keep)
    cursor.execute(f"CREATE TABLE {table_name}_new AS SELECT {columns_str} FROM {table_name}")
    
    # Drop the old table
    cursor.execute(f"DROP TABLE {table_name}")
    
    # Rename the new table to the original table name
    cursor.execute(f"ALTER TABLE {table_name}_new RENAME TO {table_name}")
    
    conn.commit()
    conn.close()

def export_table_to_csv(db_path, table_name, csv_path):
    """
    Export a database table to a CSV file.
    
    Args:
    - db_path (str): Path to the SQLite database.
    - table_name (str): Name of the table to export.
    - csv_path (str): Path to the CSV file to create.
    """
    conn = sqlite3.connect(db_path)
    
    # Read the table into a pandas DataFrame
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    
    # Export the DataFrame to a CSV file
    df.to_csv(csv_path, index=False)
    
    conn.close()

def calculate_loss(db_path, table_name, joe_score_column='joe_score'):
    """
    Calculate the MSE loss for all score variables compared to joe_score, including different iterations.
    
    Args:
    - db_path (str): Path to the SQLite database.
    - table_name (str): Name of the table to query.
    - joe_score_column (str): Name of the column containing joe_score.
    
    Returns:
    - dict: Dictionary with prompt names and iterations as keys and their corresponding loss as values.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get the current columns in the table
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [info[1] for info in cursor.fetchall()]
    
    # Filter out the columns that are score variables
    score_columns = [col for col in columns if col != joe_score_column and 'score' in col.lower()]
    
    # Read the table into a pandas DataFrame
    df = pd.read_sql_query(f"SELECT {joe_score_column}, {', '.join(score_columns)} FROM {table_name}", conn)
    
    conn.close()
    
    # Ensure joe_score_column is numeric
    df[joe_score_column] = pd.to_numeric(df[joe_score_column], errors='coerce')
    
    # Calculate the MSE loss for each score variable and iteration
    losses = {}
    for col in score_columns:
        # Ensure the column is numeric
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Drop rows with NaN values in either joe_score_column or the current column
        valid_df = df.dropna(subset=[joe_score_column, col])
        
        if not valid_df.empty:
            prompt_name = col.split('_')[0]
            iteration = col.split('_')[-1]
            key = f"{prompt_name}_{iteration}"
            
            mse = ((valid_df[col] - valid_df[joe_score_column]) ** 2).mean()
            
            if key in losses:
                losses[key].append(mse)
            else:
                losses[key] = [mse]
    
    # Average the losses for each prompt and iteration
    for key in losses:
        losses[key] = float(sum(losses[key]) / len(losses[key]))
    
    return losses

