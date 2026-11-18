# NRM Slide and Label Audit

**Audit time (local):** 2026-11-18 11:32:08 +05:30  
**Status:** STOPPED BEFORE MODEL RUN  
**Label:** EXPLORATORY, NOT CONFIRMATORY. LABELS FROM KPMP METADATA, NOT EXPERT-REVIEWED.

## Result and stop rule

The local trichrome inventory contains 34 whole-slide image files from 29 distinct participants. The inspected local reference-label audit reports **0/28** participants with a `reference_vs_ckd` value and **0/28** with a `diagnosis` value. Therefore, **0 participants have a locally documented normal/reference label** in the inspected records. This is fewer than the required 5 participants, so the normal-tissue check cannot proceed.

No diagnosis or normal/reference status was inferred from participant IDs, filenames, images, catalog access, or previous model outputs. No model was run, no tiles or masks were created, and no Phase B2 material was opened or changed.

## Slide inventory

The list below combines the 32-file local trichrome inventory in `PHASEB_slide_audit.csv` with two additional locally stored TRI whole-slide images found in participant `27-10207`'s WSI folder and listed in `data_manifest.csv`. All 34 paths existed at audit time. The 32 Phase B inventory rows have MPP values in that audit; MPP for the additional two is NOT AVAILABLE in the inspected local records. Stain is recorded as TRI because the filenames and inventory identify them as TRI. The metadata audit did not provide a tissue-category or diagnosis value for these slides.

