# PLAUS preregistration

Timestamp: 2026-11-18T10:45:10.706+05:30

**EXPLORATORY, NOT CONFIRMATORY. UNVALIDATED MASKS.**

This preregistration is written before the PLAUS runs. Any later change is recorded only in PLAUS_DEVIATIONS.md.

## Primary design

Reuse the Stage FA within-library high/low tertile design. Adjust each high-minus-low gene effect for log library size and tissue fraction; include tissue depth where supplied. Participants are the unit. The participant effect is the mean high-minus-low effect. Confidence intervals use 10,000 participant bootstrap resamples with fixed seed `20261118`.

The primary result is the mean collagen-module effect across participants.

## Negative-control genes

Fixed negative-control list, source "pre-registered common housekeeping panel":

ACTB, GAPDH, RPL13A, RPLP0, RPS18, RPS27A, UBA52, TUBB, HPRT1, PPIA, B2M, TBP, PGK1, LDHA, SDHA, GUSB, HMBS, RPL19, RPL27, EEF1A1.

Test only participants with full matrices. Expected result: effect near zero. Report the distribution and empirical rank percentile of the collagen module among negative-control effects.

## Expected-direction panel

Lower in fibrotic spots:

- SLC34A1 = LOWER
- LRP2 = LOWER
- UMOD = LOWER
- SLC12A1 = LOWER

Higher in fibrotic spots:

- COL4A1 = HIGHER
- COL5A1 = HIGHER
- COL6A1 = HIGHER
- FAP = HIGHER
- POSTN = HIGHER
- PDGFRB = HIGHER
- VIM = HIGHER
- PTPRC = HIGHER
- C1QA = HIGHER
- C1QB = HIGHER
- C1QC = HIGHER
- CD68 = HIGHER

Test these signs on the 28 full-matrix development participants. Score the sign-agreement fraction and a binomial test against 50% agreement.

## Mask sensitivity grid

Pre-register the following settings:

- Probability thresholds: 0.3, 0.5, 0.7.
- Binary masks: erosion and dilation by 2 pixels.
- Standard spot diameter: `55 / 4.1 = 13.414634146341463` pixels.
- Spot footprints: 0.75, 1.0 and 1.25 times the standard diameter.
- Spot groups: tertile and quartile.

For each available grid cell, report the collagen-module effect and participant-bootstrap CI. Probability threshold 0.3 and 0.7 will be NOT AVAILABLE if probability maps are not saved. Morphology and footprint variants use the saved mask and Phase A 4.1 um/pixel scale.

## Stain-colour stratification

Use the existing Stage FA image-derived `mean_hue`, `mean_saturation` and `mean_value` spot features. For each participant, average the selected feature over spots and divide participants into image-colour quartiles using mean hue. Because stain-group labels are NOT AVAILABLE, this is an image-colour quartile only, not a stain-type result.

Report the collagen effect in each quartile. A quartile with fewer than 5 participants is marked too small to judge.

## Robustness

- Leave one participant out: report the range of the mean collagen-module effect.
- Spatial permutation: use 4-by-4 array-coordinate blocks where tissue positions are available. Permute high/low group labels within blocks, not spots completely at random. Use 10,000 resamples and seed `20261118`.
- Tissue-edge exclusion: exclude spots within 2 standard spot diameters of the tissue edge: `26.829268292682926` pixels at target scale.
- Library-size exclusion: exclude spots below the 25th percentile of spot library size.
- Edge and edge-position checks are limited to samples with usable spot positions.

## Interpretation rules

Mark PLAUSIBLE only if all four rules pass:

1. The collagen module's mean effect ranks above the 95th percentile of negative-control effects.
2. At least 75% of expected-direction genes show the expected sign.
3. The effect keeps its direction in at least 90% of available sensitivity-grid cells and in at least 3 of 4 stain quartiles.
4. Leave-one-out and spatial permutation do not remove the collagen effect.

Otherwise mark CONCERN and name every failed rule. These thresholds are exploratory and not clinical standards.
