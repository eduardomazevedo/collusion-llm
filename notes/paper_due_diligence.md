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

## manuscript/case.tex
- Minor style point: date ranges are expressed both as “2012 to 2016” and “2012--16”; standardize --> 2012-2016 is better.
- One line in the concluding footnote reports a mean score of 65 for a transcript discussed after saying these are LLM-flagged transcripts; that may be perfectly fine because flagging used the original score, but some readers may briefly find it confusing. -> put a [TODO investigate] note there for humans to double check

## manuscript/concluding_remarks.tex
- Grammar issue: “episodes which vastly **adds**” should be “episodes which vastly **add**.”
- Grammar issue: “it **is assesses** the performance” should be corrected.
- Awkward phrasing: “conduct **deploying** an underexplored communication practice” reads awkwardly; the prior wording may have been smoother.
- Wording issue: “whether it results in **effect**” should probably be “whether it results in **effects**.”

## manuscript/online_appendix.tex
- It cites papers but does **not print a bibliography**, which triggers a PDF warning about missing citation destinations. ---> Add bibliography and TOC to SI.
- Inconsistency with `si.tex`: this file does **not** include `si_human_audit_sample_assessment.tex`, whereas `si.tex` does.
- The appendix structure itself is otherwise coherent.

## manuscript/si.tex
  - This is a stale file replaced by the online appendix.tex. Delete si.tex

## manuscript/si_alternative_llms.tex
- This file looks like a **partial / older duplicate** of material now covered in `si_prompts_llms_comparisons.tex`.
- It is not currently included by the main manuscript or by `online_appendix.tex`.
- delete

## manuscript/si_alternative_prompts.tex
- This file also looks like a **partial / older duplicate** of material now covered in `si_prompts_llms_comparisons.tex`.
- It is not currently included by the main manuscript or by `online_appendix.tex`.
- delete

## manuscript/si_human_audit_sample_assessment.tex
- The main issue is structural: it is included in `si.tex` but not in `online_appendix.tex`.
- delete

