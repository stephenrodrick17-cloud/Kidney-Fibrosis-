# Stage FA Results — EXPLORATORY, NOT CONFIRMATORY

**EXPLORATORY, NOT CONFIRMATORY. UNVALIDATED MASKS.**

## What was analyzed

The corrected analysis matched 34,735 included spots from 40 previously used participants and 41 libraries to saved U-Net and colour-mask scores. All 41 image/expression libraries passed the exact participant + library + barcode key check. Each library met the registered minimum of 20 low- and 20 high-fibrosis spots for both masks; no library was excluded.

The U-Net mask is the preregistered primary mask. The `B - R >= 2` colour mask is a robustness repeat, not a second primary endpoint. Results below are associations only. They do not show that a gene causes, drives, predicts, or explains fibrosis.

## Primary endpoint

**Numerical rule status: MET in exploratory terms, using the U-Net mask.** The module is the mean of z-scored COL1A1, COL1A2, and COL3A1, so the effect is in module z-score units. This is not a reliable or confirmatory result because Gate 1 did not pass and the participants were used in earlier stages.

| Mask | Participants | High/low spots | Mean adjusted high-minus-low collagen-module effect | Participant-bootstrap 95% CI | Positive participants | Sign-flip p |
|---|---:|---:|---:|---:|---:|---:|
| U-Net (primary) | 40 | 23,132 | 0.1249 | [0.0804, 0.1702] | 31/40 (77.5%) | 0.00010 |
| Colour (robustness only) | 40 | 23,132 | 0.0894 | [0.0509, 0.1290] | 29/40 (72.5%) | 0.00020 |

Both masks have positive mean effects and the direction agrees. The U-Net result meets the preregistered numerical rule: its confidence interval lower bound is above zero, and 70% or more of participants have a positive effect. The colour result is not a co-primary result and cannot rescue a failed U-Net result.

The reported shuffle p-values are from 10,000 permutations of fibrosis scores within participants, followed by rebuilding the tertiles within each library. Both are at or near the smallest p-value that 10,000 shuffles can resolve; they do not validate either mask.

## Secondary gene associations

Effects are high-minus-low differences in the registered log-CP10K scale. Holm adjustment was performed separately across the nine genes for each mask. Secondary targets cannot replace or rescue the primary endpoint.

| Mask | Gene | Mean difference | Participant-bootstrap 95% CI | Sign-flip p | Holm-adjusted p | Mask directions agree? |
|---|---|---:|---:|---:|---:|---|
| U-Net | COL1A1 | 0.1003 | [0.0636, 0.1364] | 0.00010 | 0.0009 | Yes |
| U-Net | COL1A2 | 0.1532 | [0.0932, 0.2131] | 0.00010 | 0.0009 | Yes |
| U-Net | COL3A1 | 0.0950 | [0.0470, 0.1443] | 0.00070 | 0.0015 | Yes |
| U-Net | FN1 | 0.1015 | [0.0571, 0.1445] | 0.00010 | 0.0009 | Yes |
| U-Net | TGFB1 | 0.0392 | [0.0221, 0.0553] | 0.00010 | 0.0009 | Yes |
| U-Net | CCN2 | 0.0544 | [0.0055, 0.1075] | 0.04710 | 0.0471 | Yes |
| U-Net | ACTA2 | 0.1401 | [0.0614, 0.2169] | 0.00050 | 0.0015 | Yes |
| U-Net | MMP2 | 0.0717 | [0.0373, 0.1088] | 0.00030 | 0.0012 | Yes |
| U-Net | TIMP1 | 0.1629 | [0.0989, 0.2290] | 0.00010 | 0.0009 | Yes |
| Colour | COL1A1 | 0.0686 | [0.0313, 0.1065] | 0.00100 | 0.0060 | Yes |
| Colour | COL1A2 | 0.1166 | [0.0736, 0.1590] | 0.00010 | 0.0009 | Yes |
| Colour | COL3A1 | 0.0649 | [0.0199, 0.1099] | 0.00760 | 0.0228 | Yes |
| Colour | FN1 | 0.0603 | [0.0257, 0.0957] | 0.00190 | 0.0095 | Yes |
| Colour | TGFB1 | 0.0330 | [0.0208, 0.0456] | 0.00010 | 0.0009 | Yes |
| Colour | CCN2 | 0.0411 | [-0.0084, 0.0894] | 0.11879 | 0.1188 | Yes |
| Colour | ACTA2 | 0.0781 | [0.0118, 0.1416] | 0.02550 | 0.0510 | Yes |
| Colour | MMP2 | 0.0532 | [0.0226, 0.0855] | 0.00250 | 0.0100 | Yes |
| Colour | TIMP1 | 0.1163 | [0.0639, 0.1723] | 0.00020 | 0.0014 | Yes |

