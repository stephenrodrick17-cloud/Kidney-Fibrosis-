# Stage 1 expression-only baselines

This folder contains the preregistered Stage 1 analysis for spot-level expression baselines. All outputs are derived from local KPMP Visium files and existing Plan B tiles. The pipeline does not register images, use trichrome/collagen values, batch-correct, fine-tune the encoder, or modify raw data or earlier outputs.

## Reproduction

From PowerShell:

```powershell
python D:\patent\stage1_expression\scripts\run_stage1.py prepare
python D:\patent\stage1_expression\scripts\run_stage1.py embed
python D:\patent\stage1_expression\scripts\run_stage1.py fit
python D:\patent\stage1_expression\scripts\run_stage1.py report
```

`PREREG.md` records the timestamp, gates, folds, targets, models, metrics, comparisons, and permutation null before model fitting. Seeds and exact model settings are fixed there.

The original coordinate-descent Elastic Net run was stopped before it emitted predictions or scores because it had made no fold checkpoint after more than 30 minutes. Before inspecting any model result, `PREREG.md` logged a solver deviation to scikit-learn SGD with the same squared-error Elastic Net penalty, alpha, and L1/L2 mix; subsequent pre-result adjustments cap it at 10 fixed epochs. The MLP was also stopped before predictions or metrics were saved; its documented compute-budget deviation is five epochs and batch size 4,096.

## Data identity and transformations

- The spot key is `(participant_id, library_id, barcode)`. `library_id` is deterministically derived from the source expression-matrix path and mapped back to that path in `library_key_map.csv`.
- Participant 28-12265 has two libraries with overlapping barcodes. They remain distinct keys and are assigned to the same participant-level fold.
- Targets are sourced from `D:\patent\qc_collagen\gene_expression_by_spot.csv` and `module_scores_by_spot.csv`, using the existing `log1p(counts / total spot UMI * 10,000)` transformation and simple-mean module scores. Raw counts for all nine genes are retained.
- Spot embeddings use the existing 224×224 tile PNGs. Wider-context embeddings use 448×448 crops from each library's own Visium hires image, resized in memory to 224×224. Tile PNGs are not regenerated.
- Only compact keyed arrays/tables, fold-specific out-of-fold predictions, metrics, and plots are written here. The script checks the estimated size before writes and rejects any output step at or above 1 GB.

## Encoder and terms

The frozen encoder is torchvision ResNet-50 with official `IMAGENET1K_V2` weights. The torchvision code is BSD-3-Clause; weight-specific terms and ImageNet dataset terms were not independently verified. The downloaded weights are stored under `model_cache\`; the URL and SHA-256 are recorded in `model_assets_manifest.csv`. No gated pathology encoder is used, and no participant data are sent to any external service.

## Outputs

- `PREREG.md`: timestamped preregistration.
- `LAB_NOTEBOOK.md`: append-only dated Stage 1 decisions, parameters, deviations, and results.
- `scripts\run_stage1.py`: prepare, embedding, fitting, metric, verification, and reporting commands.
- `stage1_config.json`: cohort counts, fold seed, and target transformations.
- `library_key_map.csv`: participant/library/source mapping.
- `targets_by_spot.csv`: unique keys, raw gene counts, normalized targets, modules, UMI, coordinates, and existing tile paths.
- `fold_assignments.csv`, `fold_summary.csv`: seven patient-grouped folds and balance.
- `spot_embeddings.npz`, `context_embeddings.npz`: compact keyed 2,048-dimensional float16 frozen-encoder outputs.
- `color_statistics.npz`: keyed per-tile RGB/HSV summaries.
- `model_assets_manifest.csv`: encoder version, URL, device, file size, and checksum.
- `oof_predictions.npz`, `oof_spot_key_index.csv`: predictions and keyed out-of-fold target arrays.
- `residualization_coefficients.csv`: training-fold depth nuisance coefficients.
- `elastic_net_fit_status.csv`: per-fold/per-target solver iterations and warnings.
- `participant_metrics.csv`, `model_summary.csv`: per-participant and aggregate out-of-fold metrics.
- `gate_comparisons.csv`, `patient_mean_wins.csv`: baseline comparisons and MAE wins.
- `spatial_block_permutation.csv`: block-level null results.
- `skipped_participant_targets.csv`: target/participant/model eligibility or scoring exclusions.
- `metric_recompute_verification.csv`, `verification_checks.csv`: independent recomputation and key/fold/count checks.
- `plots\target_spearman_summary.png`: target-level performance with participant-bootstrap 95% CIs.
- `STAGE1_REPORT.md`: final Stage 1 report and Gate A status.

Software versions observed in the analysis environment are recorded in `requirements-stage1.txt` and the final report. No random seed is used for deterministic embedding inference; all fold, training, bootstrap, and permutation seeds are preregistered.
