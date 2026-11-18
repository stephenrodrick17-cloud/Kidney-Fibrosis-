# NRM2 KPMP Acquisition Recovery Report v2

**Report date:** 2026-11-18
**Phase:** Repository discovery and filter verification
**Status:** STOPPED BEFORE DOWNLOAD
**Label:** EXPLORATORY, NOT CONFIRMATORY. SOURCE-METADATA LABELS, NOT EXPERT-REVIEWED BY THE INVENTOR.

## Executive result

The repository recovery did not accept the earlier zero-result report as sufficient evidence.

The supplied official indexed URL identifies a candidate record:

- Participant ID: `164-6`
- Filename: `S-2107-011580_TRI_1of1.svs`
- Workflow: `TRI stain`
- Experimental strategy: `Light Microscopic Whole Slide Images`
- Access: `Open`
- Size: `393 MB`

The live repository interface did **not** return this record when filtered by participant ID `164-6`, and it returned 0 rows for several official field combinations. Therefore:

- Live-UI confirmed eligible Healthy Reference + TRI + Open files: **0**
- Live-UI confirmed unique eligible participants: **0**
- Officially indexed candidate files: **1**
- Officially indexed candidate unique participants: **1**
- Live-UI confirmed descriptor records: **0**
- Live-UI confirmed matched WSI-descriptor participants: **0**

The candidate 164-6 result is recorded as indexed/secondary evidence, not as a live-UI-confirmed download candidate.

## Why the earlier zero result differed

The earlier report used a broader unverified filter interpretation and a single combined query. It added the workflow as `workflow`, which can differ from the current `Workflow Type / Panel` control. It then treated the live UI count as definitive.

The new recovery used the official interface labels and URL field identifiers:

- `experimental_strategy`
- `enrollment_category`
- `access`
- `workflow_type_panel`
- `data_category`
- `data_type`

These identifiers are consistent with the repository documentation and with the indexed URL supplied for this task. The UI labels remain the source of truth for values.

Even with the corrected identifiers, the live UI returned 0 for the 164-6 participant query and for the relevant combined filters. That conflict remains unresolved rather than being replaced by a zero result.

## Separate filter searches

| Search | Filters | Live UI result |
|---|---|---|
| A | Healthy Reference + Open | 0 files |
| B | Healthy Reference + Light Microscopic Whole Slide Images | 0 files |
| C | Healthy Reference + TRI stain | 0 files |
| D | Light Microscopic Whole Slide Images + TRI stain + Open | 0 files; one attempt also reported browser console HTTP 400 |
| E | Healthy Reference + Light Microscopic Whole Slide Images + TRI stain + Open | 0 files |
| F | Pathology Descriptor Scoring + Open | 0 files |
| G | All Open TRI whole-slide images | 0 files; one attempt also reported browser console HTTP 400 |

The live UI also returned 0 for participant ID `164-6`.

## 164-6 candidate

The supplied official indexed URL is evidence that a repository record has been indexed with:

- Participant ID `164-6`
- Filename `S-2107-011580_TRI_1of1.svs`
- Workflow `TRI stain`
- Experimental strategy `Light Microscopic Whole Slide Images`
- Access `Open`
- Size `393 MB`

The indexed URL applies:

- `experimental_strategy = Light Microscopic Whole Slide Images`
- `enrollment_category = Healthy Reference`
- `access = open`

Therefore, 164-6 is an **indexed Healthy Reference/TRI/Open candidate**. It is not counted as live-UI confirmed until the live repository returns the row or a complete official CSV export contains it.

No File UUID, Data Category, DOI, or Pixel Resolution metadata was exposed by the live query. These fields remain NOT AVAILABLE.

## Confirmed repository records

Confirmed from the live interface:

- The interface has a data table and CSV control.
- The control is visible for filtered results.
- Live filtered searches listed above returned 0 records.
- No row could be exported as a complete CSV.
- No slide metadata row was saved.

Confirmed only from the supplied official indexed result:

- 164-6
- S-2107-011580_TRI_1of1.svs
- TRI stain
- 393 MB
- Open
- Light Microscopic Whole Slide Images
- Healthy Reference by the supplied indexed filter

## CSV export attempt

The repository documentation confirms filtered records can be exported by its CSV control. The live UI displayed a CSV button for the filtered result, but clicking it did not complete; the element remained unstable and one backend request returned HTTP 400. No CSV was downloaded and no pagination or row limit could be verified.

No complete export was available to inspect for participant-level inventory or duplicate slides.

## Pathology descriptors

The official available-data page lists Pathology Descriptor Scoring as Open. The live repository filter for:

- Experimental Strategy `Pathology Descriptor Scoring`
- Access `open`

returned 0 files.

The exact 10.12.2026 filename was not found. No descriptor workbook or package was confirmed. No participant-to-WSI descriptor match was possible.

## Permissions

The repository documentation states open files may be downloaded directly; controlled files require a DUA. It does not establish unrestricted commercial or patent reuse from the open label alone.

No specific licence or permitted commercial-use wording was verified for 164-6 or descriptor data. No controlled-access registration or request was made.

## Stop decision

No slides were downloaded, no data was processed, no model was run, and no sandbox policy changed.

Exact counts at this milestone:

- Live-UI confirmed eligible unique participants: **0**
- Live-UI confirmed eligible files: **0**
- Indexed candidate unique participants: **1**
- Indexed candidate files: **1**
- Live-UI confirmed descriptor records: **0**
- Live-UI confirmed matched WSI-descriptor participants: **0**

The dataset is not declared unavailable beyond the live evidence. The official indexed record is a conflict that requires a successful live CSV export or a corrected repository index before download approval.
