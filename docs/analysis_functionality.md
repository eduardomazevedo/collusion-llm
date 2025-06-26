# Analysis Functionality

This document describes the new analysis functionality that allows you to analyze queries above a certain score threshold using separate analysis prompts.

## Overview

The analysis functionality provides a way to:
1. Find queries from a specific prompt that have scores above a threshold
2. Extract excerpts from those responses
3. Analyze the excerpts using a new analysis prompt
4. Store the analysis results in a separate database table

## Database Schema

### New Table: `analysis_queries`

The analysis functionality creates a new table called `analysis_queries` with the following structure:

```sql
CREATE TABLE analysis_queries (
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
```

- `analysis_query_id`: Unique identifier for the analysis entry
- `reference_query_id`: Links back to the original query in the `queries` table
- `prompt_name`: Name of the analysis prompt used
- `date`: When the analysis was performed
- `response`: The analysis response
- Other fields: Metadata about the LLM call (same as in `queries` table)

## Usage

### Command Line Interface

Use the provided script to analyze queries above a threshold:

```bash
python src/py/analyze_high_scores.py <original_prompt_name> <analysis_prompt_name> [--threshold 75] [--export]
```

**Examples:**
```bash
# Analyze queries with score >= 75
python src/py/analyze_high_scores.py SimpleCapacityV8 ExcerptAnalyzer --threshold 75 --export

# Analyze queries with score >= 80
python src/py/analyze_high_scores.py SimpleCapacityV8 DetailedAnalyzer --threshold 80
```

### Programmatic Usage

You can also use the functionality programmatically:

```python
from modules.queries_db import analyze_queries_above_threshold
from modules.llm import LLMQuery

# Initialize LLM query instance
llm_query = LLMQuery()

# Run analysis
results = analyze_queries_above_threshold(
    prompt_name="SimpleCapacityV8",
    analysis_prompt_name="ExcerptAnalyzer",
    score_threshold=75,
    llm_query_instance=llm_query
)

print(f"Processed: {results['processed']}")
print(f"Above threshold: {results['above_threshold']}")
print(f"Analyzed: {results['analyzed']}")
```

## Key Functions

### `analyze_queries_above_threshold()`

Main function that processes queries above a threshold.

**Parameters:**
- `prompt_name`: Name of the original prompt used to create entries
- `analysis_prompt_name`: Name of the new prompt to analyze the outputs
- `score_threshold`: Minimum score threshold (default: 75)
- `llm_query_instance`: Optional LLMQuery instance

**Returns:**
- Dictionary with counts: `{"processed": int, "above_threshold": int, "analyzed": int}`

### `extract_score_from_response()`

Extracts score from a response string, handling both valid JSON and invalid formats.

### `extract_excerpts_from_response()`

Extracts excerpts from a response string, handling both valid JSON and invalid formats.

### `insert_analysis_result()`

Inserts a new analysis result into the `analysis_queries` table.

### `fetch_analysis_results()`

Fetches analysis results from the `analysis_queries` table.

### `fetch_analysis_with_original_data()`

Fetches analysis results joined with original query data.

### `export_analysis_to_csv()`

Exports analysis results to a CSV file.

## Example Workflow

1. **Run initial queries** with a prompt that produces scores and excerpts:
   ```python
   from modules.llm import LLMQuery
   
   llm = LLMQuery()
   responses = llm.apply_prompt_to_transcripts("SimpleCapacityV8", transcript_ids)
   ```

2. **Analyze high-scoring queries**:
   ```python
   from modules.queries_db import analyze_queries_above_threshold
   
   results = analyze_queries_above_threshold(
       prompt_name="SimpleCapacityV8",
       analysis_prompt_name="ExcerptAnalyzer",
       score_threshold=75
   )
   ```

3. **Export results for review**:
   ```python
   from modules.queries_db import export_analysis_to_csv
   
   export_path = export_analysis_to_csv(
       analysis_prompt_name="ExcerptAnalyzer",
       include_original=True
   )
   ```

4. **View analysis statistics**:
   ```python
   from modules.queries_db import fetch_analysis_with_original_data
   
   df = fetch_analysis_with_original_data("ExcerptAnalyzer")
   print(f"Analysis results: {len(df)} entries")
   ```

## Response Format Handling

The system handles both valid JSON responses and malformed responses:

- **Valid JSON**: Parsed directly using `json.loads()`
- **Invalid JSON**: Uses the `extract_invalid_response()` helper function from `modules.utils`

This ensures that even if the original LLM response wasn't perfectly formatted JSON, the system can still extract scores and excerpts for analysis.

## Error Handling

The analysis process includes error handling for:
- Missing excerpts in responses
- LLM API errors
- Database connection issues
- Invalid response formats

Failed analyses are logged but don't stop the overall process.

## Best Practices

1. **Choose appropriate thresholds**: Start with a moderate threshold (e.g., 75) and adjust based on your needs.

2. **Design analysis prompts carefully**: The analysis prompt should be designed to work with excerpts rather than full transcripts.

3. **Monitor results**: Use the export functionality to review analysis results and refine your approach.

4. **Use meaningful prompt names**: Choose descriptive names for both original and analysis prompts to make results easier to track.

5. **Backup before large analyses**: Consider backing up your database before running analysis on large datasets.

## Troubleshooting

### No queries found
- Ensure you have run queries with the specified prompt name
- Check that the prompt name matches exactly (case-sensitive)

### No excerpts found
- Verify that your original prompt produces responses with excerpts
- Check the response format in your prompts.json file

### Analysis prompt not found
- Ensure the analysis prompt exists in your prompts.json file
- Check that the prompt name matches exactly

### Database errors
- Ensure the database is accessible and not locked
- Check that you have write permissions to the database file 