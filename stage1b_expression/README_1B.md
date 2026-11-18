# Stage 1b reproducibility — exploratory, post-hoc

**Label: exploratory, post-hoc.** Stage 1 Gate A remains **FAIL**.

## Purpose and constraints

This follow-up uses Stage 1's cached spot embeddings and keyed target inputs to assess converged Elastic Net fits and an MLP with participant-grouped early stopping. It does not alter Stage 1, use trichrome/collagen values, register images, batch-correct, or fine-tune an encoder. The exact analysis budget is in `PREREG_1B.md`.

The immutable key is `(participant_id, library_id, barcode)`. Counts and the saved seven participant-grouped folds are asserted before model fitting. No new encoder weights, images, or external data are downloaded.

## Reproduction command

From PowerShell:

```powershell
python D:\patent\stage1b_expression\scripts\run_stage1b.py
```

If a run stops after a saved fold checkpoint, resume the remaining folds without discarding the attempt ledger:

```powershell
python D:\patent\stage1b_expression\scripts\run_stage1b.py --resume
```

The script uses the existing inputs under `D:\patent\stage1_expression\`, appends per-fit configuration and MLP loss records, and checkpoints keyed out-of-fold predictions after each completed fold. It does not modify Stage 1 or raw data.

If a completed run has checkpointed predictions but an incomplete MLP ledger, replay the same MLP fits and regenerate final summaries with:

```powershell
python D:\patent\stage1b_expression\scripts\run_stage1b.py --resume --repair-mlp-ledger
```

## Fixed inputs, methods, and seeds

- Encoder: frozen torchvision ResNet-50 `IMAGENET1K_V2`; reuse the existing 2,048-dimensional spot embeddings. No second encoder.
- Targets: the three QC-defined simple-mean modules followed by nine normalized genes. Depth residualization is re-fit using only each applicable training split. The neighbor target averages the six adjacent in-tissue Visium spots, excluding the center, within a library.
- Outer folds: the saved seven participant-grouped folds from Stage 1.
- Elastic Net: independent per-target squared-error Elastic Net (`l1_ratio=0.5`); alpha grid `[0.001, 0.01, 0.1]`; four-fold participant-grouped inner CV; select by participant-balanced validation MSE across standardized targets; vectorized proximal FISTA with a 50,000-iteration cap and relative proximal-gradient stopping tolerance `1e-4`. Alpha candidates are evaluated high-to-low with warm starts. All solver and objective deviations, plus discarded/interrupted attempts, are timestamped in `PREREG_1B.md` and the configuration log.
- MLP: 128 hidden ReLU units, AdamW (`lr=1e-3`, `weight_decay=1e-4`), batch size 1,024; maximum 200 epochs, patience 15; inner validation split grouped by participant.
- Baselines: training participant-mean reference, depth-only Ridge (`alpha=1`), and colour-only Ridge (`alpha=1`).
- Seeds derive deterministically from `20261112`; participant bootstrap uses `20261212` with 10,000 resamples. Torch deterministic algorithms are enabled.
- Evaluation: per-participant spot Spearman; 95% participant-bootstrap CIs; non-overlapping 10-by-10 array-coordinate blocks for region-level Spearman; fixed participant-level eligibility rules; no spot-wise bootstrap.
- D: available free space before outputs was 118,152,273,920 bytes. Individual outputs are checked to remain below 1 GB.

## Software and terms

Versions observed at preregistration:

```text
Python 3.13.1
NumPy 2.2.6
pandas 3.0.6
SciPy 1.18.1
scikit-learn 1.6.1
PyTorch 2.7.1+cu118
torchvision 0.22.1+cu118
matplotlib 3.10.8
```

The torchvision code is BSD-3-Clause. Weight-specific terms and upstream ImageNet dataset terms were not independently verified. Do not redistribute source images or weights.

## Output inventory

All analysis outputs are prefixed `exploratory_posthoc_` and include the label `exploratory, post-hoc`.

- `PREREG_1B.md`: timestamped, fixed-budget protocol.
- `scripts\run_stage1b.py`: preparation, grouped inner validation, fitting, metrics, verification, plots, and report generator.
- `exploratory_posthoc_fold_assignments.csv`: spot keys and unchanged folds.
- `exploratory_posthoc_configuration_log.csv`: every baseline, outer fit, and Elastic Net alpha/inner-fold attempt, including failures and convergence status.
- `exploratory_posthoc_loss_curves.csv`: MLP train/validation loss per epoch, phase, fold, and selected/stopped epochs.
- `exploratory_posthoc_predictions_partial.npz`: last completed-fold checkpoint.
- `exploratory_posthoc_predictions.npz`: keyed out-of-fold predictions and targets.
- `exploratory_posthoc_residualization_coefficients.csv`: fold-specific target-on-depth nuisance fits.
- `exploratory_posthoc_neighbor_counts.csv`: immediate-neighbor counts by key and outer split.
- `exploratory_posthoc_participant_metrics.csv`: participant-level spot Spearman, MAE, eligibility, and patient-mean wins.
- `exploratory_posthoc_participant_block_metrics.csv`: participant-level spatial-block Spearman and exclusions.
- `exploratory_posthoc_metric_summary.csv`: module-first then gene participant-bootstrap summaries.
- `exploratory_posthoc_comparison_summary.csv`: paired candidate-minus-baseline spot and block results.
- `exploratory_posthoc_metric_recompute_verification.csv`, `exploratory_posthoc_verification_checks.csv`: independent recomputation and cohort/key/fold checks.
- `exploratory_posthoc_spot_*_summary.png`, `exploratory_posthoc_block_*_summary.png`: labeled figures with participant-bootstrap CIs.
- `exploratory_posthoc_report.md`: final Stage 1b report; Stage 1 Gate A remains FAIL.
- `LAB_NOTEBOOK.md`: dated append-only decision and result log.
- `requirements-stage1b.txt`: pinned observed package versions.

Stage 1b is exploratory and post-hoc. Its results cannot reverse Gate A or by themselves authorize registration or fusion.