The complete results, including the per-participant effects and fit status, are in [FA_SECONDARY_HOLM_FINAL.csv](./FA_SECONDARY_HOLM_FINAL.csv) and [FA_PER_PARTICIPANT_EFFECTS_FINAL.csv](./FA_PER_PARTICIPANT_EFFECTS_FINAL.csv).

## Participant-level panel and severity

The collagen-module panel correlation between participant-level tissue-normalized fibrosis percentage and depth-adjusted pseudobulk expression was:

| Mask | Spearman rho | Participant-bootstrap 95% CI | Holm-adjusted p |
|---|---:|---:|---:|
| U-Net | -0.0711 | [-0.3442, 0.2547] | 1.000 |
| Colour | -0.1970 | [-0.5036, 0.1617] | 1.000 |

Both intervals include zero. The full 10-target panel is below; every listed confidence interval includes zero.

| Mask | Target | Depth-adjusted Spearman rho | Participant-bootstrap 95% CI | Holm-adjusted p | Mask directions agree? |
|---|---|---:|---:|---:|---|
| U-Net | Collagen module | -0.0711 | [-0.3442, 0.2547] | 1.000 | Yes |
| U-Net | COL1A1 | -0.0291 | [-0.3044, 0.3189] | 1.000 | Yes |
| U-Net | COL1A2 | -0.0345 | [-0.3321, 0.2758] | 1.000 | Yes |
| U-Net | COL3A1 | -0.0949 | [-0.3874, 0.2055] | 1.000 | Yes |
| U-Net | FN1 | -0.1047 | [-0.3701, 0.1895] | 1.000 | Yes |
| U-Net | TGFB1 | 0.0831 | [-0.1880, 0.3737] | 1.000 | No |
| U-Net | CCN2 | -0.1497 | [-0.4168, 0.1907] | 1.000 | No |
| U-Net | ACTA2 | -0.1379 | [-0.4104, 0.1695] | 1.000 | Yes |
| U-Net | MMP2 | -0.1820 | [-0.4388, 0.1458] | 1.000 | Yes |
| U-Net | TIMP1 | -0.0450 | [-0.3347, 0.2397] | 1.000 | Yes |
| Colour | Collagen module | -0.1970 | [-0.5036, 0.1617] | 1.000 | Yes |
| Colour | COL1A1 | -0.1685 | [-0.4811, 0.1947] | 1.000 | Yes |
| Colour | COL1A2 | -0.1251 | [-0.4428, 0.2232] | 1.000 | Yes |
| Colour | COL3A1 | -0.2024 | [-0.5363, 0.1008] | 1.000 | Yes |
| Colour | FN1 | -0.2940 | [-0.5761, 0.0445] | 0.6343 | Yes |
| Colour | TGFB1 | -0.1887 | [-0.4593, 0.1466] | 1.000 | No |
| Colour | CCN2 | 0.0499 | [-0.3064, 0.3772] | 1.000 | No |
| Colour | ACTA2 | -0.0872 | [-0.3924, 0.2297] | 1.000 | Yes |
| Colour | MMP2 | -0.2111 | [-0.5060, 0.1280] | 1.000 | Yes |
| Colour | TIMP1 | -0.2962 | [-0.5507, 0.0252] | 0.6343 | Yes |

