# NRM2 Existing RENFAST Model and Project Audit

**Audit date:** 2026-11-18
**Scope:** Stage 1 only
**Status:** READ-ONLY AUDIT COMPLETE; NO MODEL RUN, TRAINING, DOWNLOAD OR CODE CHANGE

## Executive summary

The project contains a functional frozen 2D U-Net prototype for 512-by-512 renal histology patches and a separate Phase B WSI-region extraction workflow. It does not yet contain a complete renal compartment model, reference-calibrated fibrosis agent, validated external reference cohort, or documented pathology-label pipeline.

The strongest existing evidence is technical mask overlap on RENFAST-style patches: the Phase A test result for the frozen U-Net is macro Dice `0.9153306335833998`, with an equal-family macro Dice `0.9119221709930561` and a family-bootstrap 95% CI of `0.8872443729453038` to `0.9340497987561561`.

That is not external or clinical validation. The existing evidence has no independent, slide-matched pathologist reference for KPMP, no verified compartment masks, no confirmed reference tissue cohort, no confirmed pathology percentages, and unresolved asset permissions.

## 1. Existing RENFAST implementation

### Architecture

The frozen model is implemented in `D:\patent\stage2A_audit\run_renfast_baseline.py`.

- Input: RGB 512-by-512 patches
- Encoding: 3 -> 32 -> 64 -> 128 -> 256 -> 512 channels
- Blocks: double 3-by-3 convolution blocks
- Bottleneck: 256 -> 512 -> 256 double-convolution design
- Pooling: 2-by-2 max pooling
- Upsampling: 2-by-2 transposed convolution
- Skip connections: encoder features concatenated in decoder
- Output: one sigmoid probability map
- Fixed threshold: `0.5`
- RGB scaling: 8-bit pixels divided by `255`
- Edge handling: bottom/right padding to a multiple of 16

The model source also provides training code, smoke tests, 512-patch prediction, and archive-audit functions. The production prototype imports this same `UNet` class rather than defining a separate model.

### Frozen checkpoint

- File: `D:\patent\stage2A_audit\renfast_baseline_run\checkpoint_best.pt`
- SHA-256: `674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb`
- Status: completed
- Best epoch: 78
- Epochs completed: 90
- Seed: 20261116
- Best validation Dice at 0.5: `0.9428534372573901`
- Device used: CUDA
- GPU: NVIDIA GeForce RTX 3050 Laptop GPU

The checkpoint is read-only in prior research rules. It must not be retrained, fine-tuned, replaced or threshold-changed for external audit work.

### Colour-rule baseline

The existing fixed colour rule is `B - R >= 2`.

The threshold `2` was selected only on RENFAST training/family data. It is a secondary comparison baseline, not a gold-standard fibrosis detector.

## 2. Existing dataset assets

### RENFAST archive

- File: `D:\patent\m2t49zf6xr-1.zip`
- SHA-256: `f796f0fa585701d66bd8f6b0ed096bb30f4376eff3359cb32ccbf1fd64d08a4e`
- 500 raw official training pairs
- 250 unique training pairs
- 250 exact duplicate training entries
- 105 active training pairs
- 18 active validation pairs
- 50 official test pairs
- 10 official test filename families
- 6 training filename families
- 1 validation filename family

The existing Phase A report says filename families are not verified patient or slide identifiers. A participant-level independence claim is therefore not supported by the archive split alone.

### Local WSI inventory

A read-only local count found:

- 63 files with SVS/TIFF-style extensions across `D:\patent\data` and `D:\patent\stage2A_audit`
- 28 distinct participant strings detectable from those paths/names
- 34 previously audited KPMP TRI WSI files from 29 participant strings
- 40 Phase FA participants and 41 libraries
- 41 saved Stage FA mask NPZ files

The 34-slide/29-participant local KPMP inventory is documented in `D:\patent\stage_NRM\NRM_AUDIT.md`. It has no confirmed normal/reference diagnosis field and is not usable as a verified reference cohort.

### Stage FA data

The existing Stage FA audit found:

- 40 participants used across prior stages
- 41 libraries
- 28 participants used in Stage 1 development
- 12 participants used in prior Stage 1d evaluation
- 41 PASS spot-to-image mapping rows
- No confirmed stain/colour-group label
- No confirmed IFTA percentage or grade
- No confirmed interstitial fibrosis score
- No confirmed tubular atrophy score
- No confirmed diagnosis
- No unseen participant set

