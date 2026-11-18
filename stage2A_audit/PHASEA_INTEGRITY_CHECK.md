# Phase A Integrity Check

## Inputs and preservation

- RENFAST ZIP SHA-256: `f796f0fa585701d66bd8f6b0ed096bb30f4376eff3359cb32ccbf1fd64d08a4e`.
- Frozen checkpoint SHA-256: `674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb`.
- The existing archive, checkpoint, pair manifest, model source, previous metrics, and prior reports were read only. No raw image, mask, archive, checkpoint, or pre-existing report was changed.
- New files in the audit directory use the `PHASEA_` prefix. The analysis script refuses to overwrite its declared outputs. Corrected outputs were written as new `PHASEA_final_*` files; the earlier first-run files remain unchanged.

## Split and count verification

- 105 training pairs / 6 filename families.
- 18 validation pairs / 1 filename family.
- 50 test pairs / 10 filename families.
- 127 unique training pairs in test-overlapping filename families were excluded.
- 250 byte-identical duplicate training entries were not used.
- The script checked pairwise-disjoint active family sets and verified none overlap. These are filename families, not verified patient or slide IDs.
- [PHASEA_final_split_manifest.csv](./PHASEA_final_split_manifest.csv) records unique pair assignments and hashes.

## Independent metric recomputation checks

The final run decoded the saved test pairs and recomputed test predictions/metrics from the frozen checkpoint. It independently matched the saved per-image results within absolute tolerance `1e-12` for:

1. Dice
2. IoU
3. Recall (the saved sensitivity metric)

The 50-image macro Dice was `0.9153306335833998`, equal to the saved full-precision result. It rounds to `0.9153`, matching the report. The colour threshold was tuned only on the 105 training pairs and then frozen before test scoring.

## Post-result code edit and result provenance

After the first run's results were visible, one script edit was made to `PHASEA_run_audit.py`: the secondary bootstrap had been passed one family mean per group, which could not resample images within families. The edit changed the secondary bootstrap input to the per-image values within each family and changed output paths to new `PHASEA_final_*` names. The primary group-bootstrap calculation, metric definitions, colour threshold rule, success rule, model, and checkpoint were not changed.

Because of that correction, the secondary CIs in the first-run files `PHASEA_metrics.json`, `PHASEA_per_image_metrics.csv`, `PHASEA_per_group_metrics.csv`, `PHASEA_split_manifest.csv`, and `PHASEA_failure_gallery.png` are preliminary and should not be used. The corrected results are the `PHASEA_final_*` files.

The evaluation script was run a second time to calculate the corrected secondary intervals. No thresholds or model settings were selected from test results. The repeated test scoring is a logged deviation; see [PHASEA_DEVIATIONS.md](./PHASEA_DEVIATIONS.md).

## Reproducibility

- Python 3.13.1; NumPy 2.2.6; Pillow 11.1.0; PyTorch 2.7.1+cu118; CUDA was available.
- Primary family bootstrap seed: `20261117`; secondary within-family image bootstrap seed: `20261118`; 10,000 resamples each.
- Exact final-run command and all files/versions are listed in [PHASEA_README.md](./PHASEA_README.md).
- Pylance Python syntax check passed for `PHASEA_run_audit.py`; both evaluation commands exited with code 0.

## Integrity conclusion

The preregistered success rule and metrics were not changed after results became visible. One secondary-bootstrap implementation bug was corrected transparently; initial outputs were preserved and superseded by clearly named corrected outputs. No Phase B work was started.
