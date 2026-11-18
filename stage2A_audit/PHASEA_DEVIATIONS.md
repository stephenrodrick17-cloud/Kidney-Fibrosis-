# Phase A Deviations Log

All split groups referenced below are filename families, not verified patient or slide IDs.

## 2026-11-16 — Secondary bootstrap implementation correction

- **Observed:** The first evaluation run reported secondary within-family image-bootstrap intervals equal to the point estimates.
- **Cause:** The secondary bootstrap was given one already-averaged family mean per filename family instead of the individual image metrics within each family.
- **Correction:** Updated the secondary bootstrap input to the per-image metric vectors, retaining the preregistered stratified resampling procedure and seed. The corrected outputs are written to new `PHASEA_final_*` files; no previous output was overwritten.
- **Scope/effect:** The primary filename-family bootstrap, model predictions, per-image metrics, tuned colour threshold, preregistered metrics, and PASS/FAIL rule were unchanged. Corrected secondary intervals are reported in the final files.
- **Protocol deviation:** The frozen test split was scored a second time to produce the corrected intervals. No parameter or threshold was tuned on the test data; the first results are retained and explicitly marked preliminary in the integrity check.

No other analysis-protocol deviations were recorded. Phase B was not started.

## 2026-11-16 — Productization-path probe

- The direct `Test-Path D:\patent\productization` request was not repeated because a previous workspace attempt to access that path returned path-not-found and instructed not to retry it.
- The requested fallback directory, `D:\patent\stage2A_audit`, was visible and proved writable when the prefixed preregistration was created successfully. All new Phase A files were written there.
