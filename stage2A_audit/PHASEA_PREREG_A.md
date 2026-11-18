# Phase A Preregistration

**Registered:** 2026-11-16 16:04:08 +05:30  
**Status:** registered before any new Phase A comparison  
**Scope:** audit the existing RENFAST fibrosis U-Net; do not train a new architecture or begin Phase B.

## Hypotheses

1. Re-running the frozen checkpoint on the saved 50-image test split will reproduce the reported macro Dice of 0.9153, within numerical tolerance 1e-12.
2. The frozen U-Net will have higher test-set macro Dice than a colour-only threshold segmenter tuned only on the six training filename-family groups. The confirmatory success rule is that the lower bound of the paired 95% test-group bootstrap confidence interval for U-Net minus colour-threshold macro Dice is greater than zero.
3. The all-background predictor will have lower Dice than the U-Net; this is descriptive and is not a success criterion.

## Data split and grouping

- Use the existing split only: 105 training pairs across 6 filename families, 18 validation pairs in 1 filename family, and 50 test pairs across 10 filename families.
- These are filename families, not verified patient or slide IDs. The family-to-patient/slide relationship is unknown.
- Use only the 105 training pairs for colour-threshold tuning. Do not use the 18 validation pairs or the 127 excluded training pairs for tuning or evaluation.
- Use the 18-pair validation split only as already used to select the frozen U-Net checkpoint. Do not change the checkpoint or its probability threshold.
- Before scoring, verify from the saved pair manifest that the train, validation, and test filename-family sets are pairwise disjoint; report any discrepancy and stop comparisons if they overlap.
- Preserve the official 50-pair test split as evaluation-only. Do not tune any settings on test data.

## Models and baselines

1. **Frozen U-Net:** saved checkpoint, existing RGB preprocessing, and its registered fixed probability threshold of 0.5.
2. **Colour-threshold baseline:** for each RGB pixel, calculate `blue_minus_red = B - R` in uint8 channel units. Predict fibrosis where `blue_minus_red >= t`. Select `t` from every integer in `[-255, 255]` using the greatest equal-family-weighted mean of per-image Dice across the six training families; tie-break by choosing the largest `t`. No morphology, stain normalization, or other learned parameters. Freeze the selected threshold before test evaluation.
3. **All-background baseline:** predict background for every pixel, with no fitted parameters.

## Metrics and conventions

- For each image: Dice, IoU, precision, and recall from binary pixels.
- For each filename family: the unweighted mean of that family's per-image metrics. Overall estimates are the unweighted mean of the ten test-family means; also report image-macro means and distributions.
- Positive class is the manual fibrosis mask. For any undefined ratio, report the convention and preserve `NA` if denominator is zero; do not silently substitute a success-shaped value.
- Report the frozen U-Net's reproduced Dice and its numerical difference from 0.9153.
- Report all 50 image-level rows, all 10 family-level rows, and a failure gallery of the 12 lowest-Dice test images.

## Uncertainty

- Primary 95% confidence intervals: 10,000 paired bootstrap resamples of the 10 test filename families, seed `20261117`. Resample families with replacement; retain all images in each selected family; compute the equal-family-weighted mean. For the success rule, bootstrap the paired per-family U-Net-minus-colour Dice differences.
- Secondary intervals: 10,000 stratified bootstrap resamples, seed `20261118`, resampling images with replacement within each of the 10 fixed test families and then averaging family means equally.
- The ten test families limit precision. These intervals describe variation among the available filename families, not patient-level generalization.

## Verification and reporting

- Reconcile the split counts to 105/18/50 pairs after excluding the 127 pairs whose filename families overlap the official test split.
- Recompute at least three reported metrics from the saved checkpoint and raw test pairs.
- Record hashes, software versions, seeds, exact commands, outputs, deviations, failure cases, and unverifiable items.
- Do not claim medical accuracy, clinical utility, novelty, or patentability. Research-use-only.
- Report PASS only if the primary paired family-bootstrap 95% CI for U-Net minus colour-threshold Dice is wholly above zero; otherwise report FAIL.
