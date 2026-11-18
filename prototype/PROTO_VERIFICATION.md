# PROTO verification record

## Required warnings

W1 "RESEARCH USE ONLY. Not a medical device. Not for diagnosis, grading, treatment or any clinical decision."
W2 "Trained and tested on RENFAST trichrome kidney images at about 4.1 micrometres per pixel. Accuracy on other stains, scanners or tissues has NOT been established."
W3 "On the RENFAST test set (10 filename families) the model scored Dice 0.915 against expert masks (95% CI 0.888 to 0.934). It lost accuracy under very dark images (brightness 0.5) and at half-size resolution. On KPMP images its masks have NOT been checked against an expert reference and were often sparse."
W4 "Gene results show association only: genes that are higher in regions the model marks as fibrotic. They do not show that any gene causes fibrosis, and they cannot predict gene activity from an image."
W5 "Results from one sample cannot be generalised. Cross-participant relationships between overall fibrosis percentage and gene levels were NOT found in the validation work."

## Environment and command

- Date recorded: 2026-11-18.
- Operating system: Windows.
- Python: 3.13.1.
- NumPy: 2.2.6; Pillow: 11.1.0; PyTorch: 2.7.1+cu118; SciPy: 1.18.1; Streamlit: 1.50.0; h5py: 3.16.0.
- Device reported by PyTorch: NVIDIA GeForce RTX 3050 Laptop GPU; CUDA available.
- Exact final test command: `python -B PROTO_TESTS.py`, run from `D:\patent\prototype\`.
- Test runtime: 8.029 seconds overall; Phase A model load and five-image comparisons took 1.535 seconds.
- Spatial bootstrap seed: `20261117`; shuffled-coordinate negative-test seed: `20261118`.
- Frozen checkpoint SHA-256 checked during tests: `674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb`.

## Results

- **14 tests passed; 0 failures; 0 errors.**
- Phase A: all five prototype masks were bit-identical to the Phase A inference function. Dice values matched the saved Phase A test metrics (tolerance `1e-12`):

| Image | Dice |
|---|---:|
| `1004762` | `0.9479029721857036` |
| `1004762_16` | `0.9320208981387595` |
| `1004762_17` | `0.9167964731814842` |
| `1004762_18` | `0.7402665626031879` |
| `1004764_2` | `0.9312139486740887` |

  Saved predicted-mask PNGs were not available, so bit-identity was checked against a fresh Phase A inference call. The Dice comparison used the saved Phase A metric table. Input physical spacing was **NOT AVAILABLE** for these patches, so no fibrosis percentages were calculated.
- FA point-estimate parity passed for three participants with absolute difference `0.0` and tolerance `1e-9`:

| Participant | Prototype effect | FA effect |
|---|---:|---:|
| `27-10157` | `0.25010763618432996` | `0.25010763618432996` |
| `27-10201` | `0.34151645493699534` | `0.34151645493699534` |
| `27-10206` | `0.2787293253986934` | `0.2787293253986934` |

  This reuses the saved FA spot-analysis rows and groups. It is not a raw-image-to-count-matrix end-to-end association run.
- Synthetic shuffled-position check: the absolute collagen-module effect decreased from `2.0144813714585252` to `0.01011940831581262`.
- Synthetic 10,000-resample block-bootstrap interval test passed.
- Negative cases passed: wrong checkpoint hash, missing MPP, unsupported scale, grayscale, blank/low-tissue image, too few spots, mismatched barcodes, and output-warning scan.
- PNG warning metadata test passed for W1-W5.
- Streamlit in-process `AppTest` passed: all warnings appeared, the acknowledgement checkbox appeared, and no app exception occurred. A separate live loopback HTTP probe did not connect in this sandbox; it was stopped. No network-based UI verification is claimed.

## Limits and exceptions

- No user-supplied image with measured MPP was available. Therefore no real-sample quantification or optional gene report was produced.
- The Phase A regression images are 512-by-512 patches. This regression does not independently verify every multi-tile or rescaling condition on a new slide.
- FA parity is an estimator check on previously calculated rows, not a full optional-analysis regression from raw image and count matrix.
- The prompt requires exact warning W4 and an exact sample-only sentence containing a word also listed in its forbidden-word scan. Those exact required phrases are preserved. The automated wording scan excludes only those required warning strings and sentence; all other checked output text is scanned.
- Sharing remains blocked because data and checkpoint permissions are unresolved and inventor/attorney approval is pending.

## Reproducibility

The test runner uses the fixed seeds listed above. The exact test command and runtime are recorded here. SHA-256 values for the checkpoint, source inputs, and generated PROTO files are recorded in `PROTO_FILE_HASHES.csv`; the manifest does not contain its own hash.
