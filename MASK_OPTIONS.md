# Segmentation Ground-Truth Options

Planning comparison only. No segmentation work, annotation, mask processing, or model training has started. Effort and cost ranges are rough planning estimates, not quotes or an approved scope.

| Option | Effort | Cost basis | Claim strength and limits |
|---|---|---|---|
| **RENFAST, only after reuse terms are cleared** | About 2–4 engineering weeks to resolve the 250 colliding fibrosis-train basenames, verify image/mask pairing and raster metadata, and run a stain/domain suitability review. | Licence/reuse fee is unknown until terms are confirmed. Budget engineering time plus local compute/storage; do not assume the dataset is free to reuse. | **Moderate for fibrosis segmentation on the RENFAST Masson's-trichrome domain** if its manual masks and pairings are verified. **Weak for transfer claims to KPMP H&E**; RENFAST has no KPMP molecular linkage and its trichrome protocol is not established as interchangeable with KPMP TRI. |
| **KPMP silver masks** | About 2–4 weeks to reconcile the IFTA README/metadata contradiction, verify model provenance and slide/section linkage, and arrange independent pathologist review. | The files are already local and catalogued open, but reuse terms are not confirmed. Main cost is pathologist/researcher review time; cash cost depends on local rates. | **Low; exploratory/silver-label evaluation only.** Current files are documented as network-generated masks with pathologist QC, not direct expert masks. They cannot establish independent segmentation accuracy and the PAS-to-TRI/H&E alignment is not established. |
| **Small expert-annotated KPMP subset** | Roughly 4–8 weeks for scope/label protocol, pathologist annotation, adjudication, linkage/QC, and dataset freeze. A sample size and classes must be agreed before work starts. | Highest direct cost. For budgeting, estimate annotator hours × the institution's pathology rate, plus engineering/adjudication time; no local rate or vendor quote is available, so a defensible dollar total cannot yet be stated. | **Strongest ground-truth claim for the exact annotated slides, stains, classes, and annotation protocol.** Generalization remains limited by subset size, stain, and sampling; it would not by itself validate transfer across stains or the full KPMP cohort. |

## Recommendation

First request written RENFAST reuse/derivative-work terms. If those terms are not suitable or pairing/provenance remains uncertain, a small expert-annotated KPMP subset provides the clearest validation evidence. KPMP silver masks may support exploratory development, but should not be described as independent expert validation.

This file is an options comparison only; it does not change the closed Stage 2A blocker or authorize segmentation activity.
