# GENE2 Deviations and Execution Holds

**EXPLORATORY, NOT CONFIRMATORY.**
**RESEARCH-ONLY for all ResNet-feature-dependent outputs.**

## Registration changes

No preregistered targets, region definition, models, hyperparameter values, seeds, resampling rules, or success/failure criteria have been changed after `GENE2_PREREG.md` was written.

## Execution hold

At the preregistration timestamp, execution was blocked before any model run because:

1. The project record says the torchvision ResNet-50 implementation is BSD-3-Clause, but the pretrained-weight-specific and upstream ImageNet dataset terms were not independently verified. GENE2 requires stopping if encoder terms are unclear.

### Pre-run factual correction — 2026-11-17T10:55:32+05:30

After preregistration and before any model run, the central-directory member names of `D:\patent\stage1d_confirm\confirmation_predictions.npz` were inspected. The archive contains `embeddings.npy` and the arrays `participant_id.npy`, `library_id.npy`, and `barcode.npy`. The Stage 1 `spot_embeddings.npz` likewise lists `embeddings.npy` and the full spot-key arrays. Therefore, the preregistration's statement that the Stage 1d output has no saved feature-array file was incorrect: saved feature-array entries appear to exist for both cohorts. The array values, shapes, and row-by-row key alignment were not loaded or validated. This is a factual correction only; it does not change the registered method.

At that time the licence hold remained in force; it was later superseded for this exploratory run only by the explicit user authorization recorded below. No model, shuffled-label control, or GENE2 metric had been run. No data were downloaded, no Phase B2 material was accessed, and no existing model was modified.

## User-authorized Path A amendment — 2026-11-17

The user selected **Path A, EXPLORATORY ONLY** and explicitly authorized research-only use of the already-saved ResNet-50/ImageNet features for this run. This instruction overrides the earlier encoder-licence stop for this exploratory run only. The weight-specific and ImageNet dataset terms remain **UNVERIFIED**. These assets must not be used in a patent embodiment, commercial use, or claim. Every output depending on them is marked **RESEARCH-ONLY**.

The user also directed use of only the locally saved KPMP/RENFAST files, with data permission wording remaining **UNRESOLVED** and uninterpreted. Phikon-v2 and any other non-commercial encoder remain prohibited. The timestamped re-confirmation is appended to `GENE2_PREREG.md`; targets, model families, grid, seeds, fold scheme, convergence rule, region pooling, and primary endpoint are unchanged.

### Saved-feature validation — 2026-11-17

Before any GENE2 model run, the saved arrays passed the feature/key gates recorded in `GENE2_FEATURE_VALIDATION.md`: Stage 1 features are `(25104, 2048)` float16; Stage 1d features are `(9631, 2048)` float16; all values are finite; keys align to saved target/mapping records; no full spot keys are duplicated; and all 40 participants are represented. The two cohorts are disjoint. No frozen Stage 1d model was loaded or changed.

### Control-run budget clarification — 2026-11-17

The main nested design remains at 810 fits. A single registered within-participant label-shuffle control refits only the outer-fold-selected image model and best baseline, without retuning on outer test participants, adding at most 20 fits. The maximum is therefore 830 fits. The preregistered 60-minute per-fit limit, 1-GB output cap, and an additional 90-minute per-command wall-time cap apply. The label-shuffle outputs are exploratory and research-only.

No GENE2 model has been run as of this amendment.

## Runner implementation details — 2026-11-17, before the first fit