| Participant ID | Slide ID | Slide file | Local slide path | Stain | MPP x × y | Tissue category / diagnosis metadata |
|---|---|---|---|---|---|---|
| 34-10730 | S-2209-009414 | `97fe61fb-b97a-44e3-b4a6-258990851278_S-2209-009414_TRI_1of2.svs` | `D:\patent\97fe61fb-b97a-44e3-b4a6-258990851278_S-2209-009414_TRI_1of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 27-10157 | S-2105-008148 | `90242f36-6827-4a88-a900-bd61ce830d70_S-2105-008148_TRI_1of2.svs` | `D:\patent\data\27-10157\wsi\90242f36-6827-4a88-a900-bd61ce830d70_S-2105-008148_TRI_1of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 27-10207 | S-2305-006555 | `S-2305-006555_TRI_1of2.svs` | `D:\patent\data\27-10207\wsi\S-2305-006555_TRI_1of2.svs` | TRI | NOT AVAILABLE | NOT AVAILABLE |
| 27-10207 | S-2305-006554 | `S-2305-006554_TRI_2of2.svs` | `D:\patent\data\27-10207\wsi\S-2305-006554_TRI_2of2.svs` | TRI | NOT AVAILABLE | NOT AVAILABLE |
| 31-10078 | S-2001-005361 | `abd5770d-321f-4c53-bb8f-292c77eecb6c_S-2001-005361_TRI_1of2.svs` | `D:\patent\data\31-10078\wsi\abd5770d-321f-4c53-bb8f-292c77eecb6c_S-2001-005361_TRI_1of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 33-10005 | S-1908-009834 | `c75c3d98-199c-45de-8fe3-227c11b926b9_S-1908-009834_TRI_2of2.svs` | `D:\patent\data\33-10005\wsi\c75c3d98-199c-45de-8fe3-227c11b926b9_S-1908-009834_TRI_2of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 30-11084 | S-2006-001759 | `19c86560-b1ec-42f3-b42e-57104ab8a02e_S-2006-001759_TRI_1of2.svs` | `D:\patent\data\30-11084\wsi\19c86560-b1ec-42f3-b42e-57104ab8a02e_S-2006-001759_TRI_1of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 936-10217 | S-2310-016569 | `f8fba4af-23b9-46a2-8dc7-b77ed858dd9d_S-2310-016569_TRI_1of2.svs` | `D:\patent\data\936-10217\wsi\f8fba4af-23b9-46a2-8dc7-b77ed858dd9d_S-2310-016569_TRI_1of2.svs` | TRI | 0.262968 × 0.262968 | NOT AVAILABLE |
| 27-10206 | S-2305-006649 | `5f69b6ac-9636-4a43-9783-b75ef56531c3_S-2305-006649_TRI_1of2.svs` | `D:\patent\data\27-10206\wsi\5f69b6ac-9636-4a43-9783-b75ef56531c3_S-2305-006649_TRI_1of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 29-10422 | S-2107-015180 | `47d67899-8e0d-426e-9235-09816e2ea23b_S-2107-015180_TRI_2of2.svs` | `D:\patent\data\29-10422\wsi\47d67899-8e0d-426e-9235-09816e2ea23b_S-2107-015180_TRI_2of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 934-10003 | S-2301-008575 | `6111fe1d-1810-4f7c-a99a-fcc46b4cc3a9_S-2301-008575_TRI_1of2.svs` | `D:\patent\data\934-10003\wsi\6111fe1d-1810-4f7c-a99a-fcc46b4cc3a9_S-2301-008575_TRI_1of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 30-11197 | S-2312-004255 | `28655ea1-2b13-4d92-a81c-01fe5ab0d02c_S-2312-004255_TRI_1of2.svs` | `D:\patent\data\30-11197\wsi\28655ea1-2b13-4d92-a81c-01fe5ab0d02c_S-2312-004255_TRI_1of2.svs` | TRI | 0.262761 × 0.262761 | NOT AVAILABLE |
| 30-10125 | S-2002-007746 | `74f87672-fd20-4365-83af-11b8bfd97e09_S-2002-007746_TRI_2of2.svs` | `D:\patent\data\30-10125\wsi\74f87672-fd20-4365-83af-11b8bfd97e09_S-2002-007746_TRI_2of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 30-11197 | S-2312-004254 | `e36089fa-b099-42fa-a244-7e233ed67215_S-2312-004254_TRI_2of2.svs` | `D:\patent\data\30-11197\wsi\e36089fa-b099-42fa-a244-7e233ed67215_S-2312-004254_TRI_2of2.svs` | TRI | 0.262761 × 0.262761 | NOT AVAILABLE |
| 29-10400 | S-2002-007558 | `94bb7fdb-650c-4003-8dd2-f3985c2f2a63_S-2002-007558_TRI_2of2.svs` | `D:\patent\data\29-10400\wsi\94bb7fdb-650c-4003-8dd2-f3985c2f2a63_S-2002-007558_TRI_2of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 29-10400 | S-2002-007559 | `e73b0691-0a9e-4858-b910-1c450d7b9956_S-2002-007559_TRI_1of2.svs` | `D:\patent\data\29-10400\wsi\e73b0691-0a9e-4858-b910-1c450d7b9956_S-2002-007559_TRI_1of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 29-10439 | S-2206-007954 | `3b191a40-b129-4668-9b3d-157a5d7dd005_S-2206-007954_TRI_2of2.svs` | `D:\patent\data\29-10439\wsi\3b191a40-b129-4668-9b3d-157a5d7dd005_S-2206-007954_TRI_2of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 29-10394 | S-2102-006650 | `8133f419-4d62-464a-afb5-5eb29734e1a7_S-2102-006650_TRI_2of2.svs` | `D:\patent\data\29-10394\wsi\8133f419-4d62-464a-afb5-5eb29734e1a7_S-2102-006650_TRI_2of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 30-11192 | S-2405-000802 | `8f443d76-6a7a-416d-b569-f4c4ab965245_S-2405-000802_TRI_1of2.svs` | `D:\patent\data\30-11192\wsi\8f443d76-6a7a-416d-b569-f4c4ab965245_S-2405-000802_TRI_1of2.svs` | TRI | 0.262761 × 0.262761 | NOT AVAILABLE |
| 28-12265 | S-2102-006556 | `0a3cacc3-0527-43c3-bb57-e8b42024c599_S-2102-006556_TRI_1of2.svs` | `D:\patent\data\28-12265\wsi\0a3cacc3-0527-43c3-bb57-e8b42024c599_S-2102-006556_TRI_1of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 28-12626 | S-2307-011591 | `bcea82a1-a58a-4503-b51f-7e68ca4879db_S-2307-011591_TRI_1of2B.svs` | `D:\patent\data\28-12626\wsi\bcea82a1-a58a-4503-b51f-7e68ca4879db_S-2307-011591_TRI_1of2B.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 30-11141 | S-2307-002343 | `36171840-db11-4ce4-8d8d-d861c542b550_S-2307-002343_TRI_1of2.svs` | `D:\patent\data\30-11141\wsi\36171840-db11-4ce4-8d8d-d861c542b550_S-2307-002343_TRI_1of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 31-10013 | S-1910-000140 | `760e7379-a792-4438-bf24-bd9008737778_S-1910-000140_TRI_2of2.svs` | `D:\patent\data\31-10013\wsi\760e7379-a792-4438-bf24-bd9008737778_S-1910-000140_TRI_2of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 27-10228 | S-2306-012928 | `d369cf7f-0bd6-4f4b-9ba0-e79b80f6d27f_S-2306-012928_TRI_2of2.svs` | `D:\patent\data\27-10228\wsi\d369cf7f-0bd6-4f4b-9ba0-e79b80f6d27f_S-2306-012928_TRI_2of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 934-10007 | S-2303-008740 | `2781db46-1a7a-4c03-851a-3b5588ba6a79_S-2303-008740_TRI_2of2.svs` | `D:\patent\data\934-10007\wsi\2781db46-1a7a-4c03-851a-3b5588ba6a79_S-2303-008740_TRI_2of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 30-11141 | S-2307-002342 | `b3351edc-00f7-45d4-ab54-e1f3f1b693e4_S-2307-002342_TRI_2of2.svs` | `D:\patent\data\30-11141\wsi\b3351edc-00f7-45d4-ab54-e1f3f1b693e4_S-2307-002342_TRI_2of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 32-10205 | S-2006-001852 | `09d79760-32e4-4cd6-8915-040e007f103a_S-2006-001852_TRI_2of2.svs` | `D:\patent\data\32-10205\wsi\09d79760-32e4-4cd6-8915-040e007f103a_S-2006-001852_TRI_2of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 30-11192 | S-2405-000801 | `287d6060-10e4-4065-ad00-67d77b607b55_S-2405-000801_TRI_2of2.svs` | `D:\patent\data\30-11192\wsi\287d6060-10e4-4065-ad00-67d77b607b55_S-2405-000801_TRI_2of2.svs` | TRI | 0.262761 × 0.262761 | NOT AVAILABLE |
| 34-11066 | S-2309-028495 | `3915d4a1-fa62-4c27-9fdf-d98ba83e18fa_S-2309-028495_TRI_2of2.svs` | `D:\patent\data\34-11066\wsi\3915d4a1-fa62-4c27-9fdf-d98ba83e18fa_S-2309-028495_TRI_2of2.svs` | TRI | 0.262438 × 0.262438 | NOT AVAILABLE |
| 27-10371 | S-2311-013369 | `e5b859cd-4e8e-48c6-87fd-92482a605c65_S-2311-013369_TRI_1of2.svs` | `D:\patent\data\27-10371\wsi\e5b859cd-4e8e-48c6-87fd-92482a605c65_S-2311-013369_TRI_1of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 28-12557 | S-2109-007005 | `e8246ba9-6f85-4729-ad3e-d315d4c5c05b_S-2109-007005_TRI_1of2.svs` | `D:\patent\data\28-12557\wsi\e8246ba9-6f85-4729-ad3e-d315d4c5c05b_S-2109-007005_TRI_1of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 27-10262 | S-2212-003370 | `39d186f8-82e5-4256-a9a7-12378237e1ec_S-2212-003370_TRI_1of2.svs` | `D:\patent\data\27-10262\wsi\39d186f8-82e5-4256-a9a7-12378237e1ec_S-2212-003370_TRI_1of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 27-10201 | S-2305-006601 | `31194b20-508e-4f88-abb2-8432fc8ad870_S-2305-006601_TRI_2of2.svs` | `D:\patent\data\27-10201\wsi\31194b20-508e-4f88-abb2-8432fc8ad870_S-2305-006601_TRI_2of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |
| 31-10340 | S-2108-000599 | `314fd18b-0e4e-40fe-81ee-c547502ef632_S-2108-000599_TRI_2of2.svs` | `D:\patent\data\31-10340\wsi\314fd18b-0e4e-40fe-81ee-c547502ef632_S-2108-000599_TRI_2of2.svs` | TRI | 0.2527 × 0.2527 | NOT AVAILABLE |

## Metadata labels and comparison cohort

The exact field names in the existing local reference-label audit are `reference_vs_ckd`, `diagnosis`, `ifta_score`, `interstitial_fibrosis_score`, `tubular_atrophy`, `egfr`, `age`, and `sex`. For its 28 participants, the value counts were: `reference_vs_ckd` 0/28; `diagnosis` 0/28; `ifta_score` 0/28; `interstitial_fibrosis_score` 0/28; `tubular_atrophy` 0/28; `egfr` 0/28; `age` 0/28; and `sex` 0/28. That participant audit covers 27 of the 28 participants in the Phase B slide inventory and includes participant `27-10207`, who has the two additional TRI slides. Participant `34-10730` is not present in that reference-label audit; no separate local label metadata for that participant was found in the inspected files. The locally available metadata for `27-10207` contains technical sequencing fields but no tissue category or diagnosis. The tissue context behind any possible reference label (donor, tumour-adjacent, or other) is therefore NOT AVAILABLE.

The local slide inventory also records `catalog_access=open` and `reuse_terms_in_catalog=not stated`; these fields describe catalog access/terms, not patient tissue category or diagnosis, and do not establish reuse permission.

**Disease comparison slides:** NOT AVAILABLE as an identified group. The metadata examined contains no diagnosis values, so none of the 32 slides can be assigned to a disease cohort from these records without guessing.

## Sources and limits

- `D:\patent\stage2A_audit\PHASEB_slide_audit.csv`: 32 TRI slide rows; all 32 local paths existed at audit time; MPP was available for all 32.
- `D:\patent\data_manifest.csv` and the participant `27-10207` WSI folder: two additional locally stored TRI slides; their MPP values were NOT AVAILABLE in the inspected records.
- `D:\patent\qc_collagen\review\reference_label_availability_summary.csv`: 0/28 values for the audited reference/diagnosis and pathology fields listed above.
- `D:\patent\qc_collagen\review\metadata_label_field_audit.csv`: audited candidate label fields in local participant metadata; no populated label fields were reported.
- `D:\patent\stage0_audit\kpmp_clinical_candidates.csv`: header only; no local clinical candidate rows.
- `D:\patent\stage2A_audit\PHASEA_PERMISSION_RECORD.md`: no exact permission wording; permissions remain UNRESOLVED.

The slide list is the local inventory used in the existing Phase B audit, not a new scan of Phase B2 materials. Metadata coverage is limited to the inspected local audit files. No internet access or downloads were used.
