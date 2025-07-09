# Naming Conventions Guide

This guide establishes naming conventions for the collusion-llm project to ensure consistency across the codebase.

## File Naming

### Rule: Use snake_case (underscores) for all file names

**Examples:**
- ✅ `calculate_f1_scores.py`
- ✅ `batch_tracker.csv`
- ✅ `companies_transcripts.csv`
- ❌ `calculate-f1-scores.py`
- ❌ `batch-tracker.csv`

**Rationale:** Consistent with Python naming conventions and improves compatibility across different operating systems.

## Database Column Naming

### Rule: Use lowercase without underscores for key identifiers to match WRDS/CapIQ

**Key identifiers:**
- `transcriptid` (not `transcript_id`)
- `companyid` (not `company_id`)
- `gvkey` (not `gv_key`)

**Other columns:** Use snake_case
- `prompt_name`
- `model_name`
- `input_tokens`
- `output_tokens`

**Rationale:** Maintaining consistency with WRDS/CapIQ data sources prevents the need for constant column renaming when importing/exporting data.

## Python Variable Naming

### Rule: Use snake_case for all variables and function names

**Examples:**
```python
# Variables
transcript_id = 12345  # Local variable can use underscore
company_ids = [1, 2, 3]  # Plural for lists
max_tokens = 2000

# Function names
def calculate_f1_score():
    pass

def get_transcript_data():
    pass
```

**Exception:** When interfacing with the database, use the database column names:
```python
# Database operations
cursor.execute("SELECT transcriptid FROM queries")  # Use 'transcriptid'
insert_query_result(transcriptid=12345, ...)  # Parameter matches DB column
```

## Class Naming

### Rule: Use PascalCase for class names

**Examples:**
- `LLMQuery`
- `BatchProcessor`
- `ResponseBinary`
- `SimpleExcerptAnalyzer`

## Constants

### Rule: Use UPPER_SNAKE_CASE for constants

**Examples:**
- `DATABASE_PATH`
- `OPENAI_API_KEY`
- `MAX_BATCH_SIZE`
- `DEFAULT_TEMPERATURE`

## Import/Export Consistency

### Rule: Maintain column names when importing/exporting data

- When importing from WRDS/CapIQ: Keep `transcriptid`, `companyid`
- When exporting for analysis: Keep the same naming to maintain consistency
- Avoid renaming columns unless absolutely necessary

## Directory Structure

### Rule: Use lowercase with underscores for directory names

**Examples:**
- `pre_query/`
- `post_query/`
- `query_submission/`
- `data_preparation/`

## Summary Table

| Context | Example | Rule |
|---------|---------|------|
| Python files | `calculate_f1_scores.py` | snake_case |
| Data files | `companies_transcripts.csv` | snake_case |
| Database columns (IDs) | `transcriptid`, `companyid` | lowercase, no underscore |
| Database columns (other) | `prompt_name`, `input_tokens` | snake_case |
| Python variables | `transcript_id`, `max_tokens` | snake_case |
| Python functions | `get_transcript_data()` | snake_case |
| Python classes | `BatchProcessor` | PascalCase |
| Python constants | `DATABASE_PATH` | UPPER_SNAKE_CASE |
| Directories | `query_submission/` | lowercase, underscores |

## Migration Notes

As of the refactoring completed on 2025-07-09:
- All files with hyphens have been renamed to use underscores
- Database schema uses `transcriptid` and `companyid` (no underscores)
- All Python code has been updated to use these conventions
- Column renaming workarounds have been removed

When adding new code, please follow these conventions to maintain consistency.