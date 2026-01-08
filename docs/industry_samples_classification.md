# Industry Sample Classification: Chemicals, Construction, and Cement

This document describes the methodology and results for classifying three industry-specific samples known to have high rates of collusion: Chemicals, Construction, and Cement.

## Methodology

### Classification Strategy

We prioritize **SIC (Standard Industrial Classification)** codes over GICS codes for Construction and Cement, as GICS classifications are often too broad for these specific industry distinctions. For Chemicals, we use SIC codes as the primary classification method.

**Priority order:**
1. **SIC codes** (preferred for all three industries)
2. **NAICS codes** (alternative if SIC not available)
3. **GICS codes** (fallback if SIC/NAICS not available)

### Industry Definitions

#### 1. Chemicals Sample
- **Preferred Definition**: SIC 2800-2899 (Chemicals and Allied Products)
  - This is a standard, well-defined industry group
  - Slightly broader and more commonly used in historical economic literature
  - Captures both pharmaceuticals and industrial chemicals
- **Alternative**: GICS industry code 151010 (if SIC not available)

#### 2. Construction Sample
- **Preferred Definition**: SIC 1500-1799 (Construction Contractors)
  - **SIC 15xx**: General Building Contractors (Residential/Commercial buildings)
  - **SIC 16xx**: Heavy Construction (Highways, bridges, tunnels, dams)
  - **SIC 17xx**: Special Trade Contractors (Plumbing, electrical, etc.)
  - Targets firms that perform actual building and civil engineering (contractors), rather than materials suppliers
  - Captures the sector most prone to bid-rigging cartels (roads, bridges, infrastructure)
- **Alternative**: NAICS codes starting with 23 (Construction) if SIC not available
- **Fallback**: GICS codes starting with 2010 (Construction & Engineering) if SIC/NAICS not available

#### 3. Cement Sample
- **Preferred Definition**: SIC 3241 (Cement, Hydraulic)
  - Isolates specific manufacturers of hydraulic cement
  - Requires high granularity because GICS bundles cement with sand, glass, and bricks
- **Alternative**: NAICS 327310 (Cement Manufacturing) if SIC not available
- **Warning**: Do not use GICS 151020 ("Construction Materials") unless necessary, as it includes glass, sand, and timber companies

### Implementation

In our dataset, we have access to both SIC and NAICS codes, so we use the preferred SIC-based definitions for all three industries.

**Code Logic:**
```python
# Chemicals: SIC codes starting with "28"
chemicals_mask = df['sic'].notna() & df['sic'].astype(str).str.startswith('28')

# Construction: SIC codes starting with "15", "16", or "17"
construction_mask = df['sic'].notna() & (
    df['sic'].astype(str).str.startswith('15') |
    df['sic'].astype(str).str.startswith('16') |
    df['sic'].astype(str).str.startswith('17')
)

# Cement: SIC code exactly "3241"
cement_mask = df['sic'].notna() & (df['sic'].astype(str) == '3241')
```

## Results

### Overall Sample Statistics

- **Total transcripts in dataset**: 496,684
- **Overall LLM flag rate**: 0.87%
- **Overall LLM validation flag rate**: 0.12%
- **Overall human audit flag rate**: 0.01%

### 1. Chemicals Sample

**Sample Size:**
- **Total transcripts**: 53,551
- **Unique companies**: 1,857
- **Unique SIC codes**: 16 (all in 2800-2899 range)

**Tag Rates:**
- **LLM flag**: 0.76% (406 flagged transcripts)
- **LLM validation flag**: 0.10% (52 flagged transcripts)
- **Human audit flag**: 0.00% (1 flagged transcript)
- **Comparison to overall**: -0.12 percentage points (slightly below average)

**SIC Codes in Sample:**
2800, 2810, 2820, 2821, 2833, 2834, 2835, 2836, 2840, 2842, 2844, 2851, 2860, 2870, 2890, 2891

