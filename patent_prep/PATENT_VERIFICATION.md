# Verification Record

Draft prepared 2026-11-17. This is a read-only document cross-check; no training, inference, data analysis, downloads, or B2 tile/key/annotation access was performed for this package.

## Number and statement cross-check

The numeric entries in `PATENT_EVIDENCE_REGISTER.md` were transcribed from the indicated Phase A and Phase C report/metric files. Phase A full-precision values were taken from `PHASEA_final_metrics.json` and `PHASEA_final_per_group_metrics.csv`. Phase C paired-mean values were copied at the precision shown in `PHASEC_REPORT.md`; the two direction rows were copied from `PHASEC_robustness_summary_corrected.csv`. No values were recomputed or rounded for this package.

| Draft section | Cross-check source | Result |
|---|---|---|
| Evidence Register, Phase A overall metrics and paired difference | `PHASEA_final_metrics.json`; `PHASEA_RESULTS.md` | Values and resampling units transcribed; Phase A report confirms the 10-family limitation and filename-family grouping. |
| Evidence Register, per-family Dice | `PHASEA_final_per_group_metrics.csv` | All 10 family IDs, image counts, and both model Dice values transcribed. Per-family CIs are marked NOT AVAILABLE because none are recorded. |
| Evidence Register, Phase C robustness and resolution | `PHASEC_REPORT.md`; `PHASEC_robustness_summary_corrected.csv` | Paired means, CIs, changes, and the two individual-direction rows transcribed. |
| Method Description | `PHASEA_run_audit.py`; `PHASEB_select_regions.py`; `PHASEB_run_external_check.py`; Phase A/B reports and preregistration | Code-backed input, scaling, padding, threshold, and area-denominator statements identified; model architecture details and RENFAST physical spacing remain missing. |
| Claim Support Map | Phase A, B, B2, and C reports and records | Supported and excluded subjects are limited to what those records establish. Stage 1/1b/1d failure reasons and the specific expert-mask mismatch are marked unavailable where the permitted record did not verify them. |
| Inventive-Step Questions | Phase A/B/C code, reports, preregistration, and Phase C run metadata | Listed choices are attributed to saved records. No conclusion is made about inventiveness or human inventorship. |
| Disclosure Checklist | Phase A and C reports, manifests, code, README, metadata, and checkpoint-hash records | Recorded and missing values are labelled; Phase C ensemble metadata is distinguished from the frozen Phase A model. |
| Permissions Register | Phase A/B/B2/C licence records | Blank/unresolved terms are preserved. Phikon-v2 non-commercial status is identified as a package instruction, not independently verified from permitted Phase A-C records. |
| Limitations and Attorney Briefing | Phase A/B/C reports | Failure counts, robustness limitations, uncertainty result, baseline blocker, and research-only limitation match the saved reports. |

No numeric discrepancy was identified in the checked transcriptions. This is a manual source-to-draft check, not an independent recomputation of model metrics.

Process note: during initial source inspection, the non-prefixed file `D:\patent\stage2A_audit\run_renfast_baseline.py` was inadvertently opened, although the request restricted usable sources to Phase A–C prefixed files. It was not used as a factual source for the drafts; each technical detail included here is attributed to the permitted PHASE-prefixed reports, scripts, or metadata. Its name and hash are listed below to keep the read record complete.

## Items marked NOT AVAILABLE, NOT FOUND IN CODE, or MISSING

- Per-family 95% CIs: NOT AVAILABLE in the saved Phase A per-group table.
- RENFAST physical pixel spacing and a RENFAST scale-normalization procedure: NOT AVAILABLE / NOT FOUND IN CODE.
- Frozen U-Net layer/channel specification, normalization details, output-head details, and parameter count: NOT FOUND IN CODE in the permitted Phase A-C source set.
- The frozen Phase A model's original training seed, epoch count, best epoch, independent run metadata, and exact training loss/optimizer/augmentation record: MISSING from the permitted Phase A files. Phase C records a later recipe for its two new ensemble members.
- Exact augmentation operations/probabilities/ranges: NOT AVAILABLE.
- Original reason the frozen Phase A probability threshold was selected: NOT AVAILABLE.
- Deployment output API/schema and user-facing display: NOT AVAILABLE.
- Exact Stage 1/1b/1d failure records: NOT AVAILABLE in permitted Phase A-C files; only the user-provided FAIL labels are known.
- Exact source and result for the claimed KPMP expert-mask mismatch: NOT AVAILABLE in the Phase B report. Phase B2 reports that no human annotations had been received.
- Image–molecular registration/fusion evidence: NOT AVAILABLE in the Phase A-C reports.
- Phikon-v2 licence version and written authorization: NOT AVAILABLE in the permitted Phase A-C files; the package instruction says to treat it as non-commercial and exclude it unless written authorization is confirmed.
- Complete Phikon-v2 inventory outside the searched Phase A-C sources: NOT AVAILABLE.
- Exact KPMP data-use terms and exact RENFAST permission wording: UNRESOLVED; paste-in blocks are blank.

## Source files read and SHA-256

Hashes below were collected on 2026-11-17 using SHA-256. Paths are relative to `D:\patent\stage2A_audit`. Hashes identify the source snapshots used for these drafts.

