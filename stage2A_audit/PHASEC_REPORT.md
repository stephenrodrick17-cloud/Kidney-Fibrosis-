# Phase C Report — Frozen-Model Robustness and Uncertainty

**Status:** robustness criterion **FAIL**; uncertainty association **NOT ESTABLISHED**; stronger-baseline comparison **BLOCKED**.  
**Use:** research-only analysis. These results do not establish clinical accuracy, utility, novelty, or patentability.

## What was done

- Evaluated the frozen Phase A U-Net and unchanged colour threshold (`uint8 B - R >= 2`) on the saved 50-image RENFAST test set.
- Trained two new plain U-Nets from scratch on only the six training filename families, using the single validation family for checkpoint selection. Their frozen predictions, together with the Phase A checkpoint, form the registered three-member ensemble.
- Ran the registered colour/stain perturbations, resolution tests, and centered tile-size tests. Saved per-image metrics and equal-family summaries.
- Computed ensemble pixel/image uncertainty, reliability, and the training-only OOD flag.
- Did not access any Phase B2 tile pixels, key, or annotation results. `PHASEC_EXCLUDED_B2_TILES.csv` contains only the 20 opaque filenames.
- No data or weights were downloaded. No ablation was proposed, so ablation was skipped.

The split is 105 training pairs / 6 filename families, 18 validation pairs / 1 filename family, and 50 test pairs / 10 filename families. These are **filename families, not verified patient or slide IDs**. There is no active-family overlap. The 127 pairs excluded by Phase A because their family overlapped the official test split were not used. Ten test families limit precision.

## Clean-input test results

Values below are image-macro and equal-family-macro metrics. Bracketed intervals are 95% bootstrap CIs resampling the 10 test filename families (10,000 replicates; seed `20261125`).

| Model | Dice: image / family [95% CI] | IoU: image / family [95% CI] | Precision: image / family [95% CI] | Recall: image / family [95% CI] |
|---|---|---|---|---|
| Frozen U-Net | 0.9153 / 0.9119 [0.8876, 0.9342] | 0.8484 / 0.8426 [0.8038, 0.8784] | 0.9298 / 0.9460 [0.9249, 0.9635] | 0.9139 / 0.8911 [0.8445, 0.9351] |
| Colour threshold | 0.8417 / 0.8249 [0.7924, 0.8564] | 0.7347 / 0.7095 [0.6653, 0.7533] | 0.8245 / 0.8291 [0.8102, 0.8487] | 0.8794 / 0.8389 [0.7753, 0.9044] |
| Three-member U-Net ensemble | 0.9122 / 0.9098 [0.8827, 0.9345] | 0.8440 / 0.8401 [0.7967, 0.8798] | 0.9220 / 0.9418 [0.9174, 0.9618] | 0.9181 / 0.8935 [0.8406, 0.9422] |

Ensemble minus frozen-U-Net family-macro Dice was `-0.0021` (95% CI `-0.0062 to 0.0015`); this does not demonstrate an improvement.

## Robustness

The table gives equal-family Dice and its 95% family-bootstrap CI for the U-Net and colour baseline. The paired U-Net change is against that model's clean-input result. For paired-direction perturbations, the displayed row is the predeclared per-image mean over both directions. The rule is met when the paired-change CI lower bound is greater than `-0.05`.

