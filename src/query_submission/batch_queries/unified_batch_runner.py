#!/usr/bin/env python3
"""
Unified batch runner that delegates to appropriate batch processor based on scope.
This is a temporary solution until we can properly consolidate the batch processors.

Usage:
    # For specific companies
    python unified_batch_runner.py --companies "123,456" --prompt "PromptName" --operation all
    
    # For all companies
    python unified_batch_runner.py --all --prompt "PromptName" --operation create
"""

import argparse
import subprocess
import sys
import os

def main():
    parser = argparse.ArgumentParser(description='Unified batch runner for LLM queries')
    
    # Mutually exclusive group for scope
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument('--companies', type=str, help='Comma-separated list of company IDs')
    scope.add_argument('--all', action='store_true', help='Process all companies')
    
    parser.add_argument('--prompt', type=str, required=True, help='Name of the prompt to use')
    parser.add_argument('--operation', type=str, default='all',
                       choices=['create', 'submit', 'status', 'process', 'error', 'models', 'all'],
                       help='Operation to perform')
    parser.add_argument('--batch-id', type=str, help='Batch ID for status/process operations')
    parser.add_argument('--input-file', type=str, help='Input file for submit operation')
    
    args = parser.parse_args()
    
    # Get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    if args.companies:
        # Use batch_processor_runner for specific companies
        print(f"Processing specific companies: {args.companies}")
        cmd = [
            sys.executable,
            os.path.join(script_dir, 'batch_processor_runner.py'),
            args.companies,
            args.prompt,
            '--operation', args.operation
        ]
        
        if args.batch_id:
            cmd.extend(['--batch-id', args.batch_id])
        if args.input_file:
            cmd.extend(['--input-file', args.input_file])
            
    else:  # args.all
        # Use big_batch_runner for all companies
        print(f"Processing all companies with prompt: {args.prompt}")
        cmd = [
            sys.executable,
            os.path.join(script_dir, 'big_batch_runner.py'),
            args.prompt,
            args.operation
        ]
    
    # Execute the appropriate script
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Error running batch processor: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())