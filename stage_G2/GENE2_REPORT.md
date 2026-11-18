# GENE2 Report — EXPLORATORY, NOT CONFIRMATORY

**RESEARCH-ONLY — any result depending on saved ResNet-50/ImageNet features is research-only.**

## Outcome

The registered exploratory rule was **not met**. The primary paired difference was -0.020747, with participant-bootstrap 95% CI [-0.130057, 0.085933]. The image model's participant-macro region Spearman was 0.115376 (registered requirement: at least 0.30).

This is not proof, success, validation, or a confirmatory finding. All 40 participants were used earlier.

**Recommendation:** The registered exploratory rule was not met; this run does not provide a positive basis for recommending a confirmatory test.

## What the result does and does not mean

This analysis asks whether saved image features are associated with selected expression summaries in these already-used participants under grouped nested cross-validation. Any observed association is exploratory and may not transfer to unseen participants. It does not show that gene expression is directly visible in an image, establish a biological mechanism, or establish medical accuracy, clinical utility, novelty, or patentability.

The Spearman score compares rankings: it asks whether regions the model ranks higher also tend to have higher measured expression. The primary result averages each participant's region-ranking score equally.

## Checks and limitations

- Saved features and full spot keys passed validation. All 41 image/expression libraries passed alignment; the fold audit found no participant, library, or region overlap. There were 4635 regions and 31880 spots in eligible regions.
- The label-shuffle, depth-only, colour-only, and partial-correlation checks are recorded in the results and sanity files.
- A technical error after fitting outer fold 0 required repeating 10 completed fit calls; it is logged in `GENE2_DEVIATIONS.md` and `GENE2_RETRY_ACCOUNTING.json`. The fold's design and seeds were not changed.
- The actual total was 840 fit calls: 810 planned main fits, 20 saved shuffle fits, and 10 fits from the failed attempt. This is 10 above the registered 830-fit maximum and is disclosed as an execution deviation.
- The failed first outer-fold-0 attempt did not save its fit or command runtime; that exact runtime is **NOT AVAILABLE**. It failed after all 10 fit calls had completed. The saved successful-fold runtimes and finalization runtime are in `GENE2_VERIFICATION.md`.
- ResNet-50/ImageNet weight and dataset terms remain UNVERIFIED. The user authorized research-only use of saved features for this run only; they must not appear in patent embodiments, commercial use, or claims.
- RENFAST/KPMP permission wording remains UNRESOLVED. No wording was interpreted. Phikon-v2 and other non-commercial encoders were not used.
- Stage 1d raw gene values were reconstructed from saved depth-residualized targets and their recorded coefficients. The frozen Stage 1d model was not loaded or modified. No features were recomputed, and no data were downloaded.
- Adam was used because the preregistration did not name an optimizer; model-family tie rules and the 2,000-draw descriptive CIs are logged in `GENE2_DEVIATIONS.md`. The primary/secondary paired CIs used the registered 10,000 draws.

## Files in this package

- `GENE2_ALIGNMENT_AUDIT.csv`
- `GENE2_DATA_AUDIT.md`
- `GENE2_DEVIATIONS.md`
- `GENE2_FEATURE_VALIDATION.md`
- `GENE2_FOLD_MEMBERSHIP.csv`
- `GENE2_INNER_O0_I0.csv`
- `GENE2_INNER_O0_I1.csv`
- `GENE2_INNER_O0_I2.csv`
- `GENE2_INNER_O0_I3.csv`
- `GENE2_INNER_O1_I0.csv`
- `GENE2_INNER_O1_I1.csv`
- `GENE2_INNER_O1_I2.csv`
- `GENE2_INNER_O1_I3.csv`
- `GENE2_INNER_O2_I0.csv`
- `GENE2_INNER_O2_I1.csv`
- `GENE2_INNER_O2_I2.csv`
- `GENE2_INNER_O2_I3.csv`
- `GENE2_INNER_O3_I0.csv`
- `GENE2_INNER_O3_I1.csv`
- `GENE2_INNER_O3_I2.csv`
- `GENE2_INNER_O3_I3.csv`
- `GENE2_INNER_O4_I0.csv`
- `GENE2_INNER_O4_I1.csv`
- `GENE2_INNER_O4_I2.csv`
- `GENE2_INNER_O4_I3.csv`
- `GENE2_LABEL_SHUFFLE.csv`
- `GENE2_LICENCE_NOTE.md`
- `GENE2_METRIC_SUMMARIES.csv`
- `GENE2_NEEDS_NEW_DATA.md`
- `GENE2_OOF_REGION_PREDICTIONS.csv`
- `GENE2_OOF_SPOT_PREDICTIONS.csv`
- `GENE2_OUTER_FOLD_0.csv`
- `GENE2_OUTER_FOLD_1.csv`
- `GENE2_OUTER_FOLD_2.csv`
- `GENE2_OUTER_FOLD_3.csv`
- `GENE2_OUTER_FOLD_4.csv`
- `GENE2_PARTIAL_CORRELATIONS.csv`
- `GENE2_PER_PARTICIPANT_SPEARMAN.csv`
- `GENE2_PREFLIGHT.json`
- `GENE2_PREREG.md`
- `GENE2_PRIMARY_ENDPOINT.csv`
- `GENE2_REGION_DATA.npz`
- `GENE2_REGION_EXCLUSIONS.csv`
- `GENE2_RESULTS.md`
- `GENE2_RETRY_ACCOUNTING.json`
- `GENE2_RUNNER.py`
- `GENE2_SANITY.md`
- `GENE2_SECONDARY_HOLM.csv`
- `GENE2_SELECTION_O0.json`
- `GENE2_SELECTION_O1.json`
- `GENE2_SELECTION_O2.json`
- `GENE2_SELECTION_O3.json`
- `GENE2_SELECTION_O4.json`
- `GENE2_SPOT_TARGETS.csv`
- `GENE2_TARGET_COMPARISONS.csv`
- `GENE2_VERIFICATION.md`

## Exact next instruction needed

For a confirmatory result, provide an approved cohort containing participants never used in any earlier model or rule evaluation, and provide written permission for its use and verified encoder terms. Do not treat any of these 40 participants or the Stage 1d cohort as unseen. Otherwise stop here. No registration, fusion, multimodal integration, or filing work has been started.
