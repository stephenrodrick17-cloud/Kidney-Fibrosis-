# PLAUS availability audit

**EXPLORATORY, NOT CONFIRMATORY. UNVALIDATED MASKS.**

Audit timestamp: 2026-11-18T10:45:10.706+05:30

## Expression data inventory

The local Stage FA files contain 41 libraries across 40 participants. Saved spot-level tables contain the nine requested genes and the collagen module.

Full 10x filtered count matrices were found locally for 29 H5 files representing 28 participant directories. The separate H5 inventory found both libraries for participant `28-12265`, so there are 29 H5 files but 28 participant directories.

All 20 negative-control genes, all 4 low-fibrosis-direction genes and all 12 higher-fibrosis-direction genes listed in this stage were present in all 29 H5 files checked.

Stage 1d participants are not covered by a complete local full-matrix H5 inventory in the extracted directories inspected here. Their data availability is taken from the existing Stage FA target-gene spot table:

- COL1A1, COL1A2, COL3A1, FN1, TGFB1, CCN2, ACTA2, MMP2 and TIMP1 are represented in the Stage FA 1d spot evidence.
- Negative-control and expected-direction genes beyond the nine target genes are NOT AVAILABLE for those 12 Stage 1d participants from the extracted H5 inventory.
- Full count matrices for the 28 Stage 1 development participants are available locally and can support control-gene and expected-direction checks.

## Control-gene and panel tests

The following fixed 20-gene negative-control list can be tested on the 28 development participants with full matrices:

ACTB, GAPDH, RPL13A, RPLP0, RPS18, RPS27A, UBA52, TUBB, HPRT1, PPIA, B2M, TBP, PGK1, LDHA, SDHA, GUSB, HMBS, RPL19, RPL27, EEF1A1.

The low-direction panel can be tested on the full-matrix set:

SLC34A1, LRP2, UMOD, SLC12A1.

The high-direction panel can be tested on the full-matrix set:

COL4A1, COL5A1, COL6A1, FAP, POSTN, PDGFRB, VIM, PTPRC, C1QA, C1QB, C1QC, CD68.

The collagen module can be tested using the existing nine-gene spot table across 40 participants. Negative-control and expected-direction checks are limited to the 28 participants with complete local matrices. They cannot cover the 12 Stage 1d participants unless their full matrices are supplied or found locally outside the extracted H5 inventory.

## Existing saved masks and spot scores

Stage FA saved 41 binary NPZ masks and a 40-participant/41-library spot table. The saved table is sufficient for the primary collagen effect, stain-colour quartiles, leave-one-participant-out work and library-size thresholds.

Probability maps for thresholds 0.3 and 0.7 are NOT AVAILABLE. Only threshold 0.5 is represented by the saved masks. The 0.3 and 0.7 grid entries therefore cannot be recomputed from a probability field and will be marked NOT AVAILABLE.

Erosion/dilation and footprint variants require applying morphology or rescoring saved masks. These can be derived from the saved masks and will be reported separately. Tertile/quartile group variants can be recomputed from spot-level U-Net fibrosis fractions.

## No confirmatory status

All 40 participants were used before in Stage FA development or model evaluation. These checks cannot be confirmatory, and no claim of validation or mask accuracy is made.