**Top Companies by Transcript Count:**
1. Alnylam Pharmaceuticals, Inc. (334 transcripts, SIC 2836)
2. Ionis Pharmaceuticals, Inc. (287 transcripts, SIC 2836)
3. Amgen Inc. (248 transcripts, SIC 2836)
4. BioMarin Pharmaceutical Inc. (240 transcripts, SIC 2836)
5. Exelixis, Inc. (237 transcripts, SIC 2836)
6. Bristol-Myers Squibb Company (236 transcripts, SIC 2834)
7. Eli Lilly and Company (234 transcripts, SIC 2834)
8. Regeneron Pharmaceuticals, Inc. (233 transcripts, SIC 2834)
9. Merck & Co., Inc. (222 transcripts, SIC 2834)
10. Johnson & Johnson (222 transcripts, SIC 2834)
11. Gilead Sciences, Inc. (212 transcripts, SIC 2836)
12. Biogen Inc. (209 transcripts, SIC 2836)
13. Pfizer Inc. (209 transcripts, SIC 2834)
14. Incyte Corporation (204 transcripts, SIC 2836)
15. Neurocrine Biosciences, Inc. (203 transcripts, SIC 2836)
16. Air Products and Chemicals, Inc. (200 transcripts, SIC 2810)
17. Ecolab Inc. (192 transcripts, SIC 2842)
18. Jazz Pharmaceuticals plc (186 transcripts, SIC 2834)
19. Vertex Pharmaceuticals Incorporated (176 transcripts, SIC 2836)
20. Sanofi (175 transcripts, SIC 2834)

**Companies with Highest Tag Rates:**
1. **Olin Corporation** - 31.94% (23 flagged out of 72 transcripts, SIC 2810)
2. **Norske Skogindustrier ASA** - 38.10% (16 flagged out of 42 transcripts, SIC 2821)
3. **Nutrien Ltd.** - 15.15% (20 flagged out of 132 transcripts, SIC 2870)
4. **Huntsman Corporation** - 12.88% (17 flagged out of 132 transcripts, SIC 2860)
5. **The Mosaic Company** - 12.23% (17 flagged out of 139 transcripts, SIC 2870)
6. **Green Plains Inc.** - 13.33% (8 flagged out of 60 transcripts, SIC 2860)
7. **OCI N.V.** - 17.95% (7 flagged out of 39 transcripts, SIC 2870)
8. **Rayonier Advanced Materials Inc.** - 12.50% (6 flagged out of 48 transcripts, SIC 2820)
9. **CF Industries Holdings, Inc.** - 6.67% (10 flagged out of 150 transcripts, SIC 2870)
10. **Celanese Corporation** - 7.41% (8 flagged out of 108 transcripts, SIC 2860)

**Total companies with flagged transcripts**: 154 out of 1,857 companies (8.3%)

### 2. Construction Sample

**Sample Size:**
- **Total transcripts**: 6,083
- **Unique companies**: 230
- **Unique SIC codes**: 8 (all in 1500-1799 range)

**Tag Rates:**
- **LLM flag**: 0.85% (52 flagged transcripts)
- **LLM validation flag**: 0.18% (11 flagged transcripts)
- **Human audit flag**: 0.00% (0 flagged transcripts)
- **Comparison to overall**: -0.02 percentage points (essentially at average)

**SIC Codes in Sample:**
1500, 1520, 1531, 1540, 1600, 1623, 1700, 1731

**Distribution by SIC Major Group:**
- **SIC 15xx** (General Building Contractors): 2,616 transcripts
- **SIC 16xx** (Heavy Construction): 2,507 transcripts
- **SIC 17xx** (Special Trade Contractors): 960 transcripts

