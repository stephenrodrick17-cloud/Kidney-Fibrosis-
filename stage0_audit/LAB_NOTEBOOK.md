# Lab notebook (append-only)

## 2026-11-12 — Stage 0 storage, source, and access audit

- Scope: storage footprint, local RENFAST ZIP listing, local Seg_Masks_Features package/README/OME metadata, and the cohort's KPMP catalog records.
- Parameters: 10,000,000,000-byte cap; dimensions compared by exact full-resolution pixel width/height; no image registration or image-pixel processing.
- Decisions: no download, extraction, move, deletion, controlled-data access, model training, or registration. RENFAST terms are treated as unknown, not as permission.
- Findings: see `STAGE0_REPORT.md`; current project footprint is 32,246,580,487 bytes before Stage 0 outputs; IFTA channel provenance remains unverified.
- Reproduction: `python D:\patent\stage0_audit\scripts\audit_stage0.py`.

## 2026-11-12 — Sample-key reconciliation clarification

- Rechecked `plan_b_spot_expression_long.csv` and `plan_b_tile_manifest.csv` against source paths and `sample_metadata_audit.csv`.
- Both files contain 25,104 rows, 29 distinct `(participant_id, expression_source)` libraries, and 25,104 unique `(participant_id, expression_source, barcode)` keys.
- Their generic `sample_id` value `spatial` collapses the two 28-12265 libraries; 73 barcodes therefore repeat if keyed without `expression_source`. No earlier plan output or raw data was modified.
- Updated `cohort_count_reconciliation.csv` and the explanation in `STAGE0_REPORT.md`. Exact library identity should be preserved in any future analysis.
