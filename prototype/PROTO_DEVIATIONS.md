# PROTO deviations and constraints

| ID | Item | Handling |
|---|---|---|
| D-001 | W4 contains a word that the same prompt forbids, and the required sample-only sentence repeats it. | Preserve W1-W5 and the sentence exactly. The automatic wording scan excludes only those exact mandated phrases and checks all other generated user-facing text. |
| D-002 | Phase A has no saved model-prediction mask files in the local output inventory. | Compare the prototype mask bit-for-bit with the Phase A inference function on five test inputs and compare each Dice value with the saved Phase A metric table. Do not describe this as a comparison with stored predicted masks. |
| D-003 | The FA point-estimate table was calculated with cohort-level gene standardization and, where available, tissue-depth adjustment. A one-sample report uses within-sample standardization and includes tissue depth only if supplied. | The three-participant parity test reuses the saved FA spot-analysis rows and their group assignments to verify the OLS point-estimate implementation. It is not a full raw-image-to-count-matrix end-to-end reproduction. |
| D-004 | The required spatial-block size was not supplied. | Pre-state 4-by-4 Visium array-coordinate blocks, 10,000 resamples, and a fixed seed. Intervals are labelled approximate. |
| D-005 | The master prompt requires input size limits but does not state values. | Use protective prototype limits of 100 MB and 100 megapixels. These are implementation settings, not measured study results. |
| D-006 | A local browser UI requires a browser-to-local-process transfer of the selected file. | Use the installed Streamlit app bound to `127.0.0.1`; no remote service, telemetry, or external network call is used. |

Any additional test limitation or failure is recorded in `PROTO_REPORT.md` and `PROTO_VERIFICATION.md`.
