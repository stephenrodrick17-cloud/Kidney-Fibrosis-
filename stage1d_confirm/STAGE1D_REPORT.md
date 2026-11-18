# Stage 1d Confirmation Report

**Run timestamp:** 2026-11-13T11:47:50+05:30  
**Protocol:** [`PREREG_CONFIRM.md`](../stage1c_confirm/PREREG_CONFIRM.md)  
**Stage 1 Gate A:** remains **FAIL**. Stage 1b remains **exploratory, post-hoc**.

## Result and decision

**Primary target:** depth-residualized immediate-neighbor-mean `myofibroblast_pro-fibrotic` module.  
**Decision:** **FAIL — the image-only candidate did not show confirmatory improvement over both frozen baselines.**

The candidate was the frozen ResNet-50 IMAGENET1K_V2 spot embedding plus the frozen one-hidden-layer MLP. It was compared only with the frozen colour-only Ridge (`alpha=1`) and depth-only Ridge (`alpha=1`). No model was refit, retuned, or reselected using the new participants. The success rule required at least 10 eligible participants and both paired participant-bootstrap 95% CIs entirely above zero.

### Per-participant primary metrics

| Participant | Finite spots | Distinct target values | MLP Spearman | Colour Ridge Spearman | Depth Ridge Spearman | MLP−colour | MLP−depth | Eligible / reason |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 164-10 | 348 | 348 | 0.1573 | -0.0836 | 0.2156 | 0.2408 | -0.0583 | yes |
| 164-22 | 1127 | 1127 | 0.2751 | -0.1944 | -0.0956 | 0.4695 | 0.3707 | yes |
| 27-10123 | 1017 | 1017 | -0.0476 | 0.0051 | 0.0332 | -0.0527 | -0.0808 | yes |
| 27-10166 | 1058 | 1058 | -0.0304 | 0.1608 | 0.0844 | -0.1912 | -0.1148 | yes |
| 27-10229 | 870 | 870 | 0.1611 | -0.0337 | -0.0183 | 0.1948 | 0.1794 | yes |
| 29-10277 | 415 | 415 | 0.3517 | 0.3487 | -0.1434 | 0.0030 | 0.4952 | yes |
| 29-10282 | 787 | 787 | 0.1681 | -0.1736 | -0.2169 | 0.3417 | 0.3851 | yes |
| 30-11081 | 865 | 865 | -0.0092 | 0.0858 | -0.1025 | -0.0949 | 0.0933 | yes |
| 34-11042 | 610 | 610 | 0.1830 | 0.2948 | 0.1243 | -0.1118 | 0.0586 | yes |
| 34-11048 | 778 | 778 | 0.2070 | -0.1424 | 0.1121 | 0.3494 | 0.0949 | yes |
| 933-10271 | 948 | 948 | -0.0282 | -0.0302 | 0.0769 | 0.0020 | -0.1051 | yes |
| 933-11258 | 807 | 807 | 0.0186 | -0.0459 | 0.0055 | 0.0645 | 0.0131 | yes |

### Paired participant-level deltas

| Comparison | Eligible participants | Mean paired delta | 95% participant-bootstrap CI |
|---|---:|---:|---|
| mlp_spot - color_only_ridge | 12 | 0.1013 | [-0.0123, 0.2185] |
| mlp_spot - depth_only_ridge | 12 | 0.1109 | [0.0025, 0.2256] |

Bootstrap: 10,000 resamples at the participant level; seed `20261114`; percentile 2.5th and 97.5th quantiles. The same eligible participant set was used for both comparisons.

## Cohort, downloads, and key integrity

