# Stage FA Verification — EXPLORATORY, NOT CONFIRMATORY

**EXPLORATORY, NOT CONFIRMATORY. UNVALIDATED MASKS.**

## Result

Independent verification **PASSED: 22 of 22 checks**. The analysis-hash manifest contained 96 input/output file records; all 96 current SHA-256 values matched. The frozen RENFAST checkpoint matched the registered SHA-256:

`674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb`

## Independent recomputations

The verifier recomputed participant high-minus-low regression coefficients directly from the saved spot table. The maximum difference from the final per-participant table was 0. It then independently recomputed these three primary headline numbers from the 40 participant effects:

| Number | Recomputed | Saved final result | Check |
|---|---:|---:|---|
| U-Net mean participant effect | 0.1249339556 | 0.1249339556 | Match |
| Participant-bootstrap 95% CI lower bound | 0.0804065825 | 0.0804065825 | Match |
| Participant-bootstrap 95% CI upper bound | 0.1702242714 | 0.1702242714 | Match |

It also independently reproduced the U-Net depth-adjusted panel collagen-module rho (-0.07110694) and both image-colour eta-squared values (0.07565947 for U-Net and 0.38397479 for colour).

## Keys, groups, and alignment

- 34,735 complete participant + library + barcode spot keys were unique.
- 40 participants and 41 libraries were present; no library mapped to multiple participants.
- All 41 expression/image libraries passed; missing and extra keys were both zero.
- For each mask, all 34,735 spots had exactly one low, middle, or high tertile role. No library was excluded.
- An additional direct check confirmed all 16 final analysis tables carry both required labels.
- Stage FA did not use training/test folds, so fold-overlap checks are **NOT APPLICABLE**. Spot group exclusivity and participant/library mapping were checked instead.

## Environment and commands

- Python 3.13.1; NumPy 2.2.6; SciPy 1.18.1.
- Image run: `python -B D:\patent\stage_FA\FA_RUN_IMAGES.py` (72.743 seconds).
- Colour extraction: `python -B D:\patent\stage_FA\FA_EXTRACT_COLOUR.py` (55.759 seconds; saved score recheck difference 0).
- Corrected median-hue pass: `python -B D:\patent\stage_FA\FA_CORRECT_SLIDE_HUE.py` (19.062 seconds; no expression files read).
- Final analysis: `python -B D:\patent\stage_FA\FA_ANALYZE.py` (1,371.456 seconds; below the registered 90-minute cap).
- Verification: `python -B D:\patent\stage_FA\FA_VERIFY.py` (1.409 seconds).
- Seed: `20261117` for the primary participant bootstrap; the final run metadata records all target and label-shuffle seeds.
- Final analysis output folder size at completion: 144,054,001 bytes, below the 8 GB cap.

The exact file hashes are in [FA_ANALYSIS_HASHES_FINAL.csv](./FA_ANALYSIS_HASHES_FINAL.csv) and [FA_VERIFICATION_HASHES_FINAL.csv](./FA_VERIFICATION_HASHES_FINAL.csv). The verification check rows are in [FA_VERIFICATION_FINAL.csv](./FA_VERIFICATION_FINAL.csv); run versions and counts are in [FA_VERIFICATION_METADATA_FINAL.json](./FA_VERIFICATION_METADATA_FINAL.json).

## Limitations

The three overlay reviews checked spot-to-image placement only; they do not validate fibrosis masks. Gate 1 remains **NOT PASSED**. The final tables ending in `_FINAL` are the results to use. The unsuffixed first-pass analysis tables remain unchanged but are invalid and superseded because constant tissue-fraction columns caused 39 participants to be discarded and produced a misleading one-participant result. The intermediate `_CORRECTED` tables fixed that issue but used an incorrect label-shuffle procedure. D-006 and D-007 are recorded in [FA_DEVIATIONS.md](./FA_DEVIATIONS.md).
