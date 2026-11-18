# NRM2 Report

**Status:** STOPPED — no eligible source found. No download or model run occurred.
**Date:** 2026-11-18
**Label:** EXPLORATORY, NOT CONFIRMATORY. NORMAL LABELS FROM SOURCE METADATA, NOT EXPERT-REVIEWED BY THE INVENTOR.

## Step 0 result

The hard re-run of Step 0 found **NO source that met all requirements**:

- stain explicitly stated as trichrome, Masson, or Picrosirius;
- tissue explicitly labelled normal, healthy, or reference, with the label origin stated;
- open licence or terms readable and quoted verbatim;
- no access request, registration, agreement, institutional approval, or payment.

TCGA-KIRC was removed. GDC did not document an acceptable stain for TCGA-KIRC slide metadata, and `Solid Tissue Normal` came from a kidney-cancer cohort rather than a healthy/reference population. `Primary Tumor` was not used as a comparison group.

HPA normal kidney fails the stain and origin gates: the source says the images use highly multiplexed antibody staining and does not establish a healthy-donor label origin. KPMP requires controlled-data approval and no qualifying public normal/reference cohort was identified. TCIA candidates are tumour collections or lack the qualifying normal cohort.

## Nothing was downloaded

No slide file, image, archive, licence, metadata dataset, or model weight was downloaded. No curl or Python download was used for data.

No frozen-model inference occurred. No normal-only model was trained. No NRM2 result, AUC, over-calling result, overlay, or reading range is available.

## What is needed

A public dataset or archive must establish all four conditions before it can proceed:

1. acceptable stain;
2. explicit normal/healthy/reference label and label origin;
3. readable open terms;
4. no registration or agreement.

No near match was substituted.

## KPMP repository milestone

The repository-discovery milestone is recorded in [NRM2_acquisition_report.md](D:/patent/stage_NRM2/NRM2_acquisition_report.md) and [NRM2_repository_inventory.csv](D:/patent/stage_NRM2/NRM2_repository_inventory.csv).

The exact visible open Healthy Reference + TRI filter returned 0 files. The exact visible open Pathology Descriptor Scoring filter returned 0 files, and `KPMP TIV Descriptor Scores 10.12.2026.xlsx` was not found. No participant inventory or download approval can proceed from this result.
