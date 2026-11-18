# Phase A Results — RENFAST Prototype Audit

**Outcome against preregistered success rule: PASS.**  
**Use:** research-only mask agreement. This does not establish medical accuracy, clinical utility, novelty, or patentability.

## Main result

The frozen U-Net exceeded the training-tuned colour-threshold baseline on the equal-family-weighted test Dice estimate:

- U-Net minus colour-threshold Dice: **0.08700**
- Primary paired 95% bootstrap CI by test filename family: **0.07316 to 0.09962**
- Secondary stratified image-within-family 95% CI: **0.07857 to 0.09554**
- The primary lower confidence bound is above zero, so the registered rule passes.

There were only **10 test filename families**, which limits precision. These are filename families, **not verified patient or slide IDs**.

## Reproduction and split checks

- Recomputed U-Net macro Dice over the 50-image test split: **0.9153306336**.
- Saved full-precision value: **0.9153306336**; difference: **0.0000000000**.
- Difference from the literal rounded value `0.9153`: **+0.0000306336**; rounded to four decimals, it reproduces **0.9153**.
- Recomputed per-image Dice, IoU, and recall matched the saved values within absolute tolerance `1e-12`.
- Counts reconcile to **105 training / 18 validation / 50 test pairs**. The **127** unique training pairs with test-overlapping filename families were excluded; **250** byte-identical duplicate training entries were not used.
- The active split filename-family sets are disjoint: 6 training, 1 validation, and 10 test families. Group identifiers are not verified patient or slide IDs.

## Test performance

The image-macro and equal-family-macro estimates differ because the number of images per family is unequal. Confidence intervals are 95%; primary intervals resample test families, while secondary intervals resample images within each fixed family.

| Model | Metric | Image-macro | Equal-family macro | Primary family-bootstrap 95% CI | Secondary within-family image-bootstrap 95% CI |
|---|---|---:|---:|---:|---:|
| U-Net | Dice | 0.91533 | 0.91192 | 0.88724–0.93405 | 0.89980–0.92292 |
| U-Net | IoU | 0.84842 | 0.84259 | 0.80318–0.87835 | 0.82391–0.85963 |
| U-Net | Precision | 0.92984 | 0.94596 | 0.92558–0.96404 | 0.93357–0.95610 |
| U-Net | Recall | 0.91390 | 0.89113 | 0.84351–0.93361 | 0.87014–0.91124 |
| Colour threshold (`t=2`) | Dice | 0.84171 | 0.82492 | 0.79266–0.85506 | 0.80600–0.84289 |
| Colour threshold (`t=2`) | IoU | 0.73469 | 0.70949 | 0.66514–0.75164 | 0.68424–0.73368 |
| Colour threshold (`t=2`) | Precision | 0.82454 | 0.82909 | 0.81051–0.84872 | 0.81513–0.84136 |
| Colour threshold (`t=2`) | Recall | 0.87936 | 0.83892 | 0.77601–0.90116 | 0.80799–0.86890 |
| All background | Dice | 0.00000 | 0.00000 | 0.00000–0.00000 | 0.00000–0.00000 |
| All background | IoU | 0.00000 | 0.00000 | 0.00000–0.00000 | 0.00000–0.00000 |
| All background | Precision | NA | NA | NA | NA |
| All background | Recall | 0.00000 | 0.00000 | 0.00000–0.00000 | 0.00000–0.00000 |

Precision is NA for the all-background predictor because it predicts no positive pixels. Recall is the same quantity as sensitivity. The colour threshold was selected using training groups only; the test set was not used for tuning.

## Per-family metrics

The table gives per-family macro averages over that family's images. All values are filename-family summaries, not patient-level estimates. All-background Dice/IoU/recall are 0 and precision is NA in every family.

