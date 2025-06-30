# Project To-Do List

## Intro Plan

- We will do a simple econ style paper.
- Start intro with one LLM rediscovered example that was in the literature (like pork)
- Then one new example that the LLM discovered that is egregious and we were not aware of.
- Then explain our four contributions:
  1. This method works, we managed to discover new examples.
  2. The LLMs have severe limitations with many false positives. Headline number here will be percentage of top 100 hits that are false positives. Say that it is powerful technique but need to combine LLM with human supervision. For example, for legal discovery would combine lawyer and computer.
  3. What works better in our benchmark (compare different prompts, models, n repetitions)
  4. Where does collusive commnication happen (correlates with size, profitability, industry, and clustering).

---

## Results & Tasks

### 1. NLP with LLMs for Detection
- Demonstrate that LLMs can:
  - Rediscover cases from existing literature
  - Identify new, previously undocumented cases
- 📌 **TODO [JOE]**: 
  - Find one or two strong new case studies
  - Use these as compelling introductory examples
  - Describe the episode and industry context in detail, following the approach in Joe’s paper

---

### 2. Limitations and Use Cases
- Major issue: **High false positive rate**
- Suggested use: As a **discovery tool** to assist human lawyers
- 📌 **TODO [EDUARDO]**:
  - Let's focus on MSE relative to Joe's coding as our main metric.
  - Apply this metric to both our model and runner-up models
- 📌 **TODO [JOE]**:
  - Create a dataset of the top 100 results
  - Use this to evaluate and report the number of false positives

---

### 3. Methodological Comparison
- Aim: Evaluate what contributes to performance improvements
- 📌 **TODO [EDUARDO]**:
  - After benchmarking is finalized:
    - Run experiments varying (using our main prompt SimpleCapacityV8.1.1):
      - Number of queries (1x, 10x) ---> Ran Joe's prompts 10 times.
      - Model.
      - Follow-up queries
      - Use of prior queries

---

### 4. Industry and Descriptive Statistics
- Goal: Analyze patterns by industry, time, and firm characteristics
- 📌 **TODO [EDUARDO]**:
  - Choose relevant covariates (e.g., industry, year, market cap, profitability)
  - Download associated data from WRDS
  - Perform descriptive statistical analysis