# Stage 2A Preregistration

**Registered:** 2026-11-13T12:05:26+05:30  
**Status:** registered before reviewing Stage 2A dataset contents or running image analysis.  
**Scope:** tissue detection, image QC, stain handling, and supervised compartment/collagen segmentation, conditional on Gate 2A-1.

## Gate and data scope

Stage 2A may train or evaluate segmentation models only if the dataset audit identifies at least one usable image set with explicit expert-produced compartment or collagen masks and unambiguous participant, slide, stain, and image-to-mask linkage. An algorithm-produced mask is not expert ground truth. If no such set exists, stop Stage 2A after the audit; do not generate surrogate labels, train segmentation models, or score pseudo-labels as expert validation.

Only open-access materials with terms recorded in `DATASET_AUDIT.md` may be used. Do not access controlled or gated files. No whole-slide image is to be loaded at full resolution; use pyramid/windowed reads. A mask whose stain, section, pixel grid, annotation coverage, or producer cannot be established is not usable ground truth.

## Locked design if Gate 2A-1 passes

### Patient split

The unit of splitting is participant, with all slides, sections, patches, and masks from a participant kept together. Normalize participant identifiers by trimming whitespace and case-folding. Sort unique participant IDs by SHA-256 of `20261113|<normalized participant ID>`; ties are broken by the normalized ID. Assign the first `floor(0.70*N)` participants to train, the next `floor(0.15*N)` to validation, and all remaining participants to the sealed test set. If this leaves any split empty, segmentation training is infeasible and will not be run. Save the assignments before training. The test IDs and annotations remain unopened until model and normalization selection are frozen.

### Images, labels, tiling, and augmentation

- Train only on image/mask pairs with verified same-slide, same-stain spatial correspondence. Do not transfer a mask across stains or adjacent sections.
- Read pyramid images at the level closest to 0.50 micrometres per pixel (nominal 10x). Use 512-by-512 RGB patches with stride 512; do not create cross-slide patches. Retain only patches whose tissue region contains annotated pixels. Log excluded patches and reasons.
- Use only explicit annotation classes. Convert each class to a binary output channel; derive background as the complement of the union only where the source annotation explicitly covers the full field. Ignore unlabeled/uncertain pixels. Stop if mask semantics or coverage are ambiguous.
- Apply horizontal/vertical flips and rotations by multiples of 90 degrees, each with probability 0.5. No elastic deformation or stain jitter.

### Models and training

Compare at most three fixed architectures:

1. Four-level U-Net, encoder widths 32/64/128/256/512.
2. Attention U-Net with the same encoder widths.
3. U-Net with a randomly initialized ResNet-34 encoder and decoder widths 256/128/64/32.

No gated or unlicensed weights are used. For each architecture, compare the two pre-registered input conditions: Macenko normalization and no normalization. Fit the Macenko reference stain matrix using training participants only and apply that fixed reference to validation and test images. If stain decomposition is undefined for the audited stain or implementation, stop rather than substitute another method.

Use AdamW (learning rate `1e-3`, weight decay `1e-4`), batch size 16, maximum 100 epochs, and fixed seed `20261113`. Use the mean of per-class validation Dice as the sole early-stopping/model-selection metric; patience is 12 epochs, and restore the best validation epoch. The loss is the equally weighted sum of mean per-class binary cross-entropy and soft Dice loss over labeled pixels. Run no more than six architecture-by-normalization configurations; record every attempt, including failures, in `TRIAL_LEDGER.csv`.

### Metrics and test-set handling

For the sealed test set, report per-class Dice and IoU, plus macro averages. First aggregate pixel TP/FP/FN within each participant and class; then report the unweighted mean across test participants. Compute percentile 95% CIs by resampling participants (10,000 bootstrap replicates, seed `20261114`). Report per-participant results and failure cases. Evaluate the sealed test set once, only after all choices are frozen. Compare Macenko with no normalization on the same test participants. Do not claim test-set performance if fewer than two test participants are available; report it as descriptive and uninformative.

## Stop conditions

Stop without training if Gate 2A-1 fails, pairings or annotation semantics are ambiguous, stain normalization cannot be applied as specified, or the patient split cannot populate train/validation/test. Record the reason and options in `STAGE2A_REPORT.md` and `BLOCKER.md` as appropriate. This preregistration does not authorize downloading additional data or packages; resource and license checks must be recorded before any later acquisition.
