# RENFAST Fibrosis Segmentation Baseline Preregistration

**Registered:** 2026-11-16  
**Status:** registered before inspecting image or mask pixels. Archive member names and top-level folder names were enumerated first.

## Permission and scope

- Dataset: RENFAST Mendeley Data, DOI `10.17632/m2t49zf6xr.1`, version 1.
- The user reports that written permission from the data owners has been obtained for model use. Record the permission's scope in the project compliance records; do not redistribute source images or masks.
- Use only the fibrosis image and manual fibrosis mask folders in `FIBROSIS_TRAIN` and `FIBROSIS_TEST`. Do not use the vessel task or any KPMP files.
- This is a research baseline. It is not a clinical diagnostic tool and cannot be described as flawless, clinically validated, or externally validated.
- No foundation-model weights will be used. This avoids the unresolved Phikon-v2 non-commercial licence and patent-use question.

## Data integrity and split

- Pair image and manual fibrosis mask by exact normalized relative stem. Require identical dimensions and verified foreground/background semantics; stop on ambiguous pairing, missing masks, or incompatible mask values.
- Hash image/mask contents. Identify exact duplicate pairs and filename-family groups before any training. Do not silently deduplicate non-identical images sharing a name.
- Keep the official `FIBROSIS_TEST` partition untouched until preprocessing, model, and checkpoint selection are frozen.
- Before fitting, verify no exact image, mask, or filename-family group crosses the official train/test boundary. If the family grouping cannot be established, report image-level test metrics as potentially dependent and do not claim independent case-level validation.
- Derive a deterministic 80/20 training/validation split by filename-family group from `FIBROSIS_TRAIN`, using SHA-256 of `20261116|<group ID>` for ordering. The official test partition is never used for selection.

## Baseline model and preprocessing

- Train a four-level U-Net from random initialization with encoder widths 32, 64, 128, and 256; use a one-channel fibrosis probability output.
- Convert RGB inputs to float32 in `[0, 1]`; retain native image dimensions and pad only on the bottom/right to a multiple of 16. Use nearest-neighbor interpolation only if a verified mask/image geometry requires it.
- Use binary cross-entropy plus soft Dice loss, equally weighted. Optimize with AdamW (`lr=1e-3`, `weight_decay=1e-4`), batch size 1, fixed seed `20261116`, maximum 100 epochs, early stopping on mean validation Dice with patience 12, and restore the best validation checkpoint.
- Apply only flips and 90-degree rotations to training pairs. Apply no stain normalization, color augmentation, or test-time augmentation in this baseline.
- Save the exact pair manifest, group split, preprocessing configuration, package versions, checkpoint hash, and every failed or interrupted run.

## Evaluation

- After freezing the model and threshold, evaluate the official `FIBROSIS_TEST` set once.
- Report per-image and macro-averaged Dice, IoU, sensitivity, and specificity; include empty-mask handling explicitly. Bootstrap 95% confidence intervals by filename-family group (10,000 resamples, seed `20261117`) when the family grouping is valid.
- Report the number of unique pairs, duplicate pairs, train/validation groups, test groups, exclusions, and all test failures.
- No performance threshold will be reinterpreted after test evaluation. Report the measured result, uncertainty, limitations, and whether the data support only an internal benchmark.
- This dataset has no verified patient-level molecular linkage; do not assign predictions to KPMP participants, correlate with spatial expression, or claim multimodal integration.

## Stop conditions

Stop before training if permission does not cover the planned training use, pairings or mask semantics are ambiguous, there is train/test leakage that cannot be resolved, or the training groups cannot be separated from the held-out test groups. A separate, independently annotated kidney image cohort is required for external image-level validation.
