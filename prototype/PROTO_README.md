# PROTO local research tool

## Required warnings

W1 "RESEARCH USE ONLY. Not a medical device. Not for diagnosis, grading, treatment or any clinical decision."
W2 "Trained and tested on RENFAST trichrome kidney images at about 4.1 micrometres per pixel. Accuracy on other stains, scanners or tissues has NOT been established."
W3 "On the RENFAST test set (10 filename families) the model scored Dice 0.915 against expert masks (95% CI 0.888 to 0.934). It lost accuracy under very dark images (brightness 0.5) and at half-size resolution. On KPMP images its masks have NOT been checked against an expert reference and were often sparse."
W4 "Gene results show association only: genes that are higher in regions the model marks as fibrotic. They do not show that any gene causes fibrosis, and they cannot predict gene activity from an image."
W5 "Results from one sample cannot be generalised. Cross-participant relationships between overall fibrosis percentage and gene levels were NOT found in the validation work."

## What it does

PROTO reads one RGB kidney tissue image and reports the share of tissue pixels marked by the frozen RENFAST model. It also reports a fixed colour-rule result as a secondary comparison. It does not change model weights.

An optional command compares the image scores with nine preselected genes from a matching 10x Visium count matrix. This is a within-one-sample association report only.

All processing is local. Results go into a selected subfolder of `D:\patent\prototype\`. The checkpoint and existing research data are read in place and are never copied. Sharing the tool or checkpoint is blocked while permission remains unresolved.

## What it does not do

- It does not make a medical assessment or suggest care.
- It does not infer gene activity from an image.
- It does not test genes beyond the fixed nine-gene set.
- It does not make a claim about a new stain, scanner, tissue type, or person.

## Run from PowerShell

Read all five warnings first. Then run one image:

```powershell
python D:\patent\prototype\PROTO_QUANTIFY.py --image D:\path\to\image.png --mpp 4.1 --output results\sample1 --accept-research-use
```

Replace `4.1` with the measured micrometres per pixel for the input image. The value in this example is only an example and is not filled in automatically. The image must be PNG, JPEG, or TIFF, readable as RGB, under 100 MB and under 100 megapixels. The result folder must stay under `D:\patent\prototype\`.

The local browser page is optional:

```powershell
streamlit run D:\patent\prototype\PROTO_APP.py --server.address 127.0.0.1 --browser.gatherUsageStats false
```

The browser page shows the warnings and requires a checkbox. It accepts a local file, keeps its bytes in the local app, and saves output only below the prototype folder.

For the optional gene report, supply all of the matching inputs. The image must be the matching Visium high-resolution image described by the scale-factor file:

```powershell
python D:\patent\prototype\PROTO_ASSOCIATE.py --image D:\path\to\image.png --mpp 4.1 --positions D:\path\to\tissue_positions.csv --scalefactors D:\path\to\scalefactors_json.json --counts D:\path\to\filtered_feature_bc_matrix --output results\sample1 --accept-research-use
```

Counts may be a 10x Matrix Market folder/file, a 10x HDF5 matrix, or a CSV with `barcode`, `library_size_umi`, and `raw_` columns for the nine listed genes. Optional tissue depth is a CSV with `barcode,tissue_depth_um`.

The image command writes a binary mask PNG, an overlay PNG, and a JSON report. The optional gene command first writes those same image outputs, then writes a CSV table and a JSON report. Existing files are not overwritten. The PNG files carry the warnings in their metadata.

## Example

For Phase A test image `1004762`, the prototype mask was bit-identical to the Phase A inference function. Its Dice against the supplied test mask was `0.9479029721857036`, matching the saved Phase A table. Physical spacing for this patch is **NOT AVAILABLE**, so PROTO did not calculate or report a fibrosis percentage for it.

## Fixed model settings

- Model: the existing frozen RENFAST U-Net, loaded read-only.
- Threshold: probability `0.5`.
- Target scale: `4.1` micrometres per pixel.
- Image tiles: `512 × 512`, with white padding at image edges.
- Tissue rule: mean of the three RGB channels below `245`.
- Secondary comparison: `B - R >= 2`.
- Gene list: `COL1A1`, `COL1A2`, `COL3A1`, `FN1`, `TGFB1`, `CCN2`, `ACTA2`, `MMP2`, and `TIMP1`.
- Spatial interval: approximate 95% block-bootstrap interval, 10,000 resamples, fixed seed, 4-by-4 Visium array-coordinate blocks.

Read `PROTO_LIMITATIONS.md`, `PROTO_LICENCE_NOTE.md`, and `PROTO_REPORT.md` before use.
