# GENE2 Leakage and Sanity Checks — EXPLORATORY, NOT CONFIRMATORY

**RESEARCH-ONLY — ResNet-50/ImageNet feature-dependent results.**

## Preflight and split checks

- Image/expression library alignment: 41/41 libraries passed.
- Participants: 40; eligible regions: 4635; spots in eligible regions: 31880.
- Full spot-key duplicates: 0.
- Fold membership passed independent participant, library, and region overlap checks. Each outer fold had 8 held-out and 32 training participants; each inner fold had 8 validation and 24 training participants.
- Every library and all adjacent spots from a participant inherit that participant's fold; no participant was split.

## Controls

- Label-shuffle image-minus-best-baseline primary mean Spearman: -0.006582, 95% CI [-0.038141, 0.026379]; pre-registered sanity failure: False.
- Depth-only and colour-only Ridge baselines were fitted in the registered nested design.

| Model | Partial region Spearman after adjustment for ranked colour features and depth | Regions |
|---|---:|---:|
| depth_only | -0.031456 | 4635 |
| color_only | -0.256438 | 4635 |
| image_ridge | 0.052123 | 4635 |
| image_mlp | 0.077714 | 4635 |
| selected_image | 0.077714 | 4635 |
| selected_baseline | -0.031456 | 4635 |

These checks are exploratory and use participants with prior development/evaluation. They do not establish confirmation or clinical meaning.
