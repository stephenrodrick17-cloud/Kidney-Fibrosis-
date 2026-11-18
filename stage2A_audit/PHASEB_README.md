# Phase B README

**Run date:** 2026-11-16  
**Purpose:** preregistered external sanity check of the frozen RENFAST model on local KPMP trichrome regions.  
**Scope:** Phase B only; no retraining, tuning, downloads, or Phase C.

## Inputs and selection

- Local slide inventory: `D:\patent\atlas_repository_filelist-20261105.csv`.
- Local WSI files were used only when listed as `open` and marked `TRI stain`; no slide source file was changed.
- Selected 40 regions with seed `20261118`, target `4.1 µm/pixel`, region size `512 × 512`, minimum tissue fraction `0.50`, and 10 regions per slide-colour stratum.
- The selection was completed and saved before model inference. Candidate regions were not chosen using model outputs.
- Checkpoint: `D:\patent\stage2A_audit\renfast_baseline_run\checkpoint_best.pt`, SHA-256 `674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb`.
- Frozen colour baseline: `B − R >= 2`, recorded in `PHASEA_final_metrics.json`.
- No matched reference labels were available; no reference-based performance metrics were computed.

## Runtime

- Python 3.13.1
- OpenSlide Python 1.4.7; `openslide-bin` 4.0.1.2
- NumPy 2.2.6
- Pillow 11.1.0
- PyTorch 2.7.1+cu118
- Device: CUDA, NVIDIA GeForce RTX 3050 Laptop GPU

## Exact commands

```powershell
& 'C:\Users\asus\python.exe' 'D:\patent\stage2A_audit\PHASEB_select_regions.py'
& 'C:\Users\asus\python.exe' -m py_compile 'D:\patent\stage2A_audit\PHASEB_run_external_check.py'
& 'C:\Users\asus\python.exe' 'D:\patent\stage2A_audit\PHASEB_run_external_check.py'
& 'C:\Users\asus\python.exe' -m py_compile 'D:\patent\stage2A_audit\PHASEB_verify_outputs.py'
& 'C:\Users\asus\python.exe' 'D:\patent\stage2A_audit\PHASEB_verify_outputs.py'
```

The scripts refuse to overwrite their named outputs. No package was installed and no download was performed.

## Phase B files

- Protocol: `PHASEB_PREREG.md`
- Scripts: `PHASEB_select_regions.py`, `PHASEB_run_external_check.py`, `PHASEB_verify_outputs.py`
- Selection evidence: `PHASEB_region_manifest.csv`, `PHASEB_slide_audit.csv`, `PHASEB_region_selection.json`
- Selected source tiles and prediction panels: `PHASEB_region_images\` (40 inputs and 160 derived mask/overlay PNGs)
- Results: `PHASEB_region_metrics.csv`, `PHASEB_failure_flags.csv`, `PHASEB_top10_disagreement.csv`, `PHASEB_inference_summary.json`
- Contact sheet: `PHASEB_contact_sheet.png`
- Blank reviewer form: `PHASEB_REVIEW_FORM.csv`
- Recomputed verification: `PHASEB_VERIFICATION.json`
- Documentation: `PHASEB_REPORT.md`, `PHASEB_LICENCE_REGISTER.md`, `PHASEB_DEVIATIONS.md`, `PHASEB_INTEGRITY_CHECK.md`

All new files have the `PHASEB_` filename prefix. Existing files were not overwritten. The input slides remain local and are not redistributed.
