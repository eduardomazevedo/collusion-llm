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

## manuscript/basic_results_stats.tex
- No major factual issues found.
- Caption style is a bit inconsistent with the rest of the paper (some captions end with periods, some do not). -> pick a convention and stick through it in the whole paper.

## manuscript/correlates.tex
- Important reference issue: the text says “Figure 6” twice instead of using `Figure~\ref{...}`. This is brittle and should probably refer to `Figure~\ref{fig:high_collusion_sic_tag_rates}`.
- Typo in figure notes: “Deep Sea Domestic Freight **Transporation**” should be “**Transportation**.”
- Slight wording issue: “LLM-flagged is used as our binary indicator” would read better as “LLM-flagged status is used…”

## manuscript/audit_description.tex
- Fragile hard-coded footnote reference: “provided in the linked assessment file in **footnote~15**.” This should not hard-code a footnote number because it will drift if earlier footnotes change.
- Minor style issue: “towards understanding” could be simplified to “to understand.”
- Minor pronoun consistency issue: the text switches between singular auditor and plural pronouns in places.

## manuscript/audit_performance.tex
- Important substantive wording issue: “The true positive rate is **decreasing** in the score…” appears inconsistent with the next sentence, which says the highest bin has a higher true positive rate than the lowest bin. This likely should be **increasing in the score**.
- Typo: “faciliating” should be “facilitating.”
- Typo: “that that a high false positive rate” has a duplicated “that.”
- Typo: “sufficently” should be “sufficiently.”
- The sentence with the appendix table was moved into a footnote; that is fine.
- Some counts are hard-coded in prose (e.g. 71 companies, 192 false positives, 163, 67, 48, 14, 29). That is okay if stable, but if the underlying data may change, it would be safer to pull them from constants. --> indeed make these automated.

## manuscript/audit_errors.tex
- Grammar issue near the start: “the transcripts refer to the firm’s competitive conduct or the state of market competition **though did not connect** it…” should be “**but did not connect** it…”
- Minor style issue: “There are some transcripts referring…” could be tightened.

## manuscript/audit_types.tex
- Minor style point: there is some inconsistency between straight and curly apostrophes/quotation style across the section. --> pick a convention and stick to it
- Several long quotations generate overfull boxes in the PDF build. Not urgent, but they could be line-broken or slightly shortened if desired.

## manuscript/audit_takeaways.tex
- This file is **not currently included** in `manuscript/manuscript.tex`.
- If this text is obsolete, consider deleting or archiving it. If it is meant to appear in the paper, it is currently orphaned. --> yes delete from repo

## manuscript/detection.tex
- Typo: “the industry **large**” should be “the industry **at large**.”

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

