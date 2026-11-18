# GENE2 Data-Use Audit

**EXPLORATORY, NOT CONFIRMATORY. ZERO UNSEEN participants are locally available; no participant may serve as a new confirmatory set.**

## Result

For this audit, “locally available” means participant-level spatial expression data present in the local `D:\patent\data\` participant folders or the Stage 1d confirmation inputs. The 28 local development folders match the Stage 1 fold and library manifests; the Stage 1d confirmation manifest contains 12 additional participants. The Stage 1 and Stage 1d reports confirm that these two sets do not overlap. Every one of these 40 participants has already been used in prior model development or evaluation, so every one is DEVELOPMENT ONLY for Stage G2. None may be treated as a new confirmatory participant under the requested rule.

The spot identity key is always `(participant, library, barcode)`. Participant 28-12265 has two libraries; both must remain together within a participant group and may not be split across folds.

## Locally available participant inventory

| Participant | Prior-use label for Stage G2 | Reason |
|---|---|---|
| 27-10157 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 27-10201 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 27-10206 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 27-10207 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 27-10228 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 27-10262 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 27-10371 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 28-12265 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in Stage 1; has two libraries, grouped under the participant key. |
| 28-12557 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 28-12626 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 29-10394 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 29-10400 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 29-10422 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 29-10439 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 30-10125 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 30-11084 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 30-11141 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 30-11192 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 30-11197 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 31-10013 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 31-10078 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 31-10340 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 32-10205 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 33-10005 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 34-11066 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 934-10003 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 934-10007 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 936-10217 | Used in Stage 1 development — DEVELOPMENT ONLY | Included in the Stage 1 28-participant development cohort. |
| 164-10 | Used in Stage 1d confirmation — DEVELOPMENT ONLY | Stage 1d participant-level metrics evaluated the frozen model on this participant. |
| 164-22 | Used in Stage 1d confirmation — DEVELOPMENT ONLY | Stage 1d participant-level metrics evaluated the frozen model on this participant. |
| 27-10123 | Used in Stage 1d confirmation — DEVELOPMENT ONLY | Stage 1d participant-level metrics evaluated the frozen model on this participant. |
| 27-10166 | Used in Stage 1d confirmation — DEVELOPMENT ONLY | Stage 1d participant-level metrics evaluated the frozen model on this participant. |
| 27-10229 | Used in Stage 1d confirmation — DEVELOPMENT ONLY | Stage 1d participant-level metrics evaluated the frozen model on this participant. |
| 29-10277 | Used in Stage 1d confirmation — DEVELOPMENT ONLY | Stage 1d participant-level metrics evaluated the frozen model on this participant. |
| 29-10282 | Used in Stage 1d confirmation — DEVELOPMENT ONLY | Stage 1d participant-level metrics evaluated the frozen model on this participant. |
| 30-11081 | Used in Stage 1d confirmation — DEVELOPMENT ONLY | Stage 1d participant-level metrics evaluated the frozen model on this participant. |
| 34-11042 | Used in Stage 1d confirmation — DEVELOPMENT ONLY | Stage 1d participant-level metrics evaluated the frozen model on this participant. |
| 34-11048 | Used in Stage 1d confirmation — DEVELOPMENT ONLY | Stage 1d participant-level metrics evaluated the frozen model on this participant. |
| 933-10271 | Used in Stage 1d confirmation — DEVELOPMENT ONLY | Stage 1d participant-level metrics evaluated the frozen model on this participant. |
| 933-11258 | Used in Stage 1d confirmation — DEVELOPMENT ONLY | Stage 1d participant-level metrics evaluated the frozen model on this participant. |

UNSEEN participants: **0**. Eligible new confirmatory participants: **none**.

## Prior-use and inventory evidence

- The directory listing of `D:\patent\data\` contains the 28 Stage 1 expression-cohort participant folders, matching `D:\patent\stage1_expression\fold_assignments.csv` and `D:\patent\stage1_expression\library_key_map.csv`.
- `D:\patent\inventory.csv` is a separate pathology whole-slide image inventory; it was not used to determine the spatial-expression participant count.
- `D:\patent\stage1_expression\STAGE1_REPORT.md` records 28 participants, 29 libraries, and 25,104 spots used for Stage 1 development; its fold and participant outputs include the development participants above.
- `D:\patent\stage1d_confirm\STAGE1D_REPORT.md` records the fixed 12-participant confirmation cohort, participant-level model comparisons, and no participant overlap with the original 28.
- `D:\patent\stage1d_confirm\data_manifest.csv` lists the locally retained Stage 1d inputs for those 12 participants.
- `D:\patent\stage1c_confirm\STAGE1C_REPORT.md` identifies the same 12 additional participants as open Visium catalogue candidates; Stage 1d subsequently used them, so they are not unseen now.

This conclusion is limited to the local expression/spatial datasets inventoried in those files. No data were downloaded, no model was loaded or run, and no spot-level data were used to determine the participant census. Later, while drafting the preregistration, a short excerpt of the existing Stage 1 keyed target table was viewed only to confirm its schema; no image pixels or Phase B2 materials were opened.

**Required consequence:** GENE2 Steps 1–3 can only be an **EXPLORATORY, NOT CONFIRMATORY** design on the already-used participants. No result from those participants can be presented as a new confirmatory evaluation.

