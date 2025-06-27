# Data Codebook

(mostly auto generated) overview of datasets and their variables in `data/`.

## Datasets

### 1. `transcript-detail.feather` (37MB, 496,329 rows)

**Description**: metadata for earnings call transcripts from Capital IQ.

**Variables**:
- `companyid` (Int64): Unique identifier for the company
- `keydevid` (Int64): Unique identifier for the key development event
- `transcriptid` (Int64): Unique identifier for the transcript (primary key)
- `headline` (string): Title/headline of the earnings call
- `mostimportantdateutc` (object): Date of the earnings call in UTC
- `mostimportanttimeutc` (object): Time of the earnings call in UTC
- `keydeveventtypeid` (category): Numeric identifier for event type
- `keydeveventtypename` (category): Type of event (e.g., "Earnings Calls")
- `companyname` (string): Name of the company
- `transcriptcollectiontypeid` (category): Numeric identifier for collection type
- `transcriptcollectiontypename` (category): Type of transcript collection
- `transcriptpresentationtypeid` (category): Numeric identifier for presentation type
- `transcriptpresentationtypename` (category): Type of transcript presentation
- `transcriptcreationdate_utc` (object): Date when transcript was created
- `transcriptcreationtime_utc` (object): Time when transcript was created
- `audiolengthsec` (Float64): Length of audio in seconds (may be null)

### 2. `top_transcripts.csv` (32KB, 4,355 rows)

**Description**: List of transcript IDs that have been identified as collusion score >= 75 in the first LLM query.

**Variables**:
- `transcript_id` (integer): Unique identifier for the transcript

### 3. `top_transcripts_data.csv` (5.8MB)

**Description**: Detailed data for top transcripts.

**Variables**:
- `transcript_id` (integer): Unique identifier for the transcript
- `query_id` (integer): Unique identifier for the query
- `original_score` (float): Original score assigned to the transcript
- `mean_score` (float): Mean score across multiple queries
- `n_queries` (integer): Number of queries performed
- `reasoning` (text): Reasoning from the original score query
- `excerpts` (text): Relevant excerpts from the original score query

### 4. `human-ratings.csv` (8.0KB, 416 rows)

**Description**: Human expert ratings and comments for collusion detection in transcripts.

**Variables**:
- `transcriptid` (integer): Unique identifier for the transcript
- `joe_score` (integer): Score assigned by Joe (0-100 scale)
- `joe_comment` (text): Joe's detailed comment explaining the score
- `acl_manual_flag` (float): Manual flag from ACL (1.0 = flagged, 0.0 = not flagged)
- `acl_auto_flag` (float): Automatic flag from ACL (1.0 = flagged, 0.0 = not flagged)

### 5. `leaderboard.csv` (1.6KB, 22 rows)

**Description**: Performance leaderboard for different prompt versions on collusion detection tasks.

**Variables**:
- `prompt_name` (string): Name/version of the prompt
- `joe_continuous_accuracy` (float): Joe's continuous accuracy score
- `joe_binary_accuracy` (float): Joe's binary accuracy score
- `joe_pos_precision` (float): Joe's positive precision
- `joe_pos_recall` (float): Joe's positive recall
- `joe_neg_precision` (float): Joe's negative precision
- `joe_neg_recall` (float): Joe's negative recall
- `acl_accuracy` (float): ACL accuracy score
- `acl_pos_precision` (float): ACL positive precision
- `acl_pos_recall` (float): ACL positive recall
- `acl_neg_precision` (float): ACL negative precision
- `acl_neg_recall` (float): ACL negative recall
- `combined_accuracy` (float): Combined accuracy score

### 6. `queries.sqlite` (737MB)

**Description**: SQLite database containing LLM queries and responses.

**Tables**:

#### `queries` table (queries run on transcripts)
- `query_id` (INTEGER, PRIMARY KEY): Unique identifier for the query
- `prompt_name` (TEXT): Name of the prompt used
- `transcript_id` (INTEGER): ID of the transcript being analyzed
- `date` (TEXT): Date of the query
- `response` (TEXT): LLM response text
- `LLM_provider` (TEXT): Provider of the LLM service
- `model_name` (TEXT): Name of the LLM model used
- `call_type` (TEXT): Type of API call
- `temperature` (REAL): Temperature setting for the LLM
- `max_response` (INTEGER): Maximum response length
- `input_tokens` (INTEGER): Number of input tokens
- `output_tokens` (INTEGER): Number of output tokens

#### `analysis_queries` table (contains follow up queries that use as input a reference query from the query table)
- `analysis_query_id` (INTEGER, PRIMARY KEY): Unique identifier for the analysis query
- `reference_query_id` (INTEGER): Reference to the original query
- `prompt_name` (TEXT): Name of the prompt used
- `date` (TEXT): Date of the analysis query
- `response` (TEXT): LLM response text
- `LLM_provider` (TEXT): Provider of the LLM service
- `model_name` (TEXT): Name of the LLM model used
- `call_type` (TEXT): Type of API call
- `temperature` (REAL): Temperature setting for the LLM
- `max_response` (INTEGER): Maximum response length
- `input_tokens` (INTEGER): Number of input tokens
- `output_tokens` (INTEGER): Number of output tokens

### 7. Raw Data Files

#### `data/raw/acl_scores.csv` (18KB, 817 rows)

**Description**: Quarterly capacity discipline scores for airlines from ACL (Airline Capacity Leadership) analysis.

**Variables**:
- `carrier` (string): Airline carrier code (e.g., AA, AS, B6)
- `quarter` (integer): Quarter number (1-4)
- `year` (integer): Year
- `call_quarter` (string): Quarter of the earnings call (Q1-Q4)
- `call_year` (integer): Year of the earnings call
- `auto_capacity_discipline_count` (integer): Automated count of capacity discipline mentions
- `manual_capacity_discipline_count` (integer): Manual count of capacity discipline mentions

#### `data/raw/joe_scores.csv` (2.7KB, 92 rows)

**Description**: Joe's expert ratings for collusion detection in specific transcripts.

**Variables**:
- `transcriptid` (integer): Unique identifier for the transcript
- `joe_score` (integer): Joe's score (0-100 scale)
- `joe_comment` (text): Joe's detailed comment explaining the score

## Data Relationships

- `transcriptid` / `transcript_id` serves as the primary key linking most datasets
- `top_transcripts.csv` contains a subset of transcript IDs from `transcript-detail.feather`
- `human-ratings.csv` combines data from both Joe's scores and ACL flags
- `queries.sqlite` contains LLM analysis results for transcripts
- `leaderboard.csv` shows performance metrics for different prompt versions
