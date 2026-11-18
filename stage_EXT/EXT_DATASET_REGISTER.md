# EXT dataset search and licence register

Search and access-date timestamp: 2026-11-18T10:25:47.927+05:30

No dataset has been downloaded. Free-space and download-size checks are NOT APPLICABLE because no candidate passed the licence and data-use conditions.

## Search method

I searched public web repositories and dataset indexes for kidney histology, renal fibrosis, interstitial fibrosis, trichrome, Sirius red, Masson trichrome, Picrosirius red, expert pixel masks and expert area percentages.

Search sources included Zenodo, Dryad, Kaggle, GitHub repository search and public licence pages. The search found no candidate that both:

1. has expert interstitial-fibrosis or collagen-fibrosis masks or scores,
2. gives a clear public licence that allows research and analysis,
3. has no sign-up, personal registration, institutional approval or access request requirement,
4. includes usable physical-scale or can be excluded cleanly if scale is missing, and
5. avoids a clear stain or label mismatch.

## Candidates

| Candidate | URL | Source institution | Species | Stain | Scanner or magnification | MPP | Images/slides | Label type | Fibrosis range | Licence / terms text checked | Access requirements | Size | Verdict and exact reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Kidney glomeruli-ROIs extracted from histological slides stained with HE or PAS | https://zenodo.org/records/4299694 | Warsaw University of Technology; University of Barcelona; Cedars-Sinai Medical Center | Human kidney | HE or PAS | Pannoramic 250 Flash II, Hamamatsu NanoZoomer S60, Aperio AT Turbo; x10 | ~10 um/pixel | 78 ROIs from 20 WSIs | Pixel masks for normal and sclerosed glomeruli | NOT AVAILABLE | Zenodo record page lists the dataset as open and associated GitHub documentation states “CC BY 4.0”. CC BY 4.0 text includes: “You are free to: Share — copy and redistribute the material in any medium or format; Adapt — remix, transform, and build upon the material for any purpose, even commercially.” | Public download, no shown signed DUA or institutional approval. A scale mismatch remains: ~10 um/pixel versus 4.1 um/pixel. | 3.6 GB | BLOCKED. It is expert-labelled kidney tissue, but the labels mark normal versus sclerosed glomeruli, not interstitial fibrosis or collagen area. This is an annotation mismatch, not fibrosis evidence. The stated ~10 um/pixel scale could not be rescaled without an exact per-image rescale and the 4.1 um/pixel mismatch is outside the registered model's stated scale range. |
| RNA m6A methylation in unilateral ureteral ligations model | https://datadryad.org/dataset/doi:10.5061/dryad.r2280gbbz | Zhongshan Hospital | Mouse | The listed files are molecular data and distribution images; histology stain and MPP are NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | 5.01 MB; no image/slide count for a histology mask set | CSV and distribution plots; no fibrosis pixel masks or expert fibrosis scores | NOT AVAILABLE | Zenodo record is marked `cc-zero`; the Dryad record is the published dataset page. | Public download; no shown access request or DUA | 5.01 MB | BLOCKED. It does not provide a kidney histology mask or expert fibrosis percentage. Licence appears eligible, but the required image-and-expert-label data are absent. |
| InterstitialFibrosis GitHub implementation | https://github.com/patologiivest/InterstitialFibrosis | `patologiivest`; source paper institution NOT AVAILABLE | NOT AVAILABLE | Sirius red | NOT AVAILABLE | NOT AVAILABLE | No public image-and-annotation set listed in the repository; README says users supply Images and Annotations folders | Code for fibrosis masks and reports; no downloadable expert-labelled public test set in the repository | NOT AVAILABLE | README states: “This work is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.” Repository license: CC BY-NC-SA 4.0. | Code is public. Data are not included or a public release path was not shown. | NOT AVAILABLE | BLOCKED. It is not a public external validation set and no licence for independent external images was established. Also CC BY-NC-SA may not meet the requested research-only commercial-neutral condition because the prompt did not permit non-commercial assets or unclear licence scope. |
| Histology (PAS-HE-IHC) Images - FTU Segmentation | https://www.kaggle.com/datasets/yashvrdnjain/histology-pas-he-ihc-images-ftu-segmentation | Kaggle uploader; source institution NOT AVAILABLE | Likely kidney and other tissues; exact species NOT AVAILABLE | PAS, H&E, IHC | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | Functional tissue unit segmentation | NOT AVAILABLE | Kaggle API shows licence `MIT` | Public Kaggle dataset; no shown DUA. Source provenance and exact licence text need independent verification. | 12.18 GB | UNRESOLVED. Licence and public access appear plausible, but the public metadata does not establish expert interstitial-fibrosis labels, kidney-only scope, stain, scanner or MPP. Do not download until those facts are verified. It is under the 30 GB guard but has no registered fibrosis endpoint. |
| HuBMAP glomeruli tiles and mosaics | https://www.kaggle.com/datasets/anadelta/hubmap-glomeruli-tiles | HuBMAP-derived third-party Kaggle mirror | Human kidney | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | 1.14 GB | Glomerulus segmentation tiles | NOT AVAILABLE | Kaggle API licence: `Unknown` | Public page; no established licence text | 1.14 GB | BLOCKED. Licence is UNKNOWN and the labels are glomeruli, not interstitial fibrosis. |
| Kidney glomeruli segmentation practice dataset | https://www.kaggle.com/datasets/kairabnextlevel/kidney-dataset | Kaggle uploader; source institution NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | 1.17 GB | Glomerulus segmentation practice | NOT AVAILABLE | Kaggle API licence: `Unknown` | Public page; no established licence text | 1.17 GB | BLOCKED. Licence is UNKNOWN and fibrosis annotations are absent. |

## Licence conclusion

The candidate that is closest to kidney external histology, the 4299694 glomerulus-ROIs set, is public and appears to use CC BY 4.0, but it does not contain interstitial-fibrosis or collagen masks and it has a stated ~10 um/pixel scale. It is therefore not an eligible fibrosis external-validation set.

The Dryad mouse data is CC0 in Zenodo metadata, but it lacks expert histology fibrosis masks or fibrosis scores.

The third-party Sirius-red repository is CC BY-NC-SA 4.0 and contains no public expert-labelled external-validation dataset.

No candidate passed all four download conditions at this stage. Eligible count: **0**.

## Status

STOP at Step 0. No preregistration run, download, model run or fine-tuning plan has started. The exact decisions needed after a broader data search or a user-provided eligible dataset are:

1. approve a specific public, clearly licensed kidney fibrosis dataset,
2. provide a source with expert pixel masks or expert area percentage/IFTA scores,
3. provide stated micrometres per pixel or approve excluding images without exact scale,
4. confirm that the dataset has no signed access or institutional approval requirement.
