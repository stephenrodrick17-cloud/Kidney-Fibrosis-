# Lab notebook — Stage 1

## 2026-11-12 — Stage 1 preregistration and data preparation

- Registered gates, targets, normalization, seven participant-grouped folds, models, participant-level metrics, bootstrap, and block permutation in `PREREG.md` before fitting.
- Keyed all spots by `(participant_id, library_id, barcode)`; library IDs are SHA-256-derived from expression-source paths. Verified 28 participants, 29 libraries, 25,104 spots, and uniqueness. Both 28-12265 libraries remain together.
- Reused existing QC expression/module outputs and Plan B 224×224 tiles. No raw files or earlier outputs were edited; no tile images were regenerated.
- Encoder: frozen torchvision ResNet-50 `IMAGENET1K_V2`; saved spot and 448-pixel wider-context embeddings for all 29 libraries. The torchvision code license is BSD-3-Clause; weight-specific/ImageNet dataset terms were not independently verified.
- Initial D: free-space check before Stage 1 writes: 118,437,826,560 bytes. Stage outputs and model weights remained compact; no individual output step exceeded 1 GB.

## 2026-11-12 — Compute-budget deviations, logged before model results

- Coordinate-descent Elastic Net was stopped before it emitted any fold result. Replaced with scikit-learn SGD using the same squared-error Elastic Net penalty, alpha and L1/L2 mix; later capped at 10 fixed epochs.
- MLP runs were stopped before predictions/metrics were available. Final MLP uses the preregistered 128-unit architecture and AdamW settings, with a five-epoch budget and batch size 4,096.
- Exact timestamps and reasons are recorded in the deviation sections of `PREREG.md`. No gate, split, target, or metric was changed.

## 2026-11-12 — Stage 1 baseline results

- Seven-fold out-of-fold predictions were generated for the raw and fold-residualized targets. Participant bootstrap used 10,000 resamples; spatial null used 1,000 block permutations.
- Gate A: FAIL. No embedding model beat both depth-only and colour baselines under the registered participant-macro criterion.
- The depth-only baseline had higher mean participant Spearman than the spot-embedding Elastic Net and MLP on most targets. Limited optimization budgets constrain interpretation of the learned-model comparisons.
- Three metrics were independently recomputed; key uniqueness, fold grouping, and the 28/29/25,104 cohort reconciliation passed. Full numbers and limitations are in `STAGE1_REPORT.md`.
- No registration, collagen feature use, batch correction, fine-tuning, or later-stage work was performed.
