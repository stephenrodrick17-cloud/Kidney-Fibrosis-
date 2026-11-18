# PROTO verification tests

Run these checks from `D:\patent\prototype`:

```powershell
python -m unittest PROTO_TESTS -v
```

The regression run reads the local RENFAST archive, frozen checkpoint, Phase A manifest and saved Phase A metrics. It compares five 512-by-512 images with the Phase A inference function and checks the Dice values against the saved Phase A table. It also compares the adjusted point estimate for three participant rows against `FA_PER_PARTICIPANT_EFFECTS_FINAL.csv` with tolerance `1e-9`.

The local Phase A record contains per-image metrics but no saved predicted-mask PNGs. The mask comparison is therefore against a fresh call to the original Phase A inference function, not against a stored prediction file. The saved Phase A Dice values are checked exactly to tolerance `1e-12`.

Negative and behavior checks cover a wrong checkpoint hash, missing scale, grayscale input, tissue fraction below 0.20, a blank image, too few spots, mismatched barcodes, and shuffled coordinates on a deterministic synthetic spatial sample. The shuffle test reports both effect estimates and requires the shuffled absolute effect to be less than half the original synthetic effect.

The output scanner removes the exact required W1-W5 strings and the required sample-only sentence before checking the other output text for the forbidden terms specified in the master prompt. This is necessary because W4 and the required sample-only sentence contain a forbidden term. No warning wording is changed.

The unit suite does not alter source data or checkpoints and does not create predictions outside `D:\patent\prototype\`. Association intervals are not part of the parity test because PROTO uses the requested spatial-block bootstrap rather than the participant bootstrap used in the existing FA summary.
