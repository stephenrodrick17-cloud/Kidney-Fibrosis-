# Stage 2C Preregistration — Exploratory Phase 7 Redesign

**Registered:** 2026-11-13T12:27:35+05:30  
**Scope:** exploratory model comparison on the 40 development participants only. Stage 1d remains failed; this analysis will not rescue, rerun, or reinterpret Stage 1d. No validation-cohort data may be downloaded, opened, or summarized.

## Frozen inputs and stop conditions

- Use only the original 28 plus the 12 Stage 1d participants as development data. Reuse the hash-verified Stage 1/1b/1d loaders and saved artifacts; record their exact paths and SHA-256 values before analysis. Do not silently reimplement a loader or preprocessing step.
- Use the exact Stage 1 module definitions for the primary `myofibroblast_pro-fibrotic` target and secondary `ECM/collagen` target. A source-definition file and hash must be identified before expression values are read. If module membership, target normalization, or participant/library mapping cannot be verified consistently across all 40 participants, stop and write `BLOCKER.md`.
- The Stage 2B collagen fraction feature is unavailable and is excluded from all candidate feature sets; it will not be imputed or proxied.
- The pathology foundation model is **Phikon-v2**, frozen, with embeddings extracted from the same existing spot-centered H&E/Visium image tiles used by the Stage 1 pipeline. Use the official model-card inference transform and CLS embedding. Before downloading weights or running extraction, verify and record the official checkpoint version, SHA-256, license, and access status. If gated or terms do not explicitly permit this research use, stop under P8; do not substitute another model.
- Use only development cohort files already present locally. No new participant data downloads are authorized. Do not open or summarize any validation-cohort files.

## Regions and targets

- Form regions separately within each library using non-overlapping `10 × 10` array-coordinate blocks: `block_row=floor((array_row-min(array_row))/10)` and `block_col=floor((array_col-min(array_col))/10)`. The array row/column coordinates and library ID are taken from the existing verified spatial loader. Regions with fewer than 5 in-tissue spots are excluded. All exclusions and participant region counts are reported.
- At each spot, compute each frozen module score as the arithmetic mean of member genes' `log1p(count / spot_total_UMI × 10,000)` values. Region target is the unweighted mean of those spot module scores in the region. Keep original spot-level counts and keys unchanged.
- Primary target: region-level `myofibroblast_pro-fibrotic` module score, depth-adjusted by weighted linear residualization on region mean `log1p(spot_total_UMI)`. Fit the intercept and slope using only the training participants in each relevant split, weighting each participant equally (each of a participant's regions receives weight `1 / that participant's region count`). Apply those training-only parameters to the matching validation/test targets. Refit residualization inside every inner-training split; refit on the complete outer-training split before outer-test prediction.
- Secondary targets: region-level `ECM/collagen` module score with the same fold-specific depth adjustment, and participant-level mean primary module score as a coarse target. The coarse target is the unweighted mean of a participant's eligible region scores; use only outer-fold out-of-sample participant predictions.
- A participant is primary-metric eligible only if it has at least 10 eligible regions and nonconstant observed and predicted values. Report all exclusions and reasons; do not replace participants.

## Feature sets and models

All spot/tile features are pooled by arithmetic mean within each eligible region. Feature order is frozen from the source artifact and recorded in the output.

1. **Phikon-v2 image embeddings:** frozen CLS embeddings from the existing spot-centered tiles; use official preprocessing and no fine-tuning.
2. **ImageNet ResNet-50 legacy embeddings:** reuse the frozen Stage 1/1d embeddings and encoder; no retraining.
3. **Colour baseline:** exact existing `color_statistics(rgb)` features and parameters, pooled within region.
4. **Depth baseline:** region mean `log1p(spot_total_UMI)`.

The Stage 2B collagen feature is not used. Do not add combined feature sets or additional encoders.

For each feature set, compare these fixed estimators:

- Ridge: `alpha ∈ {0.1, 1, 10, 100}`.
- Elastic Net: `alpha ∈ {0.01, 0.1, 1}` and `l1_ratio ∈ {0.1, 0.5, 0.9}`.
- One small MLP architecture: one 64-unit ReLU hidden layer; `alpha ∈ {0.0001, 0.001}`; Adam solver, learning-rate initialization `0.001`, batch size 64, maximum 500 iterations, tolerance `1e-4`. No additional architecture or hyperparameter search.

For every fit, standardize input features using means/standard deviations fit on that fit's training rows only. Any target scaling is also fit on training rows only. The inner-CV score selects hyperparameters and the model family. For the primary comparison, the image candidate is the better inner-CV-selected model from Phikon-v2 or ResNet-50; the comparator for each outer fold is the stronger inner-CV-selected colour or depth baseline. No outer-test results may be used for selection.

## Nested patient-grouped evaluation

- Outer CV: 8 folds, with all libraries, spots, and regions from one participant assigned to exactly one fold. Use a fixed seed `20261113` to shuffle the 40 participant IDs once, then assign them round-robin to 8 folds.
- Inner CV: 4 grouped folds over outer-training participants, using deterministic shuffles derived from the outer seed and fold index. No participant may cross train/validation boundaries.
- Assert programmatically, before fitting, that participant sets are disjoint in every train/validation/test split. Save fold assignments and checks.
- Use the mean participant-level Spearman as the inner-CV selection metric. The outer predictions are strictly out of participant. Per-participant primary result is Spearman across that participant's regions; report the paired image-minus-baseline delta for every eligible participant.
- Primary summary: mean paired delta over eligible participants and participant-bootstrap percentile 95% CI (10,000 resamples, seed `20261114`). Success for further investment requires **both** lower CI bound `> 0` and positive mean delta in at least 65% of eligible participants. This is exploratory evidence only, not confirmation or clinical/predictive performance.
- Report the number of eligible participants and regions. If fewer than 10 participants meet the preregistered region rule, report the gate as not evaluable and stop.

## Permutation control and trial ledger

- Run 200 full-pipeline permutation repeats with fixed base seed `20261115`. For each repeat, shuffle the primary region target values within each participant, then repeat the complete nested model-selection and outer evaluation procedure, including fold-local residualization, scaling, and baseline/image selection. Keep the region features and participant membership fixed.
- Append every evaluated configuration/fold, permutation or observed, to `TRIAL_LEDGER.csv` with configuration, seed, target, feature set, estimator, hyperparameters, outer fold, inner fold, metric, value, and status. Include failed and interrupted attempts. Report the exact number of distinct configurations tried and total evaluation rows.
- The primary comparison and success decision use observed, unpermuted development results only. The permutation distribution is a null-control estimate and does not change model selection or the success rule.

## Reporting and gate

Write `STAGE2C_REPORT.md` with participant-level primary deltas, participant-bootstrap CI, secondary results labelled exploratory, permutation null, region/participant reconciliation, fold-isolation checks, number of configurations tried, and limitations. Do not freeze or train a final model on all 40 participants.

If the success rule fails, stop at Gate 2C: do not proceed to model freezing or Stage 2E. Report the next-step recommendation. Stage 2D is a separately preregistered power analysis and may proceed only if the task's stop instruction is not triggered; no validation data are involved.
