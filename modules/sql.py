import config
import pandas as pd
import modules.capiq as capiq
import modules.gpt as gpt
import textwrap
import modules.sql as sql
import modules.utils as utils
import sqlite3
import json
from datetime import datetime
import numpy as np

def initialize_prompt_output_log():
    # Define the database path
    db_path = f'{config.ROOT}/data/PromptOutputLog.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create the table with the static columns only
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS PromptOutputLog (
            query_id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT NOT NULL,
            run INTEGER NOT NULL,
            t_id TEXT NOT NULL,
            date_time TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
