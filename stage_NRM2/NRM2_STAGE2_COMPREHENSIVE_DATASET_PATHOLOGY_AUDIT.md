# NRM2 Stage 2 Comprehensive Dataset and Pathology Audit

**Audit date:** 2026-11-18
**Scope:** Read-only project and metadata audit
**Previous stage:** `NRM2_EXISTING_MODEL_AUDIT.md`

## 1. Executive summary

The project has one functional frozen RENFAST U-Net prototype and one partial OpenSlide region-extraction workflow, but no established external-validation cohort or verified fibrosis ground truth.

Confirmed:

- RENFAST checkpoint: `674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb`
- RENFAST 300 unique manual-mask pair population in the Phase A audit: 250 unique training and 50 test pairs
- Phase A U-Net test image-macro Dice: `0.9153306335833998`
- Phase A test image-macro IoU: `0.8484173067065782`
- 41 Stage FA computational mask NPZ files
- 40 Phase B regions from 26 slides /25 participants
- 21 unique KPMP Healthy Reference participant candidates with 22 TRI WSI metadata records
- 666 unique open TRI participants across 1315 open TRI repository metadata records
- 426 participant IDs in the descriptor workbook repository metadata

Not confirmed:

- Expert fibrosis masks
- Quantitative pathology fibrosis labels
- Ordinal expert fibrosis grades
- Histologically verified reference cohort
- Confirmed Masson's trichrome slides
- External MPP metadata
- Independent external-validation ground truth
- Dataset/pathology licences

## 2. Existing RENFAST model

The 2D U-Net uses 512-by-512 RGB patches, sigmoid output and a fixed 0.5 threshold. The checkpoint is read-only and was not modified.

Phase A reports:

- Macro Dice `0.9153306335833998`
- Equal-family macro Dice `0.9119221709930561`
- Image-macro IoU `0.8484173067065782`

These are manual-mask overlap metrics, not diagnostic accuracy or expert-confirmed interstitial fibrosis measurement.

## 3. Master dataset inventory

The master manifest is `NRM2_STAGE2_MASTER_DATASET_MANIFEST.csv`.

Generated inventory size: 1561 rows.

It includes:

- RENFAST archive and active/manual-mask pair records
- 32 existing local Phase B TRI slides
- 1315 recovered KPMP open TRI metadata records
- 41 Stage FA computational masks
- 17 local OME-TIFF/XML segmentation files
- Descriptor workbook metadata
- Additional audit records

The master manifest distinguishes downloaded/local files from repository-only metadata.

## 4. Fibrosis-label audit

The label-audit CSV contains 1543 rows:

- 155 active RENFAST pair rows, dataset-provided masks with incomplete provenance
- 41 computational Stage FA masks
- 1347 unverified Category E records

No expert-confirmed quantitative or ordinal fibrosis label was identified.

The workbook has not been downloaded or inspected. No pathology value can be extracted from its filename or repository metadata.

## 5. Expert mask audit

The expert-mask inventory contains 197 rows:

- 155 active RENFAST pair rows
- 41 Stage FA computational masks
- 1 blank Phase B expert-review form record

Confirmed expert fibrosis masks: 0.
Confirmed expert anatomical compartment masks: 0.
Confirmed expert interstitial/cortical/marginal exclusion masks: 0.

The 300 unique RENFAST manual-mask pairs documented in Phase A are dataset-provided masks. No pathologist author or independent expert review is established in the available records.

## 6. Healthy/reference cohort

Candidate count:

- 22 WSI records
- 21 unique participants
- 19 living-donor/transplant pre-perfusion candidates
- 2 nephrolithotomy/intra-operative candidates

Histologically verified reference count: 0.

The workbook metadata overlaps 5 participants: 164-8, 164-12, 164-17, 164-21, 164-22. No descriptor value was confirmed.

## 7. Stain audit

Confirmed Masson's trichrome slides: 0.

Stain categories:

- RENFAST: trichrome reported, exact protocol unspecified
- Local KPMP: catalog TRI workflow, exact protocol unspecified
- Recovered KPMP open TRI: TRI workflow, exact protocol unspecified

No slide should be assumed to be Masson's trichrome from blue collagen-like pixels or `TRI` filenames.

## 8. MPP and scanner

Verified MPP:

- 32 existing local Phase B TRI catalog slides
- 2 additional local TRI slides without MPP
- 1315 external TRI metadata records without MPP
- RENFAST patches without MPP metadata

Confirmed MPP values in external WSI inventory: 0.
Confirmed scanners: 0.

The 4.1 micrometre/pixel value is a target used by existing WSI extraction, not a substitute for missing metadata.

## 9. Phase B quality flags

The 40 Phase B regions were screened before model? The model results are existing:

- Empty-or-extreme U-Net area: 27
- Low-focus heuristic: 25
- Both flags: 25
- Extreme-only: 2
- Low-focus-only: 0
- Neither: 13
- Highly saturated: 1
- Outside tissue: 0
- Very pale: 0

The flags overlap and should not be counted as mutually exclusive.

## 10. Participant independence

Genuinely independent participant-level external validation: NOT ESTABLISHED.

Reasons:

- RENFAST filename families are not confirmed patient identities.
- Local Stage FA participants were previously used.
- Open TRI participant IDs are metadata identifiers, not an expert-ground-truth cohort.
- Multiple slides/libraries/biopsies may belong to the same participant.
- No independent expert masks or pathology percentages were identified.

Proposed cohort allocation:

- A model development: RENFAST filename-family split, identity unresolved
- B internal validation: RENFAST test/validation split, identity unresolved
- C independent external validation: not established
- D reference calibration: 21 candidate participants, zero histologically verified
- E exploratory/unverified: 666 open TRI metadata participants plus 40 local FA participants and local TRI slides

## 11. RENFAST compatibility assessment

The frozen model may process 512-patch RGB data and local extracted regions, but quantitative fibrosis measurement is not established on external data.

Compatibility evidence:

- Format: prototype supports PNG/JPEG/TIFF; OpenSlide script supports SVS extraction
- MPP: external metadata missing
- Stain: exact protocol missing
- Expert ground truth: missing
- Compartments: missing
- Whole-slide tiling: partial
- WSI coordinate reporting: partial Phase B region extraction only

## 12. Final feasibility

| Capability | Status |
|---|---|
| Binary fibrosis-like segmentation | PARTIALLY READY - RENFAST overlap evidence only |
| Interstitial fibrosis segmentation | NOT READY |
| Quantitative fibrosis percentage | NOT READY |
| IFTA assessment | NOT READY |
| Healthy-reference comparison | NOT READY |
| Reference-calibrated scoring | NOT READY |
| Participant-independent validation | NOT READY |
| External validation | NOT READY |
| Clinical interpretation | NOT READY |

## 13. Permissions

RENFAST permission, frozen checkpoint reuse and KPMP reuse terms remain unresolved. Open labels are not treated as licences.

## 14. Biggest limitations

- No expert compartment or fibrosis annotations
- No verified reference cohort
- No pathology workbook values
- No confirmed Masson's trichrome
- No external MPP/scanner metadata
- No independent external validation participant identity
- Existing masks are sparse/extreme on local Phase B sanity regions
- No validated cortical interstitial denominator

## 15. Recommended next stage

No implementation or training should start until:

1. Participant-level labels and expert masks are supplied or acquired with permission
2. The descriptor workbook is retrieved and inspected
3. Candidate reference tissue histology is reviewed
4. Exact stain and MPP metadata are verified
5. Living-donor and nephrolithotomy groups are assessed separately
6. An independent participant-level external cohort is established
