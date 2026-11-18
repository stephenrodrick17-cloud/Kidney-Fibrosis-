# NRM2 KPMP Acquisition Milestone Report

**Report date:** 2026-11-18
**Phase:** Repository discovery only
**Status:** STOPPED BEFORE DOWNLOAD
**Label:** EXPLORATORY, NOT CONFIRMATORY. SOURCE-METADATA LABELS, NOT EXPERT-REVIEWED BY THE INVENTOR.

## 1. Repository result

The KPMP Atlas Repository interface was inspected. The all-files view reported **24,104 files**. It also displayed an example open light-microscopy SVS row:

- Participant ID: `34-10730`
- File name: `S-2209-009414_TRI_1of2.svs`
- Workflow: `TRI stain`
- Access: `open`
- Format: `svs`
- Size: `19.9 MB`

This example is not counted as an eligible healthy/reference record. Its enrollment category and tissue origin were not verified in the retrieved view.

## 2. Healthy-reference inventory

The exact repository UI filter combination was inspected for:

- Experimental strategy: `Light Microscopic Whole Slide Images`
- Access: `open`
- Enrollment category: `Healthy Reference`
- Workflow: `TRI stain`

Result: **0 files**.

Therefore, the current visible result is:

- Unique eligible healthy/reference participants: **0**
- Eligible open trichrome slides in this exact filter: **0**
- Living Kidney Donor participants: **NOT AVAILABLE** by separate participant-level subtype query
- Kidney Stone Donor participants: **NOT AVAILABLE** by separate participant-level subtype query
- Pilot Nephrectomy participants: **NOT AVAILABLE** by separate participant-level subtype query

The result does not prove that no healthy/reference files exist if repository filter syntax or data release state differs. It is the exact count returned for the repository UI query.

## 3. Pathology descriptors

The repository was queried for:

- Experimental strategy: `Pathology Descriptor Scoring`
- Access: `open`

Result: **0 files**.

The exact strategy with no access filter also returned **0 files**. The requested filename `KPMP TIV Descriptor Scores 10.12.2026.xlsx` was **NOT FOUND** in the repository filter used. No fibrosis percentage, IFTA grade, pixel mask, or expert second score was obtained.

Evidence from public GitHub code references an earlier filename, `KPMP TIV Descriptor Scores 03.30.2025.xlsx`, but that is only code referencing a local or separately obtained file. It does not establish public availability or eligibility.

## 4. Access and licence

The repository documentation states:

- `Open access` files may be downloaded directly from the Atlas Repository.
- `Controlled access` files require a Data Use Agreement.
- KPMP says: “Please note: Users requesting access must submit a [Data Use Agreement] and be approved before access is granted.”

An open label was not treated as a licence. No specific licence or commercial-use permission was verified for the example SVS file or descriptor records. Research/commercial redistribution restrictions remain **NOT AVAILABLE / UNRESOLVED** until the provider's exact licence or terms are readable and quoted.

No controlled-access request was started.

## 5. Download status

No image, descriptor spreadsheet, archive, licence, or metadata file was downloaded. No model run or tile extraction occurred.

## 6. Unresolved items

- Exact living-donor, kidney-stone-donor, and pilot-nephrectomy subtype counts.
- Participant-level enrollment and tissue-source metadata for all TRI files.
- Exact 2026 descriptor filename and its access class.
- Linkage keys from descriptor records to WSI participant and sample IDs.
- Whether open Atlas files have a separate licence, commercial restriction, redistribution restriction, or attribution requirement.
- Whether any open TRI files contain verified micrometres-per-pixel and scanner metadata.
- Pixel-level expert masks.

## 7. Stop decision

Do not download under the current Phase 1 result. The exact healthy/reference TRI query returned 0 files and the exact descriptor query returned 0 files. Pathology labels and independent validation could not be matched. Approval is required before any future download because the repository has not shown a licence-permitted eligible file set.
