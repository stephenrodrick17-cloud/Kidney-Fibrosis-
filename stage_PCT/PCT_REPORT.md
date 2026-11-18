# PCT area-percentage accuracy report

This audit used 50 RENFAST official test images in 10 filename families.

## Plain-language answer

On this test set, U-Net mean area error was 0.223 percentage points (predicted minus expert). Mean absolute error was 4.154 percentage points.
Colour-rule mean area error was 3.660 percentage points, and mean absolute error was 7.151 percentage points.
U-Net root-mean-square error was 5.836 percentage points; Pearson correlation was 0.905, Spearman correlation was 0.865, and Lin concordance was 0.861.
The colour rule's root-mean-square error was 9.281 percentage points; Pearson correlation was 0.872, Spearman correlation was 0.813, and Lin concordance was 0.741.
U-Net Bland-Altman limits were -11.324 to 11.769 percentage points. The colour-rule limits were -13.227 to 20.546 percentage points.

## What this result means

This is an audit of area percentage inside tissue: positive mask pixels divided by tissue pixels. It does not measure collagen mass and does not establish clinical interstitial fibrosis.

Trust is limited to RENFAST trichrome test images. The 10 filename families are not verified patients or slides, and expert masks are not an independent clinical reference.

## Detection floor

The smallest expert tissue percentage was 25.239861% in 1004788. U-Net reported 19.671812% and the colour rule reported 20.861093%. No true limit of detection was tested.

## Expert-percent bands

The test set had 8 images in the 15-30% band and 42 in the over-30% band. It had no images in the 0-5% or 5-15% bands, so those bands cannot judge performance. The 15-30% band is reportable because it has at least 5 images.

In the 15-30 band, U-Net mean bias was -1.217 percentage points and mean absolute error was 3.948 percentage points. The colour rule had mean bias 0.816 and mean absolute error 4.088 percentage points.
In the over-30 band, U-Net mean bias was 0.497 and mean absolute error was 4.194 percentage points. The colour rule had mean bias 4.201 and mean absolute error 7.734 percentage points.

## Whole-image sensitivity

Repeating the same expert, U-Net and colour masks with the whole image as denominator gave U-Net mean bias 0.223 percentage points and mean absolute error 4.153 percentage points. The colour rule gave mean bias 3.662 and mean absolute error 7.152 percentage points. These are sensitivity checks; the tissue-pixel denominator is primary.

## Per-family and worst results

The per-family table is `PCT_PER_FAMILY.csv`. The three worst U-Net absolute errors were `1004780` (18.481 percentage points), `1004790_3` (14.036) and `1004762_18` (12.465). The three worst colour-rule absolute errors were `1004780` (30.832), `1004774_6` (17.661) and `1004774` (16.310). Full signed and absolute errors are in `PCT_PER_IMAGE.csv`; `PCT_WORST_IMAGES.csv` lists these cases.

## Bias structure

U-Net signed-error slope on expert percentage: 0.239701 (family-bootstrap 95% CI 0.101018 to 0.550440).
Colour-rule signed-error slope: 0.442267 (family-bootstrap 95% CI 0.245667 to 0.916721).
These are bias-structure checks. A linear correction would be post-hoc and was not applied.

## Where it is trustworthy and not trustworthy

The tables and plots describe this 50-image RENFAST test set under its exact preprocessing and tissue denominator. Confidence intervals resample filename families, but only 10 families were available.
Do not generalize to other stains, scanners, tissues, patients or clinical diagnosis. Small bands with fewer than five images are marked too small to judge.

No clinical accuracy, novelty or patentability claim is made.
