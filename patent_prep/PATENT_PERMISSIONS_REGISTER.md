# Permissions and Licence Register

Draft for review by a patent attorney. This register records source-file wording only; it does not interpret permissions or licences.

| Asset | Licence or permission as recorded | What remains UNRESOLVED | What the inventor must supply |
|---|---|---|---|
| RENFAST data | Phase A register says Mendeley Data DOI `10.17632/m2t49zf6xr.1`, version 1; dataset licence field is blank. | Exact permission wording, scope, permitted commercial use, redistribution, and model/output use. | Paste the exact permission text without paraphrase and provide the applicable dataset terms. |
| RENFAST manual masks | The audit treats these as expert-made manual masks; no separate mask licence was located. They derive from the RENFAST dataset. | Whether the data permission covers masks, derived models, metrics, and disclosure in a filing. | Provide the exact applicable terms and any separate mask/annotation permission. |
| KPMP local trichrome slides/tiles | Phase B records local inventory status “open”; the inventory does not state licence or reuse terms. Access status is not proof of reuse rights. | Permission for research use, external annotation, commercial use, redistribution, and filing figures. | Paste the exact KPMP data-use terms and any applicable permission, without paraphrase. |
| torchvision DeepLabV3-ResNet50 implementation | Phase C records `torchvision 0.22.1+cu118`, BSD 3-Clause. No pretrained weights were used. | Confirm obligations for any future distribution of implementation-derived code. DeepLab model comparison was blocked, so no DeepLab result exists. | Preserve the licence text and obtain attorney review if the implementation is included or distributed. |
| ResNet50 encoder | The planned DeepLab implementation uses the torchvision ResNet50-based model; no pretrained encoder weights were used. Phase C records the implementation licence as BSD 3-Clause. | No separate encoder-weight licence applies to an unused pretrained weight set, but the code/implementation provenance should be confirmed before distribution. | Confirm no external pretrained encoder weights or code were added outside the saved record. |
| Phikon-v2 | Per the package instruction, Phikon-v2 is to be treated as carrying a non-commercial licence. It must not appear in an embodiment unless the inventor confirms authorisation in writing. The licence statement was not independently found in the permitted Phase A–C records. | Exact licence version, terms, and whether any permission exists. | Provide the licence and written authorisation if relevant; otherwise exclude it. |
| GIMP annotation tool (recommendation only) | Phase B2 licence register records GNU GPL Version 3. No annotation software was installed or used in the reported package preparation. | Whether the tool will be used or distributed with any future product. | Confirm use or omit it from product materials. |
| Python, NumPy, Pillow, PyTorch | Phase A/C registers report PSF-2.0, BSD, MIT-CMU, and BSD-3-Clause/BSD package terms respectively; CUDA/transitive component terms were not fully audited. | Full dependency and redistribution obligations for a product build. | Provide a complete software bill of materials for the intended product version. |
| Local Phase A–C scripts and model weights | Phase A says no source-code licence metadata was established; the RENFAST checkpoint is derived from the dataset and has no separate weight licence found. | Redistribution rights and whether permissions extend to trained weights or source. | Provide ownership, authorship, and permission records. |

## Verbatim paste-in blocks

RENFAST PERMISSION WORDING (paste exact text, no paraphrase): [ ]

KPMP DATA-USE TERMS (paste exact text, no paraphrase): [ ]

## Phikon-v2 file inventory

A text search of the permitted Phase A, Phase B, and Phase C report/code sources reviewed for this package found no Phikon-v2 reference or declared use, so no such Phase-prefixed file or script could be listed. This is not a search of materials outside the permitted Phase A–C source set. Do not include Phikon-v2 in any embodiment unless written authorisation is provided and verified.
