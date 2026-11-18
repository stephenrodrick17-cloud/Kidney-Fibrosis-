# Stage 2 Summary

**Report date:** 2026-11-13  
**Scope:** Stage 2A and Stage 2C/2D gate status under the project’s preregistration and blocker rules.

## Status table

| Stage | Result | Gate status | Notes |
|---|---|---|---|
| Stage 2A | Blocked | Gate 2A-1 failed | No expert-mask provenance and unresolved licence/terms for the available datasets. |
| Stage 2B | Not started | Not reached | Collagen feature explicitly unavailable because Stage 2A blocked. |
| Stage 2C | Blocked | Gate 2C failed before analysis | Phikon-v2 was selected in the preregistration, but the public licence status was not cleared and no model download or analysis was permitted. |
| Stage 2D | Not run | Not reached | Power analysis requires a non-blocked Stage 2C path; no validation data were involved. |
| Stage 2E | Not reached | Not reached | Validation cohort remains unopened and uncatalogued because the earlier gates did not pass. |

## Deviations and blocker events

- D-005: Stage 2A was stopped because no dataset satisfied both expert-mask provenance and verified use terms.
- D-006: Stage 2C was stopped before modeling because Phikon-v2 is under an Owkin non-commercial licence and project eligibility was not confirmed.
- The corresponding preregistrations were written before any result-generating work and remain read-only.
- `DEVIATIONS.md` is the authoritative ledger of exceptions, retries, omissions, and blocker events.

## Evidence statement

At this point, the project has generated a blocker chain rather than a model result:

- There is no verified segmentation ground-truth route for the requested collagen/compartment task.
- There is no cleared licence path for the selected pathology foundation model.
- There is no evidence from development-data modeling because the Stage 2C gate was never passed.

This means the current evidence does not support any claim of predictive performance, valid image-molecular matching, or final model readiness. The project is therefore in an explicit blocker state, not a “negative result” state. The remaining path is to resolve the licence and ground-truth provenance questions and then re-register an approved route before any further modeling.

## What remains open

- Confirm whether the project can use the Owkin non-commercial licence for Phikon-v2.
- Resolve the segmentation ground-truth option among RENFAST, KPMP silver masks, or a small expert-annotated subset.
- Re-register any resumed Stage 2C path before any download, model extraction, or evaluation.
- Keep all outcomes, hashes, and blocker notes in `LAB_NOTEBOOK.md` and `DEVIATIONS.md`.
