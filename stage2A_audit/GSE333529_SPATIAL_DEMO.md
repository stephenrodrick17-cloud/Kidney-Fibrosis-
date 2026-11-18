# GSE333529 Spatial Expression Demonstration

**Purpose:** Check whether public spatial gene-expression measurements can be
mapped to their supplied kidney tissue images. This is a separate technical
demonstration; it does not change or validate the RENFAST fibrosis model.

## Dataset and processing

- GEO accession: [GSE333529](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE333529)
- The study reports spatial transcriptomics from human lupus-nephritis kidneys.
  Its data availability statement identifies GSE333529 as the Visium deposit.
- Downloaded archive: `external_datasets/GSE333529/GSE333529_RAW.tar`
- Archive size: 80,558,080 bytes
- SHA-256: `41cd3def3408b043fe0918708ce9df5850bc3115d1578bb88c21c4e67b3bacb6`
- Each sample has an image, a sparse gene-count matrix, barcodes, tissue
  positions, and image scale factors.

The processing code checks that the matrix dimensions match the gene and
barcode tables, that each matrix barcode has one in-tissue coordinate, and
that scaled spot coordinates fall inside the supplied high-resolution image.
Gene counts are normalized per spot to 10,000 total counts and transformed with
`log1p`. The plotted genes are `COL1A1`, `COL3A1`, and `FN1`.

| Sample | Features | In-tissue spots | Image size (pixels) |
|---|---:|---:|---:|
| P1 | 18,085 | 769 | 1,589 x 2,000 |
| P2 | 18,085 | 955 | 2,000 x 1,894 |
| P3 | 18,085 | 900 | 1,725 x 2,000 |
| P4 | 18,085 | 830 | 2,000 x 1,791 |
| **Total** | | **3,454** | |

Percent of in-tissue spots with a detected transcript:

| Sample | COL1A1 | COL3A1 | FN1 |
|---|---:|---:|---:|
| P1 | 79.1% | 93.4% | 68.4% |
| P2 | 69.5% | 83.6% | 62.3% |
| P3 | 79.0% | 88.7% | 60.1% |
| P4 | 62.0% | 89.2% | 66.4% |

These are gene-detection summaries, not model accuracy scores.

## Outputs

- Overlay figure: [spatial_expression_overlays.png](./external_datasets/GSE333529/processed/spatial_expression_overlays.png)
- Per-spot expression and coordinates: [spatial_expression_spots.csv](./external_datasets/GSE333529/processed/spatial_expression_spots.csv)
- Detection summary: [gene_detection_summary.csv](./external_datasets/GSE333529/processed/gene_detection_summary.csv)
- Alignment and archive record: [processing_summary.json](./external_datasets/GSE333529/processed/processing_summary.json)
- Reproducible script: [process_gse333529_spatial.py](./process_gse333529_spatial.py)
- Extracted tissue PNGs for manual review in [viewer_images/](./external_datasets/GSE333529/processed/viewer_images/)

Run from PowerShell:

```powershell
& 'C:\Users\asus\python.exe' 'D:\patent\stage2A_audit\process_gse333529_spatial.py'
```

Slidescape documents support for simple PNG images and annotations. Open one of
the extracted PNGs there for visual review. The GEO files are ordinary
approximately 2,000-pixel tissue images, not whole-slide images; ASAP is
primarily a whole-slide viewer and may not be the right viewer for these
particular files. Neither application trains the model. A renal pathologist
must create and review fibrosis or structure annotations before those images
can become supervised training examples. Slidescape's repository lists GPL-3.0
licensing, which should be reviewed before bundling or redistributing it with a
patented product.

## What this establishes and what it does not

This demonstrates a basic image-to-spatial-expression overlay using the
coordinates supplied with the same GEO samples. It does **not** link RENFAST
images to molecular data, train a model, provide fibrosis-mask ground truth,
grade fibrosis, identify kidney structures, or read patient reports.
`COL1A1`, `COL3A1`, and `FN1` are fibrosis-associated molecular signals; their
RNA counts are not direct collagen measurements, histologic fibrosis scores,
or a diagnosis.

Four samples are not enough for broad or independent validation. No accuracy,
clinical performance, or generalization claim is supported by this
demonstration.

The GEO files are publicly downloadable, but the GEO record and article do not
settle whether this particular dataset may be used for patent-related model
training, derived weights, or redistribution. The article says supporting data
are available from the corresponding author upon reasonable request and
identifies the GEO deposit. Confirm the applicable data and model-use terms
before patent-related use or external distribution. Do not redistribute the
source images or matrices.

## Source

Cortez et al. “A skin-kidney neutrophil axis links ultraviolet exposure to
renal angiogenesis and tissue remodeling in healthy and lupus kidneys.”
*The Journal of Immunology* (2026), DOI
[10.1093/jimmun/vkag178](https://doi.org/10.1093/jimmun/vkag178).
Visium data are deposited as [GSE333529](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE333529).
