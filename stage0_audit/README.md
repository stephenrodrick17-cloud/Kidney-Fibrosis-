# Stage 0 audit outputs

Purpose: reproducible, read-only Stage 0 storage, RENFAST archive-list, segmentation package, and KPMP catalog audit for `D:\patent`.

## Files

- `STAGE0_REPORT.md`: final Stage 0 report and gate verdict.
- `scripts/audit_stage0.py`: read-only inventory/report generator.
- `storage_top_level.csv`: exact top-level item sizes.
- `storage_per_participant.csv`: exact sizes/file counts for participant directories under `data`.
- `largest_files.csv`: 20 largest existing project files at audit time.
- `renfast_archive_inventory.csv`: ZIP member paths/types/sizes; no extraction.
- `renfast_directory_and_pairing_summary.csv`: RENFAST folder counts and basename-pair checks.
- `segmentation_package_mapping.csv`: package OME/source-slide metadata and exact-dimension checks.
- `segmentation_readme_quotes.csv`: per-package README quotations from local archives and any extracted copies.
- `kpmp_catalog_access_by_category.csv`: cohort catalog access counts by category.
- `kpmp_clinical_candidates.csv`: catalog rows matching clinical/pathology search terms (header-only when none match).
- `cohort_count_reconciliation.csv`: cross-check of participant, sample and spot counts in existing plan outputs.
- `LAB_NOTEBOOK.md`: append-only dated Stage 0 record.
- `requirements-stage0.txt`: pinned Python package versions used by the inventory script.
- `scripts\__pycache__\audit_stage0.cpython-313.pyc`: bytecode created by the syntax check.

## Software and reproducibility

- Python: 3.13.1
- OpenSlide Python: 1.4.7; OpenSlide library: 4.0.1
- tifffile: 2025.10.16; Pillow: 11.1.0
- Random seed: none; this audit uses deterministic listings and metadata reads only.
- Exact command: `python D:\patent\stage0_audit\scripts\audit_stage0.py`
- Inputs are read from `D:\patent\data`, `D:\patent\atlas_repository_filelist-20261105.csv`, `D:\patent\m2t49zf6xr-1.zip`, `D:\patent\plan_a_plan_b`, and `D:\patent\qc_collagen\review`.
- No images were extracted or decoded; no raw data or earlier outputs were edited; no files were moved or deleted.
- Dataset sources: KPMP local repository catalog dated 2026-11-05; RENFAST Mendeley landing page DOI 10.17632/m2t49zf6xr.1. RENFAST terms were not visible, so dataset use is not authorized by this audit.
