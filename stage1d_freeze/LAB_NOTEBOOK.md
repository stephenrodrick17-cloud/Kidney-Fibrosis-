# Stage 1d-prep lab notebook

## 2026-11-13 - Full-cohort confirmation candidate frozen

- Addendum registered before the fit at 2026-11-13T10:25:53+05:30; matching Stage 1b epochs were [1, 1, 2, 1, 1, 1, 3], median/rounded epoch count 1.
- Trained one `mlp_spot` model on original Stage 1 data only: 28 participants, 29 libraries, 25,104 keyed spots; 25,092 rows had finite neighbor-mean targets, and 12 no-neighbor rows were not imputed.
- Fixed seed 20261113, one epoch, AdamW (1e-3 learning rate; 1e-4 weight decay), batch size 1,024; 2,048-128-12 architecture.
- Fresh-process reload check on all original keys was bitwise identical; max absolute difference 0.0. This is a serialization check, not a performance result. No extra-cohort data or outcome was used.
- Stage 1 Gate A remains FAIL; Stage 1b remains exploratory, post-hoc. Stage 1d was not started.

### SHA-256 inventory

| Scope | Path | SHA-256 |
|---|---|---|
| freeze_artifact | `D:\patent\stage1d_freeze\encoder_reference.json` | `d9ced65240bf5b8010f126fddc77c2049e0ac635eea7d619f530bff229b019ac` |
| freeze_artifact | `D:\patent\stage1d_freeze\frozen_model_state.pt` | `c96568c1e36e4060b2377c0346b86a830a53b9486fa40b9f696c29ed8820ad53` |
| freeze_artifact | `D:\patent\stage1d_freeze\frozen_scalers.csv` | `e1357f396b82622565bbd4af10f31aca86d384deb0f8cc6de471a40c5c5ee037` |
| freeze_artifact | `D:\patent\stage1d_freeze\frozen_scalers.npz` | `bdf441fb6d6640bfa419799d43ba50bd33965856770ec6e8a27e54daf6ce5409` |
| freeze_artifact | `D:\patent\stage1d_freeze\in_process_predictions.npz` | `00aefd608565cc8c73abea3a9c8241f9bf31e58741a48c098060fb2c6bda80c9` |
| freeze_artifact | `D:\patent\stage1d_freeze\input_feature_names.json` | `31b1289267096a5c395cbe55cff49cc055ca46473ea8a14f656016bbb0e3d260` |
| freeze_artifact | `D:\patent\stage1d_freeze\PREREG_ADDENDUM.md` | `9096326b8dbe8a73f23f75bde5da180cbd0859edff2e9c0973919861bd63641a` |
| freeze_artifact | `D:\patent\stage1d_freeze\README.md` | `213d3d1997bde37ebd1d6931f73bf336674f7eca6d1660476b31982bbeea887c` |
| freeze_artifact | `D:\patent\stage1d_freeze\reload_predictions.npz` | `00aefd608565cc8c73abea3a9c8241f9bf31e58741a48c098060fb2c6bda80c9` |
| freeze_artifact | `D:\patent\stage1d_freeze\reload_verification.json` | `f9ecdf1a1d331d4685c96029c94b5d4e568efb080ffb3d9dd19f452db74710d9` |
| freeze_artifact | `D:\patent\stage1d_freeze\requirements-stage1d-freeze.txt` | `677d5a9619d4dce0b5e845f9e1d96d23e90f8ddd79f8f80cd3caaaccf1df0827` |
| freeze_artifact | `D:\patent\stage1d_freeze\residualization_parameters.csv` | `d3be232fc951b36b33fccf68ecfe4c6d4e6d2914e4015208d58084ce2d9c5157` |
| freeze_artifact | `D:\patent\stage1d_freeze\STAGE1D_PREP_REPORT.md` | `96bd176e6dcecc03582942819d6eb1403b7a2c4bc97e2b132d863190163581ed` |
| freeze_artifact | `D:\patent\stage1d_freeze\train_frozen_confirmation.py` | `b51b55fb0702d81038f6392385e3a3ed276b97ef97e2a91761680a7216d819c6` |
| freeze_artifact | `D:\patent\stage1d_freeze\training_metadata.json` | `6516d5c1a13cc80cb6bc28a901dee2c79df0cc192191c48643af8c4f8372f3e8` |
| source_reference | `D:\patent\stage1c_confirm\PREREG_CONFIRM.md` | `23238d3727ab2a4102bfdc7a558df90100692d14bf8b014b05eef08253e0f729` |
| source_reference | `D:\patent\stage1b_expression\exploratory_posthoc_configuration_log.csv` | `c8decc727bc0f38a45923af53db710ad1aea5161acefc36378de31d0156cfffd` |
| source_reference | `D:\patent\stage1b_expression\scripts\run_stage1b.py` | `2a92cc16250d963c30b71375d6ace22f4d54bda547433bd31621029ad81d89d0` |
| source_reference | `D:\patent\stage1_expression\stage1_config.json` | `cbf5c252944f833523ff3c439694e162eb5ecdd6c372042ddbc3d9c65fbb4027` |
| source_reference | `D:\patent\stage1_expression\targets_by_spot.csv` | `8dade8a328018e49c2c4bc6d5e63aed1347c18d03eba6ce295356add27fd2aa6` |
| source_reference | `D:\patent\stage1_expression\spot_embeddings.npz` | `6130ad5fcdc4bbc3315296e05d58965f290b61bf88e9c3a369844edd870b4183` |
| source_reference | `D:\patent\stage1_expression\color_statistics.npz` | `f0d5d4ecf14f646f8347ba2374bc645f22973d1e824038cac984e2d9736d6264` |
| source_reference | `D:\patent\stage1_expression\model_cache\checkpoints\resnet50-11ad3fa6.pth` | `11ad3fa62ca79e40addfd354a8ec4b7c75143b3038b8d2a807fbc68deab379ca` |
| freeze_artifact | `MODEL_MANIFEST.csv` | `8fd1784745fcc62fe51af59f0e332115bdfee2700c44d6f7acee724ddfc31d84` |

