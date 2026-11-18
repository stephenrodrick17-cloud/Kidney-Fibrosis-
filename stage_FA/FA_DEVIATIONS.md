# FA_DEVIATIONS - EXPLORATORY, NOT CONFIRMATORY

**EXPLORATORY, NOT CONFIRMATORY. UNVALIDATED MASKS.**

All entries below were recorded before any Stage FA expression values were paired with a mask.

## D-001 - Image-run implementation retries

**Date:** 2026-11-17  
**Effect on registered method:** None.

The first image-run attempts stopped before producing masks because Stage 1d archive paths were recorded relative to the spatial archive and because of an undefined resampling variable. The runner was corrected to resolve the existing archive path using the matching spatial-record path and to use the registered Pillow LANCZOS resampling. The successful run used the already registered checkpoint, 4.1 micrometres per pixel, mask thresholds, and spot rule. No expression file was opened during these attempts.

## D-002 - Single primary mask versus robustness mask

**Date:** 2026-11-17  
**Effect on registered method:** Clarifies the singular primary endpoint; does not change its target or success rule.

The frozen RENFAST U-Net is treated as the one primary mask for the registered primary endpoint. The `B - R >= 2` colour mask is the required robustness repeat because Gate 1 did not pass. It is not a second co-primary endpoint and cannot rescue a primary endpoint that is not met. All secondary associations are repeated with both masks as required by the failed-gate rule.

## D-003 - Spot-level colour features for the colour-only control

**Date:** 2026-11-17  
**Effect on registered method:** Adds an image-only feature extraction needed to implement the already registered colour-only control; no genes, endpoint, or success threshold changes.

The image-only mask run saved each library's median hue but not per-spot colour values. Before reading expression, an additional image-only pass will save each included spot's mean hue, saturation, and value from tissue pixels inside its registered circular footprint. The colour-only control will use those three spot-level features, along with the registered depth, count, tissue-fraction, and library terms, but not the high/low fibrosis group. The image-derived colour quartiles remain descriptive and are not verified stain labels.

## D-004 - Tissue-normalized slide fractions for the panel summary

**Date:** 2026-11-17  
**Effect on registered method:** No change to endpoints or tests.

The panel summary and severity wording require a slide-level tissue-normalized fibrosis percentage. The image-only pass therefore will also count mask-positive pixels among tissue pixels for each library, using the registered `mean(R,G,B) < 245` tissue rule. This is saved before expression is read and is not substituted with the mean spot score.

## D-005 - Median hue field correction

**Date:** 2026-11-17  
**Effect on registered method:** Corrects a field calculation to match the preregistered median-hue grouping; no endpoint or mask score changes.

The first image-only colour pass stored circular-mean hue in the slide field named `median_tissue_hue`. The preregistration specifies the median hue. Before reading expression, a second image-only pass recomputes that field as the median of hue values over tissue pixels and saves a separately named final slide-fraction table. The first table remains unchanged and is superseded for colour-group analysis.

## D-006 - Constant covariate columns in participant regressions

**Date:** 2026-11-17  
**Effect on registered method:** Numerical implementation correction; no covariate or endpoint is removed when it varies.

The first analysis pass treated a participant regression as invalid when tissue fraction was constant within that participant. It retained only one participant, produced a degenerate interval, and incorrectly displayed the rule as met; that result is invalid and must not be used. A constant covariate column is redundant with the intercept and cannot have a separately estimated coefficient. The runner removes only zero-variance design columns before the same ordinary least-squares fit. This is algebraically equivalent to retaining the constant column with the intercept; it preserves the registered adjustment whenever the covariate varies. The first-pass analysis tables remain unchanged and are superseded.

## D-007 - Label shuffle permutes scores, then rebuilds groups

**Date:** 2026-11-17  
**Effect on registered method:** Corrects the label-shuffle implementation to follow the preregistered permutation procedure.

The second analysis pass randomly reassigned high/middle/low labels rather than permuting the continuous fibrosis scores. The primary and secondary regression results do not depend on this control, but that pass's label-shuffle p-values are superseded. The final runner permutes the actual mask fibrosis scores within participant, then rebuilds the registered low/middle/high groups separately within each library, using barcode order for ties. The final complete output set has names ending in `_FINAL`.
