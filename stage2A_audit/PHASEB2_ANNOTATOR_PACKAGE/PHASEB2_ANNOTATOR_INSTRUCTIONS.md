# Tile Annotation Instructions

## What to mark

For each tile, outline areas of interstitial fibrosis, i.e. collagen-stained tissue between tubules; exclude glomeruli, vessel walls, capsule and pen marks. This is an annotation task, not a diagnosis or fibrosis grade.

## What you received

- Twenty `512 × 512` RGB PNG tiles. Their names are opaque IDs; keep each filename unchanged.
- A blank `PHASEB2_ANNOTATION_RETURN_TEMPLATE.csv`.
- No model or colour-baseline predictions are included. Do not request or view model overlays until all annotations have been returned and locked.

## Drawing and saving a mask

GIMP is the recommended drawing tool. For each tile:

1. Open the tile in GIMP and do not resize, rotate, crop, recolour, or overwrite it.
2. Add a new layer with the same canvas size and fill that layer black. Temporarily lower the mask layer's opacity so the original tile remains visible underneath while tracing.
3. Use a polygon/free-select tool to outline each area that meets the definition. Turn off edge antialiasing, fill each selected area white on the black mask layer, and repeat for separate areas.
4. Restore the mask layer to 100% opacity and hide the original image layer. Check that the mask layer is black everywhere except the white outlines/fill. Export the visible mask as a PNG using the exact filename in the CSV.
5. Confirm the exported PNG is exactly `512 × 512`, as grayscale or equal-channel RGB, with black `0` for not fibrosis and white `255` for fibrosis. Do not use grey, transparency, or antialiasing in the final mask.

If a tile cannot be judged, mark `gradable_yes_no` as `no`, add a short reason in `comments`, and do not create a mask for it. Do not guess.

## Returning files

- Make a separate folder for each annotator; use a short annotator ID such as `R1` or `R2` as the folder name.
- Put the completed CSV in that folder and name it `PHASEB2_ANNOTATION_STATUS.csv`.
- Put the PNG masks in the same folder. Use only the filenames listed in the CSV.
- Return the annotator folder securely to the project owner. Do not include patient identifiers or share the private ID key.
- The separate unblinded review packet must remain unopened and unshared until all masks and status forms have been returned and locked.
