# Limitations

Plain statements for attorney review. These results do not establish clinical accuracy or clinical utility.

| Limitation | Recorded fact | Source |
|---|---|---|
| Group identifiers | The split groups are filename families, not verified patient or slide IDs. | `D:\patent\stage2A_audit\PHASEA_RESULTS.md`; `D:\patent\stage2A_audit\PHASEC_REPORT.md` |
| Small test-group count | There are `10` test filename families; the reports say this limits precision. | `D:\patent\stage2A_audit\PHASEA_RESULTS.md`; `D:\patent\stage2A_audit\PHASEC_REPORT.md` |
| No external reference validation | No independent hospital cohort or aligned reference standard was evaluated. | `D:\patent\stage2A_audit\PHASEA_RESULTS.md`; `D:\patent\stage2A_audit\PHASEB_REPORT.md`; `D:\patent\stage2A_audit\PHASEC_REPORT.md` |
| KPMP regions are not scored against a reference | The saved Phase B objective flag found empty/extreme predicted area in `27` of `40` regions. “Extreme” includes empty or under-1% or over-80% predicted area of tissue; this should not be called 27 sparse masks. Without an aligned reference, correctness could not be judged. | `D:\patent\stage2A_audit\PHASEB_REPORT.md`; `D:\patent\stage2A_audit\PHASEB_inference_summary.json` |
| Unassessable structures | Glomeruli, vessels, and pen-mark overlap were not assessable because exact spatially aligned annotations were unavailable. | `D:\patent\stage2A_audit\PHASEB_REPORT.md` |
| Colour robustness | The paired brightness condition `(0.5, 1.5)` failed the pre-registered rule. Individual directions saturation `0.40` and brightness `0.50` also failed the registered Dice-change rule. | `D:\patent\stage2A_audit\PHASEC_REPORT.md`; corrected `PHASEC_robustness_summary_corrected.csv` |
| Resolution sensitivity | At `0.50×`, U-Net family Dice change from clean input was `-0.0386` with 95% CI `[-0.0431, -0.0345]`. | `D:\patent\stage2A_audit\PHASEC_REPORT.md` |
| Ensemble did not improve the frozen model | Ensemble minus frozen U-Net family-macro Dice was `-0.0021` (95% CI `-0.0062 to 0.0015`); improvement was not demonstrated. | `D:\patent\stage2A_audit\PHASEC_REPORT.md` |
| DeepLab comparison blocked | The projected DeepLab runtime exceeded the registered `7200`-second maximum; no DeepLab training or comparison was performed. | `D:\patent\stage2A_audit\PHASEC_REPORT.md`; `D:\patent\stage2A_audit\PHASEC_BLOCKED_RUNS.csv` |
| Uncertainty relation not established | The family-level entropy versus `1 - Dice` association CI included zero. | `D:\patent\stage2A_audit\PHASEC_REPORT.md` |
| OOD flag not validated | The predeclared rule flagged `0/50` test images and is described as a screening flag, not a validated OOD detector. | `D:\patent\stage2A_audit\PHASEC_REPORT.md` |
| Approximate run start times | Phase C metadata has elapsed durations, not exact wall-clock starts/ends; README start times are reconstructed estimates. | `D:\patent\stage2A_audit\PHASEC_REPORT.md`; `D:\patent\stage2A_audit\PHASEC_README.md` |
| Unresolved data rights | RENFAST licence field is blank and permission scope is unresolved. KPMP access status is “open,” but reuse terms are not stated in the local record. | `D:\patent\stage2A_audit\PHASEA_LICENCE_REGISTER.md`; `D:\patent\stage2A_audit\PHASEB_LICENCE_REGISTER.md`; `D:\patent\stage2A_audit\PHASEC_LICENCE_REGISTER.md` |

