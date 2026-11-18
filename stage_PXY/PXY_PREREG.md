# PXY preregistration

Timestamp: 2026-11-18T10:36:45.460+05:30

This preregistration records only the licence check and the paired PCT comparison. It is written before calculating the paired result.

## Paired PCT percentage comparison

- Input: `D:\patent\PCT?` no. The exact existing input is `D:\patent\stage_PCT\PCT_PER_IMAGE.csv`. It is the only new-data-free paired input.
- Tissue denominator: the PCT tissue rule, RGB channel mean `<245`, reused as recorded in PCT_PREREG and PCT_PER_IMAGE.
- Unit of resampling: filename family in the PCT table.
- Primary paired endpoint: per-image absolute area error difference:
  `U-Net absolute error minus colour-rule absolute error`.
- Secondary paired endpoint: paired squared-error difference:
  `U-Net squared error minus colour-rule squared error`.
- A negative difference means the U-Net has lower error.
- Mean difference is paired over the 50 PCT images.
- Bootstrap: 10,000 resamples by filename family, with replacement, fixed seed `20261118`.
- Bootstrap confidence interval: 2.5th to 97.5th percentile.
- Interpretation: U-Net percentage error is “significantly lower” only if the two-sided family-bootstrap 95% CI for mean absolute-error difference is entirely below zero.
- Per-family table: signed bias for U-Net and colour rule in percentage points, image count and mean absolute errors.
- U-Net better count: number of images with U-Net absolute tissue-percentage error less than colour-rule absolute tissue-percentage error.
- No correction is applied to model outputs or any percentage.
- No PCT model rerun is planned; this analysis reads saved PCT per-image values.

## Outside proxy step

Step 3 is not run because neither outside repository is eligible:

- SarderLab: licence NOT FOUND and requires DSA account/login and upload.
- ajpa2021: MIT code licence is readable, but no public checkpoint is provided and the repository KPMP image licence/access was not established.

No KPMP slide is downloaded or run. A proxy quantity, resampling unit and endpoint are therefore NOT AVAILABLE in this stage and are not guessed.

## Whole-slide step

No new whole-slide input or eligible proxy model is available. Step 4 is NOT RUN.

## Verification

Three headline numbers to recompute independently from PCT_PER_IMAGE.csv:

1. mean absolute-error difference,
2. number of images where U-Net absolute error is lower,
3. mean paired squared-error difference.
