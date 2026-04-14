# Paper due diligence notes

Review based on manual reading of the LaTeX sources in `manuscript/` plus compile checks for `manuscript.tex`, `online_appendix.tex`, and `si.tex`.

## manuscript/abstract.tex [DONE]
- Fixed unclear antecedent in the abstract by replacing “it” with “the communication.”

## manuscript/introduction.tex [DONE]
- Fixed typo in “public communications.”
- Tightened the statement of the paper's two objectives.
- Rephrased the prompt-development sentence for clearer prose.

## manuscript/methods.tex [DONE]
- Standardized the cross-reference to “Section~\\ref{sec:audit}.”

## manuscript/basic_results_stats.tex [DONE]
- Standardized the captions in this section to omit final periods, matching the dominant convention in the paper.

## manuscript/correlates.tex [DONE]
- Replaced brittle literal “Figure 6” references with `Figure~\\ref{fig:high_collusion_sic_tag_rates}`.
- Fixed the “Transportation” typo in the figure notes.
- Improved the wording around “LLM-flagged status.”

## manuscript/audit_description.tex [DONE]
- Replaced the hard-coded footnote number with a relative reference to the preceding footnote.
- Simplified “towards understanding” to “to understand.”
- Made the auditor references more consistent.

## manuscript/audit_performance.tex [DONE]
- Corrected the substantive direction: the true positive rate is increasing in the score.
- Fixed the facilitating / duplicated-word / sufficiently typos.
- Replaced the company-count hard-coding with `\\data{}` constants where available.
- Rewrote the false-positive summary to avoid brittle hard-coded subgroup counts in the prose.

## manuscript/audit_errors.tex [DONE]
- Fixed the grammar at the start of the section.
- Tightened the wording around transcripts referring to reduced industry supply or capacity.

## manuscript/audit_types.tex [DONE]
- Standardized the apostrophe style across the section.
- Lightly reflowed a couple of the longest quotations to reduce layout pressure.

## manuscript/audit_takeaways.tex [DONE]
- Deleted the orphaned file from the repo.

## manuscript/detection.tex [DONE]
- Fixed “the industry at large.”

## manuscript/case.tex [DONE]
- Standardized the date ranges to the 2012-2016 / 2022-2023 style.
- Added an inline TODO comment for the potentially confusing mean-score example in the concluding footnote.

## manuscript/concluding_remarks.tex [DONE]
- Fixed the grammar issues (“add,” “assesses,” and “effects”).
- Smoothed the opening phrasing to “conduct through an underexplored communication practice.”

## manuscript/online_appendix.tex [DONE]
- Added a table of contents.
- Added `\\printbibliography` so the appendix can stand on its own without citation-destination warnings.
- Left the appendix structure otherwise unchanged.

## manuscript/si.tex [DONE]
- Deleted the stale supplementary-information driver that had been replaced by `online_appendix.tex`.

## manuscript/si_alternative_llms.tex [DONE]
- Deleted the unused duplicate appendix fragment.

## manuscript/si_alternative_prompts.tex
- This file also looks like a **partial / older duplicate** of material now covered in `si_prompts_llms_comparisons.tex`.
- It is not currently included by the main manuscript or by `online_appendix.tex`.
- delete

## manuscript/si_human_audit_sample_assessment.tex
- The main issue is structural: it is included in `si.tex` but not in `online_appendix.tex`.
- delete

