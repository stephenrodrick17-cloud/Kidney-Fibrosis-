# FA_PREREG - EXPLORATORY, NOT CONFIRMATORY

**EXPLORATORY, NOT CONFIRMATORY. UNVALIDATED MASKS.**

**Version:** 3  
**Timestamp:** 2026-11-17T15:05:55+05:30  
**Status:** Locked before any Stage FA expression values are paired with a fibrosis mask. Later changes must be recorded only in `FA_DEVIATIONS.md`.

## Scope and fixed limits

- Use only local files already on `D:\patent`; no downloads and no internet pages will be read.
- All 40 participants have already been used in Stage 1 development or Stage 1d model evaluation. There is no unseen confirmatory participant set.
- Gate 1 is **NOT PASSED**. Every result is **EXPLORATORY, NOT CONFIRMATORY** and **UNVALIDATED MASKS**.
- Use the frozen RENFAST U-Net checkpoint read-only, with SHA-256 `674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb`. No retraining, tuning, stain normalization, or test-time augmentation.
- The fixed second mask is the colour rule `B - R >= 2`. Do not use Phikon-v2 or another encoder.
- Do not read or change Phase B2 tiles, keys, or annotations.
- The spot key is `(participant, library, barcode)`. Participant `28-12265` has two libraries; both remain in the same participant-level resampling unit.
- Stop any run by 100 minutes and before output reaches 8 GB. These limits are deliberately below the hard limits of 2 hours and 10 GB.

## Targets and expression scale

Use only the nine genes that passed the earlier detection screen among the 28 Stage 1 participants under the registered rule `>=10% spot detection in >=half of participants`: `COL1A1`, `COL1A2`, `COL3A1`, `FN1`, `TGFB1`, `CCN2`, `ACTA2`, `MMP2`, and `TIMP1`. Stage 1d availability is not established by the data audit and must be reported per gene; missing values are not to be imputed.

For each spot and available gene, use `log1p(10,000 * raw gene counts / total spot counts)`. The collagen module is the mean of the three per-gene z-scores for `COL1A1`, `COL1A2`, and `COL3A1`, with each gene z-scored across all eligible spots with complete values before averaging. No other genes or modules are tested.

## Mask and spot fibrosis score

1. Use the existing per-library Visium spot centers and scale metadata (`scalefactors_json.json` fields `spot_diameter_fullres` and `tissue_hires_scalef`) to map spots onto the image.
2. Use the nominal Visium capture-spot diameter of 55 micrometres. At the registered 4.1 micrometres per pixel, the circular footprint diameter is `55 / 4.1 = 13.4146` pixels (radius 6.7073 pixels). Pixel centers inside or on this circle are included. The local scale-factor file is the source for each library's pixel mapping; the 55-micrometre nominal platform specification was not present in the local files, so its URL/source document is **NOT AVAILABLE** and was not checked online under the no-internet rule.
3. Resample RGB images to 4.1 micrometres per pixel using the nominal spot diameter and each library's local scale factors, using Pillow LANCZOS resampling. Model inputs are non-overlapping 512 by 512 RGB tiles in `[0,1]`. Pad only the bottom and right edges with white pixels to the next 512-pixel boundary (a multiple of 16), then crop each output back to the actual image extent. Use the Phase A frozen probability threshold 0.5. Apply no normalization or augmentation.
4. Compute the second binary mask from the same resampled raw 8-bit RGB image using `B - R >= 2`.
5. For each mask, a spot fibrosis score is the number of positive mask pixels divided by the number of rasterized circular-footprint pixels. Also save spot tissue fraction, calculated with the fixed image rule `mean(R,G,B) < 245`.
6. Exclude spots whose source Visium row has `in_tissue != 1`, whose footprint has zero pixels meeting the fixed tissue rule, or whose mapping falls outside the resampled image. The existing alignment audit reports 41 of 41 libraries as PASS; the three overlay checks will be independently inspected and recorded before expression is read.
7. Save both masks and all spot scores, with participant/library/barcode keys and SHA-256 hashes, before opening any expression data for this stage.

## Groups, regression, and primary endpoint

