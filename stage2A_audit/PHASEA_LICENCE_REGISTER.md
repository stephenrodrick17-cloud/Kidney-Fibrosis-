# Phase A Licence Register

**Last updated:** 2026-11-16  
**Use scope:** Phase A research audit only. Permission wording was not interpreted or summarized.
**Grouping note:** All split groups referenced by this audit are filename families, not verified patient or slide IDs.

| Item | Version/source | Licence or terms found | Phase A status |
|---|---|---|---|
| RENFAST fibrosis dataset | Mendeley Data, DOI `10.17632/m2t49zf6xr.1`, version 1; local archive SHA-256 `f796f0fa585701d66bd8f6b0ed096bb30f4376eff3359cb32ccbf1fd64d08a4e` | Dataset licence field is blank. The local archive contains no licence file. | **Licence field blank; scope of the user-reported permission is UNRESOLVED.** Exact permission wording is requested in [PHASEA_PERMISSION_RECORD.md](./PHASEA_PERMISSION_RECORD.md). |
| Frozen RENFAST U-Net checkpoint | Locally trained checkpoint; SHA-256 `674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb` | No pretrained weights were used. This checkpoint is derived from RENFAST data; no separate weight licence was found. | The scope of the user-reported permission is **UNRESOLVED**. Do not infer permission from this audit. |
| RENFAST training/evaluation source | Existing `run_renfast_baseline.py` and new prefixed Phase A script | No source-code licence metadata was established in the workspace. | Local audit use only; redistribution rights not assessed. |
| Python | 3.13.1 | Python Software Foundation licence (PSF-2.0). | Runtime only; not embedded or redistributed. |
| NumPy | 2.2.6 | BSD licence; package metadata identifies an OSI-approved BSD licence. | Used for array and metric calculations. |
| Pillow | 11.1.0 | MIT-CMU licence, as reported by installed package metadata. | Used to read images and generate the failure gallery. |
| PyTorch | 2.7.1+cu118 | BSD-3-Clause, as reported by installed package metadata. | Used to load and run the frozen checkpoint. CUDA/transitive component terms were not separately audited. |

No new dataset or model weights were downloaded. This register does not grant, establish, or interpret data rights.
