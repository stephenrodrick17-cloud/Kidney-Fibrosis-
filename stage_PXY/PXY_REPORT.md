# PXY licence, paired comparison and proxy report

## Plain-language result

The paired PCT comparison used 50 RENFAST test images and 10 filename families. It used the tissue-pixel denominator, with tissue defined as RGB channel mean below 245.

U-Net absolute area error was lower on average than the colour rule. The mean U-Net-minus-colour paired absolute-error difference was `-2.9963386333393784` percentage points. The family-bootstrap 95% confidence interval was `-4.193187100712248` to `-1.4285297339368308`. This interval is entirely below zero, so the preregistered rule says the U-Net percentage error is significantly lower for this test set.

U-Net had lower absolute area error in 38 of 50 images. It was worse in 12 images and had no exact ties.

The mean paired squared-error difference was `-52.07772225037059` percentage points squared, with a family-bootstrap 95% confidence interval of `-78.52771956457536` to `-17.84500995019343`.

## Licence and proxy result

No outside model was eligible for a proxy run.

- SarderLab/Multi-Compartment-Segmentation: BLOCKED. A licence was not found, and the README requires a DSA account, login and WSI upload.
- vkola-lab/ajpa2021: BLOCKED for execution. The code licence is the MIT License, but no public checkpoint or weight file was found and the repository does not establish licence/access terms for external KPMP slide downloads.

No outside model weights were downloaded. No KPMP slide was downloaded or run. No proxy agreement was produced.

## What this does and does not show

The paired PCT result shows lower U-Net percentage error than the B-R colour rule on the saved RENFAST test values. It does not show agreement with a new expert-labelled external dataset and it does not show clinical accuracy.

The proxy result is unavailable, not failed. The repositories did not pass the licence and weight conditions in the request.

The four requested limits are addressed only as follows:

- Low or normal fibrosis: weakly. PCT has no 0-5 or 5-15 expert-percent images, and the lowest expert percentage is 25.239860569709418%. Low-fibrosis and normal-tissue accuracy still need pathologist labels.
- Other stains and scanners: NOT TESTED.
- Whole slides: NOT TESTED. No eligible whole-slide proxy workflow was available.
- Percentage versus colour rule: tested on 50 RENFAST images. U-Net absolute area error was lower overall under the preregistered paired rule.

## Interpretation limits

The 95% intervals resample 10 filename families, not verified patients or slides. The PCT test set does not establish clinical interstitial fibrosis, collagen mass or medical accuracy.

No proxy output was used as ground truth. No correction was applied to the U-Net or colour-rule outputs.

## Independent verification

The independent arithmetic recomputation is in `PXY_VERIFICATION.json`. It recomputed the mean absolute-error difference, the U-Net-better image count and the mean paired squared-error difference from PCT_PER_IMAGE.csv with tolerance `1e-12`.
