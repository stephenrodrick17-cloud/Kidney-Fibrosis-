# GENE2 Pre-registration

**EXPLORATORY, NOT CONFIRMATORY** — the local inventory contains zero unseen participants.
**RESEARCH-ONLY for all ResNet-50/ImageNet feature-dependent outputs in this run.**

**Registered:** 2026-11-17T10:48:30+05:30  
**Scope:** Stage G2 only. No model has been run for GENE2.  
**Interpretation constraint:** Any evaluation on the 40 inventoried participants is exploratory because each participant was used in an earlier development or evaluation stage.

## 1. Cohort and identity

- Use only the 40 locally available participants listed in `GENE2_DATA_AUDIT.md`: 28 used in Stage 1 development and 12 used in Stage 1d confirmation. No participant is confirmatory for GENE2.
- The expected inventory is 40 participants and 41 libraries (29 Stage 1 libraries plus 12 Stage 1d libraries). This is an inventory count, not a successful-alignment count.
- The unique spot key is `(participant_id, library_id, barcode)`. All libraries belonging to one participant stay in the same outer and inner fold. In particular, both libraries for participant 28-12265 stay together.
- No Phase B2 tile pixels, keys, or annotations may be opened or used.

## 2. Targets and eligibility

### Primary target

The one primary target is the collagen module: the arithmetic mean of z-scored `COL1A1`, `COL1A2`, and `COL3A1` values. First calculate each gene's spot-level value using the existing `log1p(raw count / all-gene spot UMI * 10,000)` transformation. For each outer fold, calculate each gene's mean and standard deviation from outer-training participants only; apply those values to its validation and held-out participants before averaging the three z-scores.

The earlier QC screen required at least 10% spot detection in at least half of the 28 Stage 1 participants. The saved screen reports 27/28 participants at or above 10% detection for each of the five requested genes: `COL1A1`, `COL1A2`, `COL3A1`, `FN1`, and `ACTA2`. These five genes therefore pass the prior screen. Their exact recorded cohort detection percentages are in `D:\patent\qc_collagen\gene_detection_cohort_summary.csv`.

### Secondary targets

The five separate secondary targets are `COL1A1`, `COL1A2`, `COL3A1`, `FN1`, and `ACTA2`, using the same spot-level normalized expression values. No additional genes or modules will be tested. Apply Holm correction across the five secondary targets; secondary results cannot rescue a failed primary endpoint.

## 3. Regions and image/expression alignment

- Define non-overlapping regions within each library using integer Visium array coordinates: `block_row = floor(array_row / 4)` and `block_col = floor(array_col / 4)`. Each region is a 4-by-4 array-coordinate block. Keep only in-tissue, expression-matched spots; include a block only if it contains at least four such spots. Average spot-level inputs and target values within each included block.
- The primary per-participant statistic is Spearman correlation within each held-out participant, across that participant's eligible regions. The overall image-model mean is the arithmetic mean of those participant-specific correlations (participant-macro average). Single-spot metrics are descriptive only. Also report a separate participant-level-mean analysis: average eligible region observations and predictions within each participant, then compute Spearman across participants. This cross-participant correlation is descriptive and is not the primary success-rule statistic.
- Before fitting any model, audit every participant/library. Require matching participant and library/section identifiers across expression, positions, and image records; require each included barcode to match an in-tissue position; map each spot center using the saved spatial scale factor; and require every center to fall inside the corresponding image. Report audited, passing, and excluded participant/library counts, with every exclusion reason. Do not substitute another image or partially match barcodes.
- Exclude a failed library in full. Retain a participant only if at least one of their libraries passes alignment and leaves an eligible region; otherwise report that participant as excluded and why.
- Existing Stage 1d mapping evidence reports 12 successful mappings and all listed in-tissue centers inside their images. That evidence does not replace the GENE2 audit across all 41 libraries. GENE2 alignment counts are NOT AVAILABLE until that audit is run.

## 4. Models and training

### Models

1. **Depth-only baseline:** Ridge regression using only region-mean `log1p(total spot UMI)`.
2. **Colour-only baseline:** Ridge regression using region means of the existing 12 RGB/HSV per-tile colour statistics (channel means and standard deviations).
3. **Image Ridge:** Ridge regression on region-mean, saved 2,048-dimensional ResNet-50 spot features.
4. **Image MLP with neighbour smoothing:** first average each spot's saved feature vector with the vectors of its same-library immediate neighbours at the six Stage 1 offsets `(0, ±2)` and `(±1, ±1)`, excluding no values and using no expression labels. If no neighbour is available, retain the center feature. Then average those feature vectors within each region and fit a one-hidden-layer ReLU MLP.

The only permitted image representation is an already-saved ResNet-50 feature vector. Do not run an encoder to create missing features, use Phikon-v2, or use another encoder. Fit all scaling and model parameters on the relevant training participants only. Weight each training participant to equal total influence, regardless of its region count.

