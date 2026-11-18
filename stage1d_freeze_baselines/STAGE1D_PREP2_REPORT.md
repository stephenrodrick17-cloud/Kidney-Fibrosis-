# Stage 1d-prep-2 — frozen comparison baselines

**Fit timestamp:** 2026-11-13T10:44:42+05:30
**Status:** comparison baselines frozen; Stage 1d evaluation not started.
**Stage 1 Gate A:** remains FAIL. Stage 1b remains exploratory, post-hoc.

## What was frozen

- Fitted depth-only Ridge (`alpha=1`) and colour-only Ridge (`alpha=1`) exactly as the Stage 1b fixed-baseline implementation, using `depth_residualized_neighbor_mean` targets.
- Training used only the original 28 participants, 29 libraries, and 25,092 finite-target rows out of 25,104 keyed spots. Twelve rows with no available neighbor were omitted without imputation.
- Both multi-output baselines retain the 12 Stage 1b targets in the registered order. The primary confirmation target is `myofibroblast_pro-fibrotic`.
- Target scaling was checked against the frozen MLP target scaler; maximum difference was at most 1e-12.
- Colour features are computed by `color_statistics(rgb)` in `run_stage1.py`; feature names, pixel value ranges, and parameters are recorded in `baseline_feature_definitions.json`.
- No model performance was computed or reported. No data for the 12 extra participants was opened, downloaded, or used.

## Fresh-process reload verification

- Reloaded predictions cover all 25,104 original spot keys in the same order.
- Depth-only Ridge: bitwise identical = True; maximum absolute difference = 0.
- Colour-only Ridge: bitwise identical = True; maximum absolute difference = 0.
- This is a serialization/reproducibility check, not a performance evaluation.

## Source hashes

- `D:\patent\stage1c_confirm\PREREG_CONFIRM.md` — `23238d3727ab2a4102bfdc7a558df90100692d14bf8b014b05eef08253e0f729`
- `D:\patent\stage1b_expression\scripts\run_stage1b.py` — `2a92cc16250d963c30b71375d6ace22f4d54bda547433bd31621029ad81d89d0`
- `D:\patent\stage1_expression\scripts\run_stage1.py` — `fc4a8e1eeee18b79b029aa5ecf1fb97ccf4a99d4fbe11f16a28d2e766a9b8d4c`
- `D:\patent\stage1_expression\targets_by_spot.csv` — `8dade8a328018e49c2c4bc6d5e63aed1347c18d03eba6ce295356add27fd2aa6`
- `D:\patent\stage1_expression\color_statistics.npz` — `f0d5d4ecf14f646f8347ba2374bc645f22973d1e824038cac984e2d9736d6264`
- `D:\patent\stage1d_freeze\frozen_scalers.npz` — `bdf441fb6d6640bfa419799d43ba50bd33965856770ec6e8a27e54daf6ce5409`
- `D:\patent\stage1d_freeze\residualization_parameters.csv` — `d3be232fc951b36b33fccf68ecfe4c6d4e6d2914e4015208d58084ce2d9c5157`

The complete artifact and source-reference SHA-256 inventory is in `MODEL_MANIFEST.csv`. The manifest excludes itself; its hash is recorded in the append-only Stage 1d lab notebook.

## Deviations and remaining limits

- No deviations from the frozen baseline definitions were found.
- No confirmation-cohort files or outcomes were used. Stage 1d evaluation remains unrun and awaits explicit instruction.
