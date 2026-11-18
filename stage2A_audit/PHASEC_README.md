# Phase C README

## Scope and reproducibility

Phase C follows `PHASEC_PREREG.md`; it is a research-use audit only. All newly written files use the `PHASEC_` prefix. The source RENFAST archive, prior-phase files, and Phase B2 files are not modified. Phase B2 tiles are excluded by opaque filename inventory only; their pixels, key, and annotation results are not read by the Phase C runner.

The active saved split is 105 training pairs / 6 filename families, 18 validation pairs / 1 filename family, and 50 official test pairs / 10 filename families. These are **filename families, not verified patient or slide IDs**. The 127 pairs assigned `excluded_shared_with_test_family` are not used. No active family crosses splits.

## Environment and model source

- Python `3.13.1`
- PyTorch `2.7.1+cu118`
- torchvision `0.22.1+cu118`
- NumPy `2.2.6`
- Pillow `11.1.0`
- Device: CUDA, NVIDIA GeForce RTX 3050 Laptop GPU
- Frozen Phase A checkpoint SHA-256: `674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb`
- RENFAST archive SHA-256: `f796f0fa585701d66bd8f6b0ed096bb30f4376eff3359cb32ccbf1fd64d08a4e`
- torchvision DeepLabV3-ResNet50 implementation licence: BSD 3-Clause; no pretrained weights used.

## Commands

```powershell
& 'C:\Users\asus\python.exe' 'D:\patent\stage2A_audit\PHASEC_run.py' preflight
& 'C:\Users\asus\python.exe' 'D:\patent\stage2A_audit\PHASEC_run.py' run
& 'C:\Users\asus\python.exe' 'D:\patent\stage2A_audit\PHASEC_verify.py'
```

The preflight performs five gradient-only timing steps per architecture on one training tile, without optimizer updates or saved weights. The two U-Net runs use seeds `20261122` and `20261123`; the planned DeepLab run uses seed `20261116` but is not launched if the registered two-hour runtime cap is exceeded. Bootstrap resampling uses seed `20261125` and 10,000 replicates.

## Training recipe and run state

New U-Nets use the Phase A architecture, batch size 1, AdamW (`lr=1e-3`, `weight_decay=1e-4`), equal-weight BCE and soft-Dice loss, and the Phase A flip/rotation augmentation. Training is limited to 100 epochs with patience 12 on the one validation filename family. The DeepLab threshold grid is validation-only and is used only if the DeepLab run passes the runtime preflight.

The installed torchvision ASPP global-pooling branch errors in the training-only timing preflight at batch size 1. Its ASPP pooling sub-branch was placed in evaluation mode for the timing step; this would need to be documented as a compatibility adjustment if a future DeepLab training run were explicitly approved. The runtime preflight estimated DeepLab above the two-hour cap; therefore the DeepLab run and test comparison are blocked. Only the two U-Net ensemble-member runs proceeded.

## Completed run records

| Model/run | Seed | Epochs | Best epoch | Elapsed | Approximate UTC start | Metadata write UTC | Checkpoint SHA-256 |
|---|---:|---:|---:|---:|---|---|---|
| Plain U-Net | 20261122 | 75 | 63 | 898.23 s | 2026-11-16 15:51:38Z | 2026-11-16 16:06:36Z | `df33949e87dc8665adef0718df03db1aead62512922063691771e0ce7f441e4b` |
| Plain U-Net | 20261123 | 91 | 79 | 1149.94 s | 2026-11-16 16:06:39Z | 2026-11-16 16:25:49Z | `0b54a0d6e77c2bb9b8aa9bc616cc761fd27556ce3a42c8086d5bfba9d62a1b38` |

The start times are estimates formed by subtracting the recorded elapsed time from the metadata-file write time; the training code did not persist wall-clock start/end fields, so these are not exact. The DeepLab preflight projection was `8070.79 s` against a `7200 s` cap; no DeepLab training run or test comparison occurred.

The independent verification command recomputed frozen-U-Net Dice, colour-baseline family Dice, and ensemble Brier directly from saved weights and the test pairs. All three matched the reported values exactly. Detailed outputs include [PHASEC_ENVIRONMENT.json](./PHASEC_ENVIRONMENT.json), [PHASEC_VERIFICATION.json](./PHASEC_VERIFICATION.json), the run metadata/history files, and the direction-aware [PHASEC_robustness_summary_corrected.csv](./PHASEC_robustness_summary_corrected.csv).

## Result limitations

The registered robustness rule failed under extreme brightness and two individual perturbation directions. The uncertainty/low-Dice association was not established. The stronger-baseline comparison is blocked by its preflight runtime estimate. RENFAST licensing remains unresolved, and the 10 filename-family test groups are not verified patient or slide IDs. See [PHASEC_REPORT.md](./PHASEC_REPORT.md) for all results and the next required instruction.
