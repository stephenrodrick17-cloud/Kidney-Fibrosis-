# Stage 1c confirmation plan — read-only audit

This folder contains a read-only audit of local catalog and Stage 1b outputs, plus a pre-run confirmation protocol. No data were downloaded or extracted; no model was fitted; no files outside this folder were changed or moved.

## Files

- `STAGE1C_REPORT.md`: requested audit and result summary.
- `PREREG_CONFIRM.md`: timestamped primary hypothesis and fixed future test protocol.
- `open_visium_extra_assets.csv`: 29 open expression/spatial candidate file rows for 12 additional participants, with catalog sizes, access, format, workflow, and DOI.
- `module_driver_participant_rhos.csv`: participant-level module Spearman values for six Stage 1b models, both target variants, and three modules.
- `module_driver_loo_summary.csv`: bootstrap means/CIs and leave-one-participant-out summaries.
- `primary_driver_robustness.csv`: primary Stage 1b paired comparison and leave-one-/leave-two-participant sensitivity.
- `LAB_NOTEBOOK.md`: append-only dated scope and decision record.

## Reproducibility and environment

Read-only calculations used Python 3.13.1, pandas 3.0.6, and NumPy 2.2.6. Participant-bootstrap summaries use 10,000 resamples with seed base `20261113`. Catalog sizes are rounded strings; byte totals in the CSV are estimates. Stage 1b source inputs and Stage 0 prior audit are linked in the report.

The timestamped preregistration is written before any new-cohort data or model run. Do not download or extract files, or run the confirmation test, until explicitly authorized.