### Hyperparameter grids and seeds

- Ridge alpha grid for each of the three Ridge models: `{0.01, 0.1, 1, 10, 100}`.
- MLP grid: hidden units `{64, 128}`; learning rate `{0.001, 0.0003}`; weight decay `{0.0001, 0.001}`; ReLU activation; batch size `256`; participant-balanced mean squared error.
- MLP random seeds: `20261121`, `20261122`, and `20261123`. Average the three seed predictions for each outer held-out participant.
- Outer fold assignment seed: `20261120`. Each outer fold holds out one of five participant-grouped folds. Within each outer-training set, use four participant-grouped inner folds for all tuning and early stopping. A participant and all their libraries must remain in one fold; because the split unit is participant, no participant, library, or adjacent spot from one participant can cross train/validation/test folds.
- To make fold assignment reproducible, sort participant IDs, permute them with NumPy `default_rng(20261120)`, and assign the permuted IDs round-robin to five outer folds. For inner folds, sort the outer-training IDs, permute with seed `20261120 + outer_fold_index` (outer fold indices 0–4), and assign round-robin to four folds.
- Each model fit is multi-output for the primary collagen module and all five secondary genes. Select settings using only the primary endpoint; use the resulting fixed settings to report the secondary outcomes.
- Select hyperparameters by the highest mean inner-validation participant-level region Spearman for the primary target. Break ties by choosing the larger Ridge alpha; for the MLP choose fewer hidden units, then lower learning rate, then larger weight decay. Choose between Image Ridge and MLP by the same inner-validation mean; choose the stronger of depth-only and colour-only baselines by that same criterion. Outer test results are not used in any selection.
- Train each inner MLP fit to convergence with a maximum of 200 epochs, validation weighted-MSE early stopping, patience 15 epochs, and minimum improvement `1e-4`. The selected final-fit epoch count is the median best epoch from its inner folds. No fixed small epoch count is substituted.

### Pre-registered fit budget

- Inner tuning: 5 outer folds × 4 inner folds × 5 alpha values × 3 Ridge models = 300 Ridge fits; plus 5 × 4 × 8 MLP settings × 3 seeds = 480 MLP fits.
- Outer refits: 5 folds × (3 selected Ridge models + 3 MLP seeds) = 30 fits.
- Total maximum: **810 model fits**: 315 Ridge fits (300 inner + 15 outer) and 495 MLP fits (480 inner + 15 outer). Each fit predicts all six registered targets.
- Hard compute guard: stop and report before any individual fit can exceed two hours; terminate a fit at 60 minutes if it has not completed. Do not start a fit whose runtime is projected to exceed two hours. Hard output budget: 1 GB of new GENE2 output, below the requested 10 GB cap; check available D: space and projected output size before any model run.

### Commands and execution gate

No GENE2 modelling command has been executed. An executable GENE2 runner is not present, and no exact runnable command is therefore available: **NOT AVAILABLE**. Do not substitute an invented or placeholder command. Before any run, both conditions must be satisfied:

1. A verified, authorized source for the saved ResNet-50 features and its pretrained-weight terms is available. The project record says the torchvision code is BSD-3-Clause but the weight-specific and upstream ImageNet dataset terms were not independently verified.
2. Complete already-saved ResNet feature arrays exist for all participants/libraries in the 40-participant nested analysis. The Stage 1 directory has saved spot features for its 28 participants; Stage 1d's listed output directory has confirmation predictions but no saved feature-array file for its 12 participants. Creating features by running the encoder is outside this registration.

If either gate remains unmet, stop before fitting. No new model run was authorized or started for this preregistration.

## 5. Leakage and sanity checks

After both execution gates are met, before modeling:

- Save fold membership at participant, library, and region levels and assert no participant/library overlap across the outer or inner partitions. Assert all neighboring spots and all regions from a participant remain in that participant's fold.
- Check the `(participant_id, library_id, barcode)` key for uniqueness and verify each target and feature row has exactly one full key.
- Run the label-shuffle control by independently permuting collagen-module region labels within each participant, with seed `20261125`, then rerun the registered image model and both baselines. Report all paired comparisons; a positive primary image-vs-best-baseline advantage with a 95% CI lower bound above zero on shuffled labels is a sanity-check failure.
- Run the depth-only baseline and compare it with both image models. Report partial region-level Spearman associations after residualizing the target and prediction against region-mean colour statistics and `log1p(total spot UMI)`, using participant-level held-out outputs. These checks do not change the primary model-selection rule.
- Sanity-check the held-out predictions for non-finite values, constant outputs, missing participants, and key mismatches before computing any endpoint.

These checks have not been run for GENE2.

## 6. Endpoints, resampling, and decisions

