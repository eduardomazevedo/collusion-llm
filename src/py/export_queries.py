"""
Script to export the queries database to CSV.

Usage:
    python src/py/export_queries.py [output_path]
"""

import sys
from modules.queries_db import export_to_csv

def main():
    # Get output path from command line argument if provided
    output_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Export to CSV
    export_to_csv(output_path)

if __name__ == "__main__":
    main() 