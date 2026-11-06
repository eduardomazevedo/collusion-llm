# False-Negative Audit Plan

## Goal

Estimate the share and number of genuinely collusive transcripts among those not LLM validated. This is a stratified audit: high-score transcripts are deliberately oversampled to increase the chance of finding and understanding false negatives.

Eligible transcripts must not have been included in the original human audit. Sampling is random without replacement within each stratum, uses a fixed seed, and is blinded so the auditor does not see the score or stratum.

## Proposed allocations

| Stratum | Approximate population | 100-audit proposal | 200-audit proposal |
|---|---:|---:|---:|
| Originally flagged but not validated | 3,760 | 40 | 80 |
| Original score 70--74 | 3,270 | 25 | 50 |
| Original score 65--69 | 4,233 | 20 | 35 |
| Original score 50--64 | 7,289 | 10 | 20 |
| Original score 0--49 | 479,439 | 5 | 15 |
| **Total** | **497,991** | **100** | **200** |

Broader strata are used below 65 because dividing the small audit budget among every five-point bucket would produce uninformative sample sizes. The 200-transcript design is preferable because true positives are likely to be rare, even near the threshold.

## Estimation

For each stratum \(h\), calculate the audited positive rate \(\hat p_h=y_h/n_h\). Apply that rate to the stratum population \(N_h\):

\[
\widehat{FN}=\sum_h N_h\hat p_h,
\qquad
\widehat{FOR}=\frac{\sum_h N_h\hat p_h}{\sum_h N_h}.
\]

The unweighted positive rate in the audited sample must not be interpreted as the corpus rate because high-score strata are oversampled.

## Confidence intervals and zero-positive strata

Report a 95% exact binomial or Wilson interval for each stratum. A bucket with zero positives is informative: it produces a point estimate of zero but an upper confidence bound greater than zero. Thus, zero findings do not mean the true probability is known to be zero.

For the weighted overall estimate, combine stratum uncertainty by simulation:

1. For each stratum, draw its positive probability from the Jeffreys binomial distribution \(\operatorname{Beta}(y_h+0.5,n_h-y_h+0.5)\).
2. For every draw, calculate the population-weighted false-omission rate and projected number of false negatives.
3. Use the 2.5th and 97.5th percentiles as the 95% uncertainty interval.

This method remains well behaved when a stratum has zero positives. As a frequentist robustness check, report weighted bounds constructed from simultaneous exact binomial intervals.

Zero-positive lower-score strata are expected and do not invalidate the design. They should remain in the analysis with their original population weights and nonzero upper bounds. The limitation is precision: with only \(n\) zero-positive audits, the rough 95% upper bound is approximately \(3/n\). Consequently, this audit is best viewed as an enriched study of false negatives near the threshold, not a highly precise estimate of extremely rare errors in the very large low-score population.

## Audit procedure

- Randomize and blind the review order.
- Review transcript content rather than relying only on LLM-generated excerpts.
- Apply a pre-specified definition of collusive communication.
- Preserve an uncertain category and report sensitivity analyses treating uncertain cases as positive and negative.
- Double-code at least 20% of the sample and adjudicate disagreements if resources permit.