- The preregistered MLP grid gives learning rate, weight decay, loss, batch size, and stopping rule, but does not name an optimizer. The runner uses Adam, the standard optimizer implemented in the installed PyTorch runtime. This unregistered implementation choice is disclosed; all registered target, model, grid, seed, fold, stopping, and endpoint values remain unchanged.
- The preregistration specifies tie-breaks within each model family but not between image Ridge and image MLP or between the two baselines. Exact score ties are resolved in favor of image Ridge and, for the baseline, depth-only. This only settles otherwise-equal inner-fold scores.
- Stage 1d saved target values are depth-residualized in `confirmation_predictions.npz`. To honor the registered raw log-normalized gene targets, the runner reconstructs each gene value as `saved residual + saved intercept + saved depth coefficient × saved log1p(UMI depth)` from the frozen Stage 1d residualization table. It does not use any frozen Stage 1d model predictions.
- The runner recomputes 4-by-4 region means from the saved coordinates, retaining regions with at least four paired in-tissue spots. The registered primary target's per-gene means and standard deviations are estimated from all aligned spots belonging to outer-training participants only, then applied to region means.
- Outer/inner splits are participant-grouped; every library and region from a participant inherits that participant's fold. The label-shuffle control permutes only the primary region target within each participant, as specified in the original preregistration, and refits the outer-selected image model and best baseline without retuning.
- Descriptive pooled/participant-mean metric confidence intervals use 2,000 participant-bootstrap draws for runtime; registered primary and secondary paired-difference CIs retain 10,000 draws. No success threshold or endpoint was changed.

### Pre-fit re-confirmation and report verification updates — 2026-11-17T12:05:02+05:30

- The user-authorized design was re-confirmed and timestamped in `GENE2_PREREG.md` before any real fit. Targets, region pooling, model grid, seeds, fold assignment, convergence rule, primary endpoint, resampling, and decision rule are unchanged.
- The finalizer now writes the registered results, sanity, verification, and report files, and independently recomputes the primary paired mean/CI, image participant-macro Spearman, pooled region Spearman, and MAE from saved out-of-fold predictions. It also reports participant-level differences.
- A synthetic-only finalization check exposed an initialization-order bug in reporting; it was corrected, and the synthetic finalization check then passed. No real data were used in that check.
- The original preflight outputs are preserved and will not be overwritten. Their recorded runner/document hashes predate this final report-code and timestamp update. Final verification will recompute current hashes, require the preflight data-source files to remain unchanged, and identify any changed runner or preregistration/deviation/licence documents. The saved alignment and region-count outputs remain the successful pre-run audit; no model fit has started as of this timestamp.

### Outer-fold output-indexing failure and retry — 2026-11-17T12:24:24+05:30

- The first `fit-outer --outer-fold 0` attempt completed its six registered prediction fits (three Ridge and three MLP-seed fits) and its four selected-model shuffle fits (three MLP seeds plus one Ridge baseline). It then failed while assembling the output because test-row predictions were indexed a second time with full-dataset row indices. No outer-fold output or selection file was written.
- Inner-fold selection from the saved registered results chose Image MLP and the depth-only baseline for outer fold 0, so the failed attempt completed exactly 10 fit calls.
- The output assembly was corrected to use the prediction arrays' evaluation-row order. This does not change model inputs, targets, selection, seeds, or predictions. The same outer fold must be rerun because no prediction output survived the failed command.
- This technical retry adds 10 fit calls to the planned maximum: 810 main fits plus at most 20 shuffle fits plus 10 repeated calls, for a possible actual total of 840. This exceeds the preregistered 830-fit maximum by up to 10 and is disclosed rather than hidden. The failed-attempt count is preserved in `GENE2_RETRY_ACCOUNTING.json`. No run may exceed the existing per-fit and per-command time caps.

### Finalization retry — 2026-11-17T12:52:33+05:30

- The first `finalize` run computed metrics and saved `GENE2_OOF_REGION_PREDICTIONS.csv`, then stopped when the spot-target cache's status columns collided with the final output status columns. No model fits were involved, and no existing file was overwritten.
- The finalizer now removes the cache's status columns before building spot predictions. It also compares an already-written output with the recomputed table and reuses it only if the parsed contents match exactly; otherwise it stops instead of overwriting.
- The corrected runner passed syntax validation and an exact-content check against the already-saved region output. The metrics/report finalization is being rerun; this does not add model fits or alter the analysis.