The panel direction differs between masks for TGFB1 and CCN2; those panel results do not meet the preregistered mask-direction agreement condition. Full precision and unadjusted p-values are in [FA_PANEL_SUMMARY_FINAL.csv](./FA_PANEL_SUMMARY_FINAL.csv).

Severity calibration is **NOT TESTABLE**. No confirmed local pathology or clinical reference value was available for the searched variables. The Stage 1d metadata review was incomplete for non-CSV files; no missing value was imputed.

## Controls and robustness

- **Cell-density sensitivity:** without log total counts, the U-Net mean effect was 0.1294 (95% CI [0.0829, 0.1768]); the colour-mask estimate was 0.1101 (95% CI [0.0726, 0.1491]). The direction remained positive. These are sensitivity estimates, not replacements for the registered primary result.
- **Mean participant model R-squared:** for the U-Net analysis, depth/count/tissue covariates without the high/low indicator averaged 0.0727, colour plus those covariates averaged 0.1107, and the full primary model averaged 0.0973. For the colour-mask analysis, the corresponding values were 0.0714, 0.1084, and 0.0878. These are descriptive controls; the colour-only models had higher mean R-squared than the full primary model.
- **Image-colour proxy:** actual stain labels were not available. The preregistered median-hue quartiles had mean tissue-normalized fibrosis percentages of 6.29%, 9.22%, 7.20%, and 12.21% (U-Net Q1–Q4), and 14.48%, 29.57%, 46.93%, and 55.57% (colour-mask Q1–Q4).
- **Variance flag:** the image-colour group eta-squared was 0.0757 for the U-Net mask and 0.3840 for the colour mask. These exceeded the largest squared participant Spearman gene signal (0.0331 for MMP2 under U-Net; 0.0878 for TIMP1 under colour). The registered check flags image colour as a concern for both masks. Stain groups were not verified.
- **Label shuffle:** the within-library shuffle p-value was 0.00010 for each mask. This is a control result, not evidence that the masks are accurate.

Full control outputs are in [FA_CONTROL_MODELS_FINAL.csv](./FA_CONTROL_MODELS_FINAL.csv), [FA_CELL_DENSITY_SENSITIVITY_FINAL.csv](./FA_CELL_DENSITY_SENSITIVITY_FINAL.csv), [FA_LABEL_SHUFFLE_FINAL.csv](./FA_LABEL_SHUFFLE_FINAL.csv), [FA_COLOR_GROUP_SUMMARY_FINAL.csv](./FA_COLOR_GROUP_SUMMARY_FINAL.csv), and [FA_COLOR_CONFOUND_CHECK_FINAL.csv](./FA_COLOR_CONFOUND_CHECK_FINAL.csv).

## Participant influence

The U-Net collagen-module participant effects ranged from -0.1330 to 0.3921; 31 of 40 were positive. The leave-one-participant-out mean ranged from 0.1181 to 0.1315. The colour-mask effects ranged from -0.2144 to 0.3650; 29 of 40 were positive, and the leave-one-out mean ranged from 0.0823 to 0.0971. The mean is not driven by one participant in this descriptive check, but that does not resolve mask validity or image-colour confounding.

## Interpretation

In this already-used cohort, spots in the high-fibrosis tertile had higher adjusted collagen-module expression on average than spots in the low-fibrosis tertile. This is an exploratory association under masks that have not been checked against expert outlines. Meeting the numerical rule does not establish that the mask measures fibrosis correctly, that the finding will repeat in new participants, or that it has medical or clinical meaning.

The Stage FA analysis tables ending in `_FINAL` are the analysis results to use. The earlier unsuffixed first-pass tables are **invalid and superseded**: a constant tissue-fraction covariate caused 39 participants to be discarded and created a degenerate one-participant interval. The intermediate `_CORRECTED` tables fixed that regression issue but used an incorrect label-shuffle procedure; their shuffle p-values are superseded. The final run permuted continuous fibrosis scores within participant and rebuilt the tertiles per library. See D-006 and D-007 in [FA_DEVIATIONS.md](./FA_DEVIATIONS.md).