The Stage FA evidence is explicitly exploratory and did not pass expert-mask Gate 1.

### External GSE/other assets

The project contains a GSE333529 tar and processed spatial-expression assets under `D:\patent\stage2A_audit\external_datasets\GSE333529\`.

No claim of independent expert kidney fibrosis annotation was identified in this audit. The external tar is not used in Phase A and should not be assumed to be a renal external-validation reference without separate provenance and label verification.

## 3. Existing Phase A training and evaluation

Training and evaluation are implemented by:

- `D:\patent\stage2A_audit\run_renfast_baseline.py`
- `D:\patent\stage2A_audit\PHASEA_run_audit.py`

Training uses:

- Soft Dice loss
- Adam
- Seed 20261116
- 100 maximum epochs
- Patience 12
- 512-by-512 RGB tiles
- Horizontal/vertical flip and 90-degree rotations
- Probability threshold 0.5

Saved test evidence:

| Metric | U-Net |
|---|---:|
| Image-macro Dice | `0.9153306335833998` |
| Equal-family macro Dice | `0.9119221709930561` |
| Family-bootstrap 95% CI Dice | `0.8872443729453038` to `0.9340497987561561` |
| Image-macro IoU | `0.8484173067065782` |
| Image-macro precision | `0.9298397785448145` |
| Image-macro recall | `0.9138991282944538` |

Paired U-Net minus colour-rule equal-family macro Dice difference:

- `0.08699843983256006`
- Family-bootstrap 95% CI: `0.07315876056020197` to `0.09962074456604735`

The Phase A rule passed within the saved analysis. These numbers are model-versus-supplied-manual-mask overlap metrics, not clinical accuracy.

## 4. Existing WSI support

### Implemented WSI selection

`D:\patent\stage2A_audit\PHASEB_select_regions.py` implements:

- OpenSlide access to local SVS slides
- Readable mpp-x/mpp-y metadata requirement
- Selection of pyramid level nearest 4.1 micrometres/pixel
- 512-by-512 target region extraction
- Tissue fraction threshold >=0.50
- Fixed-grid candidate generation
- Lanczos resizing
- Mean-RGB tissue rule: mean(R,G,B) < 245
- Slide-colour median of B-R
- Seeded region selection

This is partial WSI tiling infrastructure. It extracts a small fixed set of regions, not a complete tile pipeline for every slide.

The existing external-sanity run selected:

- 40 regions
- 26 slides
- 25 participants
- Maximum 3 regions per slide
- 4 colour strata

The selected region inventory is at `D:\patent\stage2A_audit\PHASEB_region_manifest.csv`.

### Existing quality-control work

The Phase B verification recomputed:

- 27 of 40 regions with empty-or-extreme U-Net area
- 25 of 40 regions with low-focus heuristic
- 1 highly saturated predicted-pixel flag
- No prediction outside tissue flag
- No independent reference-based accuracy metric

This is a region-level sanity check, not a complete pathology quality-control pipeline.

### Prototype support

The `D:\patent\prototype\` directory implements a local single-image tool:

- Frozen checkpoint verification
- PNG, JPEG and TIFF input
- Required user-supplied MPP
- RGB rescaling to 4.1 micrometres/pixel
- 512-by-512 tiling with white edge padding
- Tissue mask
- Frozen U-Net mask
- Fixed B-R colour-mask comparison
- OOD RGB z-score flags
- Tissue-fraction limit 0.20
- Binary mask PNG
- Overlay PNG
- JSON report
- Optional Visium nine-gene association
- Streamlit local app

It does not support direct SVS or TIFF pyramids in `PROTO_VALIDATE.py`. SVS support exists only in the separate OpenSlide Phase B scripts.

## 5. Tissue and compartment segmentation

Implemented:

- Tissue versus background mask using mean RGB < 245
- Binary fibrosis/collagen prediction mask
- WSI region extraction

Missing or unverified:

- Cortex versus medulla segmentation
- Renal tubule segmentation
- Glomerulus segmentation
- Blood-vessel segmentation
- Interstitial compartment segmentation
- Capsule/capsule-edge exclusion
- Normal collagen versus pathological interstitial fibrosis rule
- Expert compartment annotations
- Glomerular/vessel exclusion masks

The Phase B report explicitly records glomeruli/vessel assessments as not assessable and says no exact slide-matched spatial annotations were identified.

## 6. Collagen and fibrosis quantification

Implemented:

- U-Net positive fraction of tissue pixels
- Fixed B-R positive fraction of tissue pixels
- Tissue pixel denominator
- 512 tile inference
- Slide/region masks and overlays
- Colour/brightness OOD indicators

Missing or unverified:

- Cortical interstitial denominator
- Compartment-restricted fibrosis percentage
- Collagen-positive area separate from fibrosis
- Fibrotic-region density
- Fibrotic-area distribution
- Heterogeneity indices
- Physical-area conversions beyond prototype rescaling
- Expert-reviewed percentage
- Bland-Altman measurement validation
- Participant-level fibrosis calibration

The prototype reports tissue-pixel fraction, not clinical interstitial fibrosis percentage.

## 7. Reference calibration

No verified reference-calibration module exists.

The project contains:

- A colour OOD training-reference screen
- Phase C image-colour reference statistics
- Prototype reference warning/colour status

It does not contain:

- A histologically verified reference participant cohort
- A participant-level reference distribution
- Reference median/standard deviation/percentiles
- Living-donor versus nephrolithotomy distribution comparison
- Reference outlier pathologist-review workflow
- Z-score or empirical percentile fibrosis calibration
- Confidence intervals for reference measurements

The 21 Healthy Reference TRI metadata candidates and 22 open WSI records are not a verified reference cohort. The descriptor workbook is not downloaded or inspected, and exact stain, MPP, compartment and histology status are missing.

## 8. Comparative scoring agent

Missing.

The existing prototype accepts one image and returns:

- Validation status
- Tissue fraction
- U-Net percentage
- Colour-rule percentage
- RGB feature status
- Mask and overlay files

It does not implement:

- Whole-slide input in the final agent
- Participant identifiers
- Slide metadata registry
- Reference cohort loading
- Reference percentile or z-score
- Structured longitudinal/report schema
- HTML/PDF report
- Tile-level heatmap
- Quality-exclusion report
- Expert annotation comparison
- Pathologist review queue

## 9. Dependencies and hardware

The local environment:

- Operating system: Windows
- Python: 3.13.1
- NumPy: 2.2.6
- Pillow: 11.1.0
- PyTorch: 2.7.1+cu118
- SciPy: 1.18.1
- OpenCV/Python package: 4.10.0.84
- OpenSlide Python: 1.4.7
- OpenSlide binary: 4.0.1.2
- scikit-learn: 1.6.1
- scikit-image: 0.25.2
- tifffile: 2025.10.16
- h5py: 3.16.0
- openpyxl: 3.1.5
- Streamlit: 1.50.0
- GPU: NVIDIA GeForce RTX 3050 Laptop GPU
- CUDA: available

The RTX 3050 laptop is usable for 512-patch inference and small training, but no full-WSI throughput or memory benchmark was available. Full-slide processing may require level caching, streaming tiles or external storage.

## 10. Existing performance and verification

Verified local Phase A:

- Recomputed U-Net macro Dice: `0.9153306335833998`
- Recomputed equal-family macro Dice: `0.9119221709930561`
- Family CI: `0.8872443729453038` to `0.9340497987561561`

Verified prototype:

- 14 tests passed
- 0 failures
- 0 errors
- Five representative prototype masks were bit-identical to fresh Phase A inference calls
- Wrong checkpoint hash, missing MPP, invalid scale, grayscale, low-tissue and mismatched barcode checks passed

Existing warnings:

- Trained/tested on RENFAST trichrome patches around 4.1 micrometres/pixel
- Accuracy on other stains/scanners/tissues is not established
- Mask accuracy on KPMP is not expert-validated and masks are often sparse or extreme
- Cross-participant gene relationships were not found

## 11. Implemented, partial and missing components

| Component | Status |
|---|---|
| RENFAST U-Net architecture | Implemented |
| Frozen checkpoint loading and hash validation | Implemented |
| 512-patch inference | Implemented |
| Tissue mean-RGB mask | Implemented |
| Fixed B-R collagen baseline | Implemented |
| Phase A test/metric verification | Implemented |
| OpenSlide SVS region extraction | Implemented in Phase B, partial |
| Low-focus flag | Implemented, not expert tissue quality |
| RGB OOD screen | Implemented |
| PNG/JPEG/TIFF prototype input | Implemented |
| SVS whole-slide agent input | Missing |
| Full-slide tiling and coordinate persistence | Missing |
| Tissue overview and heatmap | Missing |
| Tubule segmentation | Missing |
| Glomerulus segmentation | Missing |
| Vessel segmentation | Missing |
| Interstitial compartment segmentation | Missing |
| Anatomical exclusion rules | Missing |
| Cortical interstitial fibrosis percentage | Missing |
| Histologically verified reference cohort | Missing |
| Reference distribution and calibration | Missing |
| Empirical reference percentile | Missing |
| Z-score only where sample size supports it | Missing |
| Comparative scoring agent | Missing |
| JSON slide report | Partial |
| PDF/HTML report | Missing |
| Expert pathologist annotation workflow | Missing |
| Quantification correlation/Bland-Altman | Missing |
| Independent external validation | Missing |

## 12. Dataset integrity findings

Existing local fibrotic/external evidence:

- 40 Stage FA participants had masks for 41 libraries, but no confirmed pathology labels
- 34 local TRI WSI files /29 participants in the earlier NRM audit had no normal/reference diagnosis metadata
- Phase B 40-region sanity run found 27 empty-or-extreme predicted-area flags
- No independent expert masks or expert fibrosis percentages were identified
- The Phase FA Gate 1 result is NOT PASSED

KPMP Stage 4 and Stage 5 findings:

- 21 unique Healthy Reference participants /22 open TRI WSI metadata records
- 666 unique open TRI participants /1315 open TRI WSI metadata records
- 426 participant IDs in the descriptor workbook metadata
- 5 Healthy Reference participant IDs overlap descriptor metadata
- The descriptor workbook was not retrieved or inspected
- Exact stain and MPP are not available for the external healthy cohort
- Commercial, patent and redistribution reuse terms remain unresolved

None of these KPMP samples should be described as normal, fibrosis-free or an established reference cohort until histology, stain, scale and pathology evidence are verified.

## 13. Permission and legal status

- RENFAST dataset permission: unresolved
- RENFAST checkpoint redistribution permission: unresolved
- KPMP WSI reuse permission: unresolved for clinical or research distribution; catalog open labels are not treated as licences
- Descriptor workbook commercial/research/patent terms: unresolved
- The exact project permission record contains no exact wording

No copying or redistribution of checkpoint or data is recommended until written permission scope is verified.

## 14. Recommended development strategy

Do not retrain or modify the frozen RENFAST checkpoint during initial development.

Recommended sequence:

1. Reuse the existing UNet and 512-patch inference implementation.
2. Add a read-only WSI wrapper around OpenSlide. Preserve the existing model class and threshold.
3. Do not use current Healthy Reference metadata as verified reference tissue.
4. Obtain and verify the KPMP descriptor workbook through a TLS-valid route before pathology label analysis.
5. Obtain MPP and stain protocol metadata for every external slide.
6. Obtain expert compartment and fibrosis masks before defining denominators.
7. Add tubule, glomerulus and vessel exclusion only after an annotation method is available.
8. Build participant-level reference calibration only from histologically verified reference participants.
9. Separate living-donor and nephrolithotomy reference distributions until comparability is tested.
10. Use participant resampling only after the unit of inference is established.
11. Add external validation only on a genuinely independent cohort.

## 15. Missing inputs required before Stage 2

The following are required before implementation can continue:

- Written permission wording for RENFAST images, masks and checkpoint
- Written reuse scope for open KPMP assets
- A successfully retrieved and TLS-verified descriptor workbook
- Histologic normal/reference status for candidate reference slides
- Exact stain protocol and Masson's trichrome verification
- Microns-per-pixel metadata
- Slide-to-specimen-to-participant identifiers
- Pixel-level or reliable region-level expert fibrosis annotations
- Independent test participant split

## 16. Audit commands and evidence

Read-only inspection used:

- `Get-ChildItem` inventory of project files
- `Get-FileHash` for checkpoint and RENFAST archive
- CSV/JSON/Markdown source reads
- Python source review
- No model execution
- No data download
- No code edit
- No checkpoint copy
- No sandbox or policy change

The existing project is suitable as a base for a modular fibrosis-quantification prototype, but the reference-calibrated agent and clinical/expert validation components are not implemented.
