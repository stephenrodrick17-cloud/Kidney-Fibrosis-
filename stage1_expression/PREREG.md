# Stage 1 preregistration — expression-only baselines

**Registered at:** 2026-11-12T12:26:43+05:30  
**Stage scope:** Stage 1 only. No image registration, trichrome/collagen inputs, batch correction, fine-tuning, or later-stage work.

## Cohort identity and inclusion

- Expected cohort: 28 participants, 29 Visium libraries, 25,104 in-tissue spots.
- The immutable spot key is `(participant_id, library_id, barcode)`. `library_id` will be deterministically derived from the source expression-matrix path and recorded with that path in a mapping table. Barcodes may repeat across libraries; `(participant_id, barcode)` is never a key.
- A spot is included only when it has a paired in-tissue position, a source expression matrix, and an existing 224×224 Plan B tile. Existing tiles are read in place; no tile PNGs are regenerated.
- All libraries belonging to one participant stay in the same outer fold. Counts and uniqueness are asserted before fitting.

## Encoder and image features

- Use torchvision ResNet-50 with official `IMAGENET1K_V2` pretrained weights as the open-weight fallback; use the 2,048-dimensional global-average-pooling feature vector. No gated pathology encoder access is assumed.
- The torchvision implementation is distributed under BSD-3-Clause. The upstream ImageNet dataset terms are not independently verified here; record this limitation and do not redistribute weights or source images.
- Spot embeddings are extracted from existing 224×224 tiles. A second, wider-context embedding is extracted by cropping 448×448 around the same Visium hires-image center and resizing that crop to 224×224. If any library lacks a usable hires image/crop, record the missing library and do not synthesize a replacement.
- Image inputs are converted to RGB and normalized using the official torchvision ResNet-50 ImageNet inference transform. The encoder is frozen and run in evaluation mode.
- Embeddings are stored compactly as float16 with the full spot key; no tile image copies are written.

## Targets

- Nine genes: `COL1A1`, `COL1A2`, `COL3A1`, `FN1`, `TGFB1`, `CCN2`, `ACTA2`, `MMP2`, `TIMP1`.
- Three modules use the existing QC simple-mean convention: ECM/collagen = mean log1p(CP10K) of `COL1A1`, `COL1A2`, `COL3A1`, `FN1`; myofibroblast/profibrotic = mean of `ACTA2`, `TGFB1`, `CCN2`, `SERPINE1`; matrix-remodelling = mean of `MMP2`, `TIMP1`. No control-gene matching is used.
- Primary targets are `log1p(raw target counts / total spot UMI × 10,000)`; raw counts and total UMI are retained. The module scores are means of the member-gene log-normalized targets.
- Also evaluate fold-specific residualized targets. In each outer fold, fit the target-versus-`log1p(total UMI)` nuisance regression using training spots only; center training residuals by training-participant means. For held-out participants, use only the training-fitted depth relationship for prediction. Held-out participant centering is used only when describing target residuals for the within-participant metric; subtracting a constant cannot change Spearman rho, and held-out labels are never used as model inputs or to fit a transform.
- A participant-target pair is eligible for Spearman only if at least 10 spots have nonzero raw target counts and there are at least 3 distinct target values. List all target/participant exclusions and their reason.

## Folds

- Seven outer folds, grouped by participant and balanced by total in-tissue spot count using deterministic seeded greedy assignment.
- Seed: `20261112`; ties are resolved by seeded participant order. Save the participant-to-fold map and per-fold participant/spot counts before fitting.
- Participant 28-12265 and both of its libraries are kept together.
- Each eligible spot receives exactly one out-of-fold prediction per model/target/target variant. No tuning on held-out folds and no participant or spot may occur in multiple test folds.

## Models, in fixed order

1. **Patient-mean reference:** training-fold grand mean target, predicted as a constant for each held-out spot. Within-participant Spearman is undefined for this constant reference; report it as such. Count model wins against this reference by per-participant MAE (lower is better), and report MAE as a supplementary metric.
2. **Library-depth-only:** Ridge regression from `log1p(total spot UMI)` to each target.
3. **Simple colour statistics:** per-tile RGB and HSV channel means and standard deviations; Ridge regression.
4. **Elastic Net on spot embeddings:** one `MultiOutputRegressor(ElasticNet(alpha=0.01, l1_ratio=0.5, max_iter=5000))` per target variant, using the frozen ResNet spot embedding. Standardize features and each target using participant-weighted training-fold statistics, and invert target scaling for predictions.
5. **Small MLP on spot embeddings:** one hidden layer of 128 ReLU units, AdamW, learning rate `1e-3`, weight decay `1e-4`, batch size 256, 100 epochs; standardize each target using training-fold means/SDs, then invert that transform for predictions. No fine-tuning of ResNet weights and no hyperparameter search.

Ridge models use `alpha=1.0`. All learned preprocessing (including feature scaling, target scaling, and residualization) is fit on outer-training participants only. For each training fold, spot weights are inverse to the number of training spots for that participant and normalized to mean one; this gives each participant equal total training weight. The patient-mean reference is the arithmetic mean of training-participant means. The wider-context embedding is a preregistered secondary input: repeat models 4 and 5 using the wider-context embeddings, without replacing the spot-embedding results.

