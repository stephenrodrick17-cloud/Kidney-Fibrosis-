# Stage 1c confirmation protocol

**Registered:** 2026-11-13T10:00:04+05:30  
**Status:** plan only; no new data acquired and no new model fitted.  
**Stage 1 Gate A:** remains **FAIL**. Stage 1b remains **exploratory, post-hoc**.

## Primary hypothesis

On the catalog-identified participants outside the existing 28-person cohort, the frozen ResNet-50 spot embedding followed by the Stage 1b one-hidden-layer MLP will have higher participant-level spot Spearman correlation for the depth-residualized, immediate-neighbor-mean **myofibroblast/profibrotic module** than both the color-only Ridge baseline and the depth-only Ridge baseline.

This is a new-cohort confirmation attempt of a hypothesis selected after seeing Stage 1b results. The Stage 1b result is exploratory and subject to selection optimism; only the disjoint new participants can meet the success rule below.

## Fixed confirmation cohort

Use the 12 additional participant IDs found in the dated local catalog, and no replacements:

`164-10`, `164-22`, `27-10123`, `27-10166`, `27-10229`, `29-10277`, `29-10282`, `30-11081`, `34-11042`, `34-11048`, `933-10271`, `933-11258`.

The participant is the analysis and resampling unit. No spots from these participants may enter training, hyperparameter selection, early stopping, normalization fitting, feature scaling, or model selection. Report all unavailable files and participant-level exclusions. A participant is eligible for the primary metric only with at least 10 finite spots, at least three distinct target values, and nonconstant predictions for all three compared models. At least 10 eligible participants are required for an interpretable confirmation; fewer means the attempt is inconclusive and the success rule is not met.

## Model, targets, and comparisons

- **Candidate model:** image-only `mlp_spot`, using a frozen torchvision ResNet-50 `IMAGENET1K_V2` 2,048-dimensional spot embedding from a 224×224 spot tile, followed by one 128-unit ReLU hidden layer and a 12-output head as in Stage 1b. For this single-target test, score only the pre-specified myofibroblast/profibrotic module. Use AdamW (`lr=1e-3`, `weight_decay=1e-4`), batch size 1,024, fixed seed `20261113`, and exactly one training epoch. One epoch is fixed as the median selected epoch across the seven Stage 1b outer fits for this target variant/model; no new-cohort early stopping or tuning is allowed.
- **Color-only baseline:** the Stage 1b 12 color-statistic features and Ridge regression with `alpha=1`.
- **Depth-only baseline:** `log1p(total spot UMI)` and Ridge regression with `alpha=1`.
- Fit the candidate and both baselines only on the existing 28 participants. Fit feature scaling and any other learned preprocessing on those 28 only. Use the same frozen encoder and Stage 1 tile/spot mapping procedure; verify the spatial coordinates and hires-image mapping before evaluation, without cross-stain registration.
- Reconstruct the module from the same normalized gene targets and simple-mean definition as Stage 1. Fit target-on-depth residualization using the 28 training participants only with participant-balanced weights. For both training and new participants, form the neighbor-mean target using only the six Stage 1b immediate array-coordinate offsets `(0, ±2)`, `(±1, ±1)`, within library and excluding the center spot. Do not impute missing neighbors or center new participants using their labels.
- Compute each eligible new participant's Spearman correlation across spots for the candidate and both baselines. For each baseline, calculate the paired participant-level delta `candidate Spearman − baseline Spearman` on the same eligible new participants.

## Primary success rule and failure conclusion

Use 10,000 participant-bootstrap resamples, seed `20261114`, with participants—not spots—as the resampling units. The primary hypothesis succeeds only if there are at least 10 eligible new participants **and** the 95% participant-bootstrap CI for the paired delta is entirely above zero against **each** baseline (color-only and depth-only).

If either interval includes zero or is below zero, conclude that the image-only candidate did **not** show confirmatory improvement over both baselines on this new cohort. If fewer than 10 participants are eligible, conclude the confirmation is inconclusive and the success rule was not met. Do not change Stage 1 Gate A, tune after inspecting new-cohort outcomes, or proceed to registration/fusion on the basis of this test.

## Secondary analyses (exploratory only)

The two other modules, the unsmoothed depth-residualized targets, the Elastic Net image model, image-plus-depth models, gene-level targets, and spatial-block summaries may be reported as exploratory secondary results. They cannot rescue a failed primary hypothesis, alter the success rule, or authorize a later stage.

## Data acquisition and licensing hold

This plan does not authorize or perform downloads. The catalog marks the listed records `open`; catalog-linked DOI collections `10.48698/16dd-vj20` and `10.48698/3z31-8924` state CC BY 4.0. Nine of the 29 listed file records have no DOI in the catalog, so their file-specific terms are not verified. The four standalone TIFF files larger than 1 GB each require explicit user approval before any download. Check disk space again immediately before any future acquisition. Do not use any file that is not open access.

## Scope and stop

This file is the pre-run protocol only. No download, archive extraction, embedding generation, model fit, or new-participant outcome inspection was performed for Stage 1c. Wait for explicit instruction before acquiring data or running this protocol.