- Within each library and for each mask separately, rank eligible spots by fibrosis score, breaking ties by barcode in ascending order. The bottom `floor(n/3)` spots are low-fibrosis, the top `floor(n/3)` are high-fibrosis, and the remainder are middle and excluded. A library is excluded for that mask if it has fewer than 20 spots in either group. Report every exclusion and reason.
- **Primary endpoint:** participant-level paired difference in collagen-module expression (high minus low), adjusted by within-participant ordinary least squares. For each participant, fit module score against high/low group, tissue depth, log total spot counts, tissue fraction, and library fixed effects where a participant has multiple libraries. The high/low coefficient is the participant effect. Participants are the resampling unit.
- Tissue depth is the distance from the spot centre to the nearest non-tissue pixel inside the tissue area, in micrometres at the 4.1-micrometre grid. Tissue fraction is the fraction of footprint pixels meeting the fixed tissue rule above.
- Report the mean participant effect, 95% participant-bootstrap CI from 10,000 resamples (seed `20261117`), and a two-sided participant sign-flip test using 10,000 random sign assignments (seed `20261117`). Success is met only when the CI lower bound is above zero and at least 70% of evaluable participants have a positive effect. Otherwise report **not met**. This rule cannot be relaxed.
- Repeat the primary calculation without log total counts as the registered cell-density sensitivity. It cannot replace the registered primary result.
- Repeat the same adjusted participant-level model for each of the nine single-gene secondary targets. Use unadjusted 95% participant-bootstrap CIs and Holm correction across the nine two-sided sign-flip p-values. Secondary results cannot rescue a primary endpoint that is not met.

## Severity, panel summary, and controls

- **Severity calibration:** the requested local metadata audit found no confirmed pathology/clinical fibrosis values. If that remains so after the mask-only step, report severity as **NOT TESTABLE** and do not seek or download new values.
- **Panel summary:** for the collagen module and each of the nine genes, calculate a participant-level pseudobulk log-CP10K value from summed counts. Regress each target on participant mean log spot counts and mean tissue fraction; correlate the residual with participant mean tissue-normalized fibrosis percentage using Spearman's rho. Report 95% CIs from 10,000 participant bootstrap resamples (seed `20261117`) and Holm-adjusted p-values across the 10 panel targets.
- **Label shuffle:** permute continuous fibrosis scores within participant 10,000 times (seed `20261117`), rebuilding the high/low groups and primary statistic each time. Report the observed statistic and two-sided shuffle p-value.
- **Depth-only and colour-only controls:** for each mask, compare the primary module response under (a) the registered depth/count/tissue-fraction covariates without the high/low indicator and (b) image-colour covariates without the high/low indicator. Report the high/low coefficient and model R-squared; do not treat these controls as alternative endpoints.
- **Stain-colour check:** no verified stain labels were found. For a descriptive proxy only, compute each library's median HSV hue among tissue pixels, assign equal-frequency quartiles across libraries with ties broken by library ID, and report mean fibrosis percentage per quartile. Compare the between-quartile eta-squared for fibrosis percentage with the largest squared participant Spearman correlation for the panel targets. Label this an image-colour check, not a verified stain-group analysis.
- **Cell-density check:** report the primary result with and without log total spot counts, as specified above. Total spot counts are the cell-density proxy; do not call them direct cell counts.
- Repeat the registered associations separately for the U-Net and colour masks. Report whether their effect directions agree. The comparison does not validate either mask.

## Participant-level panel and reporting

Report, for each mask and target, participant-level and spot-level sample sizes, participant effects, mean effects, bootstrap CIs, sign-flip or shuffle p-values as applicable, and Holm-adjusted p-values for the registered families. Show all participant effects so it is clear whether a small number of participants dominate the mean. Report negative or unavailable results plainly. No result may be described as proof, success, validation, causation, clinical accuracy, or clinical utility.

## Seeds, compute, and exact commands

- Seed for bootstrap, sign flips, label shuffles, and the three-library overlay selection: `20261117`.
- Resampling unit: participant, never spot or library.
- Maximum allowed compute for any one process: 100 minutes. Stop before 8 GB of new Stage FA outputs.
- Intended commands:
  - `python -B D:\patent\stage_FA\FA_RUN_IMAGES.py`
  - `python -B D:\patent\stage_FA\FA_ANALYZE.py`
  - `python -B D:\patent\stage_FA\FA_VERIFY.py`
- The image run must finish and its masks/scores must be saved and hashed before the analysis command reads any expression file. If image processing, alignment, or the pre-run size/time limit fails, stop and document the failure rather than changing the registered method.