## Metrics, uncertainty, and null

- Primary metric: Spearman correlation between observed and out-of-fold predicted values across spots separately for each participant and target. Report the number of eligible participants and list skipped participants for every target.
- Report the mean participant Spearman and 95% participant-bootstrap CI (10,000 resamples of participants; seed `20261113`). Do not treat spots as independent bootstrap units.
- Report the number of participants in which each predictive model has lower MAE than the training-fold patient-mean reference.
- Compare embedding models with depth-only and colour baselines using participant-level differences in Spearman. The Stage 1 gate passes only if at least one preregistered embedding model has a 95% participant-bootstrap CI for the mean difference wholly above zero against **both** baselines and has positive differences in more than half of the eligible participants for each comparison. Apply this criterion to the participant-level macro-average across eligible targets; also show all target-level comparisons.
- Spatial-block permutation null: within each library, partition array coordinates into 10×10-spot blocks and reduce observed targets and fixed out-of-fold predictions to within-block means. Compute participant-level Spearman across blocks, then permute whole block target means within each library (never individual spots) for 1,000 permutations (seed `20261114`). Report the observed participant-macro block Spearman, null distribution, and one-sided empirical p-value `(1 + #null >= observed)/(1 + 1000)`. Require at least four blocks per participant-target; list insufficient cases and do not silently substitute spot-wise permutation.

## Planned comparisons and stopping

- Compare the fixed model sequence on raw normalized targets; repeat on fold-residualized targets.
- Primary contrasts are Elastic Net versus depth-only and colour, and MLP versus depth-only and colour. Patient-mean reference is a supplementary MAE baseline because its per-participant Spearman is undefined.
- No model/target is selected for further tuning based on these results. Report Gate A as PASS or FAIL using the criterion above, with n and CIs. Stop after the Stage 1 report.

## Storage, reproducibility, and deviations

- Initial free space checked before Stage 1 writes: 118,437,826,560 bytes on D:.
- Only compact keyed embeddings, keyed target/prediction tables, folds, metrics, and plots may be written. No single output-writing step may exceed 1 GB; check available space before embedding and prediction outputs.
- Seeds: folds `20261112`; participant bootstrap `20261113`; block permutation `20261114`; model initialization `20261115` plus fold index.
- Record exact software versions, commands, encoder/weight identifier and license, output inventory, and any missing inputs in `README.md` and `STAGE1_REPORT.md`.
- Any deviation from this preregistration must be timestamped and justified in a separate section of the final report before interpreting results.

### Pre-analysis implementation clarification

At 2026-11-12T12:29:06+05:30, before fitting or scoring any model, fixed Ridge/Elastic Net hyperparameters, participant-balanced training weights, and the spatial-block null on block-mean values. This makes the null well-defined for irregular tissue masks without requiring exact-match tissue occupancy shapes between blocks.

At 2026-11-12T12:34:43+05:30, verified the three module member sets against `qc_collagen/run_qc_collagen.py` and corrected the myofibroblast/profibrotic module to include `SERPINE1`. Only input schemas and available packages were checked; no Stage 1 model fitting, predictions, or comparisons had been performed.

### Deviation before any model result

At 2026-11-12T14:13:55+05:30, after stopping an initial coordinate-descent Elastic Net attempt that had produced no fold output after more than 30 minutes, replaced its solver with scikit-learn `SGDRegressor(loss="squared_error", penalty="elasticnet", alpha=0.01, l1_ratio=0.5, max_iter=500, tol=0.001, n_iter_no_change=5, average=True)`, wrapped per target. This retains the registered Elastic Net objective and alpha/L1-L2 mix while making the multi-output cross-validation computationally feasible. No prediction, validation score, or comparison result had been produced or inspected; the gate, folds, feature sets, and metrics are unchanged. Report this solver deviation and any convergence warnings.

At 2026-11-12T19:13:15+05:30, stopped the first deterministic MLP fit after more than 4 hours without a completed-fold output or saved predictions. Before inspecting any score, reduced the fixed training budget to 10 epochs and batch size 1,024 (same 128-unit architecture, AdamW settings, and participant weighting) to make the seven-fold, two-view analysis finish in a bounded time. This is a compute-budget deviation, not a result-driven change; the gate, splits, inputs, and metrics are unchanged. Report it and interpret MLP results as a limited-epoch feasibility baseline.

At 2026-11-12T19:27:43+05:30, the reduced MLP run had still not completed a fold after more than 13 minutes and produced no outputs. Before inspecting any model score, capped the SGD Elastic Net solver at 20 fixed epochs (`tol=None`) instead of allowing up to 500. The objective, feature scaling, alpha, L1/L2 mix, seed, folds, gate, and metrics remain unchanged; this is a runtime-budget deviation. Record the fixed iteration count and interpret Elastic Net as a limited-optimization feasibility baseline.

At 2026-11-12T19:38:52+05:30, stopped a run after its first fold completed but before any predictions or metrics were saved. To bound the full seven-fold runtime, reduced the fixed SGD budget to 10 epochs and the MLP budget to 5 epochs with batch size 4,096. Architecture, optimizer/regularization, seeds, participant weights, folds, data, comparisons, and gate remain unchanged. No fold-level score or result had been inspected; interpret both learned baselines as limited-optimization feasibility models.
