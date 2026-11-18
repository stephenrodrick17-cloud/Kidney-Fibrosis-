# Phase B Licence Register

This register records observed metadata and unresolved rights. A local file marked `open` is not treated as proof of unrestricted reuse.

| Item | Observed source/status | Licence or terms | Phase B use and limits |
|---|---|---|---|
| KPMP TRI slides | Local catalog `Access=open`; no download | The local catalog does not state an applicable licence or reuse terms; **unresolved** | Used locally for a research sanity check only. Source slides were not modified or redistributed. Obtain and review the exact data-use terms before downstream use. |
| RENFAST checkpoint | Existing frozen Phase A checkpoint; SHA-256 `674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb` | No separate model-weight licence verified in this phase; underlying permission scope remains **unresolved** | Inference only; not retrained, modified, or redistributed. |
| Phase A colour-threshold baseline | Existing result metadata: rule `B − R >= 2` | Derived from Phase A work; no separate licence | Applied unchanged to the same 40 regions; not tuned here. |
| OpenSlide Python | Installed distribution `openslide-python` 1.4.7 | Distribution metadata: `LGPL-2.1-only AND BSD-3-Clause AND MIT AND LicenseRef-Public-Domain` | Used locally to read WSI metadata and regions; not redistributed. |
| OpenSlide binary | Installed distribution `openslide-bin` 4.0.1.2 | Distribution metadata reports bundled terms: `LGPL-2.1-only AND blessing AND BSD-1-Clause AND BSD-2-Clause AND BSD-3-Clause AND (BSD-3-Clause OR GPL-2.0-only) AND BSD-4.3TAHOE AND IJG AND LGPL-2.0-or-later AND (LGPL-2.1-only OR MPL-1.1) AND LGPL-2.1-or-later AND libpng-2.0 AND libtiff AND MIT AND Zlib` | Used locally through OpenSlide; not redistributed. Review the installed distribution's licence files before any redistribution. |
| NumPy | 2.2.6 | Distribution metadata classifier: BSD License; no SPDX expression exposed by installed metadata | Used locally for image processing; not redistributed. |
| Pillow | 11.1.0 | Distribution metadata: `MIT-CMU` | Used locally for image I/O and overlays; not redistributed. |
| PyTorch | 2.7.1+cu118 | Distribution metadata: BSD-3-Clause | Used locally for frozen inference; not redistributed. |
| Python runtime | Python 3.13.1 | Python Software Foundation terms; exact runtime distribution files not audited here | Used locally; not redistributed. |
| CUDA runtime | CUDA-enabled PyTorch build `+cu118`; NVIDIA GPU | NVIDIA terms were not separately audited | Used locally for inference; no CUDA components redistributed. |

No licence-clean conclusion is made for the KPMP slides or RENFAST checkpoint. No source slides, model weights, or software were included in a public release.
