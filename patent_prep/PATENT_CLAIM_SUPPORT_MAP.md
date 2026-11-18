# Supported and Unsupported Subject-Matter Map

Draft for review by a patent attorney. No claim language is drafted here. This is not legal advice and makes no statement about novelty, inventive step, or patentability.

## A. Candidate subject matter supported by recorded evidence

| Candidate subject matter | Evidence rows or source | What the evidence supports |
|---|---|---|
| Generating a binary fibrosis mask from a RENFAST RGB tissue tile using the frozen U-Net pipeline | Evidence Register: Phase A clean-test metrics; `D:\patent\stage2A_audit\PHASEA_run_audit.py`; `D:\patent\stage2A_audit\PHASEA_RESULTS.md` | The code loads the frozen model, applies a fixed probability threshold, and the predicted masks were compared with the dataset's expert-made masks. |
| Higher RENFAST mask overlap than the fixed colour-threshold baseline on the saved test split | Evidence Register: Phase A U-Net and colour-threshold Dice/IoU/precision/recall, paired Dice difference and CI; `D:\patent\stage2A_audit\PHASEA_final_metrics.json` | The registered filename-family bootstrap CI for the paired Dice difference is above zero on this split. It is not external or clinical validation. |
| Producing a descriptive predicted-area fraction on selected KPMP trichrome regions | `D:\patent\stage2A_audit\PHASEB_run_external_check.py`; `D:\patent\stage2A_audit\PHASEB_inference_summary.json`; `D:\patent\stage2A_audit\PHASEB_REPORT.md` | The code calculates predicted-positive pixels within its RGB-defined tissue mask. No aligned fibrosis reference was available, so this is not a validated fibrosis percentage. |
| A defined set of colour, resolution, tile-size, ensemble-uncertainty, and screening-flag evaluations | `D:\patent\stage2A_audit\PHASEC_PREREG.md`; `D:\patent\stage2A_audit\PHASEC_REPORT.md` | These evaluations were performed and reported. The report records both failures and outcomes that were not established; they do not prove a new model component or a clinical warning function. |

The attorney must decide whether any of these technical facts are relevant to a filing. This table does not say that they are new or protectable.

## B. Subject matter excluded from supported evidence

| Subject matter | Exact reason based on permitted records | Source |
|---|---|---|
| Gene-expression or molecular-expression prediction (the user identifies Stage 1, 1b, and 1d as FAIL) | The exact underlying Phase A–C result and failure reasons are NOT AVAILABLE in the permitted Phase A–C files reviewed. The stated FAIL status is user-provided, not independently verified here. | No Phase A–C source file recording those stage results was identified. The underlying stage report is an open question. |
| Image–molecular registration or fusion | Not performed or evaluated in the Phase A–C records reviewed; no registration-error or fusion-performance evidence is available. | `D:\patent\stage2A_audit\PHASEA_RESULTS.md`; `D:\patent\stage2A_audit\PHASEB_REPORT.md`; `D:\patent\stage2A_audit\PHASEC_REPORT.md` |
| KPMP fibrosis accuracy | Phase B had no independent, slide-aligned fibrosis reference. Dice, IoU, accuracy, sensitivity, specificity, and grade metrics against reference labels were not computed. | `D:\patent\stage2A_audit\PHASEB_REPORT.md` |
| Uncertainty as a reliable indicator of error | Family-level entropy versus `1 - Dice` association was not established: the reported CI includes zero. | `D:\patent\stage2A_audit\PHASEC_REPORT.md` |
| Validated out-of-distribution warning | The recorded rule flagged `0/50` test images; the report calls it a screening flag, not a validated OOD detector. | `D:\patent\stage2A_audit\PHASEC_REPORT.md` |
| Stronger DeepLab baseline comparison | BLOCKED before training because its projected time exceeded the registered cap; no comparison result exists. | `D:\patent\stage2A_audit\PHASEC_REPORT.md`; `D:\patent\stage2A_audit\PHASEC_BLOCKED_RUNS.csv` |
| Trichrome collagen proxy or collagen-specific measurement | The saved Phase B work is reference-free and does not validate that RGB stain colour measures collagen specifically. The model was not evaluated against an independent collagen reference. | `D:\patent\stage2A_audit\PHASEB_REPORT.md`; `D:\patent\stage2A_audit\PHASEB_PREREG.md` |
| Compartment segmentation or validated interstitial-fibrosis percentage on KPMP | The Phase B report states glomeruli, vessels, and pen marks were not assessable because aligned annotations were unavailable. No compartment masks or validated percentage were produced. The request mentions that expert masks did not match; the exact comparison is NOT AVAILABLE in the permitted Phase B record. Phase B2 reports no returned human annotations. | `D:\patent\stage2A_audit\PHASEB_REPORT.md`; `D:\patent\stage2A_audit\PHASEB2_REPORT.md` |

Whether any excluded item may appear as future work in the description only is a question for the attorney.

## Open questions for the inventor

- Supply the saved source report for Stage 1, 1b, and 1d and the exact failure reasons if those failures are to be included as facts.
- Supply the source and protocol for the claimed expert-mask mismatch; the saved Phase B report does not document such a comparison.
- Confirm whether any molecular data or spatial-registration method exists outside the permitted Phase A–C record set.
