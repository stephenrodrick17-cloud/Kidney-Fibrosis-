# NRM2 Stage 2 Audit Execution Log

**Audit date:** 2026-11-18

## Files and sources inspected

- Previous Stage 1 report: `NRM2_EXISTING_MODEL_AUDIT.md`
- RENFAST pair manifest and metrics
- Phase B slide/region/flags/metrics/report files
- Stage FA masks and reports
- Local OME-TIFF/XML segmentation files
- Recovered NRM2 v3 inventory and Stage 4 audit
- GSE333529 inventory and processing summary
- Prototype source and verification reports

## Scripts and commands

- Read-only PowerShell file inventory and SHA-256 verification
- Read-only CSV/JSON/Markdown parsing
- Participant and row reconciliation
- Cross-table overlap calculations
- CSV generation under `D:\patent\stage_NRM2\`

No training, inference, download or model execution was performed.

## Counts reconciled

- Master manifest: 1561 rows
- Fibrosis label audit: 1543 rows
- Expert mask inventory: 197 rows
- Reference cohort audit: 22 WSI candidate rows
- Stain audit: 1348 rows
- MPP scanner audit: 1348 rows
- Cohort allocation: 5 rows
- 300 unique RENFAST manual-mask pair population described in the Phase A audit
- 155 active RENFAST pair rows explicitly listed in the generated manifest
- 41 Stage FA computational masks
- 17 OME-TIFF/XML segmentation files
- 27 Phase B extreme flags
- 25 Phase B low-focus flags
- 25 overlap of extreme and low-focus flags

## Inaccessible or unresolved

- TIV Descriptor workbook was not retrieved
- External KPMP WSI files were not downloaded
- Exact stains, scanners and MPP metadata were unavailable for external records
- Expert author, independent review and pathology values were unavailable
- Permissions and reuse terms remain unresolved

## Integrity confirmation

No original dataset was modified.
No WSI was downloaded.
No model checkpoint was modified.
No threshold or architecture was changed.
No synthetic label or mask was created.
