# PROTO evidence and limitations

## Required warnings

W1 "RESEARCH USE ONLY. Not a medical device. Not for diagnosis, grading, treatment or any clinical decision."
W2 "Trained and tested on RENFAST trichrome kidney images at about 4.1 micrometres per pixel. Accuracy on other stains, scanners or tissues has NOT been established."
W3 "On the RENFAST test set (10 filename families) the model scored Dice 0.915 against expert masks (95% CI 0.888 to 0.934). It lost accuracy under very dark images (brightness 0.5) and at half-size resolution. On KPMP images its masks have NOT been checked against an expert reference and were often sparse."
W4 "Gene results show association only: genes that are higher in regions the model marks as fibrotic. They do not show that any gene causes fibrosis, and they cannot predict gene activity from an image."
W5 "Results from one sample cannot be generalised. Cross-participant relationships between overall fibrosis percentage and gene levels were NOT found in the validation work."

## Evidence from the local research records

- **RENFAST image-mask overlap:** `PHASEA_RESULTS.md` records recomputed image-macro Dice `0.9153306336`, 50 image pairs, and only 10 filename families. It states those family names are not verified patient or slide identifiers. Its family-bootstrap interval is `0.88724–0.93405`. This is overlap with supplied masks, not a medical assessment.
- **Dark and lower-resolution inputs:** `PHASEC_REPORT.md` records a robustness-rule failure for the paired extreme-brightness setting `(0.5, 1.5)`. It also records reduced Dice at half-size resolution. This supports the input warning, not broad performance.
- **KPMP images:** `PHASEB_REPORT.md` records 27 of 40 regions flagged as empty or extreme predicted area and states that no independent aligned tissue reference was available. It says the frozen model produced empty or sparse masks in many selected regions. The masks have not been checked against an expert reference.
- **No independent tissue reference:** `PHASEA_RESULTS.md` says annotation identity and independent adjudication were not verified. `PHASEB_REPORT.md` says no aligned pathologist reference was found. The local Phase FA record says Gate 1 was not passed because locked expert masks were not supplied.
- **Cross-participant gene association:** `FA_REPORT.md` says the participant-level panel analysis did not show a clear association; collagen-module intervals included zero. `W5` states that cross-participant relationships were not found in the validation work. The proposed cross-participant gene relationship was not established in this data set.
- **Gene outputs:** The FA analysis reported an exploratory within-sample association, but also found an image-colour confounding concern and did not pass its mask-validation gate. The evidence does not establish a general gene result or a gene prediction method.
- **Permissions:** `PHASEA_LICENCE_REGISTER.md`, `PHASEB2_LICENCE_REGISTER.md`, and `FA_LICENCE_NOTE.md` record unresolved RENFAST/KPMP permission scope. Catalog access labels are not treated as reuse permission.
- **Physical scale:** Phase A records state that physical pixel spacing is unavailable for its test patches. PROTO therefore requires the user to enter measured spacing for every new image and refuses to guess.
- **Data limits:** Results from a single sample cannot be extended to other samples. The optional gene intervals are approximate because they resample spatial blocks within one sample.

## Regulatory and use limits

Regulatory status of a medical-image tool in India or elsewhere has not been assessed. A qualified person must review it before any use beyond local research. The checkpoint or tool must not be shared until permission is resolved and the inventor and attorney approve.
