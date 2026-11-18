# PROTO Design and Source Audit

## Scope and safeguards

PROTO is a local research prototype. It measures the fraction of tissue pixels marked by a frozen RENFAST model and can optionally compare those spot scores with a small, preselected gene set from the same sample. It does not make a medical assessment.

- New files and generated results stay under `D:\patent\prototype\`; existing files are read-only.
- The frozen checkpoint is referenced at `D:\patent\stage2A_audit\renfast_baseline_run\checkpoint_best.pt`. Its required SHA-256 is `674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb`. No copy is made. Each command that starts a run checks this hash and refuses a mismatch.
- The model is loaded with `weights_only=True`, set to evaluation mode, and never trained or tuned. No stain normalization, augmentation, alternate encoder, or Phase B2 input is used.
- Processing is local. The optional browser interface binds only to `127.0.0.1`; it makes no external network calls. Uploaded bytes are held by the local app for processing and are not sent elsewhere.
- Run time is capped below two hours and generated content is capped at 10 GB. Outputs are not overwritten.

## Existing source reviewed

The following source files were read only. The line references below identify the source of each reused rule. PROTO imports the existing U-Net architecture directly and reimplements the remaining small steps; it does not edit or copy any source file.

| Step | Existing source and lines | PROTO handling |
|---|---|---|
| U-Net architecture | `stage2A_audit\run_renfast_baseline.py`, lines 323-366 (`DoubleConv`, `UNet`) | Imported directly from the read-only Phase A module, so layer definitions cannot drift. |
| Phase A RGB normalization, bottom/right padding to a multiple of 16, sigmoid, and threshold | `stage2A_audit\PHASEA_run_audit.py`, lines 229-244 (`run_unet`); `stage2A_audit\run_renfast_baseline.py`, line 31 (`THRESHOLD`) | Reimplemented for 512-pixel tiles. On 512-by-512 Phase A patches, there is one tile and no padding, matching the reference operation. |
| Phase A single-patch inference | `stage2A_audit\run_renfast_baseline.py`, lines 916-970 (`predict_patch`) | The same RGB-to-tensor scaling, frozen threshold, and output interpretation are followed. |
| Arbitrary-image tiling and white edge padding | `stage_FA\FA_RUN_IMAGES.py`, lines 157-181 (`render_unet`) | Reimplemented with the same 512-pixel tile size, white padding, RGB scaling, sigmoid, and threshold. The 512-pixel Phase A regression case checks equality. |
| MPP rescaling | `stage_FA\FA_RUN_IMAGES.py`, lines 345-360 | Reimplemented with the same scale formula and Lanczos resizing; the user must supply source MPP. |
| Tissue mask | `stage2A_audit\PHASEB_select_regions.py`, lines 229-257 (`read_candidate`) | Reuses the rule `mean(R,G,B) < 245` on the image at the target scale. |
| Image feature checks | `stage2A_audit\PHASEC_run.py`, lines 660-678 | Uses the six full-image RGB mean/SD features, training-only means/SDs, and the saved absolute z-score threshold of 3.0. |
| Spot position parsing and circular footprint | `stage_FA\FA_RUN_IMAGES.py`, lines 110-150, 372-405; spot diameter constant at lines 37-41 | Reimplements the Visium columns and the circular footprint of diameter `55 / 4.1 = 13.414634...` pixels. |
| High/low groups and regression | `stage_FA\FA_ANALYZE.py`, lines 234-356, 700-745 | Reuses deterministic tertiles, log-normalized gene counts, z-scores, and least-squares adjusted high-minus-low regression. PROTO uses the requested within-sample covariates and does not include participant-level or cross-sample analysis. |
| Display scaling and overlay | `stage_FA\FA_RUN_IMAGES.py`, lines 184-254 | Reimplements a local overlay; no spots or clinical interpretation are drawn unless the optional association inputs are provided. |

The exact implementation and its tests are in the other `PROTO_*.py` files. Source line references describe the audited source as inspected for this build; no source changes are made.

## Assets and permission status

| Asset | Local source | Recorded status |
|---|---|---|
| RENFAST training/test images and manual masks | `D:\patent\m2t49zf6xr-1.zip` | Dataset licence field is blank; permission wording and scope are **UNRESOLVED**. No wording is interpreted. |
| Frozen RENFAST U-Net checkpoint | `D:\patent\stage2A_audit\renfast_baseline_run\checkpoint_best.pt` | SHA-256 matches the required value. It is derived from RENFAST data; reuse and redistribution permission is **UNRESOLVED**. |
| Phase A/B/C source and summary files | `D:\patent\stage2A_audit\` | Existing local research files. Source-code redistribution terms are **NOT AVAILABLE** in the reviewed records. |
| KPMP image, spot-position, and expression files | `D:\patent\data\` and `D:\patent\stage_FA\` | The local catalog says `open` for some items, but reuse permission is **UNRESOLVED**; no status is inferred from that label. |
| Python, NumPy, Pillow, PyTorch, SciPy, Streamlit | Existing local environment only | Package metadata is recorded in `PROTO_LICENCE_NOTE.md`; nothing is downloaded or bundled. |

Sharing or distributing the checkpoint or this tool is blocked until permissions are resolved and the inventor and attorney approve. No permission is granted or inferred by this prototype.

## Implementation choices

- Supported image file types are PNG, JPEG, and TIFF. The file must decode as RGB. Default input limits are 100 MB and 100 megapixels; these are protective prototype limits, not existing study thresholds.
- Scale factor is `input micrometres per pixel / 4.1`. Target dimensions are rounded from original dimensions times that factor; Lanczos resampling is used. Factors outside 0.5-1.5 are refused.
- Tissue fraction is measured on the rescaled image. The six colour features are measured on the original input pixels, matching the Phase C feature calculation. A feature outside three training SDs is `UNUSUAL`, not an automatic stop. The tissue fraction cutoff is 0.20.
- Fibrosis percentages are computed on the 4.1-micrometre image as positive pixels within the tissue mask divided by tissue pixels. The binary mask is mapped back to original input dimensions with nearest-neighbour resampling.
- The optional browser interface uses the already-installed Streamlit package, is launched with telemetry disabled and loopback binding, and writes only below the prototype folder.
- Spatial confidence intervals use a deterministic 4-by-4 Visium array-coordinate block bootstrap with 10,000 resamples and a fixed seed. The intervals are approximate. No p-values are used as proof.

## Prompt conflict

Warning W4 must be printed exactly as supplied and conflicts with the requested forbidden-word scan. Both requirements cannot be satisfied at once. PROTO preserves all five warnings verbatim and scopes the automated scan to other generated user-facing text; the exact warnings are an explicit exception. This limitation is recorded rather than silently changing the required wording.
