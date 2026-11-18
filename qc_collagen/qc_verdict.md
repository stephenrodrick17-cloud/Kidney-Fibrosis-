# QC verdict

- Paired expression cohort: 28 participants, 29 samples, 25104 spots.
- Empirical low-quality screen: UMI < 1194 or detected features < 799; 10th percentile cutoffs pooled across spots; flagged spots were retained.
- Prediction-screen genes (>=10% detection in >=half of participants): COL1A1, COL1A2, COL3A1, FN1, TGFB1, CCN2, ACTA2, MMP2, TIMP1
- Below that gene screen: SERPINE1, MMP9, HAVCR1, LCN2
- Prediction-screen modules (at least one member detected in >=10% of spots in >=half of participants): ECM_collagen, myofibroblast_pro-fibrotic, matrix_remodelling
- Modules below that screen: none
- TRI slides analyzed: 33; slides missing MPP: 0; mask-failure flags: 0.
- Pathologist score fields found in local metadata: 0 of 28 participants.
- Correlations use one participant-level value per participant, no spot-level collagen assignment, and bootstrap resampling of participants. The cohort size (n=28 maximum) gives low power; results are exploratory.
- `trichrome_collagen_proxy` is a fixed-HSV color proxy over all masked tissue. The mask includes glomeruli, vessels, capsule, and medulla and is not an interstitial-fibrosis measure.
- Not done: image registration, model training, batch correction, or assigning collagen values to Visium spots.
- Limitations: pen marks, folds, and blur require manual review of the saved slide composites; they were not automatically classified.

## PCA batch checks

| Variable | Component | Eta-squared | Permutation p | Status |
|---|---|---:|---:|---|
| tier | PC1 | 0.069 | 0.3455 | participant-level permutation test; descriptive, not corrected |
| tier | PC2 | 0.028 | 0.7035 | participant-level permutation test; descriptive, not corrected |
| fibrosis_status | PC1 | 0.000 | NA | not estimable: metadata has no variation |
| fibrosis_status | PC2 | 0.000 | NA | not estimable: metadata has no variation |
| visium_library_ids | PC1 | 1.000 | NA | descriptive only: high-cardinality library identifier |
| visium_library_ids | PC2 | 1.000 | NA | descriptive only: high-cardinality library identifier |
| sequencer_model | PC1 | 0.011 | NA | descriptive only: at least one group has fewer than 2 participants |
| sequencer_model | PC2 | 0.093 | NA | descriptive only: at least one group has fewer than 2 participants |
| sequencing_platform | PC1 | 0.011 | NA | descriptive only: at least one group has fewer than 2 participants |
| sequencing_platform | PC2 | 0.093 | NA | descriptive only: at least one group has fewer than 2 participants |
| repository_platform | PC1 | 0.000 | NA | not estimable: metadata has no variation |
| repository_platform | PC2 | 0.000 | NA | not estimable: metadata has no variation |

PCA associations are descriptive participant-level diagnostics, not batch correction. Fibrosis-score status is unknown for the cohort; sequencing metadata is locally available only for sample rows listed in `sample_metadata_audit.csv`.

## Participant-level correlations

| Feature | n | Spearman rho | 95% participant bootstrap CI | p (asymptotic) | BH q (genes only) |
|---|---:|---:|---:|---:|---:|
| COL1A1 | 28 | -0.135 | [-0.527, 0.254] | 0.4928 | 0.8571 |
| COL1A2 | 28 | -0.155 | [-0.520, 0.236] | 0.4313 | 0.8571 |
| COL3A1 | 28 | -0.165 | [-0.536, 0.250] | 0.4022 | 0.8571 |
| FN1 | 28 | -0.082 | [-0.459, 0.328] | 0.6799 | 0.8571 |
| TGFB1 | 28 | 0.070 | [-0.281, 0.407] | 0.7252 | 0.8571 |
| CCN2 | 28 | 0.095 | [-0.330, 0.506] | 0.6317 | 0.8571 |
| SERPINE1 | 28 | -0.016 | [-0.423, 0.390] | 0.9339 | 0.9339 |
| ACTA2 | 28 | -0.218 | [-0.567, 0.180] | 0.2654 | 0.8571 |
| MMP2 | 28 | -0.169 | [-0.549, 0.218] | 0.3911 | 0.8571 |
| MMP9 | 28 | 0.179 | [-0.194, 0.515] | 0.3621 | 0.8571 |
| TIMP1 | 28 | 0.022 | [-0.354, 0.403] | 0.9098 | 0.9339 |
| HAVCR1 | 28 | -0.094 | [-0.452, 0.294] | 0.634 | 0.8571 |
| LCN2 | 28 | 0.259 | [-0.118, 0.622] | 0.1834 | 0.8571 |
| ECM_collagen | 28 | -0.170 | [-0.546, 0.243] | 0.388 | — |
| myofibroblast_pro-fibrotic | 28 | -0.086 | [-0.491, 0.363] | 0.6637 | — |
| matrix_remodelling | 28 | -0.122 | [-0.508, 0.287] | 0.5379 | — |
