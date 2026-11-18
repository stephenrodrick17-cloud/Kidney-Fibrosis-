# GENE2 Results — EXPLORATORY, NOT CONFIRMATORY

**RESEARCH-ONLY — ResNet-50/ImageNet saved features.**

All numbers are from grouped nested cross-validation on participants already used in earlier stages. They are exploratory and not confirmatory.

## Primary endpoint

Spearman measures whether regions ranked higher by a model also tend to have higher measured expression. The primary score averages these within-participant rankings equally across participants.

- Paired difference (image minus best baseline) in participant-macro region Spearman: -0.020747.
- Participant-bootstrap 95% CI: [-0.130057, 0.085933] (10,000 resamples; seed 20261124).
- Image-model participant-macro mean Spearman: 0.115376; required value: 0.30.
- The registered exploratory rule was **not met**. This does not mean proof, success, validation, or confirmation.
- Participants with paired primary metrics: 40; regions: 4635; spots in eligible regions: 31880.
- Selected image model(s) across outer folds: image_mlp; selected baseline(s): depth_only.

### Primary-target metrics

| Model | Region Spearman [95% CI] | Region Pearson [95% CI] | Participant-mean Spearman [95% CI] | Participant-mean Pearson [95% CI] | Region MAE [95% CI] |
|---|---:|---:|---:|---:|---:|
| Selected image model | 0.1314 [0.0143, 0.2448] | 0.1200 [0.0189, 0.2182] | 0.1360 [-0.1491, 0.4054] | 0.0755 [-0.1006, 0.2594] | 0.4558 [0.3953, 0.5273] |
| Selected baseline | 0.1560 [-0.0921, 0.3842] | 0.2468 [-0.0066, 0.4326] | 0.0901 [-0.2794, 0.4293] | 0.2892 [-0.1108, 0.5302] | 0.4154 [0.3557, 0.4847] |

Selected image-model participant-macro region Spearman: 0.115376 [0.051601, 0.177413].
Selected-baseline participant-macro region Spearman: 0.136123 [0.049035, 0.220723].
- The image-minus-baseline difference was positive for 18/40 participants. The three largest absolute participant differences are: 34-11042 (-0.8243), 936-10217 (-0.7379), 29-10277 (0.7005). See `GENE2_PER_PARTICIPANT_SPEARMAN.csv` for every participant.

## Secondary targets

| Target | Participants | Paired difference | 95% CI | Raw p | Holm p |
|---|---:|---:|---:|---:|---:|
| COL1A1 | 40 | -0.103452 | [-0.179306, -0.026396] | 0.0153985 | 0.0615938 |
| COL1A2 | 40 | 0.014224 | [-0.083722, 0.109309] | 0.776422 | 1 |
| COL3A1 | 40 | -0.124180 | [-0.203080, -0.048547] | 0.00339966 | 0.0169983 |
| FN1 | 40 | -0.022361 | [-0.102816, 0.058443] | 0.591541 | 1 |
| ACTA2 | 40 | 0.112059 | [0.018634, 0.209917] | 0.029897 | 0.089691 |

## Sanity checks and interpretation

- Within-participant shuffled-label mean difference: -0.006582, 95% CI [-0.038141, 0.026379]; pre-registered sanity failure: False.
- Depth-only and colour-only baselines were included in inner tuning and outer test predictions. Partial-correlation checks are reported in `GENE2_PARTIAL_CORRELATIONS.csv`.
- Every participant was used in earlier development or evaluation. These data cannot support a confirmatory claim.
- An observed image-to-expression association does not show that gene expression is directly visible in an image, establish a biological mechanism, or establish medical accuracy or clinical utility.
- **Recommendation:** the registered rule was not met, so this run does not provide a positive basis for recommending a confirmatory test.

Descriptive metric confidence intervals use 2,000 participant-bootstrap draws. Primary and secondary paired-difference intervals use the registered 10,000 draws.

Execution deviation: one failed outer-fold-0 output step required repeating 10 completed fit calls. The actual total was 840 fit calls (810 planned main fits, 20 saved shuffle fits, and 10 failed-attempt fits), which is 10 above the registered maximum. See `GENE2_DEVIATIONS.md`.

Full per-participant, per-region, per-spot, Pearson, MAE, and confidence-interval results are in the GENE2 CSV files.
