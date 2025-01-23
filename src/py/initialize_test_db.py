import pandas as pd
import sqlite3
import config
import os

# Make database from the initial Excel file
excel_file_path = f'{config.ROOT}/data/testset.xlsx'
# excel_file_path = '/Users/ioanrusu/Desktop/collusion prediction project/testset.xlsx'

# Construct the database path in the same directory as the Excel file
database_path = os.path.join(os.path.dirname(excel_file_path), 'testset.db')
# database_path = '/Users/ioanrusu/Desktop/collusion prediction project/testset.db'

# Name of the table to create in the database
table_name = 'prompt_outputs'

try:
    # Step 1: Read the Excel file into a DataFrame
    print("Reading Excel file...")
    # Specify the engine as 'openpyxl' for reading .xlsx files
    df = pd.read_excel(excel_file_path, engine='openpyxl')
    print("Excel file read successfully.")

    # Step 2: Connect to SQLite database (creates the database file if it doesn't exist)
    print(f"Connecting to database at '{database_path}'...")
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Step 3: Write the DataFrame to an SQL table
    print(f"Creating table '{table_name}' and inserting data...")
    df.to_sql(name=table_name, con=conn, if_exists='replace', index=False)
    print(f"Table '{table_name}' created successfully in database '{database_path}'.")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    # Step 4: Close the database connection
    if 'conn' in locals():
        conn.close()
        print("Database connection closed.")