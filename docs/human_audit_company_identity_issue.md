# Human audit company-identity issue

## Summary
The human audit spreadsheet (`assets/human_audit_final.xlsx`) should not be treated as the authoritative source for company identity fields such as `companyname`.

The spreadsheet is a manually maintained working file. It is reliable for:
- `transcript_id`
- `T/F/N`
- manual audit comments / notes

It is not reliable as the canonical source for:
- company names
- company-level counts
- unique-company counts

## Problem discovered
A discrepancy appeared in the count of distinct companies among true positives:
- raw unique company names in `assets/human_audit_final.xlsx`: **72**
- unique companies in transcript metadata: **71**

The immediate cause was a duplicate company represented with two names in the audit spreadsheet:
- `Daqo New Energy`
- `Daqo New Energy Corp.`

Both map to the same underlying transcript metadata company:
- `companyid = 84196527`
- canonical transcript metadata name: `Daqo New Energy Corp.`

## Root cause
The issue was caused by computing audit-company summaries directly from the spreadsheet's `companyname` column in:
- `src/post_query/analysis/audit_analysis.py`

That approach is brittle because the spreadsheet contains manual and stale name variants.

## Broader evidence
Comparing the spreadsheet against transcript metadata shows additional mismatches beyond Daqo, including:
- encoding issues (for example GOL, Rémy Cointreau, Klöckner, Companhia Siderúrgica Nacional)
- renamed / stale company labels
- some clearly non-canonical company names in the spreadsheet relative to transcript metadata

This means the spreadsheet `companyname` column is not a safe long-term source for manuscript constants or appendix company listings.

## Correct long-term solution
For audit summaries, use the spreadsheet only for audit decisions and join company identity from transcript metadata using `transcript_id`.

Recommended rule:
1. Read `assets/human_audit_final.xlsx`
2. Keep audit labels from that file
3. Merge onto transcript metadata using `transcript_id`
4. Compute company-level summaries using metadata fields, preferably `companyid`
5. Use metadata `companyname` as the canonical display name

## Fix implemented
`src/post_query/analysis/audit_analysis.py` was updated so that:
- true-positive company counts are based on transcript metadata merged by `transcript_id`
- unique company counts use metadata company identity (`companyid`) rather than raw spreadsheet `companyname`
- spreadsheet names are used only as a fallback if transcript metadata is missing

This fixes the Daqo duplication and provides a more durable basis for manuscript constants.
