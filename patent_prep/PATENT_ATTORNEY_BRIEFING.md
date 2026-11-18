# Briefing for Patent Attorney

Draft factual summary for discussion. This is not legal advice, a patentability opinion, or claim language.

## What the pipeline does

The saved pipeline takes RGB kidney-tissue tiles and uses a frozen U-Net to produce a binary fibrosis mask. A fixed probability threshold turns pixel probabilities into mask pixels. Phase A compared these masks with RENFAST expert-made masks. Phase B applied the frozen model to local KPMP trichrome regions and reported descriptive overlays and area fractions, but there was no aligned reference to judge correctness.

## Strongest evidence

On the RENFAST test split, the U-Net had family-macro Dice `0.9119221709930561`; the colour-threshold baseline had `0.824923731160496`. The paired family-macro Dice difference was `0.08699843983256006`, with family-bootstrap 95% CI `[0.07315876056020197, 0.09962074456605957]`. The dataset reference was RENFAST's expert-made masks. The 10 test groups are filename families, not verified patients or slides, so the results do not establish patient-level or clinical performance.

Phase C found that the registered robustness rule failed for the strongest paired brightness perturbation and two individual directions. The uncertainty/error association was not established. The DeepLab comparison was blocked by the registered runtime cap.

## Exclusions and open questions

- No external validation against a new annotated cohort was completed.
- No KPMP accuracy against a reference mask was measured.
- No molecular prediction, molecular-image fusion, or registration result is supported by the permitted Phase A–C record set. User-provided Stage 1/1b/1d failure labels need their original source report.
- The exact U-Net layer/channel specification, parameter count, frozen Phase A training metadata, and exact augmentation parameters are missing from the permitted files.
- RENFAST permission wording and KPMP data-use terms are unresolved.
- The precise source for the claimed expert-mask mismatch on KPMP was not found in the Phase B report.

## Package files

| File | Purpose |
|---|---|
| `PATENT_EVIDENCE_REGISTER.md` | Recorded metric values and CIs, family-level results, and what they do not establish. |
| `PATENT_METHOD_DESCRIPTION.md` | Plain-language processing steps with source status and missing technical details. |
| `PATENT_CLAIM_SUPPORT_MAP.md` | Evidence-supported candidate topics and explicitly unsupported topics; no drafted claims. |
| `PATENT_INVENTIVE_STEP_QUESTIONS.md` | Technical-origin questions for the inventor; does not decide inventiveness. |
| `PATENT_DISCLOSURE_CHECKLIST.md` | Recorded and missing AI disclosure details. |
| `PATENT_PERMISSIONS_REGISTER.md` | Data, software, model, and permission records with verbatim paste-in blocks. |
| `PATENT_LIMITATIONS.md` | Limitations and failure outcomes from the saved reports. |
| `PATENT_ATTORNEY_BRIEFING.md` | One-page plain-language overview and questions for counsel. |
| `PATENT_VERIFICATION.md` | Source cross-check, unresolved-item list, and hashes of reviewed sources. |

## Questions to ask counsel

- How should Indian Patents Act Section 3(k), including the computer-programme-per-se/algorithm exclusion and any required technical effect, be assessed for these specific facts?
- Which version of the 2025 CRI Guidelines applies, and how should counsel evaluate this implementation under those guidelines?
- What technical details are required for sufficiency of disclosure for this AI-based system, especially where exact architecture and training records are not in the saved package?
- Who qualifies as an inventor where AI tools assisted implementation, and how should the human contributions be documented? How is this different from an AI-generated contribution?
- What data, annotation, model-weight, software, and disclosure permissions are needed before any filing or public release?
- Should any excluded or unvalidated topic be left out entirely, or may it be described only as future work? This is a question for the attorney.

No conclusion is offered about Section 3(k), the CRI Guidelines, inventorship, sufficiency, novelty, inventive step, or patentability.
