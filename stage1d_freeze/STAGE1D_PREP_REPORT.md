# Stage 1d-prep report

**Generated:** 2026-11-13T10:35:16+05:30  
**Status:** frozen candidate prepared; Stage 1d has not been started.  
**Stage 1 Gate A:** remains FAIL. Stage 1b remains exploratory, post-hoc.

## What was frozen

- **PREREG_ADDENDUM.md:** The addendum was written and checked before the single training fit.
- **model:** mlp_spot: 2048 input features -> 128 ReLU units -> 12 outputs.
- **target_variant:** depth_residualized_neighbor_mean; only the myofibroblast/profibrotic module is the pre-specified later confirmation target.
- **optimizer:** AdamW, learning rate 1e-3, weight decay 1e-4; batch size 1024; one epoch; seed 20261113.
- **loss:** Participant-balanced weighted MSE over the mean squared error of the 12 standardized outputs.
- **epoch_rule:** Seven matching successful Stage 1b outer fits had selected_best_epoch values [1,1,2,1,1,1,3]; median 1, rounded to 1.

## Training scope and preprocessing

- Source cohort: the original Stage 1 outputs only; 28 participants, 29 libraries, 25,104 spots, with unique `(participant_id, library_id, barcode)` keys. No extra-cohort data files or outcomes were opened, downloaded, or used.
- All 25,104 keyed spots were considered for target residualization and prediction. The registered neighbor rule yielded 25,092 finite target rows for fitting; 12 spots without any available same-library neighbor were omitted, without imputation. All 28 participants remained represented.
- Target-on-depth coefficients and participant residual-centering values were fitted using only the original cohort. Input and target scaling were fitted on the 25,092 finite original-cohort fit rows with participant-balanced weights.
- Existing precomputed 2,048-dimensional spot embeddings were used; no tiles or encoder weights were regenerated or fine-tuned. The model outputs all 12 Stage 1 targets in the recorded order; only the pre-specified module is relevant to the later confirmation.

## Reproducibility check

- A separate Python process reloaded the weights and scalers and generated predictions for the original cohort's 25,104 keyed spots (28 participants, 29 libraries). Keys matched in order; maximum absolute prediction difference was **0.0** and predictions were bitwise identical.
 - These predictions were generated only to verify save/reload equivalence. No training-set performance metric or model-comparison result is reported.
- Device/software: CUDA; Python 3.13.1, NumPy 2.2.6, pandas 3.0.6, SciPy 1.18.1, scikit-learn 1.6.1, PyTorch 2.7.1+cu118, torchvision 0.22.1+cu118. Pinned versions and commands are in `README.md` and `requirements-stage1d-freeze.txt`.

## Checksums

Primary artifact checksums (the full file-and-source inventory is in `MODEL_MANIFEST.csv`; its own hash is recorded in `LAB_NOTEBOOK.md`):

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `PREREG_ADDENDUM.md` | 5,642 | `9096326b8dbe8a73f23f75bde5da180cbd0859edff2e9c0973919861bd63641a` |
| `train_frozen_confirmation.py` | 18,719 | `b51b55fb0702d81038f6392385e3a3ed276b97ef97e2a91761680a7216d819c6` |
| `frozen_model_state.pt` | 1,057,739 | `c96568c1e36e4060b2377c0346b86a830a53b9486fa40b9f696c29ed8820ad53` |
| `frozen_scalers.npz` | 39,605 | `bdf441fb6d6640bfa419799d43ba50bd33965856770ec6e8a27e54daf6ce5409` |
| `frozen_scalers.csv` | 171,287 | `e1357f396b82622565bbd4af10f31aca86d384deb0f8cc6de471a40c5c5ee037` |
| `residualization_parameters.csv` | 32,671 | `d3be232fc951b36b33fccf68ecfe4c6d4e6d2914e4015208d58084ce2d9c5157` |
| `input_feature_names.json` | 75,904 | `31b1289267096a5c395cbe55cff49cc055ca46473ea8a14f656016bbb0e3d260` |
| `encoder_reference.json` | 342 | `d9ced65240bf5b8010f126fddc77c2049e0ac635eea7d619f530bff229b019ac` |
| `training_metadata.json` | 2,689 | `6516d5c1a13cc80cb6bc28a901dee2c79df0cc192191c48643af8c4f8372f3e8` |
| `in_process_predictions.npz` | 2,552,874 | `00aefd608565cc8c73abea3a9c8241f9bf31e58741a48c098060fb2c6bda80c9` |
| `reload_predictions.npz` | 2,552,874 | `00aefd608565cc8c73abea3a9c8241f9bf31e58741a48c098060fb2c6bda80c9` |
| `reload_verification.json` | 269 | `f9ecdf1a1d331d4685c96029c94b5d4e568efb080ffb3d9dd19f452db74710d9` |
| `requirements-stage1d-freeze.txt` | 132 | `677d5a9619d4dce0b5e845f9e1d96d23e90f8ddd79f8f80cd3caaaccf1df0827` |
| `ResNet-50 encoder checkpoint (external reference)` | 102,540,417 | `11ad3fa62ca79e40addfd354a8ec4b7c75143b3038b8d2a807fbc68deab379ca` |

## Deviations and limitations

- **Protocol deviations:** none. The one training fit used the registered architecture, target variant, optimizer, learning rate, batch size, seed, and epoch count.
- An initial no-training preflight exposed an empty evaluation-slice limitation in the implementation; it was fixed and rechecked before training. That attempt did not fit a model or inspect results.
- No new-participant data were accessed or evaluated, and no Stage 1d primary or secondary metric was computed. The confirmation hypothesis remains untested.
- Stage 1b fold-specific models differ from this full-cohort frozen model; training predictions are not evidence of generalization. Stage 1 Gate A is unchanged.
- Frozen files are marked read-only after checksum recording; `LAB_NOTEBOOK.md` remains writable for append-only future entries.

## Stop

Stage 1d-prep is complete. Stop here. Do not download or evaluate the extra participants and do not begin any later stage without explicit instruction.
