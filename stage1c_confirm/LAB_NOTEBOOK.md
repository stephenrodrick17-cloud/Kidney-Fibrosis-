# Stage 1c lab notebook — audit and preregistration

## 2026-11-13 — Read-only audit and plan

- Reconciled open Visium expression and spatial-imaging catalog rows against the existing 28 Stage 1b participants. Found 12 additional catalog candidates and recorded their expression matrices, spatial bundles, and five same-sample TIFF image candidates in `open_visium_extra_assets.csv`.
- Checked the two DOI collection records cited by these assets; both state CC BY 4.0. Nine asset records have no DOI, so file-specific license terms remain unverified.
- Re-summarized Stage 1b participant-level Spearman results and computed participant bootstrap and leave-one-participant-out summaries from existing outputs only. No model was fitted and no new participant data were opened.
- Wrote `PREREG_CONFIRM.md` at 2026-11-13T10:00:04+05:30 before any future confirmation run. Chosen primary comparison is the Stage 1b image-only MLP for the neighbor-smoothed myofibroblast/profibrotic module against color-only and depth-only Ridge baselines, evaluated on the disjoint catalog candidates only.
- No download, archive extraction, model training, embedding generation, data movement, or deletion occurred. Stage 1 Gate A remains FAIL; Stage 1b remains exploratory, post-hoc.
