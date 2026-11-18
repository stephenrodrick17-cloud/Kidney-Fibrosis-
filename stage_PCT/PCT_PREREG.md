# PCT preregistration

Timestamp: 2026-11-18T10:02:28.273+05:30

## Required frozen inputs

Only the 50 official test images and masks in `PHASEA_final_split_manifest.csv` and `PHASEA_final_per_image_metrics.csv` will be used. Family resampling unit: `family_id` from the manifest. Family IDs are filename families, not verified patient or slide identifiers.

## Metric

Primary fibrosis percentage is:

`100 x mask-positive pixels inside tissue pixels / tissue pixels`

The tissue rule is reused exactly from Phase B:

- Source: `D:\patent\stage2A_audit\PHASEB_select_regions.py`
- Constant: `TISSUE_MEAN_RGB_THRESHOLD = 245.0`
- Exact rule: `pixels.mean(axis=2) < 245.0`

It is implemented in the existing Phase B candidate reader and in the Stage FA image runner.

The expert, U-Net and colour-rule percentages are computed on the same tissue denominator. Whole-image percentages are also reported as a labelled sensitivity check.

If saved Phase A prediction masks do not exist for all 50 test images, the frozen U-Net may regenerate them with checkpoint SHA-256 `674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb`, verified before use, using the exact Phase A RGB scaling, padding/cropping and probability threshold of 0.5. No training or tuning is allowed. The regenerated per-image Dice must equal `PHASEA_final_per_image_metrics.csv` exactly. The audit stops if not.

## Predictors

- U-Net: frozen RENFAST U-Net mask.
- Colour rule: `B - R >= 2` in the 8-bit RGB image.

No stain normalization or test-time augmentation is used.

## Primary and sensitivity summaries

For U-Net and colour-rule area percentages, report:

- mean bias, mean absolute error and root-mean-square error
- Pearson correlation
- Spearman correlation
- Lin's concordance correlation coefficient
- Bland-Altman bias and limits of agreement `bias +/- 1.96 SD`
- error by expert-% band: `0-5`, `5-15`, `15-30`, `over 30`
- per-family summaries
- three worst images by absolute error
- bias-trend slope of signed error on expert percent

Each bootstrap resamples whole filename families with replacement, with 10,000 resamples and fixed seed 20261118. Percentile intervals use the 2.5th and 97.5th percentiles. This resampling unit is preregistered before computation. The overall and per-family analyses are descriptive, not clinical validation.

The bias-trend check will fit one ordinary least-squares slope of signed error against expert percent. It will be resampled by filename family. A simple linear correction would be post-hoc and will not be applied to any model or output.

The detection-floor result will report the smallest expert percentage and the corresponding U-Net and colour-rule behaviour. No true limit of detection is claimed or tested.
