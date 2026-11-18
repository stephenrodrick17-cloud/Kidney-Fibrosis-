# PLAUS plausibility report

**EXPLORATORY, NOT CONFIRMATORY. UNVALIDATED MASKS.**

## Plain-language result

The overall preregistered result is **CONCERN**.

The collagen module had a mean high-minus-low effect of `0.12493395564397017`, with a participant-bootstrap interval of `0.08135907215889013` to `0.17081526870180228`. This is a positive association in the within-sample spot design, not a claim of real fibrosis or a cause.

The negative-control rule failed. The collagen effect was not above the 95th percentile of the 20 negative-control effects. The negative-control 95th percentile was `0.28874069019738285`, and the collagen module's empirical rank fraction was `0.45`.

The expected-direction panel passed. All 16 available genes showed the preregistered sign, giving a sign-agreement fraction of `1.0`. The binomial test against 50% gave `1.52587890625e-05`.

The available sensitivity rule passed. The only available mask grid cell was threshold 0.5; it kept the positive direction. Threshold 0.3 and 0.7, erosion, dilation and footprint variants were NOT AVAILABLE because the required probability maps or rescore inputs were not saved.

The image-colour quartile rule passed for direction in 3 of 4 quartiles. Each quartile had 10 participants. Quartile 1, 2 and 3 effects were positive; quartile 4 was negative with interval `-0.04812645870272567` to `0.010397079427450506`.

Leave-one-participant-out effects stayed positive, from `0.11808473063769895` to `0.13154714672070875`. The library-size-threshold result was positive at `0.14697198424220903`.

Rule 4 failed because the preregistered spatial-block permutation was NOT AVAILABLE in the saved spot table. Tissue-edge exclusion was also NOT AVAILABLE because no tissue-edge distance field was available.

## What the checks do

- Negative-control genes test whether the association pattern is larger than unrelated genes.
- The expected-direction panel tests whether known kidney compartment and matrix genes move in the preregistered directions.
- The mask grid tests whether conclusions change under threshold, morphology and footprint choices.
- Stain-colour quartiles test whether results cluster with image colour.
- Leave-one-out and library exclusions test simple sensitivity to participants and low-count spots.
- Spatial permutation, if it were available, would scramble high/low assignment within 4-by-4 array-coordinate blocks rather than randomly across the tissue.

## What the checks do not show

These checks are plausibility checks only. All 40 participants were used before in Stage 1 or Stage 1d. They cannot confirm that the U-Net marks real fibrosis or that a gene causes fibrosis.

No control-gene or expected-direction conclusion is made for the 12 Stage 1d participants from new full-matrix data; 28 development participants had complete H5 matrices.

The stain quartiles are image-colour groups, not validated stain categories.

No clinical accuracy, collagen mass, diagnosis, prognosis, treatment, novelty or patentability claim is made.

These checks cannot show that the masks mark real fibrosis on KPMP slides; only expert outlines can.

## Independent verification

Independent recomputation used the saved negative-control table, expected-direction table and Stage FA participant effect table. Three headline values were checked. Full details are in `PLAUS_VERIFICATION.json`.
