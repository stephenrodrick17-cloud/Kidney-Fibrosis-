# AI Technical Disclosure Checklist

Draft for review by a patent attorney. This is a factual completeness checklist, not legal advice.

| Required item | Exact recorded value or status | Source |
|---|---|---|
| Training data source | RENFAST fibrosis dataset, Mendeley Data DOI `10.17632/m2t49zf6xr.1`, version 1. Dataset licence field is blank. | `D:\patent\stage2A_audit\PHASEA_LICENCE_REGISTER.md` |
| Data and split size | `105` training pairs / `6` filename families; `18` validation pairs / `1` filename family; `50` test pairs / `10` filename families. These are filename families, not verified patient or slide IDs. | `D:\patent\stage2A_audit\PHASEA_RESULTS.md`; `D:\patent\stage2A_audit\PHASEA_final_metrics.json` |
| Split rule and manifest | Existing filename-family groups; active split family sets were checked as disjoint. Manifest: `D:\patent\stage2A_audit\PHASEA_final_split_manifest.csv`. | `D:\patent\stage2A_audit\PHASEA_final_split_manifest.csv`; `D:\patent\stage2A_audit\PHASEA_INTEGRITY_CHECK.md` |
| Excluded examples | `127` unique training pairs sharing filename families with the test set were excluded. `250` byte-identical duplicate training entries were not used. | `D:\patent\stage2A_audit\PHASEA_RESULTS.md`; `D:\patent\stage2A_audit\PHASEA_final_metrics.json` |
| Architecture | Model family is identified as U-Net. Exact layer list, channel widths, normalization, output-head details, and parameter count: **MISSING** from permitted Phase A–C source files. | `D:\patent\stage2A_audit\PHASEA_run_audit.py`; `D:\patent\stage2A_audit\PHASEC_run.py` |
| Input channels and size | RGB; evaluation tiles are `512 × 512`. RENFAST physical microns-per-pixel: **MISSING**. KPMP external region extraction targets `4.1 µm/pixel` and resamples to `512 × 512`; this is the Phase B procedure, not a confirmed RENFAST scale. | `D:\patent\stage2A_audit\PHASEC_run.py`; `D:\patent\stage2A_audit\PHASEB_select_regions.py`; `D:\patent\stage2A_audit\PHASEB_PREREG.md` |
| Input normalization | Convert RGB values to float and divide by `255.0`, yielding `[0,1]`. | `D:\patent\stage2A_audit\PHASEA_run_audit.py` |
| Padding/cropping | Bottom/right padding to a multiple of `16`; output cropped to original dimensions. | `D:\patent\stage2A_audit\PHASEA_run_audit.py` |
| Loss | Phase C new-member metadata describes equal-weight BCE and soft-Dice loss (`0.5` each) as the Phase A recipe. The exact frozen Phase A training record is **MISSING** from the permitted Phase A files. | `D:\patent\stage2A_audit\PHASEC_UNET_seed_20261122_metadata.json`; `D:\patent\stage2A_audit\PHASEC_UNET_seed_20261123_metadata.json` |
| Optimizer | Phase C new-member metadata records AdamW, `lr=1e-3`, `weight_decay=1e-4`, batch size `1`, as the Phase A recipe. Independent Phase A training metadata: **MISSING**. | The two Phase C U-Net metadata JSON files |
| Training epochs and best epoch | Frozen Phase A epoch count and best epoch: **MISSING** from permitted Phase A files. Phase C U-Net seed `20261122`: `75` epochs completed, best epoch `63`; seed `20261123`: `91` epochs completed, best epoch `79`. These are Phase C ensemble members, not the frozen Phase A model. | The two Phase C U-Net metadata JSON files; `D:\patent\stage2A_audit\PHASEC_README.md` |
| Early stopping | Phase C new members: patience `12`, maximum `100` epochs. Frozen Phase A settings: **MISSING**. | The two Phase C U-Net metadata JSON files |
| Augmentation | Phase C metadata refers to “Phase A flips/rotations.” Exact operations, probabilities, and angles: **MISSING** from permitted records. | The two Phase C U-Net metadata JSON files |
| Seeds | Phase C new U-Net seeds: `20261122`, `20261123`. Frozen Phase A training seed: **MISSING** from permitted Phase A files. | The two Phase C U-Net metadata JSON files; `D:\patent\stage2A_audit\PHASEC_README.md` |
| Probability threshold | Frozen U-Net threshold `0.5`. Phase A describes it as fixed; its original selection history is **MISSING**. The colour-baseline threshold was selected on training families only; selected value `t=2`. | `D:\patent\stage2A_audit\PHASEA_README.md`; `D:\patent\stage2A_audit\PHASEA_final_metrics.json` |
| Frozen Phase A checkpoint hash | `674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb` | `D:\patent\stage2A_audit\PHASEA_README.md`; `D:\patent\stage2A_audit\PHASEA_final_metrics.json` |
| Phase C checkpoint hashes | Seed `20261122`: `df33949e87dc8665adef0718df03db1aead62512922063691771e0ce7f441e4b`; seed `20261123`: `0b54a0d6e77c2bb9b8aa9bc616cc761fd27556ce3a42c8086d5bfba9d62a1b38`. | The two Phase C U-Net metadata JSON files; `D:\patent\stage2A_audit\PHASEC_REPORT.md` |
| Software and hardware | Python `3.13.1`; NumPy `2.2.6`; Pillow `11.1.0`; PyTorch `2.7.1+cu118`; torchvision `0.22.1+cu118`; CUDA device: NVIDIA GeForce RTX 3050 Laptop GPU. | `D:\patent\stage2A_audit\PHASEA_README.md`; `D:\patent\stage2A_audit\PHASEC_README.md`; `D:\patent\stage2A_audit\PHASEC_ENVIRONMENT.json` |
| Exact reproduction commands | Phase A corrected audit: `& 'C:\Users\asus\python.exe' 'D:\patent\stage2A_audit\PHASEA_run_audit.py'`. Phase C: `& 'C:\Users\asus\python.exe' 'D:\patent\stage2A_audit\PHASEC_run.py' preflight`; `& 'C:\Users\asus\python.exe' 'D:\patent\stage2A_audit\PHASEC_run.py' run`; verification: `& 'C:\Users\asus\python.exe' 'D:\patent\stage2A_audit\PHASEC_verify.py'`. | `D:\patent\stage2A_audit\PHASEA_README.md`; `D:\patent\stage2A_audit\PHASEC_README.md` |
| Expected model output | A thresholded binary pixel mask is confirmed by the evaluation code. Exact deployment output format, API/schema, and user-facing display are **MISSING**. | `D:\patent\stage2A_audit\PHASEA_run_audit.py`; `D:\patent\stage2A_audit\PHASEB_run_external_check.py` |
| Expected audit outputs | Phase A records per-image metrics, per-family metrics, split manifest, and failure gallery. Phase B records masks/overlays, area summaries, and objective flags. | `D:\patent\stage2A_audit\PHASEA_README.md`; `D:\patent\stage2A_audit\PHASEB_REPORT.md` |

## Open questions for the inventor

- Provide the authoritative frozen-model source code, exact U-Net layer/channel specification, and parameter count.
- Provide the frozen Phase A run metadata showing original training seed, epochs, best epoch, loss, optimizer, batch size, and augmentation details.
- Confirm which listed values describe the frozen Phase A model versus the later Phase C ensemble members.
- Provide the intended deployment input constraints and output schema.
- Confirm the source and terms authorizing use of the RENFAST images and masks.