This notebook is append-only. The manifest excludes itself and this notebook to avoid recursive checksums; the manifest checksum is listed above.


## 2026-11-13 — Stage 1d-prep-2 comparison baselines

- Registered `stage1d_freeze_baselines\PREREG_ADDENDUM_2.md` before fitting. Frozen definitions: Stage 1b depth-only and colour-only Ridge, both alpha=1, on the original 28 participants only.
- Fit both models on the same 25,092 finite `depth_residualized_neighbor_mean` rows as the frozen MLP; no Stage 1d metrics were computed and no extra-participant data was accessed.
- Fresh-process reload predictions were bitwise identical for both baselines; see the prep-2 report and `reload_verification.json`.

### Stage 1d-prep-2 artifact SHA-256

| Path | SHA-256 |
|---|---|
| `D:\patent\stage1d_freeze_baselines\baseline_coefficients.csv` | `0b7c060438e8f2924afdcce172b03668f92616899fc5ce3f8ebd184de54e8b54` |
| `D:\patent\stage1d_freeze_baselines\baseline_feature_definitions.json` | `b689a3ed37f51edac46313644032172c9601b347997eeae157c81aaf0625f452` |
| `D:\patent\stage1d_freeze_baselines\baseline_scaler_values.csv` | `e54cd4fa92b7767f020718d738119cfbe1b47a4674e070222e9012bfbe28e664` |
| `D:\patent\stage1d_freeze_baselines\baseline_scalers.npz` | `0b2d68e9972fe55c933cdb13d8f3c0a9f62fbd0c9799b7fa1c64ba45a06d6758` |
| `D:\patent\stage1d_freeze_baselines\freeze_comparison_baselines.py` | `a0a41684a52604208914bc8151f785294f7f42c1b93f0107cdd8ce0effed1bad` |
| `D:\patent\stage1d_freeze_baselines\frozen_ridge_models.joblib` | `9628fa34eacba0915d805148c5f0129fa7cf01a6b3b7b24bd3298b428d25041f` |
| `D:\patent\stage1d_freeze_baselines\in_process_predictions.npz` | `aa41f6b66c00f97bc9ef6931255d437b3ee4283e0af2328b6bc1b5227d3bd1b5` |
| `D:\patent\stage1d_freeze_baselines\PREREG_ADDENDUM_2.md` | `c6fe81ce73324596da5b2a9f1de9db665a946f3d4976e469ae2cc22d430ad067` |
| `D:\patent\stage1d_freeze_baselines\reload_predictions.npz` | `aa41f6b66c00f97bc9ef6931255d437b3ee4283e0af2328b6bc1b5227d3bd1b5` |
| `D:\patent\stage1d_freeze_baselines\reload_verification.json` | `a61e4a4d2733176ad0db846b3e6846253d6710c66e1e8ef034251bcf6aec1e89` |
| `D:\patent\stage1d_freeze_baselines\STAGE1D_PREP2_REPORT.md` | `9e487b7c8c33bbd8d4b2c8e6a96249e4746c756a15727b7775ec5ad556e5ba0d` |
| `D:\patent\stage1d_freeze_baselines\target_residualization_parameters.csv` | `d3be232fc951b36b33fccf68ecfe4c6d4e6d2914e4015208d58084ce2d9c5157` |
| `MODEL_MANIFEST.csv` | `23fd7c80233ca9399843866bed93d0ec8b3b4b429523422fcc491aab05c99592` |

The manifest excludes itself and this append-only notebook to avoid recursive checksums.
