# Data and Methods

## Data Sources

### Corporate Communication Transcripts
Our primary data source consists of transcripts from public corporate communications obtained through S&P Capital IQ. Importantly, this dataset encompasses all available public calls, not solely quarterly earnings calls. This comprehensive coverage includes earnings calls, investor day presentations, industry conferences, analyst meetings, and other public corporate communications where company executives discuss business strategy, market conditions, and operational decisions.

The transcripts span from February 2002 to April 2025, covering 18,751 companies across diverse industries and sectors. Our dataset comprises 498,863 transcripts in total. Capital IQ provides verbatim transcriptions of these calls, including both the prepared remarks by company executives and the subsequent question-and-answer sessions with analysts and investors. This broader scope beyond traditional earnings calls is particularly valuable for detecting potential collusive behavior, as discussions of competitive dynamics and capacity decisions may occur in various corporate communication settings.

Each transcript in our dataset includes metadata such as the company identifier, call date, call type, participating executives, and the full text of the discussion. The inclusion of diverse call types strengthens our analysis by capturing a wider range of contexts in which executives might inadvertently signal competitive intentions or discuss market coordination.

### Human Expert Annotations
[Describe the two human-annotated datasets:
- Joe's dataset: scoring methodology (0-100), number of transcripts, annotation process
- ACL dataset: binary classification (0/1), focus on airline industry, number of transcripts]

## Sample Selection
[Explain how companies/transcripts were selected for analysis, any exclusion criteria, final sample size]

## Methodology

### LLM-Based Detection System
[Describe the overall approach - using LLMs to analyze transcripts for collusive language]

### Prompt Development
[Explain the iterative process of developing prompts, mention the 40+ variations tested, focus on SimpleCapacityV8.1.1 as the primary prompt]

### Analysis Pipeline
[Describe the technical pipeline:
1. Data ingestion from Capital IQ
2. Text preprocessing (if any)
3. LLM analysis using OpenAI API
4. Structured output extraction (score, reasoning, excerpts)
5. Database storage and management]

### Scoring Methodology
[Explain the 0-100 scoring system, what the scores represent, how they map to collusion risk]

### Two-Stage Analysis Approach
[Describe the follow-up analysis for high-scoring transcripts:
- Initial full transcript analysis
- Secondary analysis of excerpts only for transcripts scoring ≥75
- Purpose of this validation step]

## Performance Evaluation

### Benchmark Datasets
[Describe how Joe's and ACL's annotations serve as ground truth]

### Evaluation Metrics
[List the metrics used:
- Precision, Recall, F1 Score, Specificity
- Threshold selection (75 for LLM, 50 for Joe's scores)
- Separate evaluation on Joe's, ACL's, and pooled samples]

### Evaluation Approaches
[Describe the different evaluation strategies:
- Non-interactive: single response, average of multiple responses
- Agentic: repeated high-confidence, analysis-corrected, analysis-filtered]

## Implementation Details

### Technical Infrastructure
[Mention key technical aspects:
- OpenAI GPT-4o-mini as primary model
- Batch processing for large-scale analysis
- SQLite database for result storage
- Python-based implementation]

### Cost and Efficiency Considerations
[Discuss token usage, batch processing benefits, cost per transcript]

## Limitations
[Acknowledge any limitations in the data or methodology]

## Data Availability
[Statement about data availability, reproducibility]