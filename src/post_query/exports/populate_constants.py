#!/usr/bin/env python3
"""
Script to convert YAML files to LaTeX constants.

Takes all YAML files from output/yaml/ and converts them to text files in output/constants/
that can be imported into LaTeX using \\input{../output/constants/path/to/field.txt}

The script processes different data types:
- Numbers: saved as _int.txt (with commas), _float.txt (2 decimals), _percentage.txt (escaped %), _scientific.txt
- Dates: saved as original string and _date.txt (formatted as "February 2nd, 2002")
- Strings: copied literally
"""

import os
import yaml
from pathlib import Path
from datetime import datetime
import re
from typing import Any, Dict, Union
import config

def format_number_with_commas(num: Union[int, float]) -> str:
    """Format number with thousands separators."""
    return f"{num:,}"


def format_float_two_decimals(num: float) -> str:
    """Format float with two decimal places and commas."""
    return f"{num:,.2f}"


def format_percentage(num: float) -> str:
    """Format number as percentage with escaped % for LaTeX."""
    return f"{num:.2f}\\%"


def format_scientific(num: Union[int, float]) -> str:
    """Format number in scientific notation."""
    return f"{num:.2e}"


def format_date_string(date_str: str) -> str:
    """Convert date string (YYYY-MM-DD) to formatted date (Month DDth, YYYY)."""
    try:
        # Parse the date string
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Get the day with ordinal suffix
        day = date_obj.day
        if 10 <= day % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
        
        # Format the date
        return date_obj.strftime(f'%B {day}{suffix}, %Y')
    except ValueError:
        # If parsing fails, return the original string
        return date_str


def is_date_string(value: str) -> bool:
    """Check if a string looks like a date (YYYY-MM-DD format)."""
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    return bool(re.match(date_pattern, value))


def is_integer(value: Union[int, float]) -> bool:
    """Check if a number is effectively an integer."""
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return value.is_integer()
    return False


def create_constants_for_value(base_path: Path, field_name: str, value: Any) -> None:
    """Create constant files for a single value based on its type."""
    base_path.mkdir(parents=True, exist_ok=True)
    
    if isinstance(value, (int, float)):
        # For numbers, create multiple format files
        if is_integer(value):
            # Integer formats
            int_val = int(value)
            with open(base_path / f"{field_name}_int.txt", 'w') as f:
                f.write(format_number_with_commas(int_val))
        
        # Float format (always create for numbers)
        with open(base_path / f"{field_name}_float.txt", 'w') as f:
            f.write(format_float_two_decimals(float(value)))
        
        # Percentage format
        with open(base_path / f"{field_name}_percentage.txt", 'w') as f:
            f.write(format_percentage(float(value)))
        
        # Scientific format
        with open(base_path / f"{field_name}_scientific.txt", 'w') as f:
            f.write(format_scientific(value))
    
    elif isinstance(value, str):
        if is_date_string(value):
            # Date string - create both original and formatted versions
            with open(base_path / f"{field_name}.txt", 'w') as f:
                f.write(value)
            
            with open(base_path / f"{field_name}_date.txt", 'w') as f:
                f.write(format_date_string(value))
        else:
            # Regular string - just copy literally
            with open(base_path / f"{field_name}.txt", 'w') as f:
                f.write(str(value))
    
    else:
        # For other types (bool, None, etc.), convert to string
        with open(base_path / f"{field_name}.txt", 'w') as f:
            f.write(str(value))


def process_yaml_data(data: Dict[str, Any], base_constants_path: Path, yaml_filename: str) -> None:
    """Process YAML data recursively and create constant files."""
    # Remove .yaml extension from filename for directory name
    yaml_base_name = yaml_filename.replace('.yaml', '').replace('.yml', '')
    yaml_dir = base_constants_path / yaml_base_name
    
    def process_nested(nested_data: Dict[str, Any], current_path: Path) -> None:
        """Recursively process nested dictionaries."""
        for key, value in nested_data.items():
            if isinstance(value, dict):
                # Create subdirectory for nested data
                nested_path = current_path / key
                process_nested(value, nested_path)
            else:
                # Create constant files for this value
                create_constants_for_value(current_path, key, value)
    
    process_nested(data, yaml_dir)


def main():
    """Main function to process all YAML files."""
    # Set up paths
    yaml_dir = Path(os.path.join(config.DATA_DIR, 'yaml'))
    constants_dir = Path(os.path.join(config.DATA_DIR, 'constants'))
    
    # Create constants directory if it doesn't exist
    constants_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Processing YAML files from: {yaml_dir}")
    print(f"Outputting constants to: {constants_dir}")
    
    # Process each YAML file
    yaml_files = list(yaml_dir.glob("*.yaml")) + list(yaml_dir.glob("*.yml"))
    
    if not yaml_files:
        print("No YAML files found in the yaml directory.")
        return
    
    for yaml_file in yaml_files:
        print(f"Processing: {yaml_file.name}")
        
        try:
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)
            
            if data is None:
                print(f"  Warning: {yaml_file.name} is empty or invalid")
                continue
            
            process_yaml_data(data, constants_dir, yaml_file.name)
            print(f"  ✓ Created constants for {yaml_file.name}")
            
        except Exception as e:
            print(f"  ✗ Error processing {yaml_file.name}: {e}")
    
    print("\nDone! Constants are ready for LaTeX import.")
    print("Usage in LaTeX: \\newcommand{\\data}[1]{\\input{../output/constants/#1.txt}\\unskip}")
    print("Example: \\data{transcript-stats/n_transcripts_int}")


if __name__ == "__main__":
    main()
