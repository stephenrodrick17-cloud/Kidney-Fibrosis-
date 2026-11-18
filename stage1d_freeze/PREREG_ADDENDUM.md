# Stage 1d-prep preregistration addendum

**Registered:** 2026-11-13T10:25:53+05:30  
**Status:** frozen before training; no Stage 1d evaluation or extra-participant data access is authorized here.  
**Stage 1 Gate A:** remains FAIL. Stage 1b remains exploratory, post-hoc.

## Reason for this addendum

Stage 1 and Stage 1b saved predictions and the frozen ResNet-50 encoder, but did not save trained prediction-head weights. This addendum freezes the single training procedure needed to create the full-cohort confirmation candidate. It does not change the Stage 1c confirmation hypothesis or permit evaluation on any participant outside the original 28.

## Protocol comparison and fixed configuration

The Stage 1c candidate specifies `mlp_spot`, a frozen 2,048-dimensional ResNet-50 `IMAGENET1K_V2` spot embedding from a 224x224 tile, a 128-unit ReLU hidden layer, a 12-output head, AdamW (`lr=1e-3`, `weight_decay=1e-4`), batch size 1,024, seed `20261113`, and a median-outer-fold epoch rule. Stage 1b's exact matching configuration is `target_variant=depth_residualized_neighbor_mean`, `input=spot`, `model=mlp_spot`, `phase=mlp_outer_fit`.

The seven successful Stage 1b `selected_best_epoch` values for outer folds 0-6 are `1, 1, 2, 1, 1, 1, 3`. Their median is 1; rounding to the nearest integer remains **1 epoch**. This agrees with the one-epoch instruction in `PREREG_CONFIRM.md`; no conflict was found. No early stopping, validation split, hyperparameter search, or post-training epoch adjustment will be used.

### Frozen candidate

- **Input:** existing Stage 1 frozen ResNet-50 `IMAGENET1K_V2` spot embeddings, 2,048 features per 224x224 spot tile; no encoder fine-tuning and no new tile generation.
- **Network:** linear 2,048-to-128 layer, ReLU, then linear 128-to-12 output layer. The 12 outputs are the three Stage 1 QC-defined module targets followed by the nine normalized gene targets, in the Stage 1b `TARGETS` order. Only `myofibroblast_pro-fibrotic` is the pre-specified confirmation target; the other outputs are trained solely to preserve the preregistered 12-output Stage 1b architecture.
- **Target variant:** `depth_residualized_neighbor_mean`. For each of the 12 normalized targets, fit a weighted linear regression on `log1p(total spot UMI)` using original-cohort training spots, subtract its fitted values, and center training residuals within participant using participant-balanced weights. Then take the mean of available in-tissue neighbor residuals in the same library at offsets `(0, ±2)`, `(±1, ±1)`, excluding the center spot. Do not cross library boundaries or impute spots without neighbors; omit rows with non-finite target vectors from the fit.
- **Scaling:** fit weighted means and standard deviations for the embedding inputs and all 12 target columns using only finite training rows from the original 28. Weights give each participant equal total weight; non-finite or near-zero scales (`<1e-12`) are replaced by 1, as in Stage 1b.
- **Loss:** participant-balanced weighted mean squared error over the mean squared error of the 12 standardized output columns, matching the Stage 1b training objective.
- **Optimizer and schedule:** AdamW, learning rate `1e-3`, weight decay `1e-4`, batch size 1,024, exactly 1 epoch, no early stopping.
- **Seed:** `20261113` from `PREREG_CONFIRM.md`. Enable deterministic PyTorch algorithms and deterministic cuDNN behavior as in Stage 1b.

## Training cohort and separation

The fitting inputs are exclusively the original Stage 1 cohort: **28 participants, 29 libraries, 25,104 keyed spots**, uniquely identified by `(participant_id, library_id, barcode)`. The Stage 1 configuration records these reconciled counts and the Stage 1b loader asserts them before fitting. The model will be fitted once on finite transformed targets from this cohort only. No new-participant files, identifiers, labels, images, or outcomes will be accessed during this preparation.

All target-on-depth coefficients, participant centering values, input scaling values, and target scaling values are fitted from the original 28 only. The neighbor transform is restricted to the same original libraries. No confirmation-cohort labels or features enter fitting or preprocessing.

## Difference from Stage 1b models

Stage 1b fitted separate outer-fold models on subsets of participants, with fold-specific inner grouped validation, selected epochs, and derived per-fold seeds. This is a distinct single full-cohort fit on all original participants, with the fixed Stage 1c seed and the median epoch count. Its training predictions are only for a save/reload equivalence check and will not be reported as performance evidence.

## Source records fixed before training

- Confirmation protocol: `D:\patent\stage1c_confirm\PREREG_CONFIRM.md`, SHA-256 `23238d3727ab2a4102bfdc7a558df90100692d14bf8b014b05eef08253e0f729`.
- Stage 1b configuration ledger: `D:\patent\stage1b_expression\exploratory_posthoc_configuration_log.csv`, SHA-256 `c8decc727bc0f38a45923af53db710ad1aea5161acefc36378de31d0156cfffd`.
- Stage 1b implementation: `D:\patent\stage1b_expression\scripts\run_stage1b.py`, SHA-256 `2a92cc16250d963c30b71375d6ace22f4d54bda547433bd31621029ad81d89d0`.
- Encoder checkpoint reference: `D:\patent\stage1_expression\model_cache\checkpoints\resnet50-11ad3fa6.pth`, SHA-256 `11ad3fa62ca79e40addfd354a8ec4b7c75143b3038b8d2a807fbc68deab379ca`.

No conflict was found between the confirmation protocol and the matching Stage 1b model configuration or epoch records. Any change to these details requires a dated deviation before training.
