# Stage 1d-prep-2 — frozen comparison baselines

**Registered:** 2026-11-13T10:39:43+05:30  
**Status:** registered before baseline fitting. No Stage 1d evaluation or extra-participant data access is authorized here.  
**Stage 1 Gate A:** remains FAIL. Stage 1b remains exploratory, post-hoc.

## Scope and reconciliation

This addendum freezes only the two baselines specified in `PREREG_CONFIRM.md`: depth-only Ridge and colour-only Ridge. That confirmation protocol names no additional baseline. Stage 1b also implemented a patient-mean reference, but it is not named in the confirmation protocol and will not be fitted as part of this freeze.

The confirmation protocol and Stage 1b implementation agree on both baselines: fixed Ridge `alpha=1`, the `depth_residualized_neighbor_mean` target variant, and the inputs defined below. Stage 1b uses participant-balanced feature/target scaling and participant weights in Ridge fitting. The baseline routine is deterministic and does not use a random seed; it records no seed. The confirmation seed `20261113` applies to the MLP candidate, not these Ridge fits. No protocol/code conflict was found.

## Fixed fit cohort and targets

- Fit only on the original Stage 1 cohort: 28 participants, 29 libraries, and 25,104 spots keyed by `(participant_id, library_id, barcode)`.
- Use exactly the 25,092 rows with finite values across all 12 Stage 1b `depth_residualized_neighbor_mean` targets, matching the finite-target mask used for the frozen MLP. Do not impute the 12 no-neighbor rows.
- Preserve the Stage 1b target order: `ECM_collagen`, `myofibroblast_pro-fibrotic`, `matrix_remodelling`, `COL1A1`, `COL1A2`, `COL3A1`, `FN1`, `TGFB1`, `CCN2`, `ACTA2`, `MMP2`, `TIMP1`. The primary confirmation target is `myofibroblast_pro-fibrotic`; retaining all 12 outputs matches the multi-output Stage 1b Ridge implementation and supports only the preregistered exploratory secondary comparisons.
- Target construction is the same Stage 1b transformation: fit weighted linear regression of each normalized target on `log1p(total spot UMI)` using all 25,104 original-cohort spots; subtract fitted depth effect, center training residuals within participant using the participant-balanced weights, then average available immediate array-coordinate neighbors in the same library at offsets `(0, ±2)`, `(±1, ±1)`, excluding the center. No neighbor is imputed. This target-transform fit uses the same original-cohort procedure as the frozen MLP.
- Use only the 25,092 finite transformed rows for baseline input/target scaling and Ridge fitting, with participant weights recomputed over those finite rows exactly as Stage 1b does. No files, identifiers, labels, or outcomes for the 12 extra participants are to be opened or used.

## Frozen baseline definitions copied from Stage 1b

Both baselines use `sklearn.linear_model.Ridge(alpha=1.0)` with no alpha search or stochastic fitting. Each is a 12-output regression on the same row mask and target matrix.

### Depth-only Ridge

- **Input feature:** one column, `log1p(library_size_umi)`, where `library_size_umi` is the total spot UMI count recorded in the Stage 1 `targets_by_spot.csv` table. Stage 1b loads it as `np.log1p(frame["library_size_umi"].to_numpy(dtype=np.float64))`.
- **Scaling and fit:** weighted-standardize the one input column and all target columns using training-only weighted means and population standard deviations. The Stage 1b helper uses `np.average(..., weights=...)`; non-finite or `<1e-12` scales are replaced with 1. Fit Ridge on the standardized arrays with `sample_weight` and inverse-transform predictions using the stored target mean and scale.
- **Participant weights:** for the finite training rows, each spot has raw weight `1 / (number of finite training rows for its participant)`, then weights are divided by their overall mean. This gives every training participant equal total weight before the mean-one normalization used by Stage 1b.
- **Regularization and randomness:** `alpha=1.0`; no alpha selection and no random seed (deterministic Ridge).

### Colour-only Ridge

- **Input features:** the existing 12 Stage 1 colour statistics in this order: `rgb_mean_r`, `rgb_mean_g`, `rgb_mean_b`, `rgb_std_r`, `rgb_std_g`, `rgb_std_b`, `hsv_mean_h`, `hsv_mean_s`, `hsv_mean_v`, `hsv_std_h`, `hsv_std_s`, `hsv_std_v`.
- **Feature-generation function:** `color_statistics(rgb)` in `D:\\patent\\stage1_expression\\scripts\\run_stage1.py`. It expects a tile converted to RGB (`PIL.Image.convert("RGB")`, yielding uint8 RGB pixels); computes channel-wise means and population standard deviations over axes `(0, 1)` from raw RGB values; converts the same RGB array with `cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)` and computes the same statistics over HSV. Values are not otherwise normalized. OpenCV's HSV encoding is used (H 0–179; S and V 0–255). Stage 1b loads these exact features from `color_statistics.npz`. The confirmation protocol specifies the 224×224 spot tile; use the same tile-generation/mapping procedure when these features are applied to new tiles.
- **Scaling and fit:** weighted-standardize all 12 input and target columns using the same Stage 1b weighted-mean/population-standard-deviation procedure and scale guard described above. Fit Ridge on standardized arrays with participant `sample_weight`; store target mean/scale for inverse transformation.
- **Participant weights:** identical to depth-only Ridge, computed over the same finite training rows.
- **Regularization and randomness:** `alpha=1.0`; no alpha selection and no random seed (deterministic Ridge).

## Fixed source records

| Source | SHA-256 |
|---|---|
| `D:\\patent\\stage1c_confirm\\PREREG_CONFIRM.md` | `23238d3727ab2a4102bfdc7a558df90100692d14bf8b014b05eef08253e0f729` |
| `D:\\patent\\stage1b_expression\\scripts\\run_stage1b.py` | `2a92cc16250d963c30b71375d6ace22f4d54bda547433bd31621029ad81d89d0` |
| `D:\\patent\\stage1_expression\\scripts\\run_stage1.py` | `fc4a8e1eeee18b79b029aa5ecf1fb97ccf4a99d4fbe11f16a28d2e766a9b8d4c` |
| `D:\\patent\\stage1_expression\\targets_by_spot.csv` | `8dade8a328018e49c2c4bc6d5e63aed1347c18d03eba6ce295356add27fd2aa6` |
| `D:\\patent\\stage1_expression\\color_statistics.npz` | `f0d5d4ecf14f646f8347ba2374bc645f22973d1e824038cac984e2d9736d6264` |
| `D:\\patent\\stage1d_freeze\\frozen_scalers.npz` | `bdf441fb6d6640bfa419799d43ba50bd33965856770ec6e8a27e54daf6ce5409` |
| `D:\\patent\\stage1d_freeze\\residualization_parameters.csv` | `d3be232fc951b36b33fccf68ecfe4c6d4e6d2914e4015208d58084ce2d9c5157` |

No baseline fit or prediction computation has been performed at the time of this registration.