- Fixed preregistered cohort: 12 participants; no replacements.
- Downloaded and SHA-256 logged: 24 files (12 expression matrices and 12 spatial bundles), 488,131,053 bytes in total. No TIFF, FASTQ, or whole-slide image file was downloaded.
- Successfully paired and processed: 12 participants, 12 libraries, 9,631 in-tissue spots. Each key is `(participant_id, library_id, barcode)`; keys are unique and none overlap the original 28 participants or 29 libraries. The original frozen key file reconciled to 28 participants, 29 libraries, and 25,104 unique spots.
- Confirmation inputs remain in `D:\patent\data_confirm\`; no archive members were extracted to disk. Only positions, scalefactors, and the hires image were read from each spatial archive.
- Disk free after download and analysis: 117,291,159,552 bytes on D: (required reserve: 2,000,000,000 bytes).
- The catalog marks all 24 selected records open. Sixteen records link to the two catalog DOI collections named in the protocol, which state CC BY 4.0; eight records have no catalog DOI, so their file-specific terms remain unverified.

## Processing and frozen-model application

- Expression parsing used the existing Matrix Market ZIP reader. In-tissue spatial barcodes had to match the expression matrix completely, following the original pairing rule; no partial match or alternate matrix was substituted.
- The hires image was decoded as RGB, and spot centers were mapped from full-resolution coordinates using `tissue_hires_scalef`, rounded as in Stage 1. Mapping dimensions, coordinate bounds, and expression-barcode coverage are recorded in `spatial_mapping_qc.csv`.
- Spot inputs were 224×224 crops with `BORDER_REFLECT_101`. Colour features used the original `color_statistics(rgb)` function. ResNet-50 encoder features were stored as float16 before the frozen MLP scaler, matching Stage 1 embedding precision. No tile PNGs were written.
- Targets used the QC expression normalization `log1p(count / total_spot_UMI × 10,000)`. Module scores are unweighted means of member-gene log-normalized values. Stored original-cohort target-on-depth coefficients were applied to new participants; no new-cohort residual-centering, scaling, fitting, tuning, or imputation was performed. Neighbor means used exactly `(0, ±2)`, `(±1, ±1)`, within library and excluding the center spot.
- The frozen encoder checkpoint matched its recorded SHA-256. MLP and Ridge model/scaler checksums matched their manifests; source checks are listed in `source_integrity_checks.csv`.
- The MLP head produced all 12 registered target outputs. Only the single primary target determined the decision. Frozen predictions for other targets and unsmoothed targets are separately labelled exploratory in the secondary CSVs. Exploratory outputs evaluate the frozen three models on the other module/gene heads, the unsmoothed residual targets, and 10×10 array-coordinate blocks. The exploratory Elastic Net image and image-plus-depth models had no frozen weights in the authorized directories and were not refit or applied.

## Exclusions and verification

- Primary-score spot exclusions: 1 spots; reasons and full keys are in `excluded_spots.csv`. No missing neighbor was imputed.
- Participant input or primary-metric exclusions: 0; details are in `participant_exclusions.csv`. Primary metric eligibility was restricted to at least 10 finite spots, at least three distinct target values, and nonconstant predictions from all three models.
- Spatial mapping audit: 12 successful mappings; all listed in-tissue centers were inside their hires images. Archive-member summaries are in `spatial_archive_contents.csv`.
- Fresh-process independent metric recomputation checked 36 model/participant Spearman values using Pearson correlation of average ranks. Maximum absolute difference from the primary table: 8.33e-17. Full evidence is in `metric_recomputation.json`.
- Key audit: 9,631 unique full keys; 0 duplicate keys. No cross-validation folds were used in this external-cohort test.

## Deviations and what could not be verified

- **Protocol deviations affecting primary inference:** no changes to the preregistered cohort, models, targets, metrics, thresholds, or decision rule are recorded. Implementation retries and code/report fixes did occur; see `D:\patent\DEVIATIONS.md` entries D-001–D-004, including the historical script-hash gaps. Network retries used the same catalog URLs and exact 24 authorized open files.
- The eight catalog records without a DOI do not have file-specific license terms verified in the catalog.
- Atlas did not provide server checksums for these transfers; the manifest records locally computed SHA-256 values and actual byte sizes.
- The exploratory Elastic Net image and image-plus-depth models were not available as frozen artifacts; applying them would require fitting/refitting, which this task forbids. Their results are therefore not reported.
- Optional secondary analyses cannot alter the primary success/failure decision or Stage 1 Gate A.

## Output files

- Download log: `data_manifest.csv`
- Primary participant values and decision inputs: `primary_participant_metrics.csv`, `primary_comparison_summary.csv`
- Exploratory target outputs: `exploratory_secondary_participant_metrics.csv`, `exploratory_secondary_summary.csv`
- Exploratory spatial blocks: `exploratory_spatial_block_metrics.csv`, `exploratory_spatial_block_summary.csv`
- Input and integrity audits: `spatial_mapping_qc.csv`, `spatial_archive_contents.csv`, `source_integrity_checks.csv`
- Exclusions and verification: `excluded_spots.csv`, `participant_exclusions.csv`, `metric_recomputation.json`

### Verified frozen artifacts and source code

- `D:\patent\stage1d_freeze\frozen_model_state.pt` — SHA-256 `c96568c1e36e4060b2377c0346b86a830a53b9486fa40b9f696c29ed8820ad53`
- `D:\patent\stage1d_freeze\frozen_scalers.npz` — SHA-256 `bdf441fb6d6640bfa419799d43ba50bd33965856770ec6e8a27e54daf6ce5409`
- `D:\patent\stage1d_freeze\input_feature_names.json` — SHA-256 `31b1289267096a5c395cbe55cff49cc055ca46473ea8a14f656016bbb0e3d260`
- `D:\patent\stage1d_freeze\residualization_parameters.csv` — SHA-256 `d3be232fc951b36b33fccf68ecfe4c6d4e6d2914e4015208d58084ce2d9c5157`
- `D:\patent\stage1d_freeze\encoder_reference.json` — SHA-256 `d9ced65240bf5b8010f126fddc77c2049e0ac635eea7d619f530bff229b019ac`
- `D:\patent\stage1_expression\model_cache\checkpoints\resnet50-11ad3fa6.pth` — SHA-256 `11ad3fa62ca79e40addfd354a8ec4b7c75143b3038b8d2a807fbc68deab379ca`
- `D:\patent\stage1d_freeze_baselines\frozen_ridge_models.joblib` — SHA-256 `9628fa34eacba0915d805148c5f0129fa7cf01a6b3b7b24bd3298b428d25041f`
- `D:\patent\stage1d_freeze_baselines\baseline_scalers.npz` — SHA-256 `0b2d68e9972fe55c933cdb13d8f3c0a9f62fbd0c9799b7fa1c64ba45a06d6758`
- `D:\patent\stage1d_freeze_baselines\baseline_feature_definitions.json` — SHA-256 `b689a3ed37f51edac46313644032172c9601b347997eeae157c81aaf0625f452`
- `D:\patent\stage1d_confirm\run_frozen_confirmation.py` — SHA-256 `ee11e4075c63b5de1d531feb6bf1e96c5a190f49a033ccfefefb92ce14f0dab9`
- `D:\patent\stage1d_confirm\download_confirmation_inputs.py` — SHA-256 `e8bb41507af7b36b3b865ef9c5b552f57180a449020ad1e1bdd8bf7197e2aeb1`
- `D:\patent\stage1_expression\scripts\run_stage1.py` — SHA-256 `fc4a8e1eeee18b79b029aa5ecf1fb97ccf4a99d4fbe11f16a28d2e766a9b8d4c`
- `D:\patent\stage1b_expression\scripts\run_stage1b.py` — SHA-256 `2a92cc16250d963c30b71375d6ace22f4d54bda547433bd31621029ad81d89d0`
- `D:\patent\analyze_cohort_plan_a_b.py` — SHA-256 `f930cad5958a9809af6cb9816ad82306eda2edb3043dc77fa1cf3364b5f496ea`
- `D:\patent\qc_collagen\run_qc_collagen.py` — SHA-256 `fc0b2e60a18a1053d34b082a2048f8fa88285e4901931356f0dc6134e7871e7e`