**Top Companies by Transcript Count:**
1. MasTec, Inc. (145 transcripts, SIC 1623) - Heavy construction, utilities
2. Quanta Services, Inc. (121 transcripts, SIC 1731) - Special trade contractors
3. Hovnanian Enterprises, Inc. (111 transcripts, SIC 1531) - Home builders
4. PulteGroup, Inc. (100 transcripts, SIC 1531) - Home builders
5. KB Home (97 transcripts, SIC 1531) - Home builders
6. Beazer Homes USA, Inc. (92 transcripts, SIC 1531) - Home builders
7. Toll Brothers, Inc. (92 transcripts, SIC 1531) - Home builders
8. Fluor Corporation (92 transcripts, SIC 1600) - Heavy construction, engineering
9. Meritage Homes Corporation (91 transcripts, SIC 1531) - Home builders
10. Sekisui House U.S., Inc. (90 transcripts, SIC 1531) - Home builders
11. D.R. Horton, Inc. (89 transcripts, SIC 1531) - Home builders
12. Dycom Industries, Inc. (83 transcripts, SIC 1623) - Heavy construction
13. YIT Oyj (80 transcripts, SIC 1500) - General building contractors
14. Orion Group Holdings, Inc. (78 transcripts, SIC 1600) - Heavy construction
15. M/I Homes, Inc. (77 transcripts, SIC 1531) - Home builders
16. EMCOR Group, Inc. (76 transcripts, SIC 1731) - Special trade contractors
17. Great Lakes Dredge & Dock Corporation (75 transcripts, SIC 1600) - Heavy construction
18. Barratt Redrow plc (75 transcripts, SIC 1520) - Home builders
19. Tutor Perini Corporation (75 transcripts, SIC 1600) - Heavy construction
20. Persimmon Plc (74 transcripts, SIC 1520) - Home builders

**Companies with Highest Tag Rates:**
1. **Taylor Morrison Home Corporation** - 8.00% (4 flagged out of 50 transcripts, SIC 1531)
2. **Toll Brothers, Inc.** - 5.43% (5 flagged out of 92 transcripts, SIC 1531)
3. **CalAtlantic Group, Inc.** - 5.00% (2 flagged out of 40 transcripts, SIC 1531)
4. **Strabag SE** - 5.26% (1 flagged out of 19 transcripts, SIC 1600)
5. **Sekisui House U.S., Inc.** - 4.44% (4 flagged out of 90 transcripts, SIC 1531)
6. **PulteGroup, Inc.** - 4.00% (4 flagged out of 100 transcripts, SIC 1531)
7. **Vistry Group PLC** - 4.00% (1 flagged out of 25 transcripts, SIC 1520)
8. **Redrow plc** - 4.55% (1 flagged out of 22 transcripts, SIC 1520)
9. **Green Brick Partners, Inc.** - 7.32% (3 flagged out of 41 transcripts, SIC 1531)
10. **Glenveagh Properties PLC** - 6.67% (1 flagged out of 15 transcripts, SIC 1531)

**Total companies with flagged transcripts**: 30 out of 230 companies (13.0%)

### 3. Cement Sample

**Sample Size:**
- **Total transcripts**: 970
- **Unique companies**: 49
- **Unique SIC codes**: 1 (exactly 3241)

**Tag Rates:**
- **LLM flag**: 5.77% (56 flagged transcripts)
- **LLM validation flag**: 1.03% (10 flagged transcripts)
- **Human audit flag**: 0.00% (0 flagged transcripts)
- **Comparison to overall**: +4.90 percentage points (**6.6x the overall average**)

**SIC Code in Sample:**
3241 (Cement, Hydraulic) - exactly as specified

**NAICS Codes in Sample:**
324199, 327310 (Cement Manufacturing)

**Top Companies by Transcript Count:**
1. CEMEX, S.A.B. de C.V. (77 transcripts, SIC 3241) - Mexico-based global cement producer
2. Holcim AG (76 transcripts, SIC 3241) - Swiss-based global cement producer
3. CRH plc (58 transcripts, SIC 3241) - Ireland-based building materials
4. Heidelberg Materials AG (55 transcripts, SIC 3241) - Germany-based global cement producer
5. Titan S.A. (36 transcripts, SIC 3241) - Greece-based cement producer
6. Cementos Pacasmayo S.A.A. (35 transcripts, SIC 3241) - Peru-based cement producer
7. Grasim Industries Limited (33 transcripts, SIC 3241) - India-based cement producer
8. Rain Industries Limited (33 transcripts, SIC 3241) - India-based cement producer
9. Vicat S.A. (33 transcripts, SIC 3241) - France-based cement producer
10. PPC Ltd (32 transcripts, SIC 3241) - South Africa-based cement producer
11. The Siam Cement Public Company Limited (30 transcripts, SIC 3241) - Thailand-based cement producer
12. UltraTech Cement Limited (30 transcripts, SIC 3241) - India-based cement producer
13. Cementir Holding N.V. (26 transcripts, SIC 3241) - Italy-based cement producer
14. JK Lakshmi Cement Limited (25 transcripts, SIC 3241) - India-based cement producer
15. Dangote Cement Plc (24 transcripts, SIC 3241) - Nigeria-based cement producer
16. Loma Negra Compañía Industrial Argentina Sociedad Anónima (24 transcripts, SIC 3241) - Argentina-based cement producer
17. UNACEM Corp S.A.A. (23 transcripts, SIC 3241) - Peru-based cement producer
18. Buzzi S.p.A. (22 transcripts, SIC 3241) - Italy-based cement producer
19. Texas Industries, Inc. (21 transcripts, SIC 3241) - US-based cement producer (acquired by Martin Marietta)
20. Sagar Cements Limited (20 transcripts, SIC 3241) - India-based cement producer