- **One primary endpoint:** mean participant-level difference in region-level Spearman for the best inner-selected image model minus the best inner-selected one of the two baselines, on the collagen module. Compute participant-level paired differences from outer out-of-fold predictions; bootstrap participants, not spots or regions, for 10,000 resamples using seed `20261124`; report the percentile 95% CI.
- **Exploratory success criterion only:** the primary CI lower bound is above zero and the image model's participant-macro mean of within-participant region Spearman is at least 0.30. Even if both conditions are met, this is not confirmation because every participant has prior use.
- **Failure rule:** anything else is a FAIL against the exploratory rule. Do not relax the rule, change targets, or add post-hoc models.
- For each secondary target, compare the primary-selected image model with the primary-selected best baseline using paired participant-level differences in region Spearman. Compute two-sided sign-flip permutation p-values using 10,000 random sign patterns, seed `20261126`, then Holm-adjust across the five targets. Report paired participant-bootstrap 95% CIs using seed `20261124`; secondary targets cannot rescue the primary endpoint.
- Save outer out-of-fold predictions for every eligible spot, region, and participant mean, each with participant keys. The spot key is `(participant_id, library_id, barcode)`; the region key is `(participant_id, library_id, block_row, block_col)`.
- Report participant-level and region-level Spearman and Pearson, MAE, participant-bootstrap 95% CIs, Holm-adjusted p-values, per-participant outcomes, sample counts, the shuffle control, and missing/excluded keys. Secondary targets cannot rescue the primary endpoint.
- If an execution gate fails, mark metrics and outcomes NOT AVAILABLE and do not claim a pass or fail from absent results.

## 7. Data-use and scope restrictions

No downloads, internet access, registration, fusion, multimodal integration, use of Phase B2 materials, or changes to the frozen Stage 1d model are allowed. The Stage 1d model may only be loaded read-only as a comparison baseline if separately authorized; it is not one of the four registered GENE2 models. All outputs from this stage are exploratory and not confirmatory.

## Timestamped re-confirmation — Path A (exploratory only)

**Re-confirmed:** 2026-11-17T11:33:16+05:30, before any GENE2 model run.

- Use the 40 already-used development participants only. No unseen participant exists; every GENE2 output is **EXPLORATORY, NOT CONFIRMATORY** and cannot be described as proof, success, or validation.
- `GENE2_FEATURE_VALIDATION.md` confirms that the saved 2,048-dimensional feature arrays are finite, have matching full spot keys, include all 40 participants, and contain no duplicate keys. The earlier missing-feature statement is corrected in `GENE2_DEVIATIONS.md`.
- For this run only, the user authorizes research-only use of the already-saved ResNet-50/ImageNet features despite the terms remaining **UNVERIFIED**. This overrides the previous licensing stop for this exploratory run only. Do not use the checkpoint to recompute features. Every feature-dependent output must say **RESEARCH-ONLY**. These weights/features must not appear in patent embodiments, commercial use, or claims.
- Local RENFAST/KPMP permission wording remains **UNRESOLVED**; do not interpret any wording. Use only files already on `D:\patent`. Do not use Phikon-v2 or another non-commercial encoder.
- Targets, models, alpha/grid values, seeds, five outer/four inner participant-grouped folds, 4-by-4 region pooling, early-stopping rule, primary endpoint, bootstrap rule, and exploratory pass criterion remain as previously registered. The feature-validation and licence authorization do not change the analysis method.
- The label-shuffle control uses one independently shuffled permutation of the registered region-level targets within each participant, seed `20261125`; it uses the primary-selected models and hyperparameters from the corresponding outer training fold, with no tuning on that outer test fold. The shuffle refits do not alter the primary model selection or endpoint.
- Fit budget: retain the 810 main nested-CV fits; add at most 20 selected-model label-shuffle fits (maximum total **830 fits**). The selected image model is either one Ridge fit or three MLP-seed fits; the selected baseline is one Ridge fit. All original 60-minute per-fit and 1-GB output caps remain in force. Each runner invocation also has a 90-minute wall-time cap and must stop before two hours.
- Exact command sequence, using the approved interpreter:
  1. `C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py preflight`
  2. For each outer fold `0`–`4` and inner fold `0`–`3`: `C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold <i> --inner-fold <j>`
  3. For each outer fold `0`–`4`: `C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py fit-outer --outer-fold <i>`
  4. After all folds finish: `C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py finalize`

Only the registered cached features and locally saved targets may be used. No GENE2 model run has occurred as of this re-confirmation.

## Timestamped pre-fit re-confirmation — 2026-11-17T12:05:02+05:30

Before any GENE2 fit, the user-authorized Path A design and all registered targets, models, grids, seeds, participant-grouped nested folds, 4-by-4 regions, convergence stopping rule, primary endpoint, bootstrap settings, and exploratory decision rule were re-confirmed without change. The saved-feature validation remains passed. The latest saved alignment preflight reports 41/41 libraries passed, 40 participants, 4,635 eligible regions, and 31,880 spots in those regions. No model fit has started as of this timestamp. This is exploratory only; the ResNet feature-dependent work is research-only, and dataset permissions remain unresolved.

