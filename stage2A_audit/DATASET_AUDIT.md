# Stage 2A Dataset Audit

**Audit date:** 2026-11-13  
**Scope:** public dataset documentation and already-present local KPMP/RENFAST files. No data were downloaded, extracted, or opened beyond prior Stage 0 inventory and package documentation. No images or masks were loaded for pixel analysis.

## Sources reviewed

1. RENFAST official Mendeley Data record: https://data.mendeley.com/datasets/m2t49zf6xr/1 (DOI `10.17632/m2t49zf6xr.1`), accessed 2026-11-13.
2. KPMP project site: https://www.kpmp.org/ and Kidney Tissue Atlas: https://atlas.kpmp.org/, accessed 2026-11-13. The project site describes kidney-biopsy research and the Atlas; the Atlas landing page describes tools for retrieval, exploration, discovery, and analysis of KPMP data.
3. The local Atlas repository file-list snapshot, [atlas_repository_filelist-20261105.csv](</D:/patent/atlas_repository_filelist-20261105.csv>), and prior Stage 0 source audit, [STAGE0_REPORT.md](</D:/patent/stage0_audit/STAGE0_REPORT.md>). This snapshot marks 164 Pathology records as open: 152 whole-slide-image records and 12 segmentation-mask/pathomics records across the 28-participant development cohort.
4. The 12 local package READMEs and their source excerpts, summarized in [segmentation_readme_quotes.csv](</D:/patent/stage0_audit/segmentation_readme_quotes.csv>) and [segmentation_package_mapping.csv](</D:/patent/stage0_audit/segmentation_package_mapping.csv>); local dimensions/channels are summarized in [segmentation_package_audit.csv](</D:/patent/qc_collagen/review/segmentation_package_audit.csv>). Package content was not extracted or applied.

## RENFAST

| Item | Finding |
|---|---|
| Officially described content | The Mendeley record describes 300 Masson's trichrome (`TRIC`) images for renal fibrosis detection and 350 periodic acid-Schiff (`PAS`) images for vessel segmentation. It describes the image dataset and manual annotations used with the RENFAST algorithm. |
| Annotations | The local archive has manual fibrosis and tissue masks (`MANUAL_FIBROSIS`, `MANUAL_TISSUE`) for the fibrosis task, and manual vessel masks (`MANUAL`) for the vessel task. The page and archive do not document a separate numeric fibrosis/Karpinski score table. |
| Formats | The existing archive contains PNG images/masks, arranged in four train/test task folders. |
| Counts and pairing caveat | The archive is 2,350 entries. It contains 550 fibrosis image entries but only 300 unique normalized basenames (250 train and 50 test); the 250 extra train entries have colliding/duplicate basenames. File contents were not compared, so those entries cannot be assumed to be exact duplicates or independently paired cases. Vessel counts reconcile to 350 unique image/mask basenames (300 train, 50 test). The Mendeley record does not state a patient count; participant identities/linkage to KPMP are not reported. |
| Resolution | The Mendeley record does not state physical pixel spacing or magnification. This audit did not decode all PNG headers to calculate raster dimensions. No numeric resolution is asserted. |
| Stain relationship | Fibrosis annotations are for Masson's trichrome, not H&E. This is a different stain from KPMP H&E; it is a trichrome modality like KPMP TRI, but stain protocol, scanner, section identity, and color distribution are not established as interchangeable. RENFAST has no molecular data or KPMP participant linkage in the reviewed documentation. |
| Licence/access | The Mendeley page's licence field is blank, and the local archive contains no README/licence/terms file. Reuse, derivative-work, and commercial terms remain unverified. Do not train on, redistribute, or otherwise use RENFAST for modeling until the applicable terms are confirmed. |
| Download size | The already-present local ZIP is 518,896,940 bytes; its member metadata reports 520,111,286 uncompressed bytes. The Mendeley record does not provide a displayed total in the reviewed page. No new download occurred. |

## KPMP histology

| Item | Finding |
|---|---|
| Dataset scope | The Atlas repository file-list snapshot marks 164 Pathology records open across 28 development participants: 152 WSI records and 12 segmentation-mask/pathomics records. The project-level local image inventory contains 33 TRI slides. These are counts from the available catalog/local cohort, not a claim that the Atlas is exhaustive. |
| Formats | Catalogued WSI are principally `.svs`; segmentation packages are `.zip` archives containing OME-TIFF/TIFF masks, XML metadata, feature workbooks, and README files. |
| Stains | Local cohort WSI include TRI, PAS, H&E and other stains. The 12 local segmentation packages identify PAS source slides (sections 1 of 2 or 2 of 2), not H&E or TRI slides. Their OME annotation grids are reported at `0.2527 × 0.2527 µm/pixel`. The TRI slides used in the prior QC audit were read at pyramid level 2, approximately `4.04–4.21 µm/pixel`; this is the analysis level, not native scanner resolution. |
| Annotations | The packages contain compartment channels such as tubules, glomeruli, vessels/arterioles, peritubular capillaries, and cortex. Six of 12 package metadata inventories list an `IFTA` channel. The READMEs describe masks generated by a deep-learning network and subsequently quality-controlled by a renal pathologist; they do not establish that each mask, including IFTA, was directly expert-drawn. The v2 README says OME-TIFFs after slide `S-2006-005094` lack IFTA, which conflicts with later OME channel metadata listing IFTA. No direct expert-drawn collagen mask or verified numeric pathologist score was identified. A prior audit found no requested clinical/pathology fibrosis fields for the 28 participants. |
| Slide linkage | The package OME masks match their packaged PAS source-slide identifiers/dimensions. For all 12 packages, the PAS archive slide identifier differs from the participant's TRI slide identifier and no exact full-resolution TRI dimension match exists. Participant identity alone does not establish section correspondence. No registration was attempted. |
| Licence/access | The local Atlas file list marks the 164 Pathology records `open`. The reviewed file-list snapshot does not establish per-file copyright or reuse terms; those terms remain unverified and should be recorded as such. No controlled files were accessed. |
| Download size | The catalog contains per-file size values but does not state a total histology download size. The existing `D:\patent\data` folder is 15,817,172,196 bytes across modalities and is not a histology-only total. No bulk download or new file download occurred. |

## Project-diagram mismatch and usability

The project diagram's implied supply of expert collagen/compartment masks is not supported by the current KPMP package evidence: the available compartment outputs are network predictions with pathologist QC, and IFTA provenance is contradictory. RENFAST does provide manual fibrosis masks, but its reuse terms are blank/unverified and its 250 colliding train basenames have not been content-checked. Therefore, **there is currently no dataset that can be designated both usable under verified terms and supported by the required expert-mask provenance**.

The stain assumption also needs to be explicit: RENFAST fibrosis labels correspond to Masson's trichrome, not H&E. Matching stain family to KPMP TRI is not evidence that images, sections, staining protocols, or labels can be transferred to KPMP H&E/TRI.

## Audit limits

- The KPMP Atlas page and project overview describe the resource at a high level; the local repository file-list snapshot and package documentation provide the file-level evidence used here.
- KPMP catalog completeness, per-file licence terms, IFTA mask provenance, RENFAST patient count, RENFAST physical resolution, and the identity/content of duplicate-basename RENFAST entries remain unverified.
- This was a documentation/metadata audit only. No model, preprocessing, image-pixel analysis, or expert-mask metric was run.
