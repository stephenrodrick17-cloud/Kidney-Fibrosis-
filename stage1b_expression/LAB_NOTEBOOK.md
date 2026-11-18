# Stage 1b lab notebook — exploratory, post-hoc

## 2026-11-12 — Registration before fitting

- Registered `PREREG_1B.md` at 2026-11-12T20:27:57+05:30 before any Stage 1b model fit. Stage 1 Gate A remains FAIL.
- Confirmed existing Stage 1 keyed arrays reconcile to 28 participants, 29 libraries, and 25,104 spots. Reused the original seven participant-grouped folds and ResNet-50 spot embeddings.
- Fixed the budget to one encoder, two target types, and two learned image-model families: converged coordinate-descent Elastic Net and grouped-validation early-stopped MLP. No second encoder was attempted.
- Immediate Visium neighbors are the six array-coordinate offsets `(0, ±2)`, `(±1, ±1)`, computed within library only. Spatial target smoothing excludes the center spot and does not impute missing neighbors.
- Initial D: free-space check: 118,152,273,920 bytes. No new data was downloaded.

## Results

Results and any fit failures will be appended here after Stage 1b verification. All outputs are labeled exploratory, post-hoc; no later stage is started automatically.

## 2026-11-12 — Pre-result implementation correction

- At 2026-11-12T22:10:07+05:30, stopped the first un-precomputed Elastic Net inner-CV fit after more than 90 minutes without a validation result. No model scores had been inspected. The first attempt's three completed fixed baselines and interrupted Elastic Net attempt are retained in the corrected configuration ledger.
- Corrected the configuration CSV schema so all attempts retain their named fields, and enabled coordinate-descent Gram precomputation for the rerun. The Elastic Net objective, participant-grouped inner CV, alpha grid, tolerance, maximum iterations, and selection rule are unchanged.
- Added completed-fold checkpoint resume handling. The deviation is timestamped in `PREREG_1B.md`; no result or gate has changed.

## 2026-11-12 — Pre-outer-test Elastic Net objective correction

- At 2026-11-12T22:24:49+05:30, inspected six inner-validation fits from the scikit-learn multi-output Elastic Net implementation. The library's multi-output formulation uses a coupled L21 row-group penalty, not independent per-gene/module Elastic Net penalties. Those six fits and validation scores are preserved in the configuration ledger as discarded; no outer-test scores were inspected.
- Switched the implementation to vectorized independent-target proximal FISTA with the same squared-error Elastic Net penalty, alpha grid, participant-weighted scaling, inner grouped CV, and validation selection rule. Alpha candidates are evaluated from high to low with warm starts. Exact convergence residuals and objective curves are saved.
- Validated the FISTA implementation on a seeded synthetic dataset against separate scikit-learn `ElasticNet` fits: at alpha 0.01 and 0.1, it met the registered `1e-4` stopping tolerance in 20 iterations; mean prediction MSE differences were `2.74e-9` and `6.06e-10`, respectively. This was a solver unit test, not a KPMP participant/model evaluation.

## 2026-11-12 — Output schema and paired-comparison correction

- At 2026-11-12T22:57:34+05:30, after all seven outer folds were checkpointed and before participant-level metrics were inspected, final summarization failed because candidate and baseline participant rows were not filtered to the current target. The MLP predictions had been checkpointed, but the logger rejected two inner-validation participant-count fields and therefore did not save its curves.
- Corrected the per-target paired comparison filter, registered the existing MLP metadata fields, and replayed all 28 same-seed MLP fits from the completed folds. The original logger-rejected records remain in the attempt ledger; replayed curves and fit details are saved separately as successful records. No model budget, hyperparameter, target, fold, or metric changed.

## 2026-11-12 — Stage 1b results verified

- Completed the exploratory, post-hoc report at 2026-11-12T23:06:41+05:30. Reconciled 28 participants, 29 libraries, and 25,104 unique `(participant_id, library_id, barcode)` keys; the saved participant folds match Stage 1 and both libraries of participant 28-12265 remain together. Three saved participant metrics were independently recomputed with zero difference.
- All 336 corrected independent-target Elastic Net inner fits converged within the registered `1e-4` optimality tolerance; all 28 outer Elastic Net fits succeeded. All 28 MLP fold/variant/input configurations completed on replay; selected epochs ranged from 1 to 4, with early stopping at epochs 16 to 19. Inner validation and refit loss curves are present in the ledger.
- The post-hoc neighbor-smoothed target often had higher spot-level associations than the unsmoothed target. For example, smoothed MLP myofibroblast-module mean Spearman was 0.195 (participant-bootstrap 95% CI 0.150 to 0.239; n=28); this is exploratory and not confirmatory.
- Across the 48 image-only candidate/target/target-variant contrasts, 27 participant-bootstrap CIs were entirely above zero versus depth-only and 18 versus colour-only. Across 48 image-plus-depth contrasts, 26 CIs were entirely above zero versus depth-only and 17 versus colour-only. These counts are exploratory, involve multiple comparisons, and do not change Stage 1 Gate A **FAIL** or justify registration/fusion.
- Output folder size after final reporting was about 60.3 MB; largest individual output was about 15.8 MB. Weight-specific/ImageNet dataset terms, external-cohort performance, deployment-time depth availability, and independent confirmation remain unverified. No registration, fusion, batch correction, fine-tuning, or later stage was performed.
