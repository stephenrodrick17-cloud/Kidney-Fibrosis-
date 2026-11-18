# NRM2 Complete Model Status Report

**Audit date:** 2026-11-18
**Scope:** Stage 1 and Stage 2

## A. Technical foundation

The existing system has:

- A 2D RENFAST U-Net
- A frozen checkpoint at `D:\patent\stage2A_audit\renfast_baseline_run\checkpoint_best.pt`
- Checkpoint SHA-256 `674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb`
- 512-by-512 RGB patch inference
- Fixed sigmoid threshold 0.5
- A fixed B-R colour-rule baseline
- Tissue mean-RGB masking
- PNG/JPEG/TIFF prototype support
- Partial OpenSlide SVS region extraction
- JSON/PNG/overlay prototype outputs

The system does not yet have a whole-slide agent, compartment model or reference-calibration module.

## B. Dataset foundation

Available:

- RENFAST archive with 300 unique manual-mask pairs in the Phase A summary
- 41 Stage FA U-Net NPZ masks
- 34 previously audited local TRI WSIs/29 participant strings
- 40 Phase B regions/26 slides/25 participants
- 1315 KPMP open TRI metadata records/666 unique participants
- 22 candidate Healthy Reference WSI metadata records/21 participants
- 426 IDs in descriptor workbook metadata

Missing:

- Expert fibrosis masks
- Quantitative pathology labels
- Verified histological reference tissue
- Exact trichrome/Masson protocol
- External MPP and scanner metadata
- Workbook-confirmed measurements
- Pathologist authorisation and reuse permission

## C. Existing capabilities

Works locally:

- Checkpoint hash verification
- Frozen U-Net inference on 512 patches
- Tissue-pixel fraction calculation
- Binary mask and overlay output
- RGB OOD indicators
- 512 region extraction from local SVS
- Low-focus and extreme-predicted-area screening

Quantitatively evaluated:

- RENFAST test image-macro Dice `0.9153306335833998`
- RENFAST test IoU `0.8484173067065782`

Exploratory only:

- KPMP region outputs
- Stage FA associations
- Reference metadata

Not developed:

- Cortical interstitial denominator
- Tubule/glomerulus/vessel/capsule segmentation
- Reference distribution
- Whole-slide aggregation
- Expert validation

## D. Missing components

Missing components include renal anatomical segmentation, compartment exclusion, quantitative cortical fibrosis, reference calibration, whole-slide heatmaps, pathologist annotation workflow, independent validation and PDF/HTML reporting.

## E. Scientific readiness

| Area | Status |
|---|---|
| Software foundation | PARTIALLY READY |
| Segmentation readiness | PARTIALLY READY |
| Quantitative fibrosis assessment | NOT READY |
| Reference-cohort readiness | NOT READY |
| Clinical validation readiness | NOT READY |
| Research-paper readiness | NOT READY |
| Patent-development readiness | NOT READY |

## F. Development roadmap

1. Dataset and pathology-label verification
2. Expert annotation and anatomical segmentation
3. Compartment-specific fibrosis quantification
4. Reference cohort establishment
5. Reference-calibrated scoring
6. Independent validation
7. Final reporting and deployment

Development gates 1-5 cannot proceed until missing evidence is obtained.
