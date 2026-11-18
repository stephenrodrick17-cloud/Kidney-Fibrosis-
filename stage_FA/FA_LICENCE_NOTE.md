# Stage FA Licence and Permission Note — EXPLORATORY, NOT CONFIRMATORY

**EXPLORATORY, NOT CONFIRMATORY. UNVALIDATED MASKS.**

This note records local status only. It does not interpret licence wording or grant permission.

| Asset | Local evidence used | Licence / permission status |
|---|---|---|
| RENFAST fibrosis data | Existing local dataset and training/evaluation source; see the local Phase A licence register. | **UNRESOLVED.** The local register reports the dataset licence field is blank and no licence file is in the local archive. The exact permission record is blank. |
| Frozen RENFAST U-Net | Checkpoint at `D:\patent\stage2A_audit\renfast_baseline_run\checkpoint_best.pt`; SHA-256 `674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb`. Loaded read-only; no retraining or tuning. | **UNRESOLVED.** The local register reports no separate weight licence. No permission wording is inferred. |
| KPMP kidney images and spatial/expression data | Existing Stage 1 and Stage 1d local image, position, scale-factor, and expression files listed in the data and analysis hash manifests. | **UNRESOLVED.** No exact applicable reuse wording was present in the permission record. A local catalogue access field is not treated as reuse permission. |
| Phikon-v2 | No file or model from Phikon-v2 was loaded or used by the Stage FA analysis. | **NOT USED.** |
| Other non-commercial or unclear encoder | No alternative encoder was loaded. The analysis used the frozen RENFAST U-Net masks and the fixed colour rule. | **NOT USED.** |
| Runtime packages | Python 3.13.1, PyTorch 2.7.1+cu118, NumPy 2.2.6, SciPy 1.18.1, Pillow 11.1.0. | The existing local Phase A register records Python PSF-2.0, NumPy BSD, Pillow MIT-CMU, and PyTorch BSD-3-Clause package metadata. CUDA and transitive component terms were not separately audited. |

Some Stage FA files contain the field `asset_status=RESEARCH-ONLY`. This is a workflow label, not evidence of an applicable licence, authorization, or permission decision. The RENFAST and KPMP statuses remain **UNRESOLVED** as stated above.

No catalogue or licence page was read on the internet. No URL was visited, and no data or model weights were downloaded.

## Files and assets touching restricted encoders

No Stage FA run file loaded or used Phikon-v2 or another non-commercial encoder. The image runner loaded only the frozen RENFAST checkpoint named above. No encoder-license interpretation was performed.

## Sources

- Local exact-permission record: `D:\patent\stage2A_audit\PHASEA_PERMISSION_RECORD.md` (blank).
- Local licence register: `D:\patent\stage2A_audit\PHASEA_LICENCE_REGISTER.md`.
- The current run's source and output hashes are recorded in [FA_ANALYSIS_HASHES_FINAL.csv](./FA_ANALYSIS_HASHES_FINAL.csv) and [FA_VERIFICATION_HASHES_FINAL.csv](./FA_VERIFICATION_HASHES_FINAL.csv).