**Companies with Highest Tag Rates:**
1. **CEMEX, S.A.B. de C.V.** - 19.48% (15 flagged out of 77 transcripts, SIC 3241)
2. **Texas Industries, Inc.** - 19.05% (4 flagged out of 21 transcripts, SIC 3241)
3. **Cementir Holding N.V.** - 11.54% (3 flagged out of 26 transcripts, SIC 3241)
4. **CEMEX Latam Holdings, S.A.** - 11.76% (2 flagged out of 17 transcripts, SIC 3241)
5. **Heidelberg Materials AG** - 9.09% (5 flagged out of 55 transcripts, SIC 3241)
6. **Buzzi S.p.A.** - 9.09% (2 flagged out of 22 transcripts, SIC 3241)
7. **Holcim AG** - 7.89% (6 flagged out of 76 transcripts, SIC 3241)
8. **Lafarge S.A.** - 10.53% (2 flagged out of 19 transcripts, SIC 3241)
9. **BUA Cement Plc** - 14.29% (1 flagged out of 7 transcripts, SIC 3241)
10. **Orient Cement Limited** - 7.14% (1 flagged out of 14 transcripts, SIC 3241)

**Total companies with flagged transcripts**: 21 out of 49 companies (42.9%)

## Key Findings

### Cement Industry Shows Exceptionally High Tag Rate

The cement sample exhibits a tag rate of **5.77%**, which is **6.6 times higher** than the overall sample average of 0.87%. This finding is consistent with the well-documented history of cartel activity in the cement industry, which has been subject to numerous antitrust investigations and fines globally.

**Notable observations:**
- **CEMEX** and **Texas Industries** show particularly high tag rates (19.48% and 19.05% respectively)
- **42.9% of cement companies** have at least one flagged transcript, compared to 8.3% for chemicals and 13.0% for construction
- The sample includes major global cement producers from multiple continents, suggesting the pattern is not region-specific

### Chemicals and Construction Near Average

Both the chemicals and construction samples show tag rates very close to the overall sample average:
- **Chemicals**: 0.76% (-0.12 percentage points from average)
- **Construction**: 0.85% (-0.02 percentage points from average)

This suggests that while these industries may have historical collusion cases, the overall rate of collusive communication in earnings call transcripts is not systematically higher than other industries in our sample.

### Classification Verification

All three industry samples were verified to contain only the expected SIC codes:
- ✓ **Chemicals**: All SIC codes start with "28" (2800-2899 range)
- ✓ **Construction**: All SIC codes start with "15", "16", or "17" (1500-1799 range)
- ✓ **Cement**: All SIC codes are exactly "3241"

The company names in each sample are consistent with the intended industry classifications, including major publicly-traded companies that are well-known in their respective industries.

## Data Quality Notes

- SIC codes are stored as 4-digit zero-padded strings (e.g., "3241", "2800")
- NAICS codes are stored as 6-digit zero-padded strings (e.g., "327310")
- All classifications use the preferred SIC-based definitions since SIC codes are available in our dataset
- The samples are not mutually exclusive and may overlap with other industry classifications in the broader analysis

## Files Generated

This analysis is produced by `src/post_query/analysis/correlation_analysis.py` and the industry sample statistics are saved to `data/yaml/correlates_collusive_communication.yaml`.
