# Phase C Preregistration — Robustness, Uncertainty, and Stronger Baseline

**Registered:** 2026-11-16 16:46:29 +05:30  
**Status:** registered before any Phase C evaluation, training, or model comparison  
**Scope:** frozen RENFAST robustness, a predeclared deep-ensemble uncertainty analysis, and one stronger segmentation baseline. Research-use only.

## Data, split, and exclusions

- Use the existing RENFAST archive, saved pair manifest, saved Phase A filename-family split, frozen checkpoint, and Phase A metrics only.
- Active split: 105 training pairs / 6 filename families; 18 validation pairs / 1 filename family; 50 held-out test pairs / 10 filename families. These are **filename families, not verified patient or slide IDs**. Confirm that no active family crosses splits before any analysis.
- The 127 training pairs already excluded by Phase A remain excluded. Do not reconstruct or alter the split.
- Explicit Phase B2 exclusion: all 20 `PHASEB2_ANNOTATOR_PACKAGE\PHASEB2_<opaque-id>.png` tiles, their key-mapped regions, and any Phase B2 annotation/return files are excluded from training, tuning, evaluation, threshold fitting, and uncertainty fitting. Record the 20 opaque filenames in `PHASEC_EXCLUDED_B2_TILES.csv` by filename inventory only; do not read their pixels, inspect the private key, or use annotation results.
- Do not download data. Do not edit any existing file. Do not use any Phase B2 annotation result.

## Registered tests, metrics, and criteria

### 1. Frozen-model colour/stain robustness

Evaluate the frozen Phase A U-Net and the unchanged Phase A colour-threshold baseline (`uint8 B − R >= 2`) on the same 50 official test images and masks. Do not tune any transformation, threshold, or model on test data.

Apply each of the following deterministic transformations to each input tile. For paired-direction levels, report each direction and the per-image mean over the two directions:

| Transformation | Three registered strength levels |
|---|---|
| Hue shift in HSV | ±5°, ±10°, ±20° |
| Saturation multiplier | (0.8, 1.2), (0.6, 1.4), (0.4, 1.6) |
| Brightness multiplier | (0.9, 1.1), (0.75, 1.25), (0.5, 1.5) |
| Contrast multiplier | (0.9, 1.1), (0.75, 1.25), (0.5, 1.5) |
| Simulated stain-vector shift | Rotate optical-density RGB vectors about the fixed normalized `[1,1,1]` axis by ±5°, ±10°, ±15°. Use `OD = -ln((RGB+1)/256)`, clamp transformed OD to nonnegative values, and invert with `RGB = 256*exp(-OD)-1`, rounded and clipped to uint8. This is a synthetic OD-space perturbation, not stain deconvolution or a learned stain model. |

Hue uses a circular HSV hue shift. Saturation, brightness, and contrast use their named multipliers, applied independently. After perturbation, the frozen colour baseline is applied to the transformed RGB image with `B − R >= 2`; it is not retuned.

For each model and condition, report image-level and equal-family-macro Dice, IoU, precision, and recall. Report Dice versus strength and the paired change from that model's clean-input result. Compute two-sided 95% percentile bootstrap CIs by resampling the 10 test filename families with replacement, 10,000 replicates, seed `20261125`. The primary robustness criterion is met only if, for every registered strength level, the U-Net's paired Dice-change CI lower bound is greater than `-0.05`. Otherwise report robustness as not demonstrated and identify the conditions that do not meet the rule. The same tables/CIs for the colour baseline are descriptive, not a separate pass criterion.

### 2. Resolution and tile-size sensitivity

- Resolution scales: `0.5×`, `0.75×`, `1.25×`, and `1.5×`. Resize RGB inputs with Lanczos; run inference at the resulting dimensions with bottom/right padding to a multiple of 16; resize the binary prediction back to the original `512 × 512` grid with nearest-neighbour interpolation. Apply the frozen colour rule at the transformed resolution and map its binary mask back the same way.
- Tile sizes: centered crops of `256 × 256`, `384 × 384`, and `512 × 512` pixels at the original pixel scale. Evaluate each prediction against the corresponding centered crop of the reference mask; do not resize/crop the reference differently from the input.
- Report the same image/family metrics and family-bootstrap 95% CIs, and paired Dice change versus the registered `512 × 512` condition. Apply the same `-0.05` lower-CI robustness criterion to each non-reference condition.

### 3. Predictive uncertainty, calibration, and OOD flag

Use a **three-member deep ensemble** for uncertainty: the frozen Phase A checkpoint plus two new plain U-Nets trained from scratch. Ensemble members use seeds `20261116` (existing frozen member), `20261122`, and `20261123`. The two new members use only the 105 Phase A training pairs from the six training filename families; the single validation family may be used for early stopping/checkpoint selection. The test families are accessed only after all member weights are frozen.

