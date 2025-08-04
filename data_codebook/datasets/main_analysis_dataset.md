Original file: main_analysis_dataset.feather
File type: Feather file
Shape: 569,624 rows x 43 columns
Columns: companyid, keydevid, transcriptid, headline, mostimportantdateutc, mostimportanttimeutc, keydeveventtypeid, keydeveventtypename, companyname, transcriptcollectiontypeid, transcriptcollectiontypename, transcriptpresentationtypeid, transcriptpresentationtypename, transcriptcreationdate_utc, transcriptcreationtime_utc, audiolengthsec, benchmark_sample, benchmark_human_flag, llm_flag, transcript_year, conm, consol, costat, curcd, datadate, datafmt, emp, fic, fyear, ggroup, gind, gsector, gsubind, gvkey, indfmt, loc, mkvalt, naics, naicsh, sic, sich, spcindcd, spcseccd

## Key Variables

### benchmark_sample
- **Type**: int64
- **Description**: Binary indicator for whether the transcript is included in the human benchmark sample
- **Values**: 
  - 1: Transcript is in the human benchmark sample (390 transcripts)
  - 0: Transcript is not in the human benchmark sample (569,234 transcripts)

### benchmark_human_flag  
- **Type**: float64
- **Description**: Human rating for collusion detection (only available for transcripts in benchmark sample)
- **Values**:
  - 1.0: Flagged as collusion by human raters (131 transcripts)
  - 0.0: Not flagged as collusion by human raters (259 transcripts)
  - NaN: No human rating available - transcript not in benchmark sample (569,234 transcripts)

### llm_flag
- **Type**: int64
- **Description**: Binary indicator for whether the transcript was flagged as collusion by the LLM

## Data Processing Notes
- Dataset is filtered to include only transcripts that are also present in the queries database
- `benchmark_human_flag` is set to NaN for transcripts not in the human benchmark sample, distinguishing between "not flagged" (human said no collusion) vs "no data available"
- Compustat financial data is merged at the company-year level using `transcript_year` derived from `mostimportantdateutc`