| Condition | U-Net family Dice [95% CI] | U-Net change vs clean [95% CI] | Colour family Dice [95% CI] | Rule |
|---|---|---|---|---|
| Hue ±5° | 0.9118 [0.8875, 0.9340] | -0.0001 [-0.0005, 0.0002] | 0.8253 [0.7930, 0.8565] | PASS |
| Hue ±10° | 0.9111 [0.8868, 0.9334] | -0.0008 [-0.0016, -0.0002] | 0.8251 [0.7932, 0.8560] | PASS |
| Hue ±20° | 0.9067 [0.8814, 0.9300] | -0.0052 [-0.0083, -0.0028] | 0.8212 [0.7907, 0.8508] | PASS |
| Saturation (0.8, 1.2) | 0.9106 [0.8862, 0.9328] | -0.0014 [-0.0030, 0.0000] | 0.8247 [0.7920, 0.8565] | PASS |
| Saturation (0.6, 1.4) | 0.9059 [0.8806, 0.9287] | -0.0060 [-0.0119, -0.0011] | 0.8245 [0.7913, 0.8567] | PASS |
| Saturation (0.4, 1.6) | 0.8931 [0.8684, 0.9147] | -0.0188 [-0.0303, -0.0081] | 0.8241 [0.7901, 0.8573] | PASS |
| Brightness (0.9, 1.1) | 0.9116 [0.8874, 0.9336] | -0.0003 [-0.0007, 0.0000] | 0.8291 [0.7966, 0.8606] | PASS |
| Brightness (0.75, 1.25) | 0.9098 [0.8869, 0.9305] | -0.0022 [-0.0043, -0.0001] | 0.8349 [0.8023, 0.8668] | PASS |
| Brightness (0.5, 1.5) | 0.8680 [0.8403, 0.8927] | -0.0440 [-0.0568, -0.0319] | 0.8435 [0.8095, 0.8776] | **FAIL** |
| Contrast (0.9, 1.1) | 0.9114 [0.8870, 0.9338] | -0.0005 [-0.0007, -0.0003] | 0.8251 [0.7925, 0.8567] | PASS |
| Contrast (0.75, 1.25) | 0.9090 [0.8839, 0.9319] | -0.0029 [-0.0038, -0.0021] | 0.8304 [0.7977, 0.8620] | PASS |
| Contrast (0.5, 1.5) | 0.9005 [0.8748, 0.9239] | -0.0114 [-0.0163, -0.0074] | 0.8326 [0.7998, 0.8651] | PASS |
| OD rotation ±5° | 0.9116 [0.8874, 0.9338] | -0.0003 [-0.0006, -0.0001] | 0.8250 [0.7930, 0.8561] | PASS |
| OD rotation ±10° | 0.9107 [0.8867, 0.9327] | -0.0012 [-0.0022, -0.0005] | 0.8239 [0.7924, 0.8544] | PASS |
| OD rotation ±15° | 0.9090 [0.8853, 0.9305] | -0.0029 [-0.0050, -0.0012] | 0.8225 [0.7922, 0.8519] | PASS |
| Resolution 0.50× | 0.8733 [0.8511, 0.8942] | -0.0386 [-0.0431, -0.0345] | 0.8136 [0.7825, 0.8435] | PASS |
| Resolution 0.75× | 0.8895 [0.8665, 0.9108] | -0.0224 [-0.0249, -0.0200] | 0.8192 [0.7878, 0.8493] | PASS |
| Resolution 1.25× | 0.9015 [0.8772, 0.9237] | -0.0104 [-0.0115, -0.0094] | 0.8223 [0.7904, 0.8531] | PASS |
| Resolution 1.50× | 0.9038 [0.8790, 0.9263] | -0.0081 [-0.0098, -0.0065] | 0.8236 [0.7915, 0.8547] | PASS |
| Center crop 256×256 | 0.9157 [0.8875, 0.9395] | 0.0037 [-0.0026, 0.0097] | 0.8213 [0.7903, 0.8539] | PASS |
| Center crop 384×384 | 0.9149 [0.8906, 0.9371] | 0.0030 [0.0017, 0.0043] | 0.8260 [0.7949, 0.8571] | PASS |

The 512×512 tile is the reference condition. At the individual-direction level, two additional comparisons fail the same lower-bound threshold: saturation multiplier `0.40` has Dice change `-0.0291` (95% CI `-0.0571 to -0.0048`), and brightness multiplier `0.50` has Dice change `-0.0719` (95% CI `-0.0936 to -0.0500`). The paired mean for brightness `(0.5, 1.5)` also fails as shown above. Thus, 1 of 21 paired-mean/non-reference conditions and 2 individual directions do not meet the criterion.

The lowest U-Net Dice under the paired extreme-brightness condition occurred for `1004762_18` (family `1004762`, Dice `0.6673`), followed by `1004790_3` (family `1004790`, Dice `0.7362`). Full per-image values are in [PHASEC_robustness_per_image.csv](./PHASEC_robustness_per_image.csv). Use [PHASEC_robustness_summary_corrected.csv](./PHASEC_robustness_summary_corrected.csv) as the canonical grouped summary: it retains the correct paired-mean/non-reference rows and adds individual-direction rows. The initial [PHASEC_robustness_summary.csv](./PHASEC_robustness_summary.csv) pooled paired directions under the first direction label; do not use those direction-labeled rows. The explicit individual-direction summaries are also in [PHASEC_robustness_direction_summary.csv](./PHASEC_robustness_direction_summary.csv). See [PHASEC_DEVIATIONS.md](./PHASEC_DEVIATIONS.md) for details.

## Uncertainty, calibration, and OOD flag

The three-member ensemble was the frozen Phase A model plus two new U-Nets. On 13,107,200 held-out pixels:

- Mean predictive entropy: `0.09346`; pixel entropy median `0.00648`, 95th percentile `0.59438`.
- Mean ensemble probability variance: `0.002728`; pixel variance median `2.20e-7`, 95th percentile `0.01678`.
- Across the 50 images, mean image entropy was `0.09346` (median `0.09228`, 95th percentile `0.13705`); mean image probability variance was `0.002728` (median `0.002600`, 95th percentile `0.004069`). Per-image values are in [PHASEC_ensemble_uncertainty_per_image.csv](./PHASEC_ensemble_uncertainty_per_image.csv).
- Brier score: `0.04663`; fixed 10-bin ECE: `0.02591`. Reliability plot: [PHASEC_reliability_plot.svg](./PHASEC_reliability_plot.svg).
- Family-level Spearman correlation of mean entropy with `1 - Dice`: `0.1515`, family-bootstrap 95% CI `-0.5472 to 0.6914`. The CI includes zero, so the registered uncertainty/low-Dice association is **not established**. Image-level Spearman was `0.1881` (descriptive only).
- Training-only means for `(R_mean, G_mean, B_mean, R_sd, G_sd, B_sd)` were `(109.89, 102.45, 112.09, 61.28, 66.70, 63.26)`; between-image feature SDs were `(27.37, 27.29, 26.97, 15.04, 14.43, 13.75)`. The six-feature OOD rule flagged `0/50` test images; all 50 unflagged images had mean ensemble Dice `0.9122`, and there is no flagged subset against which to compare Dice. This is only a screening flag, not a validated OOD detector. Full fitted values are in [PHASEC_ood_feature_stats.json](./PHASEC_ood_feature_stats.json).

## Stronger baseline and ablation

The installed `torchvision 0.22.1+cu118` implementation's BSD 3-Clause licence was verified; no pretrained weights were used. After a training-only timing preflight, the registered 100-epoch DeepLabV3-ResNet50 run was projected at `8,070.79 seconds`, exceeding the `7,200-second` maximum. It was **not launched**. No validation threshold was selected and no test inference or comparison against DeepLab was performed. The stronger-baseline outcome is **BLOCKED**, not a performance result. See [PHASEC_BLOCKED_RUNS.csv](./PHASEC_BLOCKED_RUNS.csv) and [PHASEC_DEVIATIONS.md](./PHASEC_DEVIATIONS.md).

No improvement component was proposed, so no ablation was run.

## Verification, environment, and limitations

An independent second pass recomputed three values from the saved model weights, official test pairs, and fixed colour rule. All matched exactly (absolute difference `0.0`): frozen U-Net image-macro Dice `0.9153306336`; colour-baseline family-macro Dice `0.8249237312`; ensemble Brier `0.0466317452`. See [PHASEC_VERIFICATION.json](./PHASEC_VERIFICATION.json). The archive, checkpoint, split counts, and zero family overlap were verified; 20 Phase B2 exclusions were reconciled using filenames only.

- Python `3.13.1`; PyTorch `2.7.1+cu118`; torchvision `0.22.1+cu118`; NumPy `2.2.6`; Pillow `11.1.0`.
- Device: CUDA, NVIDIA GeForce RTX 3050 Laptop GPU.
- U-Net seed `20261122`: 75 epochs, best epoch 63, elapsed `898.23 s`; checkpoint SHA-256 `df33949e87dc8665adef0718df03db1aead62512922063691771e0ce7f441e4b`.
- U-Net seed `20261123`: 91 epochs, best epoch 79, elapsed `1149.94 s`; checkpoint SHA-256 `0b54a0d6e77c2bb9b8aa9bc616cc761fd27556ce3a42c8086d5bfba9d62a1b38`.
- The Phase A checkpoint SHA-256 remains `674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb`.
- Run metadata records elapsed seconds but not explicit wall-clock start/end. The README gives approximate start times reconstructed from output modification times; they are not exact.
- RENFAST's dataset licence field is blank, and the scope of the user-reported permission remains **UNRESOLVED**. No permission wording was interpreted. See [PHASEC_LICENCE_REGISTER.md](./PHASEC_LICENCE_REGISTER.md).
- No external cohort or independent reference was used. Filename families are not verified patient or slide IDs; results do not establish generalization beyond this split.

## Integrity and next instruction

The preregistration and success thresholds were not changed. The only post-result source edit and the independent recomputations are listed in [PHASEC_INTEGRITY_CHECK.md](./PHASEC_INTEGRITY_CHECK.md). Full outputs, commands, seeds, and split manifest are linked in [PHASEC_README.md](./PHASEC_README.md).

**Exact next instruction needed:** paste the exact RENFAST permission wording into [PHASEA_PERMISSION_RECORD.md](./PHASEA_PERMISSION_RECORD.md) without paraphrase, then say whether to accept the DeepLab comparison as blocked or preregister a separately approved under-two-hour baseline. Do not start Phase D until explicitly instructed.
