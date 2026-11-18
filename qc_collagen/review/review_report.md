# Proxy and independent-reference review

## Scope and safeguards

- New files are confined to `D:\patent\qc_collagen\review\`; earlier QC outputs and raw data were read-only.
- No registration, model training, batch correction, or mask-based measurement was performed.
- Slide-level summaries use n=33 slides; participant-level summaries and tests use participants as the unit.
- The source used for the proxy is `qc_collagen\trichrome_slide_proxy_summary.csv`; participant proxy is `qc_collagen\participant_trichrome_collagen_proxy.csv`.

## Part A: proxy and stain/tissue

- Slides ranked: 33. Contact sheets show the ten lowest and ten highest existing QC composites.
- Spearman correlations are in `slide_color_proxy_correlations.csv`, each with n=33 slides. A descriptive absolute-rho threshold of 0.70 flags strong association; flagged statistics: tissue_median_hue. P-values are nominal and not multiplicity-adjusted.
- Color statistics were recomputed from each existing TRI WSI at the same recorded OpenSlide level used by the original proxy; median hue, saturation, and value were computed inside the tissue mask and inside baseline collagen candidates.
- Threshold sensitivity: baseline is H=75-140, S>=35; permissive is H=65-145, S>=20; strict is H=85-135, S>=60. Percentile normalization maps the per-slide tissue RGB 2nd-98th percentile to 0-255, then applies the baseline HSV window.
- Participant-level rank agreement between proxy variants is in `participant_proxy_rank_agreement.csv`; slide-level variants are in `slide_color_proxy_statistics.csv`.
- Three randomly selected slides were reopened and recomputed from source WSI pixels (seed=20261112); results: S-2107-015180: diff=0; S-2006-001852: diff=0; S-2301-008575: diff=0.
- This checks sensitivity to the stain-color rule, not biological validity of collagen segmentation. No expression outcome was used to choose thresholds.

## Part B: independent reference labels

- Catalog candidates are listed in `reference_candidate_inventory.csv` with access level from `atlas_repository_filelist-20261105.csv`. It includes 225 cohort-specific metadata/pathology/segmentation candidate records.
- Catalog candidate access levels: {'open': 225}. There are 61 Experimental Metadata workbooks; these assay-specific sheets were screened, not assumed to be clinical labels.
- Open experimental-metadata downloads completed: 60; failed: 0. Only catalog rows marked open were eligible; downloaded files and SHA-256 values are in `metadata_download_manifest.csv`.
- Inspected 61 local/catalog-listed experimental-metadata workbooks across 26 participants; participants with any requested clinical/pathology label value: 0 of 28.
- No catalog-listed experimental metadata workbook was available locally or in the open candidate set for: 27-10371, 34-11066.
- Labels unavailable for every participant: reference_vs_ckd, diagnosis, ifta_score, interstitial_fibrosis_score, tubular_atrophy, egfr, age, sex.
- Tier values recorded from `tier_a_download_checklist.csv`: {'A': 17, 'C': 3, 'B': 8}. The definition of Tier A/B/C was not found in the inspected source files; tier was not treated as an outcome or clinical group.
- `reference_group_tests.csv` has 24 label/outcome rows. No inferential test is run where fewer than 10 participants have a labeled value; available n is shown per row.
- Local metadata search covered participant metadata files and all catalog-listed cohort Experimental Metadata workbooks marked open; catalog metadata was not treated as a clinical value unless the workbook explicitly labeled it. No restricted file was requested or downloaded.
- Segmentation feature workbook header audit: 70 sheets reviewed; see `segmentation_feature_header_audit.csv`. Feature values were not extracted.

## Part C: segmentation package availability

- Local segmentation packages: 12 across 11 participants; 6 packages contain a channel named IFTA.
- Alignment check against participant TRI WSI: {'archive slide ID differs from participant TRI slide IDs; no exact full-resolution dimension match': 12}. Archive and TRI slide IDs, channel names, and exact full-resolution pixel dimensions are listed in `segmentation_package_audit.csv`; per-image plane dimensions are in `segmentation_image_dimensions.csv`.
- All segmentation OME files are listed as PAS slides; channel availability or equal pixel dimensions alone would not prove section identity or registration. No masks were applied to the proxy.

## Explicit gaps / not verified

- No independently labeled reference/CKD, diagnosis, IFTA/interstitial fibrosis, tubular atrophy, eGFR, age, or sex values were found in the inspected metadata files.
- Tier A/B/C semantics were not defined by the inspected local files.
- The proxy's blue/green HSV range is an exploratory stain-color threshold, not a validated collagen stain deconvolution or interstitial fibrosis measurement.
- Manual visual review checklist remains blank; pen marks, folds, blur, focus and large empty regions were not manually adjudicated.
- Segmentation-to-TRI alignment is only checked by archive slide ID and exact pixel dimensions; no image registration or mask application was performed.
- Any catalog metadata not specifically downloaded is listed with its access level and was not assumed to contain labels.

## Output inventory

- `manual_slide_review_checklist.csv`
- `metadata_download_manifest.csv`
- `metadata_download_status.csv`
- `metadata_label_field_audit.csv`
- `participant_proxy_rank_agreement.csv`
- `participant_proxy_variants.csv`
- `participant_reference_labels.csv`
- `proxy_vs_slide_color_stats.png`
- `reference_candidate_inventory.csv`
- `reference_group_tests.csv`
- `reference_label_availability_summary.csv`
- `review_qc_collagen.py`
- `segmentation_feature_header_audit.csv`
- `segmentation_image_dimensions.csv`
- `segmentation_package_audit.csv`
- `slide_color_proxy_correlations.csv`
- `slide_color_proxy_statistics.csv`
- `slide_proxy_rankings.csv`
- `three_slide_recompute_verification.csv`
- `contact_sheets/lowest_10_proxy.png` and `contact_sheets/highest_10_proxy.png`
- `metadata_downloads/<participant>/<file>` for newly downloaded open metadata

Software: OpenSlide Python 1.4.7, OpenSlide library 4.0.1, OpenCV 4.10.0, NumPy 2.2.6, SciPy 1.18.1, Pandas 3.0.6, tifffile 2025.10.16, openpyxl 3.1.5. Random seed: 20261112; bootstrap replicates: 5000.

## Participant label availability

| Label | Participants with value | Blank |
|---|---:|---:|
| reference_vs_ckd | 0 | 28 |
| diagnosis | 0 | 28 |
| ifta_score | 0 | 28 |
| interstitial_fibrosis_score | 0 | 28 |
| tubular_atrophy | 0 | 28 |
| egfr | 0 | 28 |
| age | 0 | 28 |
| sex | 0 | 28 |

## Slide color-statistic correlations

| Statistic | n slides | Spearman rho | p |
|---|---:|---:|---:|
| tissue_median_hue | 33 | -0.837 | 1.242e-09 |
| tissue_median_saturation | 33 | -0.098 | 0.5879 |
| tissue_median_value | 33 | -0.048 | 0.7887 |
| collagen_candidate_median_hue | 33 | -0.318 | 0.0716 |
| collagen_candidate_median_saturation | 33 | 0.384 | 0.0274 |
| collagen_candidate_median_value | 33 | -0.083 | 0.6476 |

## Participant proxy rank agreement

| Comparison | n participants | Spearman rho | p |
|---|---:|---:|---:|
| original participant proxy vs permissive_proxy | 28 | 0.903 | 5.195e-11 |
| original participant proxy vs strict_proxy | 28 | 0.834 | 3.635e-08 |
| original participant proxy vs percentile_normalized_proxy | 28 | 0.882 | 5.376e-10 |
| permissive_proxy vs strict_proxy | 28 | 0.620 | 0.0004314 |
| permissive_proxy vs percentile_normalized_proxy | 28 | 0.902 | 5.57e-11 |
| strict_proxy vs percentile_normalized_proxy | 28 | 0.675 | 8.175e-05 |

## Recompute checks

| Participant | Slide | Status | Absolute difference |
|---|---|---|---:|
| 29-10422 | S-2107-015180 | PASS | 0 |
| 32-10205 | S-2006-001852 | PASS | 0 |
| 934-10003 | S-2301-008575 | PASS | 0 |
