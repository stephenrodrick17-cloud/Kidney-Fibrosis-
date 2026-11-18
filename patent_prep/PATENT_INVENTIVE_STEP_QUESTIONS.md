# Inventive-Step Fact-Finding Questions

This file does not decide what is inventive. It lists technical choices visible in the permitted saved Phase A–C records and asks the inventor to explain their origin. It is not legal advice.

The permitted Phase A–C sources do not document a custom U-Net component. They identify and call a U-Net, but the layer-by-layer architecture is not present in the inspected prefixed source files. Therefore, this record cannot establish that the full implementation is simply a standard U-Net or that it has no custom element.

| Recorded design choice | What was done | Where recorded | Why chosen, if recorded | Standard alternative to ask about |
|---|---|---|---|---|
| Filename-family split and exclusion | The active data were split by filename family: 6 training, 1 validation, and 10 test families; 127 pairs sharing test families were excluded. These IDs are not verified patient/slide IDs. | `PHASEA_RESULTS.md`, `PHASEA_final_split_manifest.csv`, `PHASEA_PREREG_A.md` | To reduce overlap across the available filename-derived groups and preserve the official test groupings. | Random image-level split; patient- or slide-level split if verified identifiers are available. |
| Fixed probability threshold | Frozen U-Net probabilities are binarized at `0.5`. | `PHASEA_README.md`, `PHASEA_run_audit.py`, `PHASEB_PREREG.md` | Kept fixed for the frozen model; test threshold tuning was not allowed. The original threshold-selection history is not fully recorded in the permitted Phase A files. | Select a threshold on a validation set, or use another predeclared threshold rule. |
| RGB scaling and no stain normalization | RGB channels are converted to floating point and divided by `255.0`; Phase B specified no stain normalization, colour augmentation, or test-time augmentation. | `PHASEA_run_audit.py`, `PHASEB_PREREG.md`, `PHASEB_REPORT.md` | Existing handling was frozen; no additional normalization was introduced. | A separately specified stain-normalization or colour-normalization method. |
| Padding and cropping | Pad bottom/right to a multiple of `16` and crop model output to the original image bounds. | `PHASEA_run_audit.py`, `PHASEB_run_external_check.py` | Compatibility with the model's recorded spatial multiple while preserving tile dimensions. | Resize to a fixed model canvas or use a different padding/tiling scheme. |
| External fixed-scale tile selection | For the KPMP sanity check, select the closest slide-pyramid level to `4.1 µm/pixel`, resample to `512 × 512`, require tissue fraction at least `0.50`, and select 40 regions across four colour strata with a seed. | `PHASEB_select_regions.py`, `PHASEB_PREREG.md` | Registered in advance to sample slide-colour variation without using model output to choose regions. | Whole-slide inference, random spatial sampling, or another declared physical scale. |
| Colour baseline and training-only threshold tuning | The baseline predicts where `B - R >= t`; `t` was chosen on training families only. The selected threshold was `2`. | `PHASEA_PREREG_A.md`, `PHASEA_README.md`, `PHASEA_final_metrics.json` | A simple fixed colour comparator for the segmentation model. | A different fixed colour rule or a learned comparison model. |
| Phase C loss and optimizer for new U-Net members | The two Phase C U-Nets used equal-weight BCE and soft-Dice loss and AdamW (`lr=1e-3`, `weight_decay=1e-4`), batch size `1`, and the Phase A flip/rotation augmentation recipe. | `PHASEC_UNET_seed_20261122_metadata.json`, `PHASEC_UNET_seed_20261123_metadata.json`, `PHASEC_run.py` | Reused the recorded Phase A recipe; exact Phase A augmentation parameter values are not stated in the permitted reports. | A single loss, another optimizer, or different augmentation choices. |
| Validation-based early stopping for Phase C models | Maximum `100` epochs and patience `12` using the single validation family; recorded best epochs were `63` and `79` for the two new U-Nets. | The two Phase C metadata JSON files and `PHASEC_README.md` | Stop at the best recorded validation checkpoint. | Fixed epoch count without early stopping or another validation rule. |
| Robustness perturbation suite | Predeclared colour/stain perturbations, resolution changes, and tile-size changes were applied to frozen models. | `PHASEC_PREREG.md`, `PHASEC_REPORT.md`, `PHASEC_run.py` | To assess sensitivity of the frozen model under declared input changes. | No perturbation testing or a different predeclared suite. This is an evaluation method, not a documented model component. |
| Deep ensemble and OOD screen | An ensemble used the frozen Phase A model plus two new U-Nets; a six-feature colour-statistic rule was fit on training images and used as a screening flag. | `PHASEC_PREREG.md`, `PHASEC_REPORT.md` | Predeclared uncertainty and screening analyses. The uncertainty/error association was not established, and the flag is not validated. | Single-model output or another declared uncertainty/OOD method. |

## Questions for the inventor

- Which of these choices did you personally design, and on what date?
- Which choices were taken from a paper, tutorial, public repository, library, or another person's work? Provide exact citations and versions.
- Was any code written by a contractor, collaborator, student, or AI tool? Who contributed which parts, and when?
- What exact U-Net layers, channels, normalization layers, and output head are used by the frozen checkpoint? Where is the authoritative source code?
- Are the `4.1 µm/pixel` extraction, `512 × 512` size, threshold, and RGB tissue mask intended product requirements or only audit settings?
- What exact augmentation operations and parameter ranges were used for the frozen Phase A training?
- What problem was each design choice intended to solve, and what standard alternatives were tried or considered?
- Which observed results were known before any public disclosure, sale, presentation, or filing? Provide dates and supporting records for attorney review.
- Who conceived the technical approach before any AI-assisted implementation? Who provided directions, selection criteria, or architecture decisions?

