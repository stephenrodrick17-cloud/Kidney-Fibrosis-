# NRM2 KPMP Acquisition Recovery Report v3

**Report date:** 2026-11-18
**Phase:** Indexed official repository inventory and descriptor identification
**Status:** INVENTORY RECOVERED; no WSI download; descriptor workbook not downloaded
**Label:** EXPLORATORY, NOT CONFIRMATORY. SOURCE-METADATA LABELS, NOT EXPERT-REVIEWED BY THE INVENTOR.

## Executive result

The official KPMP repository search API recovered the inventory and corrected the earlier browser-zero result.

- Healthy Reference + Light Microscopic Whole Slide Images + TRI stain + Open: **22 files**
- Unique Healthy Reference participants with these records: **21**
- Target: at least 15 unique Healthy Reference participants
- Result: **TARGET MET AT THE METADATA LEVEL**
- All Open TRI whole-slide images: **1315 files**
- Unique participants across all Open TRI records: **666**
- Open pathology descriptor workbook: **1 file**
- Participant IDs listed in the descriptor repository metadata: **426**
- Healthy Reference participants whose IDs overlap the descriptor ID list: **5**

This meets the healthy-participant file-count target, but it does not establish expert fibrosis values, because the descriptor workbook could not be downloaded and inspected.

## Healthy Reference inventory

The API returned 22 Healthy Reference TRI SVS records for 21 unique `redcap_id` values.

The indexed 164-6 record is confirmed by the repository search API:

- Participant ID: `164-6`
- File UUID: `90961d69-e963-402a-bee7-830733dde53e`
- Filename in repository: `90961d69-e963-402a-bee7-830733dde53e_S-2107-011580_TRI_1of1.svs`
- Protocol: `HRT Living Donor Protocol`
- Tissue source: `KPMP Opportunity Pool HRT Site`
- Sample type: `Transplant Pre-perfusion Biopsy`
- Enrollment category: `Healthy Reference`
- Workflow: `TRI stain`
- Experimental strategy: `Light Microscopic Whole Slide Images`
- Access: `open`
- Format: `svs`
- Repository size: `392552203` bytes

The 164-6 record therefore confirms one healthy-reference living-donor pre-perfusion biopsy in the open repository inventory.

The full 22-row Healthy Reference WSI inventory is in `NRM2_repository_inventory_v3.csv`.

## Descriptor workbook

The exact open descriptor resource was identified:

- Filename: `KPMP TIV Descriptor Scores 10.12.2026.xlsx`
- Full repository filename: `06f24766-f09c-4dea-a858-53b14965a562_KPMP TIV Descriptor Scores 10.12.2026.xlsx`
- File UUID: `06f24766-f09c-4dea-a858-53b14965a562`
- Package UUID: `a7eb92af-678b-413e-8f06-2948af1a2f10`
- Access: `open`
- Data category: `Pathology`
- Data type: `Pathology Study Data`
- Format: `xlsx`
- Size: `468577` bytes
- Experimental strategy: `Pathology Descriptor Scoring`
- Release: `Recently Released - Q3 2026`

The repository record lists 426 participant IDs. The relationship key is the repository `redcap_id` field, the same ID field used in WSI metadata. No approximate name matching is needed.

Healthy participant IDs overlapping the descriptor ID list:

- `164-8`
- `164-12`
- `164-17`
- `164-21`
- `164-22`

Participant `164-6` does not appear in the descriptor participant-ID list returned by the repository metadata.

## Fibrosis percentages and grades

The descriptor record confirms that participant IDs are associated with the open descriptor workbook, but the workbook itself was not downloaded or inspected.

Therefore:

- Fibrosis percentage values: **NOT AVAILABLE**
- IFTA or pathology grades: **NOT AVAILABLE**
- Region-level values: **NOT AVAILABLE**
- Pixel-level fibrosis masks: **NOT AVAILABLE**
- Independent second-pathologist scores: **NOT AVAILABLE**

It is not valid to claim that the 5 overlapping healthy participants have normal, minimal, mild, moderate, or severe fibrosis grades until the workbook columns are inspected.

## All open TRI records

The repository search API returned 1315 open TRI WSI files for 666 unique participants.

Enrollment-category counts:

| Enrollment category | Files | Unique participants |
|---|---:|---:|
| AKI | 178 | 93 |
| CKD | 995 | 493 |
| DM-R | 120 | 59 |
| Healthy Reference | 22 | 21 |

These counts cover open TRI WSI records. They do not establish fibrosis severity. The descriptor workbook must be inspected and matched by participant ID before assigning fibrosis percentage or grade bands.

## Workbook download attempt

A download URL was derived only from the official repository JavaScript download pattern:

`https://atlas.kpmp.org/api/v1/file/download/a7eb92af-678b-413e-8f06-2948af1a2f10/06f24766-f09c-4dea-a858-53b14965a562_KPMP TIV Descriptor Scores 10.12.2026.xlsx`

The `curl.exe` attempt stopped at certificate verification and did not bypass TLS. The browser direct-download attempt also failed. No descriptor workbook was downloaded or saved.

No WSI was downloaded.

## Why previous zero results were wrong

The previous report relied on live browser filtering and incorrectly treated live UI zero responses and HTTP 400 responses as definitive dataset absence. The repository has an official public search API embedded in the repository application. It returned:

- 22 healthy TRI records
- 1315 open TRI records
- 1 open descriptor workbook

An indexed result, search API result, and downloaded file are separate states. The 164-6 and descriptor records are confirmed by repository metadata/API search, but the descriptor workbook and WSI files are not downloaded.

## CSV export mechanism

The repository JavaScript uses a public search API endpoint:

`https://atlas.kpmp.org/spatial-viewer/search/api/as/v1/engines/atlas-repository/search.json`

The JavaScript also uses the official download endpoint:

`https://atlas.kpmp.org/api/v1/file/download/{package_id}/{file_name}`

The CSV control is generated by the repository application. Its live button was not relied on for recovery. The search API was used with the public search key embedded in the official application. This did not bypass authentication or access controls.

## Permissions and access

The repository labels these records `open`. Open means direct repository download according to official documentation. It does not establish unrestricted commercial or patent reuse. Exact licence terms and redistribution restrictions remain NOT VERIFIED.

No controlled-access DUA was requested or signed.

## Objective assessment

Does KPMP currently provide at least 15 unique healthy-reference participants with TRI images?

**Yes, at metadata level: 21 unique participants and 22 open SVS records.**

Does the current evidence establish matched pathology percentages or grades?

**No. Only 5 healthy participants overlap the descriptor participant-ID list. The workbook was not downloaded, so actual values remain NOT AVAILABLE.**

Can the 1315 open TRI records support a fibrotic comparison cohort?

**At metadata level, yes: 645 unique participants outside Healthy Reference are present across AKI, CKD, and DM-R. The available pathology grades and fibrosis percentages remain unverified without the workbook.**

## Stop decision

No WSI image was downloaded.
No descriptor workbook was saved.
No image processing, tile extraction, or model run occurred.
No training or fine-tuning occurred.

Before future download, exact commercial/research licence terms and workbook values must be verified.
