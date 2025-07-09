# Modules Directory

This directory contains core Python modules that provide shared functionality across the project.

## Module Overview

### llm.py
Interface for OpenAI API interactions:
- `LLMQuery` class for running prompts on transcripts
- Response format handling with Pydantic models
- Token counting and cost tracking
- Structured output support for compatible models

### batch_processor.py
Handles OpenAI Batch API operations:
- Create batch input files
- Submit and monitor batch jobs
- Process batch results
- Error handling and retry logic

### queries_db.py
Database operations for query results:
- Insert and fetch query results
- Export functionality
- Analysis query management
- Score and excerpt extraction utilities

### db_manager.py
High-level database management:
- Database initialization
- Google Drive sync operations
- Database verification
- Backup functionality

### capiq.py
Capital IQ data interface:
- Fetch earnings call transcripts
- WRDS database connections
- Transcript formatting utilities

### utils.py
General utility functions:
- Score extraction from various response formats
- Token size calculations
- Data processing helpers
- Configuration management

## Usage Examples

### Running a Query
```python
from modules.llm import LLMQuery

llm = LLMQuery()
responses = llm.apply_prompt_to_transcripts("SimpleCapacityV8.1.1", [12345, 67890])
```

### Batch Processing
```python
from modules.batch_processor import BatchProcessor

processor = BatchProcessor()
batch_id = processor.submit_batch("input.jsonl")
status = processor.check_batch_status(batch_id)
```

### Database Operations
```python
from modules.queries_db import fetch_all_queries, export_to_csv

# Get all queries as DataFrame
df = fetch_all_queries()

# Export to CSV
export_to_csv("output.csv", prompt_names=["SimpleCapacityV8.1.1"])
```

## Configuration

Modules use environment variables from `.env`:
- `OPENAI_API_KEY` - Required for LLM operations
- `WRDS_USERNAME` / `WRDS_PASSWORD` - For Capital IQ access
- `ROOT` - Project root directory

## Error Handling

All modules include comprehensive error handling:
- API failures with retry logic
- Database connection issues
- Missing data graceful handling
- Detailed logging for debugging