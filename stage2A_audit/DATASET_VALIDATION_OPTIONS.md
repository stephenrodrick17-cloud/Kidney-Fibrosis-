# Other Kidney Data Sources for the Proposed Functions

**Checked:** 2026-11-16  
**Scope:** Publicly described resources and papers that may support separate
validation tasks. The small public GEO archive GSE333529 has since been
downloaded for a separate spatial-mapping demonstration; it was not used to
train or validate the RENFAST fibrosis model. Public availability does not
itself grant reuse, commercial, patent, or redistribution rights.

## What was found

| Need | Candidate and verified evidence | What it could support | Access/important limits |
|---|---|---|---|
| Fibrosis-mask baseline | [RENFAST Mendeley record](https://data.mendeley.com/datasets/m2t49zf6xr/1) describes 300 Masson's trichrome fibrosis images with manual annotations, and 350 PAS vessel images. | The current binary fibrosis-mask task; a separate vessel-mask experiment could be designed from its vessel subset after a dedicated integrity and permission review. | The Mendeley licence field is blank. The user reports written permission, but its exact scope was not reviewed. Images are not accompanied by narrative pathology reports, validated fibrosis grades, or matched molecular measurements. |
| Several kidney structures and fibrosis grades | [He et al., 2025, multi-class kidney histology segmentation](https://pmc.ncbi.nlm.nih.gov/articles/PMC12592389/) describes 147 training/validation WSIs and 24 external-test WSIs. It annotates glomeruli, tubules, arteries, and a residual interstitium class; the external cases have Banff lesion scores and IFTA difficulty groups. The authors report annotations reviewed by a nephropathologist. | The strongest located candidate for a separate, structure-segmentation validation and for studying performance by fibrosis/inflammation severity. It is not a universal label set for every kidney structure or stain. | The paper says annotated WSIs are available from the corresponding author only after data-transfer agreements with the contributing medical centers. It uses Jones-silver stain, unlike RENFAST's trichrome fibrosis patches. Obtain access and confirm derivative-model/patent rights before use. The paper's code is public at [AmsPath/MMS_Segmentation](https://github.com/amspath/MMS_Segmentation), but the images are not thereby open. |
| Glomeruli segmentation only | [HuBMAP - Hacking the Kidney Kaggle challenge](https://www.kaggle.com/competitions/hubmap-kidney-segmentation/overview) is explicitly a task to identify glomeruli in human kidney images. | A focused glomerulus-detection/segmentation benchmark. | It does not provide fibrosis grades, report text, all-compartment annotations, or matched molecular data. Check Kaggle's current data-use terms and the source image rights for patent/model use before downloading or training. |
| Fibrosis grade/clinical associations | [Pandit et al., 2025, kidney histomorphology study](https://pmc.ncbi.nlm.nih.gov/articles/PMC12508135/) reports 1,421 WSIs across cohorts, including TRIDENT clinical biopsies, and tests association with pathologist-quantified interstitial fibrosis and clinical/genetic variables. | Potential slide-level fibrosis/outcome validation if the cohort files and labels can be accessed. | The article states that the sensitive data are not openly available and may be requested from the corresponding author. It reports structured pathologist measurements, not a public set of narrative reports; it is not the same as a spatially registered molecular dataset. |
| Spatial molecular measurements | [GSE333529](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE333529) includes four human lupus-nephritis Visium samples with tissue images, spot-position tables, scale factors, and gene-count matrices. The article reports the spatial data under GSE333529. | A small technical demonstration can map spatial gene counts onto the accompanying images. This has now been run for COL1A1, COL3A1, and FN1. | The archive was downloadable from GEO and passed matrix/barcode/image-coordinate consistency checks. The GEO record and article do not establish patent/derived-model rights; the article also says supporting data are available from the corresponding author upon reasonable request. This is exploratory mapping, not fibrosis ground truth or external validation of RENFAST. |
| Spatial molecular measurements | [HuBMAP](https://portal.hubmapconsortium.org/) provides a portal for human-tissue molecular and spatial data; its project describes a human tissue atlas at single-cell resolution. | Candidate source for testing a spatial-data workflow where a kidney specimen has both usable histology and molecular coordinates. | Check the exact kidney specimen, files, assay, matching section, registration metadata, access status, and reuse terms record by record. A general portal or an image from the same donor does not establish same-section registration or fibrosis labels. |
| Human diabetic-kidney spatial study | [Qiu et al., 2026, spatial atlas of human diabetic kidney](https://pmc.ncbi.nlm.nih.gov/articles/PMC13247493/) describes scanned histology, pathology review, and Visium HD spatial expression on human FFPE kidney tissue (three tissue sections in the described human spatial set), alongside other clinical/molecular analyses. | A possible small proof-of-concept reference for mapping image regions to spatial expression, if source data and coordinates are obtained. | The article page does not establish that the raw image/expression files are openly downloadable under terms suitable for this project. Confirm data access, licensing, sample IDs, and image-to-assay coordinate transforms with the authors before use. Three human sections are far too few for broad validation. |

## Direct answer about the proposed functions

- **Read patient reports:** No suitable public set of de-identified narrative kidney
  pathology reports paired to the same digitized slides was confirmed. This needs
  separate report-text access, explicit de-identification/privacy approval,
  structured ground truth, and a separate NLP validation. The datasets above
  mostly provide scores or labels, not reports.
- **Grade fibrosis:** The multi-class paper provides external Banff/IFTA severity
  groups and the HPL/TRIDENT paper describes slide-level pathologist fibrosis
  quantification. Both require author/institution access; neither currently
  licenses the model to make patient diagnoses.
- **Identify kidney structures:** The multi-class paper is a promising source
  for glomeruli, tubules, arteries, and interstitium, subject to its data
  transfer agreements. The Kaggle challenge is narrower (glomeruli only).
- **Connect images to molecular data:** HuBMAP and the diabetic spatial atlas
  describe molecular/spatial resources, but usable validation requires proof
  that the tissue image, assay, metadata, and coordinate registration refer to
  the same specimen/section. A limited four-sample GEO demonstration now maps
  Visium spots to their supplied tissue images; it does not connect RENFAST
  images to molecular data or validate fibrosis. Do not join by disease name
  or patient alone.

## Recommended next steps

1. Request the multi-class annotated WSI dataset and its labels from the
   corresponding author; ask specifically about model training, patent filing,
   derived-weight use, and external sharing.
2. Separately request the HPL/TRIDENT slide-level fibrosis labels and WSI access
   if grade prediction is a priority.
3. Before any molecular linkage, obtain a sample-level manifest with section
   identifiers, assay files, histology image files, and registration transforms.
4. For report reading, first obtain a de-identified paired report corpus and
   expert-defined extraction targets; do not infer narrative labels from image
   masks.
5. Add no new cohort to model fitting until its terms and split are documented.
   Keep an external cohort fully held out for evaluation.
6. Review the GSE333529 data and article terms with the rights holder/legal
   adviser before using the data to train or support a patented/derived model or
   distributing any derived weights or outputs.

These are component-specific options, not a single ready-made dataset that
provides fibrosis masks, clinical reports, all anatomy, and registered
molecular data together.