| Test filename family | Images | U-Net Dice | U-Net IoU | U-Net precision | U-Net recall | Colour Dice | Colour IoU | Colour precision | Colour recall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1004762 | 4 | 0.88425 | 0.80192 | 0.95878 | 0.83440 | 0.78531 | 0.66077 | 0.81928 | 0.77233 |
| 1004764 | 3 | 0.91970 | 0.85370 | 0.95569 | 0.89017 | 0.83313 | 0.72504 | 0.89164 | 0.79186 |
| 1004766 | 5 | 0.94275 | 0.89237 | 0.96713 | 0.92143 | 0.88134 | 0.78850 | 0.83269 | 0.93989 |
| 1004768 | 9 | 0.94684 | 0.89918 | 0.94952 | 0.94582 | 0.88990 | 0.80223 | 0.85178 | 0.93478 |
| 1004774 | 14 | 0.92982 | 0.87097 | 0.88367 | 0.98532 | 0.88013 | 0.78848 | 0.79922 | 0.98591 |
| 1004780 | 5 | 0.90889 | 0.83611 | 0.89560 | 0.93356 | 0.81843 | 0.69528 | 0.79386 | 0.86769 |
| 1004784 | 2 | 0.92766 | 0.86515 | 0.93518 | 0.92034 | 0.82022 | 0.69526 | 0.85269 | 0.79233 |
| 1004788 | 1 | 0.86801 | 0.76681 | 0.99086 | 0.77227 | 0.76208 | 0.61561 | 0.84180 | 0.69615 |
| 1004790 | 6 | 0.83172 | 0.71734 | 0.95495 | 0.75683 | 0.72684 | 0.58173 | 0.82644 | 0.67206 |
| 1004798 | 1 | 0.95959 | 0.92232 | 0.96819 | 0.95114 | 0.85187 | 0.74196 | 0.78146 | 0.93621 |

The full per-image table and unrounded family-level table are [PHASEA_final_per_image_metrics.csv](./PHASEA_final_per_image_metrics.csv) and [PHASEA_final_per_group_metrics.csv](./PHASEA_final_per_group_metrics.csv).

## Failure gallery

The 12 lowest U-Net Dice images, in ascending order, are:

| Image stem | Filename family | Dice |
|---|---|---:|
| 1004790_3 | 1004790 | 0.73424 |
| 1004762_18 | 1004762 | 0.74027 |
| 1004790_6 | 1004790 | 0.79012 |
| 1004790_7 | 1004790 | 0.80105 |
| 1004780 | 1004780 | 0.81829 |
| 1004774_6 | 1004774 | 0.83718 |
| 1004790_4 | 1004790 | 0.84082 |
| 1004774_8 | 1004774 | 0.85436 |
| 1004764_4 | 1004764 | 0.86730 |
| 1004788 | 1004788 | 0.86801 |
| 1004790_2 | 1004790 | 0.89653 |
| 1004766_18 | 1004766 | 0.90603 |

See [PHASEA_final_failure_gallery.png](./PHASEA_final_failure_gallery.png) for input images, manual masks, and model/baseline overlays.

## What remains unverified

- Filename-family identifiers are not verified patient or slide IDs; patient-level separation/generalization cannot be established.
- The RENFAST dataset licence field is blank. The user reports written permission, but its exact wording and scope remain **UNRESOLVED**; see [PHASEA_LICENCE_REGISTER.md](./PHASEA_LICENCE_REGISTER.md) and the blank [PHASEA_PERMISSION_RECORD.md](./PHASEA_PERMISSION_RECORD.md).
- The dataset documentation describes manual annotations, but annotator identity and independent adjudication were not verified.
- No independent hospital cohort, patient fibrosis grade, or clinical reference standard was evaluated.
- Physical pixel spacing is unavailable, so no boundary distance in microns is reported.
- No separate published architecture was run because a licence-clean implementation/checkpoint already present for this audit was not established.
- The image metrics assess overlap with the dataset masks only; they do not establish clinical performance.

## Next instruction

Review the Phase A files. Paste the permission's exact wording into [PHASEA_PERMISSION_RECORD.md](./PHASEA_PERMISSION_RECORD.md) without paraphrase, then explicitly instruct whether to begin Phase B. Phase B has **not** been started.
