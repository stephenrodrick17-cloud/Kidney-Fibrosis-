# Phase B Integrity Check

- `PHASEB_PREREG.md` was timestamped before region selection and model inference.
- `PHASEB_select_regions.py` and its preregistered outputs recorded all selected regions before inference; selection did not use model outputs.
- A stratum-field propagation issue in the selection script was corrected before the selection script was run. The corrected file passed syntax validation; the manifest and slide audit include the resulting stratum assignments.
- `PHASEB_run_external_check.py` was written and syntax-checked before model inference. It verified the frozen checkpoint hash, Phase A metadata, and fixed thresholds before loading the model.
- `PHASEB_verify_outputs.py` was added after inference outputs were visible. It only recomputes stored-pixel area differences, objective flags, counts, output dimensions, blank form status, and the top-10 ranking; it does not change model outputs or analysis rules.
- No script was edited after results became visible to alter model behavior, selected regions, metric definitions, thresholds, or success criteria.
- Verification recomputed 40 regions, 10 per colour stratum, 25 participant IDs, 26 slides, maximum 3 regions per slide, all five objective flag counts, per-region area comparisons, and the top-10 disagreement order.
- Verification status: `verified`; see `PHASEB_VERIFICATION.json`.
- Existing files and raw slide data were not overwritten or modified.
