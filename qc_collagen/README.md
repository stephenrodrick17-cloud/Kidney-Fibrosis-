# Spatial expression and trichrome proxy QC

This analysis uses only files already present under `D:\patent\data`. It does not register slides, train models, correct batches, or assign slide-derived collagen values to Visium spots.

## Re-run

```powershell
python D:\patent\qc_collagen\run_qc_collagen.py
```

The script imports the verified expression/spatial readers and barcode-coverage pairing helpers from `D:\patent\analyze_cohort_plan_a_b.py`.

## Methods

- Confirmed cohort: 28 participants, 29 paired spatial-expression samples, 25,104 in-tissue spots.
- Per-spot expression is `log1p(counts / all-gene spot UMI * 10,000)`; raw target-gene counts are retained. Missing matrix features remain blank and are listed in `gene_feature_match_audit.csv`.
- Mitochondrial fraction is calculated from mitochondrial UMIs in the expression matrix; read-level mitochondrial percentages are unavailable from these matrices.
- Low-quality screen cutoffs are pooled empirical 10th-percentile thresholds: UMI < 1194 or detected features < 799. Both distributions are plotted; the flags are screening annotations only and no spot is removed.
- Module score is a simple arithmetic mean of member-gene log1p(CP10K), with no control-gene matching. Module spot detection means at least one member gene has a positive raw count; module output is blank if a required member feature is missing from any paired sample matrix.
- Pseudobulk sums raw counts across every paired in-tissue spot for a participant, then computes `log1p(CPM)`. PCA uses common features with nonzero between-participant variance (up to 2,000 highest-variance features). Batch associations are participant-level diagnostics only; no correction is performed.
- TRI analysis uses OpenSlide level nearest 3 µm/pixel. All local slides are read at a pyramid level, not full resolution. The tissue mask uses per-slide Otsu thresholding of HSV saturation, then removes objects smaller than 0.005 mm² and fills holes smaller than 0.0025 mm².
- Collagen proxy uses the same white-reference balance and HSV rule on every slide: OpenCV hue 75–140, saturation >= 35, inside the tissue mask. This fixed blue/green window is an exploratory color proxy, not a validated collagen stain deconvolution. Slide-specific color and illumination statistics are saved to expose between-slide staining/scanner variation.
- Participant proxy is tissue-area weighted across the participant's local TRI slides. Grid heterogeneity uses 256 µm blocks with at least 100 tissue pixels. Tissue includes glomeruli, vessels, capsule, and medulla; it is not interstitial fibrosis.
- The quality composites are for manual review. Pen marks, folds, and blur are not reliably auto-classified; review is marked as required. A relative Laplacian sharpness metric and data-derived low-sharpness flag are supplied.
- Participant-level Spearman correlations use asymptotic p-values, 5,000 participant bootstrap replicates for 95% CIs, and BH correction across the 13 gene tests only. Module correlations are not multiplicity-corrected. With at most 28 participants, power is low.
- Local pathologist-score search checks files under `D:\patent\data` only. No external search, download, or access request was made.

## Reproducibility

- Seeds: PCA/diagnostics=20261111; bootstrap=20261112; three-slide recomputation=20261210; bootstrap replicates=5000.
- The run checks final participant/sample/spot counts against `plan_a_plan_b\plan_a_patient_summary.csv`.

Software versions:
- python: 3.13.1
- numpy: 2.2.6
- pandas: 3.0.6
- scipy: 1.18.1
- opencv: 4.10.0
- openslide_python: 1.4.7
- openslide_library: 4.0.1
- scikit_learn: 1.6.1
- scikit_image: 0.25.2
- matplotlib: 3.10.8
- pillow: 11.1.0
- tifffile: 2025.10.16

## Outputs

- `analysis_config.json`
- `run_qc_collagen.py`
- `requirements-qc.txt`
- `spot_qc_table.csv`
- `sample_qc_summary.csv`
- `gene_expression_by_spot.csv`
- `gene_detection_by_participant.csv`
- `gene_detection_cohort_summary.csv`
- `gene_feature_match_audit.csv`
- `module_scores_by_spot.csv`
- `module_detection_by_participant.csv`
- `module_detection_cohort_summary.csv`
- `pseudobulk_log_cpm.csv`
- `pca_participant_scores.csv`
- `pca_metadata_associations.csv`
- `sample_metadata_audit.csv`
- `local_metadata_fields_read.csv`
- `trichrome_slide_proxy_summary.csv`
- `participant_trichrome_collagen_proxy.csv`
- `participant_collagen_expression_correlations.csv`
- `segmentation_compartment_availability.csv`
- `pathologist_score_metadata_audit.csv`
- `slide_processing_errors.csv`
- `three_slide_recompute_verification.csv`
- `qc_verdict.md`
- `plots\spot_qc_distributions.png`
- `plots\gene_detection_prevalence.png`
- `plots\pca_by_tier.png`
- `plots\pca_by_fibrosis_status.png`
- `plots\pca_by_visium_library_ids.png`
- `plots\pca_by_sequencer_model.png`
- `plots\pca_by_sequencing_platform.png`
- `plots\pca_by_repository_platform.png`
- `slides\<participant_id>\<slide_id>_qc.png`: one composite per TRI slide (analysis-level thumbnail, tissue mask, collagen proxy overlay).
- `plots\correlations\<feature>.png`: participant-labeled scatter plot for each gene/module correlation.

See `qc_verdict.md` for the data-derived usability screen, slide flags, correlation table, and explicit limitations.
