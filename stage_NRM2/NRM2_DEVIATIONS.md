# NRM2 Deviations and Execution Stops

**Date:** 2026-11-18
**Label:** EXPLORATORY, NOT CONFIRMATORY. NORMAL LABELS FROM SOURCE METADATA, NOT EXPERT-REVIEWED BY THE INVENTOR.

## Changes made

1. Removed TCGA-KIRC from the eligible plan. GDC/API metadata did not state trichrome, Masson, or Picrosirius staining.
2. Removed GDC `Solid Tissue Normal` and `Primary Tumor` from Stage NRM2. They do not meet the healthy/reference and fibrosis-comparison requirements.
3. Re-ran source review under the new stain, label-origin, licence, and no-access-request hard gates.
4. Marked HPA, KPMP, TCIA candidates, and unresolved repositories NOT SUITABLE or NOT ELIGIBLE.
5. Superseded the earlier TCGA-KIRC preregistration and replaced the report with a no-eligible-source stop.
6. Deleted the temporary NRM2 downloader script. No future downloader `.ps1` is to be used.
7. Started a repository-discovery-only milestone for the KPMP Atlas. It found 0 files in the exact open Healthy Reference + TRI filter and 0 in the exact open Pathology Descriptor Scoring filter. No file was downloaded.
8. Added v2 recovery evidence after the official 164-6 indexed record was supplied. Separate live filters still returned 0; 164-6 is retained as one indexed candidate only, not as live-UI-confirmed eligible data.
9. Added v3 recovery using the official repository search API discovered in the repository JavaScript. Confirmed 22 Healthy Reference TRI files/21 participants, 1315 open TRI files/666 participants, and one open descriptor workbook covering 426 participant IDs. Matched 5 healthy participants by exact redcap_id metadata.
10. Attempted to download only the open descriptor workbook. Curl stopped on untrusted TLS verification and browser download failed. No workbook or WSI was saved.
11. Added Stage 4 metadata-only pathology and reuse audit. It distinguishes transplant living-donor context, native kidney stone-donor context, descriptor-ID overlap, missing pathology values and unresolved reuse terms. No workbook or WSI download occurred.
12. Started Stage 5 and attempted to retrieve only the open KPMP descriptor workbook through the official repository endpoint. The browser download returned net::ERR_ABORTED and no workbook persisted; no workbook was inspected and no fibrosis labels were fabricated.

## Download and policy status

No data was downloaded. No sandbox or execution policy was changed. The earlier PowerShell refusal was not used to change policy or attempt an alternate download route.

No frozen-model inference, tile extraction, mask creation, training, overlay, or summary was performed.
