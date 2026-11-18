# Stage 1 — Expression-only baselines

**Run timestamp:** 2026-11-12T20:15:04+05:30  
**Gate A:** **FAIL**  
**Scope:** expression-only image baselines. No registration, collagen feature use, batch correction, or fine-tuning.

## Preregistered protocol and cohort

The model sequence, preprocessing, folds, metrics, comparisons, gate, and spatial-block null were timestamped in [PREREG.md](./PREREG.md) before fitting. The immutable spot key is `(participant_id, library_id, barcode)`; library IDs are SHA-256-derived from the source expression-matrix path.

- Reconciled: **28 participants, 29 libraries, 25,104 spots**.
- Key uniqueness: 25,104/25,104.
- 28-12265: 2 libraries in 1 fold.
- Seven participant-grouped folds are balanced by in-tissue spot count; see `fold_assignments.csv` and `fold_summary.csv`.
- Eligible targets: COL1A1, COL1A2, COL3A1, FN1, TGFB1, CCN2, ACTA2, MMP2, TIMP1, ECM_collagen, myofibroblast_pro-fibrotic, matrix_remodelling. Normalization is the same `log1p(counts / total spot UMI × 10,000)` as `qc_collagen`; modules use the documented simple mean of member-gene log-normalized values.

## Encoder, license, and image features

- Frozen encoder: torchvision ResNet-50 `IMAGENET1K_V2`; features are the 2,048-dimensional global-average-pooling output. The torchvision code license is BSD-3-Clause; weight-specific and upstream ImageNet dataset terms were not independently verified. No gated pathology encoder was used.
- Device: NVIDIA GeForce RTX 3050 Laptop GPU; official weights URL: https://download.pytorch.org/models/resnet50-11ad3fa6.pth; weight file SHA-256: `11ad3fa62ca79e40addfd354a8ec4b7c75143b3038b8d2a807fbc68deab379ca` (102,540,417 bytes).
- Spot embeddings were extracted from existing 224×224 tiles; wider-context embeddings use 448×448 Visium hires crops resized to 224×224. Context available for 29/29 libraries.
- Tiles were read in place. No PNG tile folder was regenerated, and no participant data were uploaded.

## Model results

Per-target mean participant Spearman and participant-bootstrap 95% CIs are in `model_summary.csv`; participant-level estimates and skips are in `participant_metrics.csv` and `skipped_participant_targets.csv`. The primary results are the raw normalized targets; fold-residualized results are secondary. The constant patient-mean reference has undefined within-participant Spearman by construction, so its predictive-model wins are counted by MAE in `patient_mean_wins.csv`.

### Per-target raw normalized performance

| Target | n participants | Depth-only rho [95% CI] | Colour rho [95% CI] | Elastic Net spot rho [95% CI] | MLP spot rho [95% CI] | Elastic Net context rho [95% CI] | MLP context rho [95% CI] |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| COL1A1 | 28 | 0.127 [0.088, 0.164] | 0.014 [-0.025, 0.058] | 0.000 [-0.016, 0.017] | 0.012 [-0.014, 0.039] | -0.002 [-0.032, 0.027] | 0.025 [-0.008, 0.060] |
| COL1A2 | 28 | 0.030 [-0.023, 0.079] | 0.047 [0.007, 0.092] | -0.017 [-0.040, 0.007] | 0.058 [0.032, 0.084] | 0.002 [-0.021, 0.028] | 0.034 [0.005, 0.067] |
| COL3A1 | 28 | 0.131 [0.095, 0.164] | 0.015 [-0.020, 0.054] | -0.010 [-0.026, 0.005] | 0.011 [-0.010, 0.031] | -0.004 [-0.020, 0.012] | 0.017 [-0.009, 0.043] |
| FN1 | 28 | 0.099 [0.061, 0.135] | -0.008 [-0.052, 0.035] | -0.007 [-0.024, 0.010] | 0.031 [0.012, 0.051] | 0.003 [-0.020, 0.026] | 0.011 [-0.009, 0.031] |
| TGFB1 | 27 | 0.186 [0.157, 0.216] | 0.025 [-0.010, 0.063] | 0.012 [0.001, 0.024] | 0.023 [0.007, 0.038] | -0.000 [-0.020, 0.020] | 0.005 [-0.012, 0.022] |
| CCN2 | 27 | 0.029 [-0.019, 0.078] | 0.065 [0.023, 0.113] | 0.013 [-0.005, 0.031] | 0.085 [0.055, 0.114] | 0.020 [-0.002, 0.042] | 0.051 [0.029, 0.076] |
| ACTA2 | 28 | 0.034 [-0.023, 0.089] | 0.006 [-0.033, 0.046] | -0.006 [-0.025, 0.011] | 0.073 [0.045, 0.103] | -0.021 [-0.048, 0.005] | 0.048 [0.014, 0.086] |
| MMP2 | 28 | 0.137 [0.102, 0.172] | 0.007 [-0.022, 0.043] | 0.006 [-0.008, 0.023] | 0.018 [-0.004, 0.038] | -0.007 [-0.026, 0.011] | 0.008 [-0.007, 0.023] |
| TIMP1 | 28 | 0.101 [0.061, 0.139] | 0.052 [0.015, 0.092] | 0.008 [-0.005, 0.021] | 0.060 [0.036, 0.082] | -0.003 [-0.028, 0.019] | 0.032 [0.010, 0.056] |
| ECM_collagen | 28 | 0.118 [0.055, 0.177] | 0.029 [-0.023, 0.083] | -0.011 [-0.024, 0.002] | 0.049 [0.017, 0.080] | -0.013 [-0.043, 0.015] | 0.035 [0.005, 0.063] |
| myofibroblast_pro-fibrotic | 28 | 0.076 [0.014, 0.139] | 0.058 [0.015, 0.103] | -0.022 [-0.044, -0.000] | 0.086 [0.060, 0.113] | -0.010 [-0.034, 0.012] | 0.049 [0.023, 0.082] |
| matrix_remodelling | 28 | 0.133 [0.089, 0.175] | 0.040 [0.001, 0.083] | 0.016 [-0.002, 0.033] | 0.053 [0.030, 0.075] | -0.003 [-0.023, 0.017] | 0.026 [0.004, 0.050] |