| Source file | SHA-256 |
|---|---|
| PHASEA_RESULTS.md | `54e955c931c095b79ecf8ec699dd0615b865101ecd8b92b32a13f57ca9c13f57` |
| PHASEA_README.md | `79433c17d1ddc0ba64679659434fb828f48502877af2b6704158251edff48254` |
| PHASEA_final_metrics.json | `d6bfc41e656b86c252a32f2b113026b760b8ea91a83e790409fa525b44473bfd` |
| PHASEA_final_per_group_metrics.csv | `f815cd8fbc602e418be4e6df2b4e4cb217475c8fe40c53fee86d2904d0317618` |
| PHASEA_final_split_manifest.csv | `2eafb2ec6d2ec7b2d8d3762bc27b2f159c4736fbeaefb4da03356d83f6a055ee` |
| PHASEA_LICENCE_REGISTER.md | `ffa5ac2ca8806b3cc8a1f0062a939e4766f7017ebc0564e1177e7cfca6a1c84e` |
| PHASEA_PREREG_A.md | `0bb4a2c7e1c471a2f7296d51b9174f75cd7b2833b9fdd0ff840bb24cdad482ab` |
| PHASEA_run_audit.py | `b1d1f7652109d019a81bb006d02984b11abdb7d0dfc8a17938b95673ff9511b2` |
| run_renfast_baseline.py (inadvertently opened; not used as a source) | `29698e03cfc0135133468d224db46ebf856bb5e15fc2953a40208efde62e1001` |
| PHASEA_PERMISSION_RECORD.md | `d7f0af966e50bedfb664693ff2097892f740955f8ce43060dfad4687de3a44d1` |
| PHASEA_INTEGRITY_CHECK.md | `96f77340629d96cfd88ace7befdbed5f3ff883cbb2526f92a2c75becf88977eb` |
| PHASEA_DEVIATIONS.md | `b7afb24e26f818cf41bc16ba6dd92ab069682240dc09987ab9d64e47a8c21656` |
| PHASEB_REPORT.md | `917fa4915cbb817e2e81788d644ef0b18374ee06621cf5a303e85d91290e554a` |
| PHASEB_PREREG.md | `e8a2cdc5d6e30cd5c4cfaf63cc9dd131902cfe620b3daa50f323278d8047c8dc` |
| PHASEB2_REPORT.md | `b1aa000afb4abf4ab1ac527b8de4981d6081528592a08ce62a093db81b531b75` |
| PHASEB2_LICENCE_REGISTER.md | `7c78a3cfbb229357192a77bebcb4cce111809f3afc89c10a18c20e688cfe3835` |
| PHASEB_inference_summary.json | `fe805f19fb97a0d72dcd173f4f65c6dc77401a858bfedbef2bbc1167eec68551` |
| PHASEB_region_metrics.csv | `b700444eaf97e329ac97dfe060685229bf538e08730497227b3d257e19030cc4` |
| PHASEB_run_external_check.py | `bb5baee0324d66dd83c25267f41c9bdfbc0d8d1282d2e7dc7d06b95b3ac641f9` |
| PHASEB_select_regions.py | `382e385096604ce71551f97803d865b1f56e8d0785fa4ddef60c6b5ca4e51d4a` |
| PHASEC_PREREG.md | `4d00421202895ba05897a009c7c1c57f2c1556de12f7056018bad8774d861c26` |
| PHASEC_REPORT.md | `738f350b101650ed71888dd36b2ab2c98d4e0f6f17c6e18369218daa64df089d` |
| PHASEC_DEVIATIONS.md | `5e66dc7358a40f0849c7eec22bc8253e6ffbb52ff61f3e4db47af2d54ff8d3ba` |
| PHASEC_README.md | `ce728a5877920fc9f9d9774e3e3dd09081dd13945eeff1728db8b3e604ade416` |
| PHASEC_ENVIRONMENT.json | `951fcbb9ed07d79f68c5b5f2be04ad4c4a93942cdfa2706157d06a623cad2fec` |
| PHASEC_VERIFICATION.json | `397dd5e42442965aaea189a3657e4a9c9346c49e3dc3eb922c1a92596209c8dc` |
| PHASEC_LICENCE_REGISTER.md | `54b48701eb534786fd342ee12ef4ad64f5d3f9297d1fd8c9b0cde854399f5552` |
| PHASEC_run.py | `9a4a350e673a52445b03c03e000a6b636b284629e8e75f832a8d87a668d34636` |
| PHASEC_UNET_seed_20261122_metadata.json | `b72daa0173d18e9e1b4cff11f3a3a6b301e572af25a115759e5c6ff6b9689677` |
| PHASEC_UNET_seed_20261123_metadata.json | `b44884d42159416bf1573038414daeac97a9cf35fba5cd76ed9ce90c994186cb` |
| PHASEC_PREFLIGHT.json | `383e3a719b2b6e639320fb3fef0819aef882966241aa6a1bd296ec8a96162c77` |
| PHASEC_BLOCKED_RUNS.csv | `27d8f4159f2b2fc7947e6e4855b8759fef3372b81cc4126d55e9af85c597ae3f` |
| PHASEC_EXCLUDED_B2_TILES.csv | `d3698fa04f69f1ba9b4ff24e8b22a9938389bbc4e1573df19d357ed24ad9ce88` |
| PHASEC_robustness_direction_summary.csv | `ba51bb394322fa30dc84c9367e14771ae58b869cdef526511403e39d3e9cdb29` |
| PHASEC_robustness_summary_corrected.csv | `36607264483c9b54d7758452034241aee1c8b22f78b667b7089a79d132d24be1` |

No Phase B2 tile pixels, private key, or annotations were opened or used.
