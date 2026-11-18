# NRM2 Stage 2 Fibrosis Label Audit

**Status:** READ-ONLY; no label generation or WSI download

## Counts

The generated label-audit CSV contains 1,543 rows:

- Category C, dataset-provided mask with incomplete provenance: 155 active Phase A training/test pair rows
- Category D, computational/automatically generated: 41 Stage FA NPZ masks
- Category E, unverified/inferred: 1,347 rows

No Category A expert-confirmed quantitative fibrosis label was identified.
No Category B expert-confirmed ordinal fibrosis label was identified.

## Category C - RENFAST archive

The RENFAST archive contains manual binary masks associated with 250 unique training pairs and 50 test pairs in the Phase A audit: 300 unique pair records. The active pair manifest used for the label CSV contains 105 training and 50 test rows, so the CSV rows do not represent every archive pair.

No pathologist author or independent expert review is documented in the available manifest. The labels are therefore dataset-provided masks with incomplete provenance, not expert-confirmed ground truth.

## Category D - Computational Stage FA masks

The 41 Stage FA NPZ masks are frozen-RENFAST U-Net outputs. They are computational masks and are labelled UNVALIDATED.

They are not:

- Expert fibrosis masks
- Histology grades
- Quantitative fibrosis percentages
- Independent expert annotations

## Category E - Unverified

The 32 local Phase B TRI slides and 1315 recovered KPMP open TRI repository rows have no confirmed fibrosis label in the inspected files.

Enrollment category, disease cohort or TRI workflow is not a fibrosis label. No fibrosis percentages, IFTA grades or expert severity labels were confirmed.

## Quantitative and ordinal counts

- Expert-confirmed quantitative fibrosis labels: 0
- Expert-confirmed ordinal fibrosis labels: 0
- Dataset-provided quantitative fibrosis labels: 0 confirmed
- Dataset-provided ordinal fibrosis labels: 0 confirmed
- Computational masks: 41
- RENFAST manual-mask pairs: 300 unique archive pairs /155 active manifest rows listed

**Usable fibrotic WSI samples: UNKNOWN - evidence unavailable.**