### Participants beating the patient-mean reference by MAE

Counts below are participant-target wins out of 336 possible per model (28 participants × 12 targets); target-level counts are in `patient_mean_wins.csv`.

| Model | Participant-target wins |
| --- | ---: |
| color_only | 155 |
| depth_only | 228 |
| elasticnet_context | 0 |
| elasticnet_spot | 0 |
| mlp_context | 159 |
| mlp_spot | 149 |

### Participants excluded from per-target Spearman

- **COL1A1:** none.
- **COL1A2:** none.
- **COL3A1:** none.
- **FN1:** none.
- **TGFB1:** 31-10013 (fewer_than_10_detected_spots; 7 detected).
- **CCN2:** 31-10013 (fewer_than_10_detected_spots; 8 detected).
- **ACTA2:** none.
- **MMP2:** none.
- **TIMP1:** none.
- **ECM_collagen:** none.
- **myofibroblast_pro-fibrotic:** none.
- **matrix_remodelling:** none.

### Gate A macro comparisons (raw targets)

| Model | Baseline | n participants | Mean Δ Spearman | 95% participant-bootstrap CI | Positive participants |
| --- | --- | ---: | ---: | --- | ---: |
| elasticnet_spot | depth_only | 28 | -0.1016 | [-0.1386, -0.0628] | 4 |
| elasticnet_spot | color_only | 28 | -0.0304 | [-0.0607, -0.0051] | 10 |
| mlp_spot | depth_only | 28 | -0.0538 | [-0.0965, -0.0084] | 7 |
| mlp_spot | color_only | 28 | 0.0174 | [-0.0152, 0.0434] | 18 |
| elasticnet_context | depth_only | 28 | -0.1031 | [-0.1437, -0.0617] | 6 |
| elasticnet_context | color_only | 28 | -0.0319 | [-0.0680, -0.0021] | 11 |
| mlp_context | depth_only | 28 | -0.0716 | [-0.1092, -0.0303] | 8 |
| mlp_context | color_only | 28 | -0.0004 | [-0.0308, 0.0270] | 16 |

**Gate decision:** FAIL. No preregistered embedding model met both baseline comparisons with a CI above zero and positive deltas in more than half of eligible participants.

