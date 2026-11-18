# Stage 1d confirmation model freeze

This folder contains the preregistered full-cohort confirmation candidate and its reproducibility artifacts. It does not contain Stage 1d results. No extra-participant files are read, downloaded, or processed.

## Frozen design

- Train once on existing Stage 1 data only: 28 participants, 29 libraries, 25,104 keyed spots.
- Candidate: frozen ResNet-50 `IMAGENET1K_V2` spot embedding and `mlp_spot` (2,048 inputs, 128 ReLU hidden units, 12 outputs).
- Target transform: `depth_residualized_neighbor_mean`; score target for a later confirmation remains the myofibroblast/profibrotic module.
- Seed `20261113`, AdamW (`lr=1e-3`, `weight_decay=1e-4`), batch size 1,024, one epoch. The one-epoch count is the median of the seven matching Stage 1b selected epochs.
- Fit residualization, participant centering, and input/target scalers on the original 28 only.
- Stage 1b implementation and configuration hashes are recorded in `PREREG_ADDENDUM.md` and `training_metadata.json`.

## Reproduction commands

Run from PowerShell with the pinned environment:

```powershell
python D:\patent\stage1d_freeze\train_frozen_confirmation.py --preflight
python D:\patent\stage1d_freeze\train_frozen_confirmation.py
```

The training command fits one model, saves the frozen artifacts, then launches a separate Python process with `--verify-reload`. The second process reloads only the original Stage 1 inputs and saved artifacts, compares keyed predictions against the in-process reference, and records the maximum absolute difference. It does not fit another model or compute performance metrics.

## Files

- `PREREG_ADDENDUM.md`: timestamped, pre-training protocol and selected-epoch calculation.
- `train_frozen_confirmation.py`: exact preparation, one-fit, serialization, and fresh-process verification code.
- `frozen_model_state.pt`: trained prediction head; the encoder weights remain at the referenced Stage 1 checkpoint.
- `frozen_scalers.npz` and `frozen_scalers.csv`: input and target scaling parameters and names/order.
- `residualization_parameters.csv`: target-on-depth coefficients and participant residual-centering values.
- `input_feature_names.json`: ordered 2,048-dimensional embedding feature names.
- `encoder_reference.json`: encoder path, size, and SHA-256.
- `in_process_predictions.npz`, `reload_predictions.npz`, `reload_verification.json`: keyed reload-equivalence check only, not performance results.
- `training_metadata.json`: fixed configuration, cohort reconciliation, software versions, and source hashes.
- `MODEL_MANIFEST.csv`: SHA-256 and size for each artifact and source dependency; its own checksum is recorded in `LAB_NOTEBOOK.md`.
- `STAGE1D_PREP_REPORT.md`: freeze status, checksums, and limitations.
- `LAB_NOTEBOOK.md`: append-only record of the freeze and artifact checksums.

All frozen artifacts are marked read-only after validation. `LAB_NOTEBOOK.md` remains writable for future append-only entries.
