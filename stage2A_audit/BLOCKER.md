# Stage 2A Blocker — Gate 2A-1 / Data-Use Terms

**Date:** 2026-11-13  
**Status:** STOP. No segmentation preprocessing, training, or evaluation was run.

## Decision

Gate 2A-1 is not satisfied for a dataset that is currently usable under verified terms:

- RENFAST's official record describes manually annotated Masson's-trichrome fibrosis images and PAS vessel images, but the Mendeley licence field is blank and the local archive has no licence/terms file. Its reuse terms are unresolved. The fibrosis training directory also has 250 colliding/duplicate normalized basenames whose image contents have not been checked.
- The KPMP package READMEs describe network-generated segmentation outputs quality-controlled by a renal pathologist, not direct expert-drawn masks. Their IFTA metadata conflicts with the v2 README, and all 12 local packages annotate PAS slides rather than the participant's TRI slides. They are not verified expert ground truth for the requested segmentation validation.

Using RENFAST before its terms are verified would violate the project's licensing gate. Treating the KPMP network outputs as expert masks would misstate their documented provenance. No workaround or substitute labels were used.

## Options to unblock

1. Obtain written confirmation of RENFAST reuse and derivative-work terms from the rights holder/data repository; then re-evaluate the dataset usability and duplicate-name issue before training.
2. Obtain a small, explicitly expert-annotated KPMP subset with slide/stain/section linkage and permission to use it; register a protocol update before any analysis on that subset.
3. Identify another kidney histology dataset with explicit expert pixel masks and verified reuse terms, then preregister its inclusion before use.

Until one option is resolved, do not proceed to segmentation training or the dependent Stage 2 analyses. Stage 2A preregistration is frozen and has not been amended.
