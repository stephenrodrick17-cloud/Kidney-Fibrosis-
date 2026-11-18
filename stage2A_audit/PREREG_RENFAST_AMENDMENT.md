# RENFAST Baseline Protocol Amendment

**Registered:** 2026-11-16  
**Applies to:** [PREREG_RENFAST_BASELINE.md](./PREREG_RENFAST_BASELINE.md)

## Reason for amendment

The archive audit found 500 fibrosis training image/mask entries but only 250
unique content pairs; each unique pair is present twice with identical image
and mask bytes. The 50 official test pairs are unique. No exact image or mask
content is shared across the official train and test partitions.

The leading numeric filename token (the part before the first underscore) gives
17 training filename groups and 10 test filename groups. All 10 test groups
also occur in the original training partition. The archive documentation
reviewed so far does not establish that these tokens are patient identifiers.
They will therefore be treated only as conservative filename-family groups,
not as verified patients or cases.

## Revised split, before fitting

- Deduplicate only byte-identical image/mask copies within the same normalized
  filename stem. Keep and report any non-identical content; do not silently
  collapse it.
- Exclude every unique training pair whose filename-family group occurs in the
  official test partition. This leaves 123 unique training pairs from 7
  train-only filename groups; 127 unique training pairs from the 10 overlapping
  groups are excluded.
- Sort the 7 eligible training groups by
  `SHA-256("20261116|<group ID>")`. The first group is validation and the
  remaining 6 groups are training. This produces 18 validation pairs and 105
  training pairs.
- Keep all 50 official test pairs sealed for model selection. The resulting
  evaluation is disjoint by filename-family ID, but cannot be called
  patient-level or external validation because the identifiers' semantics and
  participant independence are unverified.
- Use a fixed probability threshold of 0.5 for validation early stopping and
  final metrics. Do not tune a threshold on the official test set.
- The test image/mask bytes may be hashed for duplicate/leakage checks before
  training. Do not decode test images or masks until the checkpoint and
  threshold are frozen.

This amendment changes only the split required to prevent the observed
filename-family overlap from leaking into model fitting. The model, optimizer,
loss, preprocessing, augmentation, stopping rule, and metrics remain as
registered in the baseline protocol.
