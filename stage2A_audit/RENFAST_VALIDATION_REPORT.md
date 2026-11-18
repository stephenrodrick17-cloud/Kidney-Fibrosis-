# RENFAST Fibrosis Segmentation Baseline: Validation Report

**Run date:** 2026-11-16  
**Purpose:** Research-only pixel segmentation of RENFAST Masson's trichrome
patches against the archive's manual fibrosis masks.

## Result

The scratch-trained U-Net completed 90 epochs. The best checkpoint was selected
at epoch 78 using the fixed 0.5 threshold and validation Dice. On the untouched
50-image RENFAST test partition, the per-image macro scores were:

| Metric | Mean | 95% filename-family bootstrap interval |
|---|---:|---:|
| Dice | 0.9153 | 0.8830–0.9351 |
| IoU | 0.8484 | 0.7976–0.8798 |
| Sensitivity | 0.9139 | 0.8423–0.9568 |
| Specificity | 0.9462 | 0.9239–0.9737 |

Intervals use 10,000 resamples of the 10 filename-family groups (seed
`20261117`). The validation Dice at the selected checkpoint was `0.9429`.
These values measure agreement with RENFAST's manual masks, not diagnostic
accuracy or agreement with an independently adjudicated pathology standard.

An additional frozen-checkpoint analysis reproduced the saved pixel metrics
and measured boundary distances on the same 50 images: ASSD `0.6127` pixels
(95% filename-family bootstrap CI `0.4612–0.7578`) and HD95 `2.7640` pixels
(`1.9696–3.4155`). Physical distances cannot be reported because patch pixel
spacing is unavailable. See the [capability evaluation report](./CAPABILITY_EVALUATION_REPORT.md)
and [per-image boundary results](./renfast_baseline_run/boundary_metrics_per_image.csv).

## Data integrity and split

- The archive contained 500 training image/mask entries, which reduced to 250
  unique byte-identical pairs after removing duplicate copies.
- The 50 official test pairs had no exact image or mask duplicates across the
  official train/test boundary.
- The filename token before the first underscore yielded 17 training groups and
  10 test groups. All 10 test group IDs also appeared in the original training
  partition.
- To prevent this filename-family overlap from entering model fitting, 127
  unique training pairs from those shared groups were excluded. The remaining
  123 pairs from 7 groups were split into 105 training pairs across 6 groups
  and 18 validation pairs from 1 group.
- The final test set remained 50 pairs from the 10 held-out filename groups.
  The archive does not establish that these IDs are patient IDs, so this is not
  patient-level validation.
- All 250 unique training masks were 512x512 binary masks with values 0 and
  255. Test image and mask bytes were hashed before training for integrity
  checks, but test pixels were not decoded until the checkpoint was frozen.

## Model and reproducibility

- Four-level U-Net trained from random initialization; no pretrained model or
  KPMP data was used.
- Input: RGB values scaled to `[0, 1]`; only horizontal/vertical flips and
  90-degree rotations for training.
- Loss: equally weighted binary cross-entropy and soft Dice loss.
- Optimizer: AdamW (`lr=0.001`, `weight_decay=0.0001`), batch size 1.
- Seed: `20261116`; early stopping patience: 12 epochs.
- Checkpoint SHA-256:
  `674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb`

Reproducibility and output files:

- Training and inference code: [run_renfast_baseline.py](./run_renfast_baseline.py)
- Dataset/split amendment: [PREREG_RENFAST_AMENDMENT.md](./PREREG_RENFAST_AMENDMENT.md)
- Pair/hash/split manifest: [renfast_pair_manifest.csv](./renfast_baseline_run/renfast_pair_manifest.csv)
- Audit summary: [audit_summary.json](./renfast_baseline_run/audit_summary.json)
- Training history and run record: [train_history.csv](./renfast_baseline_run/train_history.csv),
  [run_metadata.json](./renfast_baseline_run/run_metadata.json)
- Checkpoint: [checkpoint_best.pt](./renfast_baseline_run/checkpoint_best.pt)
- Overall and per-image test results: [test_metrics.json](./renfast_baseline_run/test_metrics.json),
  [test_metrics_per_image.csv](./renfast_baseline_run/test_metrics_per_image.csv)

To segment a single matching 512x512 patch, run in PowerShell:

```powershell
& 'C:\Users\asus\python.exe' 'D:\patent\stage2A_audit\run_renfast_baseline.py' `
  --mode predict --image 'D:\path\to\patch.png' `
  --prediction 'D:\path\to\predicted_mask.png'
```

This writes a binary mask and a JSON sidecar. It does not resize whole-slide
images; a whole-slide tiling and registration workflow is not implemented.

## Full-cohort scoring (requested after the initial held-out evaluation)

The frozen checkpoint and threshold were then applied to every unique image in
the archive. Duplicate copies were not counted again. This additional scoring
did not change the checkpoint, threshold, or any model settings; the official
test-set Dice, IoU, sensitivity, and specificity exactly matched the initial
held-out report.

| Partition | Images | Macro Dice | Macro IoU | Pixel accuracy |
|---|---:|---:|---:|---:|
| Training (in-sample) | 105 | 0.9219 | 0.8572 | 0.9421 |
| Validation (one filename family) | 18 | 0.9429 | 0.8927 | 0.9545 |
| Not used for fitting; shares filename families with official test | 127 | 0.8987 | 0.8224 | 0.9305 |
| Original official held-out test | 50 | 0.9153 | 0.8484 | 0.9405 |
| **All unique pairs (descriptive; includes training images)** | **300** | **0.9122** | **0.8431** | **0.9377** |

The 250 duplicate training entries were omitted, leaving 300 unique image/mask
pairs. The training score is in-sample and is not an independent accuracy
estimate. Pixel accuracy counts every pixel and can look high when background
pixels are common; Dice/IoU better summarize overlap for this segmentation
task. “Accuracy” here is mask agreement, not clinical or diagnostic accuracy.

Full-cohort outputs: [all_sample_metrics.json](./renfast_baseline_run/all_sample_metrics.json)
and [all_sample_metrics_per_image.csv](./renfast_baseline_run/all_sample_metrics_per_image.csv).

## Separate spatial-data demonstration

A public GEO Visium cohort (GSE333529) was processed separately to demonstrate
mapping spatial gene counts onto its supplied tissue images. This did not use
RENFAST images or alter the checkpoint, and it is not external validation of
the fibrosis segmenter. See [GSE333529_SPATIAL_DEMO.md](./GSE333529_SPATIAL_DEMO.md)
for alignment checks, outputs, and reuse limitations.

## Limitations and use restrictions

- This is an internal RENFAST benchmark, not external validation. Only 10
  filename groups were held out, and their relationship to patients or biopsy
  cases is undocumented.
- Validation uses one filename group. The modest cohort and uncertainty
  intervals limit generalization claims.
- The run did not independently verify who drew or adjudicated the manual
  masks. The scores should be interpreted as model-to-mask agreement.
- It produces a binary mask only. It does not calculate a clinical fibrosis
  score, read patient reports, identify tubules/glomeruli/vessels, register
  slides to molecular data, or make a diagnosis.
- It is research-only and not suitable for clinical decisions. Expert review
  and validation on an independently labelled, permission-cleared cohort are
  required before broader use.
- The user reports written RENFAST permission. Its scope was not independently
  reviewed, and the archive itself did not contain licence terms. Confirm that
  training, derived-weight use, patent filing, and any distribution are covered
  before using or sharing the checkpoint. Do not redistribute source images or
  masks.
