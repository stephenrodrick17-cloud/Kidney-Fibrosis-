# PROTO build report

## Required warnings

W1 "RESEARCH USE ONLY. Not a medical device. Not for diagnosis, grading, treatment or any clinical decision."
W2 "Trained and tested on RENFAST trichrome kidney images at about 4.1 micrometres per pixel. Accuracy on other stains, scanners or tissues has NOT been established."
W3 "On the RENFAST test set (10 filename families) the model scored Dice 0.915 against expert masks (95% CI 0.888 to 0.934). It lost accuracy under very dark images (brightness 0.5) and at half-size resolution. On KPMP images its masks have NOT been checked against an expert reference and were often sparse."
W4 "Gene results show association only: genes that are higher in regions the model marks as fibrotic. They do not show that any gene causes fibrosis, and they cannot predict gene activity from an image."
W5 "Results from one sample cannot be generalised. Cross-participant relationships between overall fibrosis percentage and gene levels were NOT found in the validation work."

## Created files

- `PROTO_DESIGN.md`
- `PROTO_WARNINGS.md`
- `PROTO_VALIDATE.py`
- `PROTO_QUANTIFY.py`
- `PROTO_ASSOCIATE.py`
- `PROTO_APP.py`
- `PROTO_TESTS.py`
- `PROTO_README.md`
- `PROTO_LIMITATIONS.md`
- `PROTO_LICENCE_NOTE.md`
- `PROTO_DEVIATIONS.md`
- `PROTO_VERIFICATION.md`
- `PROTO_FILE_HASHES.csv`
- `PROTO_REPORT.md`

All new files are in `D:\patent\prototype\`. Existing files were read only. The frozen checkpoint was not copied.

## Verification summary

- Final command `python -B PROTO_TESTS.py`: **14 passed, 0 failed, 0 errors**.
- Five Phase A test masks matched a fresh call of the Phase A inference function bit-for-bit; their Dice values matched the saved Phase A metrics.
- Three FA participant point estimates matched at tolerance `1e-9`.
- Negative validation, shuffled-coordinate, spatial-block interval, warning metadata, and in-process interface tests passed.
- A live loopback HTTP probe did not connect in the sandbox. The in-process Streamlit test passed; no network UI test is claimed.
- Full outputs for test values, runtime, versions, seeds, and limits are in `PROTO_VERIFICATION.md`.

## Failed, unavailable, or incomplete checks

- No new sample image with a user-measured micrometres-per-pixel value was provided. A sample fibrosis percentage and full image-plus-count association report are therefore **NOT AVAILABLE**.
- Physical spacing for the five Phase A regression patches is **NOT AVAILABLE**. Their model masks and Dice were checked, but a physical-unit percentage was not produced.
- The FA parity test uses saved spot rows and group assignments. It does not validate the full input-to-association workflow on a new sample.
- Saved Phase A predicted-mask PNGs were **NOT AVAILABLE**. Mask identity was verified against a fresh Phase A inference call instead.
- The exact mandatory W4 warning and sample-only sentence conflict with the prompt's forbidden-word scan. The precise required wording is retained; the exception is logged in `PROTO_DEVIATIONS.md` and described in `PROTO_VERIFICATION.md`.

## Deviations and safety constraints

See `PROTO_DEVIATIONS.md` for the documented prompt conflict and implementation choices. RENFAST and KPMP permission status remains **UNRESOLVED**. Distribution of the checkpoint or tool is blocked until permissions are resolved and the inventor and attorney approve. No clinical, regulatory, or filing work was started.

## Exact inputs still needed from the inventor

1. Written permission wording and scope for RENFAST images, masks, and the frozen checkpoint, and for any KPMP assets used.
2. A decision about whether distribution is intended; no distribution can proceed until permissions are resolved and both inventor and attorney approve.
3. If KPMP performance is to be evaluated, a labelled KPMP-style image set with suitable expert reference masks and permission for that use.
4. For a real prototype run, a sample image, its measured micrometres per pixel, and (only if the optional within-sample report is wanted) matching 10x Visium spot-position, scale-factor, and count-matrix files.

No package, publication, deployment, or sharing was performed. Stop here pending the inputs above.
