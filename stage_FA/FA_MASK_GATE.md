# FA_MASK_GATE - EXPLORATORY, NOT CONFIRMATORY

**EXPLORATORY, NOT CONFIRMATORY. UNVALIDATED MASKS.**

## Gate 1 result

**GATE 1: NOT PASSED.**

Gate 1 requires completed, locked pathologist masks for the relevant tiles (or an independent expert-labelled kidney set) and a preregistered analysis showing that the frozen U-Net meets its registered threshold against those masks. The local records examined do not provide that evidence:

- The Phase B report says no independent, slide-matched fibrosis reference was available and reports no reference-based accuracy metric.
- The Phase B reviewer form is blank.
- No completed pathologist outlines or independent expert-labelled reference set were supplied for this work.

The Phase B report records that **27 of 40 regions** had an empty-or-extreme U-Net predicted-area flag, defined as predicted area below 1% or above 80% of tissue. This is a combined algorithmic flag: it does not mean that all 27 masks were sparse or empty, and it is not a comparison with ground truth.

## Consequence for Stage FA

Every downstream Stage FA output is **EXPLORATORY, NOT CONFIRMATORY** and **UNVALIDATED MASKS**. Each registered association must be computed separately using:

1. the frozen RENFAST U-Net mask; and
2. the fixed colour mask `B - R >= 2`.

The result is considered credible only if the two analyses agree in direction. Disagreement must be reported plainly. Agreement alone does not pass Gate 1 or establish mask accuracy.

The local data audit also found no stain/colour-group labels. The preregistered image-colour comparison is therefore only a descriptive proxy and cannot establish that stain differences are absent.

## What is needed to change this gate

The inventor must supply completed, locked expert masks for the relevant images and the registered B2 analysis showing the frozen U-Net meets its previously registered threshold on those masks. Until then, no output may be described as validated, reliable, clinically accurate, or confirmatory.
