# Phase A Audit README

**Run date:** 2026-11-16  
**Purpose:** reproduce the frozen RENFAST fibrosis-mask result and compare it with preregistered simple baselines.  
**Scope:** Phase A only. No new model training; Phase B was not started.

## Preregistration

- [PHASEA_PREREG_A.md](./PHASEA_PREREG_A.md), registered 2026-11-16 16:04:08 +05:30, before new Phase A comparisons.
- [PHASEA_PREREG_AMENDMENT.md](./PHASEA_PREREG_AMENDMENT.md), registered before comparisons; corrects the reproduction criterion to compare the full-precision rerun with the saved full-precision score and the rounded score to four decimals.

## Data, split, and provenance

- RENFAST archive: `D:\patent\m2t49zf6xr-1.zip`, SHA-256 `f796f0fa585701d66bd8f6b0ed096bb30f4376eff3359cb32ccbf1fd64d08a4e`.
- Frozen checkpoint: `D:\patent\stage2A_audit\renfast_baseline_run\checkpoint_best.pt`, SHA-256 `674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb`.
- Unique pairs used: 105 training pairs in 6 filename families, 18 validation pairs in 1 filename family, and 50 test pairs in 10 filename families. A further 127 unique training pairs sharing filename families with the official test set were excluded; 250 byte-identical duplicate training entries were not used.
- The split check found no filename family in more than one active split. These identifiers are filename families, **not verified patient or slide IDs**.
- The test metrics are agreement with RENFAST manual masks, not medical or diagnostic accuracy.

## Methods

- Frozen U-Net: existing checkpoint, existing RGB preprocessing, and fixed probability threshold 0.5.
- Colour threshold: `B - R >= t`; searched every integer from -255 through 255 and selected `t` by equal-family-weighted mean image Dice on the 105 training pairs only. The selected threshold was `t = 2`.
- Trivial baseline: all pixels predicted background.
- Primary 95% CIs: 10,000 paired resamples of the 10 test filename families, seed `20261117`, equal weight per family.
- Secondary 95% CIs: 10,000 stratified resamples of images within each of the 10 fixed test filename families, seed `20261118`, then equal weight per family.
- The 10 test families limit precision. They are not verified patients or slides.
- A separate published architecture was not run: no already-available, licence-clean implementation/checkpoint was established for this phase, and no new architecture was trained.

## Software and exact command

Runtime versions observed with `C:\Users\asus\python.exe`:

- Python 3.13.1
- NumPy 2.2.6
- Pillow 11.1.0
- PyTorch 2.7.1+cu118
- Device: CUDA, NVIDIA GeForce RTX 3050 Laptop GPU

Command used for the corrected final run:

```powershell
& 'C:\Users\asus\python.exe' 'D:\patent\stage2A_audit\PHASEA_run_audit.py'
```

The script refuses to overwrite its named outputs. The corrected final outputs use the `PHASEA_final_*` prefix. The same script was run once before a bootstrap implementation issue was found and corrected; the first-run outputs are preserved under `PHASEA_*` names without `final`. See [PHASEA_DEVIATIONS.md](./PHASEA_DEVIATIONS.md) and [PHASEA_INTEGRITY_CHECK.md](./PHASEA_INTEGRITY_CHECK.md).

## Phase A outputs

- [PHASEA_RESULTS.md](./PHASEA_RESULTS.md) — findings, metrics, PASS/FAIL, limits, and next instruction.
- [PHASEA_final_metrics.json](./PHASEA_final_metrics.json) — full estimates, confidence intervals, hashes, split counts, and verification.
- [PHASEA_final_per_image_metrics.csv](./PHASEA_final_per_image_metrics.csv) — all 50 images × 3 baselines, with Dice/IoU/precision/recall.
- [PHASEA_final_per_group_metrics.csv](./PHASEA_final_per_group_metrics.csv) — all 10 filename families × 3 baselines.
- [PHASEA_final_split_manifest.csv](./PHASEA_final_split_manifest.csv) — unique split assignments and source hashes; excluded pairs are retained as excluded, not used.
- [PHASEA_final_failure_gallery.png](./PHASEA_final_failure_gallery.png) — 12 lowest-U-Net-Dice test images with input, manual mask, U-Net overlay, and colour-threshold overlay.
- [PHASEA_LICENCE_REGISTER.md](./PHASEA_LICENCE_REGISTER.md) and [PHASEA_PERMISSION_RECORD.md](./PHASEA_PERMISSION_RECORD.md) — data/model/software rights record and blank user paste-in section.
- [PHASEA_INTEGRITY_CHECK.md](./PHASEA_INTEGRITY_CHECK.md) and [PHASEA_DEVIATIONS.md](./PHASEA_DEVIATIONS.md) — recomputation checks, edits, and deviations.

All new files are prefixed `PHASEA_`. No pre-existing file in the audit folder or raw dataset was modified.
