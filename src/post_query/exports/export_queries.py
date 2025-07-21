"""
Script to export the queries database to CSV.

Options:
    --output OUTPUT_PATH    Path where to save the CSV file
    --prompts PROMPT1 ...   List of prompt names to filter by
    --latest-only          Only export the latest query result for each transcript
"""

import sys
import argparse
from modules.queries_db import export_to_csv

def main():
    parser = argparse.ArgumentParser(description='Export queries database to CSV')
    parser.add_argument('--output', help='Path where to save the CSV file')
    parser.add_argument('--prompts', nargs='+', help='List of prompt names to filter by')
    parser.add_argument('--latest-only', action='store_true', help='Only export the latest query result for each transcript')
    
    args = parser.parse_args()
    
    # Export to CSV with the specified options
    export_to_csv(
        output_path=args.output,
        prompt_names=args.prompts,
        latest_only=args.latest_only
    )

if __name__ == "__main__":
    main() 