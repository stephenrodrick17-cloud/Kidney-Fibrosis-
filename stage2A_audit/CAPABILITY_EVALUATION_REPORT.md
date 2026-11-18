# Capability-wise Evaluation

**Evaluation date:** 2026-11-16  
**Purpose:** Report measured results for each requested capability using only
the data and labels currently available in the workspace. This is a research
evaluation, not a medical-device authorization or a patentability opinion.

## Results

| Capability | Result | Interpretation |
|---|---|---|
| Binary fibrosis mask | **Measured on RENFAST's 50-image test split** | Dice 0.9153 (95% filename-family bootstrap CI 0.8830–0.9351); IoU 0.8484 (0.7976–0.8798); sensitivity 0.9139 (0.8423–0.9568); specificity 0.9462 (0.9239–0.9737). Boundary ASSD 0.613 pixels (0.461–0.758); HD95 2.764 pixels (1.970–3.416). |
| Fibrosis grade | **Not measured** | The current model outputs a binary mask, not a grade. The local score audit found no fibrosis-grade values for 28 participants, so weighted kappa, ICC, and grade error cannot be calculated. |
| Kidney structures | **Not measured** | No structure model has been evaluated against an independent expert reference. Twelve local segmentation packages contain structure labels, but their documentation describes network-generated segmentations quality-checked by a pathologist; they are not independent hand-drawn ground truth. |
| Pathology-report reading | **Not measured** | No de-identified kidney biopsy report set with expert-verified target fields was found. Precision, recall, and extraction error cannot be calculated. |
| Image-to-molecular mapping | **Technical coordinate check only** | GSE333529 has four samples and 3,454 in-tissue spots. All matrix barcodes matched in-tissue position rows, and all scaled spot coordinates fell within their supplied images. This checks file/coordinate consistency; it is not an independent registration-error measurement or validation of a fibrosis prediction. |
| Sample-level image/molecular analysis | **Exploratory only** | Across 28 participants, correlations between a tissue-wide trichrome color proxy and pseudobulk RNA were small and uncertain: COL1A1 rho -0.135 (95% CI -0.527 to 0.254; p=0.493), COL3A1 rho -0.165 (-0.536 to 0.250; p=0.402), FN1 rho -0.082 (-0.459 to 0.328; p=0.680), and ECM-collagen module rho -0.170 (-0.546 to 0.243; p=0.388). These are not fibrosis-grade associations; the image proxy includes multiple tissue compartments. |

## Fibrosis-mask test details

The frozen RENFAST checkpoint and threshold `0.5` were used without retraining
or tuning. The boundary-metric run reproduced the saved per-image Dice, IoU,
sensitivity, and specificity for all 50 test images. Boundary contours were
defined as each binary mask minus its 3x3 erosion; Euclidean distances were
pooled in both directions. ASSD is their mean and HD95 their 95th percentile.
Distances are in pixels because the patches have no verified physical pixel
spacing.

The 95% intervals resample the 10 filename-family groups (10,000 resamples,
seed `20261117`). Those identifiers are not verified patient or biopsy IDs.
This remains a within-RENFAST mask-agreement benchmark, not external-site or
patient-level validation, diagnostic accuracy, or evidence of clinical
performance.

Reproducible outputs:

- Boundary calculation: [evaluate_renfast_boundary_metrics.py](./evaluate_renfast_boundary_metrics.py)
- Summary and per-image boundary results: [boundary_metrics.json](./renfast_baseline_run/boundary_metrics.json), [boundary_metrics_per_image.csv](./renfast_baseline_run/boundary_metrics_per_image.csv)
- Original held-out metrics and limitations: [RENFAST_VALIDATION_REPORT.md](./RENFAST_VALIDATION_REPORT.md), [test_metrics.json](./renfast_baseline_run/test_metrics.json)

## Why the other capabilities are not scored

- **Fibrosis grade:** [reference_label_availability_summary.csv](../qc_collagen/review/reference_label_availability_summary.csv) reports no local values for IFTA or interstitial-fibrosis scores.
- **Structures:** [segmentation_compartment_availability.csv](../qc_collagen/segmentation_compartment_availability.csv) inventories the local label packages. Because they are model outputs with pathologist QC and there is no evaluated multi-class model plus independent reference, class-wise Dice, object precision/recall, and sensitivity are unavailable.
- **Reports:** the workspace contains no paired, de-identified renal pathology reports with expert-checked extraction labels.
- **Molecular registration:** the GSE333529 coordinate check is documented in [GSE333529_SPATIAL_DEMO.md](./GSE333529_SPATIAL_DEMO.md). A separate KPMP cross-section registration attempt is explicitly provisional; its final mask overlap is 0.386 and it has no independent landmark-error reference ([registration record](../data/27-10207/qc/registration_quality_final.json)). This is not sufficient for quantitative image-to-molecular validation.
- **Sample-level correlations:** the exploratory values above are in [participant_collagen_expression_correlations.csv](../qc_collagen/participant_collagen_expression_correlations.csv); the [QC verdict](../qc_collagen/qc_verdict.md) explains why the color proxy is not an interstitial-fibrosis measure.

## Overall conclusion

Only binary fibrosis-mask overlap and pixel-space boundary distances were
measured. Grade prediction, independent structure segmentation, report
extraction, and validated image-to-molecular prediction remain untested. No
result in this report establishes patent novelty, medical-device readiness,
or safety for patient-care decisions.
