# Phase C Integrity Check

## Preregistration and analysis integrity

- `PHASEC_PREREG.md` was timestamped before Phase C evaluations and new training runs; it was not edited afterward.
- The Phase A active split was copied to `PHASEC_SPLIT_MANIFEST.csv` without the 127 excluded pairs. Split counts are 105/18/50 pairs across 6/1/10 filename families; no family overlap was found. These are filename families, not verified patient or slide IDs.
- The 20 Phase B2 excluded tiles were inventoried by opaque filename only. No B2 image pixels, private key, or annotation results were read.
- Test pixels were opened only after the two under-budget U-Net runs completed. No test threshold or hyperparameter was tuned.
- The DeepLab run was blocked before training because its training-only preflight projection was 8,070.79 seconds, above the 7,200-second cap. No DeepLab test results exist.
- The preregistered metrics, success rules, thresholds, perturbation levels, OOD rule, bootstrap unit, and seeds were not changed.

## Scripts and edits after results were visible

1. `PHASEC_run.py` was changed after the evaluation output was visible to copy NumPy inference inputs before `torch.from_numpy`, avoiding a warning for read-only transformed arrays. The input values and model logits are exactly unchanged on a synthetic test; model weights, metric calculations, transformations, and criteria were untouched.
2. `PHASEC_verify.py` was not edited after test outputs became visible.
3. Direction-aware summaries were generated from the saved per-image CSV after reviewing output. The original paired-mean rows were retained; direction-specific rows are correctly represented in `PHASEC_robustness_direction_summary.csv` and the combined canonical `PHASEC_robustness_summary_corrected.csv`. No model was rerun and no success rule was changed.

## Independent numerical verification

`PHASEC_verify.py` made a separate pass over the saved checkpoints and official test pairs. It recomputed:

| Quantity | Recomputed | Reported | Absolute difference |
|---|---:|---:|---:|
| Frozen U-Net image-macro Dice | 0.9153306335833998 | 0.9153306335833998 | 0.0 |
| Colour-threshold family-macro Dice | 0.8249237311604960 | 0.8249237311604960 | 0.0 |
| Ensemble Brier score | 0.04663174521178007 | 0.04663174521178007 | 0.0 |

See [PHASEC_VERIFICATION.json](./PHASEC_VERIFICATION.json). The archive and checkpoint SHA-256 values match the Phase A records. The test set contains 50 pairs from 10 filename families.

## Unverified items

- RENFAST's dataset licence field is blank, and the scope of the user-reported permission remains unresolved; no permission wording was interpreted.
- Filename-family separation does not verify patient- or slide-level separation.
- The DeepLabV3-ResNet50 performance comparison is blocked; its threshold was not selected.
- The two-hour preflight is an estimate based on measured one-batch timing scaled by the recorded Phase A runtime. No DeepLab training run was launched.
- Run elapsed durations were recorded to hundredths of a second; explicit wall-clock start/end fields were not saved. README start times are estimates from file modification times.
