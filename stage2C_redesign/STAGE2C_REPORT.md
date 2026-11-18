# Stage 2C Report

**Report date:** 2026-11-13  
**Status:** BLOCKED at Gate 2C before any development-data modeling or trial evaluation. No validation data were opened or downloaded.

## What was done

- Wrote the timestamped preregistration `PREREG_2C.md` before any Stage 2C data inspection or modeling.
- Locked the preregistration and recorded its SHA-256 in `D:\patent\LAB_NOTEBOOK.md`.
- Documented the blocker in `BLOCKER.md` because the planned encoder (Phikon-v2) is publicly listed under an Owkin non-commercial licence and the project’s authorization status was not confirmed.
- Left `TRIAL_LEDGER.csv` as header-only; no model fit, region construction, feature extraction, permutation loop, or outer validation was executed.
- Kept Stage 2B collagen features unavailable and excluded from the preregistration as required.

## Findings and gate decision

- Stage 2A was already closed at Gate 2A-1 due to a lack of verified expert-mask provenance and unresolved dataset-use terms.
- The Stage 2C preregistration explicitly required a pathology foundation model and selected Phikon-v2 as the only approved encoder.
- The official Phikon-v2 model card and public listing state an Owkin non-commercial licence. No user-side acceptance, project-specific commercial/non-commercial clearance, or licence review was completed.
- Because Phikon-v2 is gated by a licensing/authorization condition that the assistant cannot resolve without explicit user/project confirmation, the protocol required a stop under P8 before any download or model use.
- The gate was triggered before any Stage 2C analysis. The decision is therefore: STOP at Gate 2C.

## Why this is not a model result

- No development table was constructed.
- No tissue tiles were extracted.
- No region target definitions were materialized.
- No folds were assigned or checked.
- No image embeddings were generated.
- No hyperparameter grid was run.
- No permutation control was executed.
- No success decision was computed.

This is a procedural stop, not a scientific result. It does not count as evidence of a model effect, no-effect, or failure to meet the Phase 7 redesign rule.

## Deviations and skipped items (copied from `D:\patent\DEVIATIONS.md`)

### D-005 — Segmentation training skipped at Gate 2A-1 / licence blocker

- **Skipped:** No preprocessing, training, or evaluation was run. RENFAST's Mendeley licence field is blank, and the KPMP segmentation packages document network-generated outputs with pathologist QC rather than direct expert masks. The KPMP IFTA provenance is also contradictory.
- **Reason:** No usable dataset met both expert-source provenance and verified-use-terms requirements.
- **Outcome:** Stage 2A stopped at the data audit; this was not replaced with a surrogate dataset or alternative mask source.

### D-006 — Stage 2C / 2D analysis held before data access

- **Skipped:** No development-table construction, image embedding extraction, model fitting, permutation test, or power analysis has been run. `TRIAL_LEDGER.csv` contains only its header.
- **Reason:** The locked Stage 2C preregistration selects Phikon-v2; its official model card states an Owkin non-commercial licence. Project eligibility/authorization is unconfirmed. P8 requires stopping when licence acceptance cannot be completed by the assistant.
- **Outcome:** No model weights or participant data were downloaded for this stage; no validation data were accessed. `BLOCKER.md` records the issue. The Stage 2C preregistration was not changed.

## What could not be verified

- Whether the project is non-commercial and permitted to use the Owkin non-commercial Phikon-v2 licence.
- Whether any user-side licence acceptance or institutional approval is required.
- Whether a compliant path exists to continue with alternative encoders under a new preregistration.
- Any downstream Stage 2D power analysis, because the Stage 2C gate did not pass and no modeling question was evaluable.

## Artifact SHA-256

| Artifact | SHA-256 |
|---|---|
| `PREREG_2C.md` | `aefd7733dc08f7c308f35912eac49f8b69e6ee5d6f48f559fc83e6b2c49dc8ea` |
| `BLOCKER.md` | `c4921d1e5a0f60431d14bf4e3d9e69ec85edb2ce7dd5e7032c253f131682c879` |
| `TRIAL_LEDGER.csv` | `046c77c00c00787f8856ef78925984a77c5784992d52965c641610f02577a15b` |
| `D:\patent\DEVIATIONS.md` | `a70a51d275c0c5e43a5c0906c5e2b3e84195cec8bbfddbb13414ea76c189a163` |

The report checksum is recorded in `D:\patent\LAB_NOTEBOOK.md` after file finalization.

## Next step recommendation

1. Confirm the project’s non-commercial status and whether the Owkin non-commercial licence is acceptable for the planned use.
2. If clearance is approved, record the exact model-card reference and checkpoint SHA-256, then proceed only with a re-registered and re-hashed Stage 2C specification.
3. If clearance is not approved, keep the project in blocker mode and select a non-gated pathology encoder or a different ground-truth route only after a new preregistration is written and hashed.
