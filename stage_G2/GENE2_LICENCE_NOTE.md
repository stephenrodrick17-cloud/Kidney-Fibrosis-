# GENE2 Licence and Permission Note

**EXPLORATORY, NOT CONFIRMATORY.**
**RESEARCH-ONLY for this exploratory run.**

The registered exploratory nested cross-validation was completed on the locally saved features and targets. No data or weights were downloaded, no internet pages were accessed for GENE2, and no Phase B2 material was opened. The entries below distinguish recorded terms from unresolved items; they do not interpret any licence.

## Dataset and model status

| Asset | Recorded status | GENE2 use | Unresolved item |
|---|---|---|---|
| KPMP Visium spatial-expression data, original 28 participants | Local Stage 1 inventory/report records 28 participants, 29 libraries, and 25,104 spots. The sources reviewed for GENE2 do not record complete data-use terms for these local files. | Used only from existing local files in exploratory grouped nested cross-validation. No image pixels were re-read or downloaded. | File- and project-specific permission wording: **UNRESOLVED**. |
| KPMP Visium data for 12 Stage 1d participants | Stage 1d report records 24 downloaded files for 12 participants. It reports 16 catalogue DOI-linked records and 8 without a catalogue DOI; the two cited DOI collections are recorded as CC BY 4.0. | Used only from existing local files in exploratory grouped nested cross-validation. Gene values were reconstructed from saved residual targets and recorded residualization coefficients; the frozen Stage 1d model was not loaded. | Terms for the 8 records without DOI and any project-specific data-use requirements: **UNRESOLVED**. |
| Existing catalogue candidate set for the same 12 participants | Stage 1c lists 29 candidate records (24 expression/spatial files plus 5 TIFF candidates), approximately 6.09334 GB by rounded catalogue sizes; 20 records cite DOI collection(s) recorded as CC BY 4.0, and 9 have no DOI. | Not downloaded or newly used. All 12 participants were already evaluated in Stage 1d and are development-only for GENE2. | File-specific terms for the 9 records without DOI: **UNRESOLVED**. |
| torchvision ResNet-50 implementation | Project README records BSD-3-Clause for the torchvision code. | The encoder was not run for GENE2; only already-saved ResNet-50 feature arrays were used. | No GENE2 confirmation of any additional package terms. |
| ResNet-50 `IMAGENET1K_V2` checkpoint and upstream ImageNet dataset | Existing project records say weight-specific and ImageNet dataset terms were not independently verified. The checkpoint is identified in `D:\patent\stage1_expression\model_assets_manifest.csv`; its recorded SHA-256 is `11ad3fa62ca79e40addfd354a8ec4b7c75143b3038b8d2a807fbc68deab379ca`. | The user authorized research-only use of the already-saved feature arrays for this run. The arrays were validated and used; no checkpoint was loaded, no encoder was run, and no weights were downloaded. | Weight-specific and upstream dataset terms remain **UNVERIFIED**. |
| Frozen Stage 1d MLP/Ridge models | Existing frozen-artifact manifests record local checkpoint files; no separate GENE2 licence determination was made. | Not loaded or used for GENE2. | Any applicable third-party/model terms: **UNRESOLVED**. |
| Phikon-v2 | Stage 2C project records describe it as carrying an Owkin non-commercial licence and record that the project authorization was not established. | Not used, downloaded, or evaluated in GENE2. | Project authorization and licence terms remain unresolved in the existing record. |
| Any other encoder | None selected or used for GENE2. | None. | Not applicable. |

The existing Stage 1c report cites `https://doi.org/10.48698/16dd-vj20` and `https://doi.org/10.48698/3z31-8924` as pages stating CC BY 4.0, with the report dated 2026-11-13. No internet pages were accessed or reread for GENE2.

## Files mentioning Phikon-v2 or a non-commercial asset

The following existing files mention or plan around Phikon-v2; the project record describes references or a blocked plan, not GENE2 use:

- `D:\patent\stage2C_redesign\PREREG_2C.md` — describes a planned Phikon-v2 encoder; no GENE2 use.
- `D:\patent\stage2C_redesign\BLOCKER.md` — records the licence blocker and says no checkpoint was downloaded.
- `D:\patent\stage2C_redesign\STAGE2C_REPORT.md` — records that Stage 2C stopped before model use.
- `D:\patent\stage2A_audit\PREREG_RENFAST_BASELINE.md` — mentions avoiding Phikon-v2.
- `D:\patent\patent_prep\PATENT_PERMISSIONS_REGISTER.md` and `D:\patent\patent_prep\PATENT_VERIFICATION.md` — preserve the prior package's licence note and limitations.
- `D:\patent\stage_G2\GENE2_PREREG.md` — mentions Phikon-v2 only as a prohibited encoder.

A text search found no GENE2 script or other GENE2 file that loads, extracts features from, or evaluates Phikon-v2. No file named for a Phikon checkpoint was found in the local workspace. This is not a claim that no such asset exists outside the searched workspace.

## Original stop condition (superseded for this run only)

The earlier record required stopping until the inventor supplied or approved relevant data-use terms and ResNet-50 weight/ImageNet terms were verified. The dated user authorization below overrides the encoder stop for this exploratory run only. It does not resolve or interpret any licence or permission wording.

## User decision for this run — 2026-11-17

The user authorized Path A and research-only exploratory use of the already-saved ResNet-50/ImageNet features for this run, overriding the earlier encoder stop condition for this run only. The weight-specific and upstream ImageNet terms remain **UNVERIFIED**. These features must not appear in patent embodiments, commercial use, or claims. Any output depending on these features must be labelled **RESEARCH-ONLY**.

The user directed use of only the local KPMP/RENFAST files. Their permission wording remains **UNRESOLVED**; no wording is interpreted. Phikon-v2 and any other non-commercial encoder were not used. All result files depending on the saved ResNet-50/ImageNet features are labelled **RESEARCH-ONLY**. These features must not appear in patent embodiments, commercial use, or claims.