The exact candidate/baseline conditions were:
- elasticnet_spot vs depth_only: n=28, mean_delta=-0.1016, 95% CI=[-0.1386, -0.0628], positive_participants=4
- elasticnet_spot vs color_only: n=28, mean_delta=-0.0304, 95% CI=[-0.0607, -0.0051], positive_participants=10
- mlp_spot vs depth_only: n=28, mean_delta=-0.0538, 95% CI=[-0.0965, -0.0084], positive_participants=7
- mlp_spot vs color_only: n=28, mean_delta=0.0174, 95% CI=[-0.0152, 0.0434], positive_participants=18
- elasticnet_context vs depth_only: n=28, mean_delta=-0.1031, 95% CI=[-0.1437, -0.0617], positive_participants=6
- elasticnet_context vs color_only: n=28, mean_delta=-0.0319, 95% CI=[-0.0680, -0.0021], positive_participants=11
- mlp_context vs depth_only: n=28, mean_delta=-0.0716, 95% CI=[-0.1092, -0.0303], positive_participants=8
- mlp_context vs color_only: n=28, mean_delta=-0.0004, 95% CI=[-0.0308, 0.0270], positive_participants=16

### Spatial-block permutation null

The null aggregates targets and fixed out-of-fold predictions to 10×10 array-coordinate blocks and permutes block target means within library (1,000 permutations; no spot-wise shuffling). Full per-model/per-target results and skip counts are in `spatial_block_permutation.csv`.
- 68/144 available model/target/variant tests had marginal one-sided empirical p < 0.05 (uncorrected; exploratory). Block-level support is not a substitute for participant-level gate comparisons.

## Compute deviations and interpretation

- The coordinate-descent Elastic Net run was stopped before any fold output; the solver was changed before seeing scores to SGD with the same squared-error Elastic Net penalty, alpha and L1/L2 mix, then capped at 10 epochs. The fixed iteration count is recorded in `elastic_net_fit_status.csv`.
- Two MLP runs were stopped before predictions/metrics were available. The final model uses five epochs and batch size 4,096 (128-unit architecture and AdamW settings unchanged). These learned models are limited-optimization feasibility baselines, not tuned or converged candidates.
- These compute deviations were recorded in `PREREG.md` before inspecting model results. The participant folds, target definitions, metric, bootstrap, comparisons and gate were unchanged.

## Verification

- Independently recomputed three participant-level Spearman metrics; maximum absolute difference: 6.25e-17. Details: `metric_recompute_verification.csv`.
- Confirmed no spot key is repeated and no participant appears in more than one test fold; both 28-12265 libraries share one fold.
- Counts reconcile to the existing Plan A/Plan B cohort: 28 participants, 29 libraries, 25,104 spots.

## Risks, gaps, and what was not done

- ResNet-50 is ImageNet-pretrained, not pathology-pretrained; ImageNet dataset usage terms were not independently verified. No claims are made about histology-specific representation quality.
- Per-participant Spearman is descriptive on this cohort; participants and spots are few for generalization, and many spot-level values are sparse. Skipped participant-targets are listed rather than imputed.
- Patient-mean Spearman is undefined for a constant prediction; its comparison is supplementary MAE only.
- Stage 1 does not test clinical fibrosis labels, collagen/compartment features, registration, batch correction, fine-tuning, or external-cohort performance.
- Gate A result is **FAIL**; do not proceed to a later stage without explicit instruction.

## Software versions and commands

```text
{"numpy": "2.2.6", "opencv": "4.10.0", "pandas": "3.0.6", "pillow": "11.1.0", "python": "3.13.1", "scikit_learn": "1.6.1", "scipy": "1.18.1", "torch": "2.7.1+cu118", "torchvision": "0.22.1+cu118"}
```

- Preparation: `python D:\patent\stage1_expression\scripts\run_stage1.py prepare`
- Embeddings: `python D:\patent\stage1_expression\scripts\run_stage1.py embed`
- Fitting: `python D:\patent\stage1_expression\scripts\run_stage1.py fit`
- Metrics/report: `python D:\patent\stage1_expression\scripts\run_stage1.py report`

## Output inventory

- `color_statistics.npz`
- `context_embeddings.npz`
- `elastic_net_fit_status.csv`
- `fold_assignments.csv`
- `fold_summary.csv`
- `gate_comparisons.csv`
- `LAB_NOTEBOOK.md`
- `library_key_map.csv`
- `metric_recompute_verification.csv`
- `model_assets_manifest.csv`
- `model_summary.csv`
- `oof_predictions.npz`
- `oof_spot_key_index.csv`
- `participant_metrics.csv`
- `patient_mean_wins.csv`
- `PREREG.md`
- `README.md`
- `requirements-stage1.txt`
- `residualization_coefficients.csv`
- `skipped_participant_targets.csv`
- `spatial_block_permutation.csv`
- `spot_embeddings.npz`
- `stage1_config.json`
- `targets_by_spot.csv`
- `verification_checks.csv`
- `plots/target_spearman_summary.png`
