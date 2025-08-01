Original file: queries.sqlite
File type: SQLite database
Tables: queries, analysis_queries
queries table columns: query_id (INTEGER PRIMARY KEY), prompt_name (TEXT), transcriptid (INTEGER), date (TEXT), response (TEXT), LLM_provider (TEXT), model_name (TEXT), call_type (TEXT), temperature (REAL), max_response (INTEGER), input_tokens (INTEGER), output_tokens (INTEGER)
analysis_queries table columns: analysis_query_id (INTEGER PRIMARY KEY), reference_query_id (INTEGER), prompt_name (TEXT), date (TEXT), response (TEXT), LLM_provider (TEXT), model_name (TEXT), call_type (TEXT), temperature (REAL), max_response (INTEGER), input_tokens (INTEGER), output_tokens (INTEGER)