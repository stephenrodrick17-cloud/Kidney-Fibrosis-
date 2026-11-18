# Plan A / Plan B cohort analysis

The cohort runner processes the 28 participants in
`D:\patent\tier_a_download_checklist.csv` using files already downloaded to
`D:\patent\data` (17 Tier A, 8 Tier B, and 3 Tier C). It pairs each spatial
position file with one expression matrix by complete in-tissue barcode
coverage. If multiple non-equivalent matrices match the same spatial barcodes,
or coverage is incomplete, that sample is reported as ambiguous/unmatched and
excluded rather than guessed.

## Rerun

From PowerShell:

```powershell
python D:\patent\analyze_cohort_plan_a_b.py
```

The script uses a fixed random seed and writes dependency versions and key
settings to `analysis_config.json`. Spot centers use full-resolution coordinates
multiplied by `tissue_hires_scalef`; 224 x 224 tiles come only from the Visium
hires image. Each tile has a paired row in the manifest and spot-expression
table. Sample-level barcodes must match before expression statistics or tiles
are generated.

## Measurements

- Patient expression: per-patient mean raw counts per paired in-tissue spot and
  mean counts per 10,000 total spot counts (CP10K), with detected spot counts
  and detection prevalence for COL1A1, COL3A1, FN1, TGFB1, and ACTA2.
- "Enough spots" is an exploratory screen: detection in at least 10% of paired
  in-tissue spots. It is not a prediction-readiness criterion.
- Fibrosis percentage is blank unless an explicit fibrosis/collagen measure and
  defensible tissue denominator are available. Generic renal-structure
  pathomics or an interstitium annotation alone is not treated as a fibrosis
  percentage. Segmentation archive discovery includes versioned `_v2` ZIP names.
- Plan B uses only Visium hires images, their own spot coordinates/scalefactors,
  and barcoded expression. No slide registration, training, or prediction is
  performed.

## Outputs

- `plan_a_patient_summary.csv`: one row per Tier A/B participant, including
  paired sample/spot counts and missing-data reasons.
- `plan_a_segmentation_audit.csv`: per-package OME channel names, fibrosis-
  related workbook headers, and the reason a fibrosis percentage is or is not
  supportable.
- `plan_b_gene_spot_check.csv`: gene prevalence and expression summaries by
  participant.
- `plan_b_spot_expression_long.csv`: raw counts and CP10K for each target gene
  and matched in-tissue spot.
- `plan_b_tile_manifest.csv`: one row per tile, with center, scale, and
  expression-source metadata.
- `tiles\<participant>\<sample>\`: all generated 224 x 224 spot-centered PNG
  tiles for successfully paired samples.
- `galleries\<participant>_tile_gallery.png`: deterministic sample gallery for
  each participant with paired spots.

`D:\patent\audit_table.csv` is refreshed with local file-presence fields and
Plan A/B pairing status. Failed or incomplete acquisition remains visible in
that table and in `D:\patent\data_manifest.csv`.
