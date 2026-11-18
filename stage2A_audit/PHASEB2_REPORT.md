# Phase B2 Report — Blinded Annotation Package

**Status:** Package prepared; no human annotations have been received or analyzed.  
**Scope:** Blinding, package preparation, and synthetic-only testing of the analysis script. No training, download, or model change.

## What was prepared

- Timestamped preregistration: `PHASEB2_PREREG.md`, written before tile export.
- Seeded selection: 20 of the 40 Phase B regions, 5 from each colour stratum, selected with seed `20261119` without reading prediction or disagreement outputs. The selected set spans 14 catalog participant IDs.
- Blinded package: [PHASEB2_ANNOTATOR_PACKAGE](./PHASEB2_ANNOTATOR_PACKAGE/) contains 20 raw `512 × 512` RGB PNGs with cryptographically random opaque filenames, the one-page instructions, and the return template.
- Private mapping: [PHASEB2_KEY_DO_NOT_SHARE.csv](./PHASEB2_KEY_DO_NOT_SHARE.csv) links opaque IDs to region/participant/slide identifiers and coordinates. It is outside the annotator package.
- Separate held packet: [PHASEB2_UNBLINDED_REVIEW_PACKET](./PHASEB2_UNBLINDED_REVIEW_PACKET/) contains raw inputs, U-Net overlays, colour-baseline overlays, a blank rating form, and a hold notice. **Do not share it until all annotation masks and forms are returned and locked.**
- Analysis plan and script: `PHASEB2_PREREG.md` and `PHASEB2_analyze_annotations.py`. The script was run only with its synthetic self-test; it was not run on returned masks or real annotations.
- Tool licence record: `PHASEB2_LICENCE_REGISTER.md`.

## Blinding and verification

The package audit and independent verifier confirmed:

- Exactly 20 selected regions and 5 per colour stratum.
- All 20 exported PNG pixel hashes match the selected raw input tiles; each is `512 × 512` and has no embedded image metadata.
- The annotator folder contains 20 images plus the instructions and blank return template. It contains no model/baseline images, masks, overlays, source IDs, coordinates, or private key.
- Image filenames use only opaque IDs; no prediction class appears in an annotator-visible filename.
- The private key is separate. The unblinded packet is separate and contains 62 files; its rating form has 20 blank rows.
- The analysis script's synthetic test passed: perfect-overlap Dice/IoU/precision/recall were `1.0`; for a synthetic partial-overlap case they were Dice `0.57143`, IoU `0.4`, precision `0.8`, recall `0.44444`. The two-participant bootstrap smoke test returned `[0.25, 0.75]`. These are synthetic test values, not model results.

See [PHASEB2_VERIFICATION.json](./PHASEB2_VERIFICATION.json) and [PHASEB2_PACKAGE_AUDIT.json](./PHASEB2_PACKAGE_AUDIT.json).

## What could not be verified

- No annotator has completed the masks, so annotation quality, agreement, the Dice/IoU/precision/recall comparisons, and the registered success rule remain unevaluated.
- The local KPMP inventory's access field is `open`, but applicable reuse terms are not stated in that inventory. No permission or licence was interpreted. Confirm the applicable terms before sending tiles to an external annotator.
- The annotation definition is the supplied draft and has not been reviewed by a kidney pathologist. The user may edit it before release; any wording change after this preregistration must be timestamped before annotation begins.
- The recommended tool's licence is recorded, but no software was installed or used for annotation.

## What the user must do

1. Review the annotation definition. If you edit it, timestamp an amendment and update the annotator instructions to match before annotators begin.
2. Confirm the applicable data-use terms before sharing the tile package. Give annotators only the contents of `PHASEB2_ANNOTATOR_PACKAGE`; keep the key and unblinded packet private.
3. Have each annotator return one `PHASEB2_ANNOTATION_STATUS.csv` and masks named exactly as listed, inside a folder named for that annotator.
4. After all annotations are returned and locked, place them under `PHASEB2_ANNOTATIONS_RETURNED\<annotator_id>\` and explicitly instruct me to run the preregistered analysis.

No Phase C work or analysis of real annotations has started.
