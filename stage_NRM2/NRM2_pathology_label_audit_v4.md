# NRM2 Stage 4 Pathology Metadata, Label and Reuse Audit

**Report date:** 2026-11-18
**Status:** METADATA AUDIT COMPLETE; WORKBOOK AND HISTOLOGY NOT VERIFIED
**Label:** EXPLORATORY, NOT CONFIRMATORY. SOURCE-METADATA LABELS, NOT EXPERT-REVIEWED BY THE INVENTOR.

## 1. Healthy Reference participant verification

The v3 inventory contains 22 Healthy Reference TRI WSI files for 21 unique participants.

Participant metadata available in v3:

- 19 participants: HRT Living Donor Protocol
- 2 participants: HRT Percutaneous Nephrolithotomy Protocol
- 19 living-donor records use Transplant Pre-perfusion Biopsy
- 2 nephrolithotomy records use Intra-operative Biopsy

Classification:

- Living-donor tissue is transplant-kidney context from the protocol and sample type.
- Nephrolithotomy tissue is native kidney stone-donor context at metadata level.
- Healthy Reference enrollment does not establish histologically normal or reference tissue.

Staining and imaging:

- Repository metadata says TRI stain for all audited Healthy Reference records.
- It does not explicitly document that TRI means Masson's trichrome.
- Exact staining protocol: NOT VERIFIED
- Masson's trichrome explicit: NOT VERIFIED
- Anatomical compartment: NOT VERIFIED
- Micrometres per pixel: NOT VERIFIED
- Slide format: SVS

The exact 164-6 record is confirmed as:

- Participant 164-6
- HRT Living Donor Protocol
- Transplant Pre-perfusion Biopsy
- Healthy Reference
- TRI stain
- Open
- 392552203 bytes

## 2. Five descriptor-overlapping participants

The open KPMP TIV Descriptor Scores 10.12.2026.xlsx record lists 426 participant IDs. Five overlap with the 21 Healthy Reference participants:

- 164-8
- 164-12
- 164-17
- 164-21
- 164-22

Participant 164-6 does not appear in the descriptor participant-ID list.

The workbook was not downloaded or inspected. For all five participants, these remain NOT VERIFIED:

- Interstitial fibrosis descriptor
- Tubular atrophy descriptor
- Cortex-specific fibrosis estimate
- Medullary fibrosis estimate
- Percentage-based score
- Pathologist score
- Slide-level association
- Participant-level association
- Usable fibrosis measurement

No value was inferred from the workbook filename or repository metadata.

## 3. Wider open TRI cohort

The v3 inventory contains:

- 1315 open TRI WSI files
- 666 unique participants
- AKI: 178 files / 93 participants
- CKD: 995 files / 493 participants
- DM-R: 120 files / 59 participants
- Healthy Reference: 22 files / 21 participants

Enrollment category or TRI staining is repository metadata, not a workbook-confirmed fibrosis label or expert histology result.

No mild, moderate, or severe fibrosis examples can be confirmed until the open descriptor workbook is downloaded through an approved TLS-verified route and its columns, participant rows and sample associations are inspected.

## 4. Reuse permissions

Official repository documentation states:

- Open files may be downloaded directly.
- Controlled clinical and pathology data require a Data Use Agreement.
- Users are asked to cite KPMP data when publishing work based on it.

NOT VERIFIED:

- Commercial use
- Patent or filing use
- Redistribution of original images
- Redistribution of derived masks or annotations
- Whether open terms differ by file type

The exact Data Use Policy and DUA text were not verified as verbatim licence terms in this stage.

## 5. Verification states

For every participant in `NRM2_pathology_label_audit_v4.csv`:

- Repository metadata is confirmed by the official search API.
- Histologically normal/reference status is NOT VERIFIED.
- Native versus transplant context is verified only when protocol/sample metadata identifies it.
- Exact TRI/Masson protocol is NOT VERIFIED.
- Anatomical compartment is NOT VERIFIED.
- MPP is NOT VERIFIED.
- Fibrosis percentage and grade are NOT VERIFIED.
- Pathologist information is NOT VERIFIED.
- Commercial/patent/redistribution terms are NOT VERIFIED.

## 6. Download and execution status

No WSI file was downloaded.
No descriptor workbook was downloaded or inspected.
No model was run.
No tile extraction or image processing occurred.
No TLS verification was bypassed.
