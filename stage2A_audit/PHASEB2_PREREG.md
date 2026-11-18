# Phase B2 Preregistration — Blinded Annotation and Analysis

**Registered:** 2026-11-16 16:35:19 +05:30  
**Status:** registered before exporting annotation tiles or preparing the unblinded packet  
**Scope:** blinded human annotation package and a pre-registered analysis plan for 20 regions selected from the 40 Phase B regions. No training, downloads, or model changes.

## Annotation target

Current draft definition, supplied by the user and editable before any annotator receives the package:

> Outline areas of interstitial fibrosis, i.e. collagen-stained tissue between tubules; exclude glomeruli, vessel walls, capsule and pen marks.

If the user changes this wording after registration, record the change in a timestamped amendment before annotators begin. Any annotator-provided ungradable/uncertain status will be retained in the return form; masks will not be silently adjudicated or edited by the analysis script.

## Region selection before export

- Source: only the 40 fixed-scale regions in `PHASEB_region_manifest.csv`.
- Select exactly 5 regions from each of the four existing `colour_stratum` groups (20 total).
- Selection seed: `20261119`. For each stratum, sort candidate region IDs lexicographically, then use one `random.Random(20261119)` instance to sample 5 without replacement from each stratum in ascending stratum order.
- Use only region IDs and registered colour-stratum labels for selection. Do not inspect or use U-Net predictions, colour-baseline predictions, overlays, or disagreement scores.
- Participant IDs, slide IDs, coordinates, and model outputs are excluded from annotator-visible filenames and package contents.
- Record the selected region IDs and all opaque-ID links only in the separate protected key.

## Annotation and blinding

- Export only the selected raw RGB tiles for annotators, as `512 × 512` PNG files. Re-save pixels without source metadata; assign cryptographically random opaque IDs unrelated to source IDs or coordinates.
- Provide one binary mask per tile and annotator: `512 × 512` PNG; black `0` is not fibrosis and white `255` is fibrosis. No resizing, resampling, rotation, or registration is allowed.
- The annotator package must not include model or baseline outputs, predictions, overlays, metrics, source region IDs, participant/slide IDs, coordinates, or the key.
- Store the mapping from opaque IDs to region IDs and coordinates in `PHASEB2_KEY_DO_NOT_SHARE.csv`, outside the annotator package.
- Keep the separate unblinded review packet inaccessible to annotators until all annotation masks have been returned and locked.

## Metrics and aggregation

For each annotator separately, evaluate the frozen U-Net and frozen Phase A colour-threshold prediction (`B − R >= 2`) against that annotator's binary mask. No predictions are tuned or altered.

- Report Dice, IoU, precision, and recall for each region and for each participant.
- Region metrics are computed on the aligned `512 × 512` masks. Participant metrics are the arithmetic mean of that participant's region-level metrics; report the number of regions per participant and retain `NA` values rather than silently imputing.
- Dice is `2TP/(2TP+FP+FN)` and IoU is `TP/(TP+FP+FN)`; if the union is empty, both are 1. Precision is `TP/(TP+FP)` and is `NA` when there are no predicted positives. Recall is `TP/(TP+FN)` and is `NA` when the annotation has no positive pixels.
- Primary comparison: per participant, average the U-Net region Dice minus colour-baseline region Dice. Estimate the mean of these participant-level differences and its two-sided percentile 95% CI using 10,000 bootstrap resamples of participants with replacement, seed `20261120`.
- The participant is the resampling unit. Report participant count and region count; do not treat regions as independent participants.
- If two or more annotators return masks, report inter-annotator Dice, IoU, precision, and recall per region and participant. Evaluate each model separately against each annotator. Do not create a consensus mask or adjudicate differences in the analysis script. If only one annotator returns masks, state that inter-annotator agreement is unavailable.
- A returned mask is analyzable only if it is exactly `512 × 512`, binary `{0,255}`, and matched to a selected opaque ID. Report invalid/missing masks; do not repair them. Marked ungradable regions are excluded from metric computation and counted in the report.

## Success rule and interpretation

- **Pass:** the lower bound of the participant-bootstrap 95% CI for mean participant-level U-Net minus colour-baseline Dice is strictly greater than zero.
- **Not met:** if the lower bound is zero or below, the registered success rule is not met; report that this small annotated sample did not demonstrate the U-Net's Dice advantage over the colour baseline. Do not infer equivalence, clinical failure, or medical accuracy.
- **Blocked:** if fewer than two participants have analyzable masks, or no usable annotations are returned, the participant bootstrap/success rule cannot be evaluated.
- Even a pass is limited to this research-use sample and does not establish clinical performance, clinical utility, novelty, or patentability.

## Stop conditions

Do not analyze real returned masks until the user supplies them and confirms annotation is finished. Do not show the unblinded packet before that point. This phase prepares and synthetically tests the analysis script only; it does not run the analysis on real annotations.
