# Phase B Preregistration — External Sanity Check

**Registered:** 2026-11-16 16:17:21 +05:30  
**Status:** registered before Phase B region selection, model inference, or overlay review  
**Scope:** frozen RENFAST fibrosis segmenter on eligible local KPMP trichrome slides only. No retraining, tuning, downloads, or Phase C work.

## Permission and data gate

- Use only local KPMP TRI slides whose existing repository inventory marks them open. Do not fetch or download files.
- Record each selected slide's inventory status and any stated licence/terms. If a slide is not marked open or its terms prohibit this research evaluation, exclude it before region selection; if no eligible slides remain, stop and report.
- Do not infer use rights from file accessibility. Record unavailable or ambiguous licence terms as unresolved; do not distribute source slides.

## Frozen model and stain handling

- Checkpoint SHA-256: `674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb`.
- Use the frozen model only, with the Phase A RGB handling: convert to RGB, scale channels to `[0, 1]`, no stain normalization, colour augmentation, or test-time augmentation, and classify with the fixed probability threshold `0.5`.
- Extract each region at a target physical scale of `4.1 µm/pixel`, resampling the local slide pyramid level nearest that scale if needed, into a `512 × 512` RGB model input. Pad bottom/right only if needed for a multiple of 16, then crop output back to `512 × 512`.
- The target scale is based on the prior local TRI audit's level-2 range (`4.04–4.21 µm/pixel`). If a slide lacks reliable microns-per-pixel metadata or a level that can be resampled to this target, exclude it before inference and report why.
- No extra colour/stain handling is permitted. If metadata reveals a requirement that changes RGB handling, stop before inference and register an amendment first.

## Region selection before model outputs

- Seed: `20261118`.
- Fixed region: `512 × 512` pixels at `4.1 µm/pixel`.
- For each eligible slide, compute one colour statistic from its existing low-resolution thumbnail, before any model inference: the median `B − R` across thumbnail pixels with mean RGB below 245. Rank slides by this value, breaking ties by slide ID, and divide the ordered slides into four balanced colour-statistic strata.
- Generate candidate regions on a non-overlapping `512 × 512` grid at the target scale. Use the fixed tissue rule `mean(R,G,B) < 245`; retain only candidates with at least 50% tissue pixels. Do not use any prediction, manual mask, or model overlay to select regions.
- Select 10 regions per colour stratum (40 total) with a seeded pseudorandom procedure. Within each stratum, prefer participants with the fewest selected regions, then slides with the fewest selected regions; break ties and choose eligible grid cells with the seeded RNG. Enforce at most 3 regions per slide. A region can be selected once only.
- If 40 qualifying regions cannot be selected with 10 in each stratum, stop before inference and report the achievable count; do not relax tissue, scale, or quota rules.
- Save a manifest with participant/slide identifiers, region coordinates, pyramid level, resampling scale, slide colour statistic/stratum, tissue fraction, and seed before inference.

## Measurements and comparison

- Apply the frozen model to all 40 selected regions and save input/predicted-mask/overlay panels for every region plus a contact sheet.
- Apply the Phase A colour-threshold baseline to the same RGB regions, using its frozen rule `B − R >= 2`; do not tune it. Report the 10 regions with the greatest absolute difference in predicted-positive area fraction of tissue, in percentage points, with ties by region ID.
- This is a visual/exploratory sanity check only. There is no independent aligned pathologist reference for these regions; do not calculate Dice, IoU, accuracy, sensitivity, specificity, fibrosis grades, or other reference-based performance numbers.

## Objective failure-mode flags

These are predeclared algorithmic screening flags, not diagnoses or validated pathology findings:

1. **Extreme predicted area:** predicted-positive pixels are under 1% or over 80% of tissue pixels, or no positive pixels are predicted.
2. **Prediction outside tissue:** tissue is `mean(R,G,B) < 245`; flag if more than 5% of predicted-positive pixels fall outside that tissue mask.
3. **Very pale predicted pixels:** flag if at least 20% of predicted-positive pixels have mean RGB `>=225`.
4. **Highly saturated predicted pixels:** use `S=(max(R,G,B)-min(R,G,B))/max(R,G,B)` with zero when max is zero; flag if at least 20% of predicted-positive pixels have `S>=0.8`.
5. **Low-focus heuristic:** convert to 8-bit grayscale, compute variance of the 3×3 discrete Laplacian, and flag if variance is `<50`.
6. **Glomeruli/vessels and pen marks:** quantify predicted overlap only if an already-local annotation is exactly slide-matched and spatially aligned without new registration. Otherwise report `not assessable`; do not infer alignment or create labels.

For rules 2–4, if no positive pixels are predicted, the corresponding fraction is `NA` and the extreme-area rule records the empty prediction.

## Reporting and stop conditions

- Report counts of eligible slides/participants, selected regions, each objective flag, exclusions, and any unassessable categories. Report no performance numbers against a reference.
- Save a blank reviewer form with one row per selected region; do not fill it in.
- Preserve all existing files. Every Phase B file created by this phase must have a `PHASEB_` filename prefix.
- End Phase B with what was done, key observations, what could not be verified, and the exact next instruction needed. Do not begin Phase C.