- Member and ensemble hard masks use probability threshold `0.5`.
- Per-pixel predictive probability is the arithmetic mean of the three member probabilities. Pixel uncertainty is predictive entropy and ensemble probability variance. Image-level uncertainty is the mean pixel entropy and mean pixel variance per image.
- Report per-image uncertainty, image Dice, and equal-family summaries. Test whether high uncertainty tracks low Dice using Spearman correlation between each test family's mean image entropy and its mean `1 − Dice`; report a 95% family-bootstrap CI using the registered 10-family resampling rule. Also report the image-level correlation descriptively. Support for the registered association requires the family-bootstrap CI lower bound for correlation to be above zero; otherwise say the association is not established.
- Reliability plot: ten fixed probability bins `[0,.1), …, [.9,1]` on held-out test pixels; report Brier score and 10-bin expected calibration error (ECE). No calibration method or bin edge is tuned on test data. These are descriptive calibration outcomes with no independent pass/fail threshold.
- OOD flag: on each image compute six features (mean and standard deviation of R, G, and B over all pixels). Fit a mean and standard deviation for each feature using only Phase A training images; use a `1e-6` floor for zero feature SD. Flag an image if any absolute standardized feature deviation exceeds `3.0`. Report training-derived feature statistics, test flag count, and Dice by flag status; do not tune the rule on validation or test data. This is a predeclared screening flag, not a validated OOD detector.
- Report pixel- and image-level uncertainty summaries, calibration, and family-bootstrap CIs for the association and group comparisons. With only 10 test families, state the precision limitation.

### 4. Stronger baseline

Train exactly one `DeepLabV3-ResNet50` semantic-segmentation model, as implemented by `torchvision`, with no pretrained weights. Record the installed `torchvision` version and exact licence text before training. If its licence is unclear or non-commercial, stop without training and report the blocker.

- Use the same Phase A split and the same 105/18/50 pair assignments. Train only on the six Phase A training families; use the one validation family for early stopping, checkpoint selection, and threshold selection; do not use test results for tuning.
- One new training run, seed `20261116` (same seed as the original Phase A run); no architecture, optimizer, or augmentation grid. The only threshold grid is `[0.30, 0.40, 0.50, 0.60, 0.70]`, selected by mean per-image validation Dice on the single validation family; ties go to the threshold closest to `0.50`, then the lower threshold. Freeze the chosen threshold before test inference.
- Initialize from random weights; no external pretrained weights or data.
- For the two new U-Net ensemble members and this baseline, maximum 100 epochs, patience 12 on validation Dice, with the fixed Phase A training recipe and no other hyperparameter search. Save split assignment and seeds.
- Training budget: **3 new runs total** (2 U-Net ensemble members + 1 DeepLabV3-ResNet50); seeds `20261122`, `20261123`, `20261116`; **zero** architecture/optimizer/augmentation grid trials; one five-value DeepLab output-threshold grid on validation only. The existing frozen checkpoint is reused, not retrained.
- Before each run, verify the expected wall time against the recorded Phase A run duration and available device. Do not launch any run projected to exceed 2 hours; if projected time cannot be verified or exceeds 2 hours, stop before that run and report. Do not extend the run budget.

Compare DeepLabV3-ResNet50 to the frozen U-Net on the same 50 test images using Dice, IoU, precision, recall per image and family, plus paired family-bootstrap 95% CIs (10,000 resamples, seed `20261125`). Report `DeepLab − U-Net` Dice. It beats the U-Net only if the paired CI lower bound is greater than zero; it matches within the preregistered descriptive margin only if the full CI lies within `[-0.02, +0.02]`. Otherwise state that it underperforms or that the comparison is inconclusive, as supported by the interval.

### 5. Ablation

No improvement component was proposed in this request. Skip ablation; do not invent a component or add training runs.

## Training, tuning, and reproducibility budget

- No Phase C test output may be viewed before all registered training, validation decisions, thresholds, perturbations, OOD features, and uncertainty definitions are frozen.
- No test-based threshold or hyperparameter tuning. No test-time augmentation.
- The Phase A filename-family split is authoritative; family IDs are not verified patient or slide IDs.
- All bootstrap summaries resample test filename families, not images.
- Preserve the exact commands, environment/library versions, seeds, per-run start/end times, and checkpoint hashes in the README and integrity record.
- No Phase C file may overwrite an existing file; every new filename starts with `PHASEC_`.

## Stop conditions

Stop before any training run whose projected duration exceeds 2 hours, if the required architecture licence is unclear/non-commercial, if the saved Phase A split/checkpoint cannot be verified, or if any Phase B2 tile or annotation result would be accessed. Record the reason in `PHASEC_REPORT.md` and `PHASEC_DEVIATIONS.md`. Do not start a later phase.
