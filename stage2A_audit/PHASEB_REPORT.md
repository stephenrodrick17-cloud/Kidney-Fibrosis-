# Phase B Report — Frozen RENFAST Check on Local KPMP TRI Regions

**Status:** Completed; external sanity check only.  
**Use:** Research-only visual review. This does not establish medical accuracy, clinical utility, novelty, or patentability.

## What was done

The timestamped protocol in [PHASEB_PREREG.md](./PHASEB_PREREG.md) was written before region selection and model inference. No slides were downloaded or modified. The frozen RENFAST checkpoint was applied without retraining, tuning, stain normalization, colour augmentation, or test-time augmentation.

- Frozen checkpoint SHA-256: `674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb`.
- Input: 40 preregistered `512 × 512` RGB regions, extracted at the target scale of `4.1 µm/pixel`.
- Selection: seed `20261118`; 10 regions in each of four slide-colour strata; 25 catalog participant IDs across 26 slides; maximum 3 regions per slide.
- Eligible local inventory: 32 files marked `open`, spanning 28 catalog participant IDs. Catalog access status is not proof of reuse rights.
- Minimum selected-region tissue fraction: `0.5178`; all selected regions met the preregistered `>=0.50` cutoff.
- Model handling: RGB scaled to `[0,1]`, fixed probability threshold `0.5`, no stain normalization; same padding/cropping as Phase A.
- Frozen colour baseline: `B − R >= 2`, as selected using Phase A training data; it was not tuned on these regions.

## Visual observations

The full 40-region contact sheet and native-resolution overlays for representative high-disagreement regions were reviewed. The frozen model produced empty or very sparse masks in many selected regions and broader masks in some others. In several regions the colour-threshold baseline covered substantially more area, including pale image areas. These are visual observations only: without an aligned pathologist reference they cannot be classified as correct fibrosis detection or as false positives/negatives.

See [PHASEB_contact_sheet.png](./PHASEB_contact_sheet.png), per-region panels in `PHASEB_region_images`, and the blank [PHASEB_REVIEW_FORM.csv](./PHASEB_REVIEW_FORM.csv).

## Objective screening flags

These are preregistered algorithmic flags, not pathology judgments. Flags can overlap.

| Preregistered flag | Regions flagged (n=40) |
|---|---:|
| Empty or extreme predicted area (`<1%` or `>80%` of tissue) | 27 |
| More than 5% of predicted pixels outside the tissue mask | 0 |
| At least 20% of predicted pixels very pale | 0 |
| At least 20% of predicted pixels highly saturated | 1 |
| Low-focus heuristic (Laplacian variance `<50`) | 25 |

Glomeruli, vessels, and pen marks were **not assessable**: no exact slide-matched, spatially aligned annotations were identified. The low-focus statistic is an image heuristic and is not a pathologist assessment.

## Largest U-Net / colour-baseline area differences

Area is predicted-positive pixels as a percentage of the region's tissue pixels. Difference is the absolute percentage-point difference. These values compare two algorithms, not either algorithm with ground truth.

| Region | U-Net area | Colour-baseline area | Absolute difference |
|---|---:|---:|---:|
| PHASEB_REGION_040 | 0.00% | 34.30% | 34.30 pp |
| PHASEB_REGION_036 | 0.00% | 33.87% | 33.87 pp |
| PHASEB_REGION_034 | 24.41% | 52.35% | 27.94 pp |
| PHASEB_REGION_016 | 29.77% | 54.77% | 25.00 pp |
| PHASEB_REGION_010 | 0.20% | 19.43% | 19.23 pp |
| PHASEB_REGION_035 | 2.34% | 20.54% | 18.20 pp |
| PHASEB_REGION_031 | 1.30% | 18.29% | 16.99 pp |
| PHASEB_REGION_039 | 6.12% | 22.20% | 16.08 pp |
| PHASEB_REGION_028 | 11.65% | 27.58% | 15.94 pp |
| PHASEB_REGION_005 | 19.88% | 35.31% | 15.43 pp |

Full precision and identifiers are in [PHASEB_top10_disagreement.csv](./PHASEB_top10_disagreement.csv); all region area values are in [PHASEB_region_metrics.csv](./PHASEB_region_metrics.csv).

## Verification

The separate verification script recomputed areas from saved RGB inputs and masks, recomputed the objective flags from saved pixels, and checked counts and ranking:

- 40 unique regions; 10 per stratum; 25 participant IDs; 26 slides; no more than 3 regions per slide.
- All 160 derived mask/overlay panels exist; the contact sheet is `800 × 7312` pixels.
- Recomputed objective-flag totals match the report: 27 extreme-area, 0 outside-tissue, 0 very-pale, 1 saturated, and 25 low-focus.
- Recomputed the top-10 area-difference ranking; it matches the saved table.
- The review form has 40 rows, with all reviewer fields blank.

See [PHASEB_VERIFICATION.json](./PHASEB_VERIFICATION.json) for the recomputed values.

## What could not be verified

- The local catalog marks the slides `open`, but does not state their licence or reuse terms. Access status alone does not establish permission for this evaluation or any downstream use.
- No independent aligned fibrosis annotation or pathologist reference exists for these selected regions. Dice, IoU, accuracy, sensitivity, specificity, fibrosis grades, and other reference-based metrics were not computed.
- No aligned masks were available to quantify overlap with glomeruli, vessels, or pen marks.
- This region sample does not establish patient-level representativeness, external generalization, or clinical performance.
- No 95% confidence intervals are reported: this preregistered Phase B analysis is a descriptive, reference-free sanity check, not an estimate of performance against a reference standard.

## Outcome and next instruction

Phase B is complete. It produced overlays for all 40 regions and documented substantial model/baseline disagreement, but it cannot say which mask is more accurate without independent review.

**Next instruction:** arrange for a qualified kidney pathologist to complete `PHASEB_REVIEW_FORM.csv`, provide the exact applicable KPMP data-use terms or permission, and then explicitly instruct whether to begin Phase C. Phase C has not been started.
