# Stage FA Report — EXPLORATORY, NOT CONFIRMATORY

**EXPLORATORY, NOT CONFIRMATORY. UNVALIDATED MASKS.**

## Outcome

The preregistered U-Net primary numerical rule was **MET in exploratory terms**: the adjusted participant-level collagen-module difference was 0.1249 z-score units (40 participants; 95% bootstrap CI [0.0804, 0.1702]), and 31/40 participant effects were positive. The colour-mask repeat was also positive (0.0894; 95% CI [0.0509, 0.1290]); the directions agree.

This is not a reliable or confirmatory result. All 40 participants had appeared in earlier stages, and **Gate 1 was NOT PASSED** because no locked pathologist masks or independent expert reference with the registered threshold evidence were supplied. The Phase B report recorded the combined empty-or-extreme predicted-area flag for 27 of 40 regions; this is not ground-truth validation.

The preregistered colour check also raised a confounding concern: the image-colour quartile eta-squared exceeded the largest squared participant Spearman gene signal for both masks. The colour-only controls had higher mean R-squared than the full primary model. Therefore the requirement for a confirmatory recommendation is **not met**, even though the primary numerical rule was met and the mask directions agreed.

## What the result does and does not mean

In these previously used slides, spots marked high by each mask had higher adjusted collagen-module expression on average than spots marked low. That is an association in this exploratory analysis. It does not establish that the masks correctly locate fibrosis, that genes cause or predict fibrosis, or that the result will repeat in new patients. No clinical or medical accuracy claim is made.

The participant-level panel analysis did not show a clear association: the collagen-module correlations had confidence intervals that included zero, and all panel targets had Holm-adjusted results in the final tables. Severity calibration was **NOT TESTABLE** because no confirmed local pathology or clinical values were available in the records examined.

## Deviations and verification

- D-005 corrected the slide-level hue field to use the preregistered median. The earlier slide table remains unchanged; the corrected table was used for colour-group analysis.
- D-006 corrected the regression handling of constant covariate columns. The first-pass tables are invalid and superseded.
- D-007 corrected the label-shuffle control to permute fibrosis scores within participants and rebuild per-library groups. The intermediate `_CORRECTED` shuffle table is superseded; the final analysis tables end in `_FINAL`.
- Independent verification passed 22/22 checks, including recomputation of participant regression effects, the primary mean and confidence interval, the panel collagen-module correlation, image-colour eta-squared, spot-key/group integrity, and hashes for 96 analysis-manifest files.
- The frozen checkpoint SHA-256 matched the registered value. No folds were used in Stage FA, so fold-overlap checks are not applicable; spot tertile assignments were verified to be exclusive within each mask.
- RENFAST and KPMP permissions remain **UNRESOLVED**. The `RESEARCH-ONLY` asset field in some run files is not a licence determination.

## Recommendation and next input

**Do not begin a confirmatory test yet.** The color-confound check is flagged, the masks are unvalidated, the current participants were previously used, and permissions remain unresolved.

The next required input is:

1. Completed, locked pathologist masks for the relevant B2 tiles (or an independent expert-labelled kidney set), plus the already registered B2 analysis showing the frozen U-Net meets its threshold; and
2. The exact applicable RENFAST and KPMP permission wording in the permission record, without interpretation.

For a confirmatory test, also supply a genuinely unseen participant set with matching images, spatial coordinates, expression data, and documented permission status. Do not start registration, fusion, multimodal integration, or filing work.

## Detailed records

- Step 0 data audit: [FA_DATA_AUDIT.md](./FA_DATA_AUDIT.md)
- Gate 1: [FA_MASK_GATE.md](./FA_MASK_GATE.md)
- Frozen preregistration: [FA_PREREG.md](./FA_PREREG.md)
- Deviations: [FA_DEVIATIONS.md](./FA_DEVIATIONS.md)
- Corrected results: [FA_RESULTS.md](./FA_RESULTS.md)
- Independent verification: [FA_VERIFICATION.md](./FA_VERIFICATION.md)
- Permission record: [FA_LICENCE_NOTE.md](./FA_LICENCE_NOTE.md)
