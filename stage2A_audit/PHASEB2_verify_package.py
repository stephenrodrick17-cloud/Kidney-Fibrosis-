"""Verify blinded-package contents without inspecting prediction pixels."""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

ROOT = Path(r"D:\patent\stage2A_audit")
SOURCE_MANIFEST = ROOT / "PHASEB_region_manifest.csv"
KEY_PATH = ROOT / "PHASEB2_KEY_DO_NOT_SHARE.csv"
ANNOTATOR_DIR = ROOT / "PHASEB2_ANNOTATOR_PACKAGE"
UNBLINDED_DIR = ROOT / "PHASEB2_UNBLINDED_REVIEW_PACKET"
OUTPUT_PATH = ROOT / "PHASEB2_VERIFICATION.json"
SEED = 20261119


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def pixel_hash(path: Path) -> tuple[str, tuple[int, int], str, dict[str, Any]]:
    with Image.open(path) as image:
        mode = image.mode
        size = image.size
        info = dict(image.info)
        if mode != "RGB":
            raise ValueError(f"Expected RGB image: {path}")
        pixels = np.asarray(image, dtype=np.uint8).copy()
    return hashlib.sha256(pixels.tobytes()).hexdigest(), size, mode, info


def main() -> None:
    if OUTPUT_PATH.exists():
        raise FileExistsError(f"Refusing to overwrite {OUTPUT_PATH}")
    manifest = read_csv(SOURCE_MANIFEST)
    key = read_csv(KEY_PATH)
    if len(manifest) != 40 or len(key) != 20:
        raise ValueError("Phase B source or Phase B2 key row counts do not reconcile.")

    rng = random.Random(SEED)
    expected: list[dict[str, str]] = []
    for stratum in ("1", "2", "3", "4"):
        candidates = sorted(
            (row for row in manifest if row["colour_stratum"] == stratum),
            key=lambda row: row["region_id"],
        )
        if len(candidates) != 10:
            raise ValueError(f"Unexpected source stratum size for {stratum}.")
        expected.extend(rng.sample(candidates, 5))
    expected_ids = {row["region_id"] for row in expected}
    keyed_ids = {row["region_id"] for row in key}
    opaque_ids = {row["opaque_id"] for row in key}
    if len(opaque_ids) != 20 or keyed_ids != expected_ids:
        raise ValueError("Key does not match the preregistered seeded region selection.")

    package_files = list(ANNOTATOR_DIR.iterdir())
    image_files = [path for path in package_files if path.suffix.lower() == ".png"]
    non_images = {path.name for path in package_files if path.suffix.lower() != ".png"}
    expected_non_images = {
        "PHASEB2_ANNOTATOR_INSTRUCTIONS.md",
        "PHASEB2_ANNOTATION_RETURN_TEMPLATE.csv",
    }
    if len(image_files) != 20 or non_images != expected_non_images:
        raise ValueError("Annotator package contains unexpected files or count.")
    if KEY_PATH.name in {path.name for path in package_files}:
        raise ValueError("Private key was placed in annotator package.")
    image_by_name = {path.name: path for path in image_files}
    if len(image_by_name) != 20:
        raise ValueError("Annotator image filenames are not unique.")

    manifest_by_id = {row["region_id"]: row for row in manifest}
    checked_hashes = 0
    expected_names: set[str] = set()
    for row in key:
        opaque_id = row["opaque_id"]
        expected_name = f"PHASEB2_{opaque_id}.png"
        expected_names.add(expected_name)
        if not re.fullmatch(r"PHASEB2_[0-9a-f]{16}\.png", expected_name):
            raise ValueError("Annotator filename is not an opaque random ID.")
        if expected_name not in image_by_name:
            raise ValueError("Keyed raw tile is missing from annotator package.")
        package_hash, package_size, _, package_info = pixel_hash(image_by_name[expected_name])
        source_row = manifest_by_id[row["region_id"]]
        source_path = ROOT / source_row["input_image"].replace("/", "\\")
        source_hash, source_size, _, _ = pixel_hash(source_path)
        if package_size != (512, 512) or source_size != package_size:
            raise ValueError("A blinded tile has the wrong dimensions.")
        if package_hash != source_hash or package_hash != row["input_sha256"]:
            raise ValueError("Blinded raw tile pixels differ from the selected input.")
        if package_info:
            raise ValueError("Blinded PNG contains unexpected embedded metadata.")
        checked_hashes += 1
    if set(image_by_name) != expected_names:
        raise ValueError("Annotator filenames do not match the private key.")

    template = read_csv(ANNOTATOR_DIR / "PHASEB2_ANNOTATION_RETURN_TEMPLATE.csv")
    if len(template) != 20 or {row["opaque_id"] for row in template} != opaque_ids:
        raise ValueError("Return template does not match the blinded image set.")
    if any(
        row["annotator_id"] or row["gradable_yes_no"] or row["comments"]
        for row in template
    ):
        raise ValueError("Return template contains filled annotation fields.")

    packet_files = list(UNBLINDED_DIR.iterdir())
    expected_packet_names = {
        "PHASEB2_POST_ANNOTATION_RATING_FORM.csv",
        "PHASEB2_HOLD_UNTIL_ANNOTATION_COMPLETE.md",
    }
    for opaque_id in opaque_ids:
        expected_packet_names.update(
            {
                f"PHASEB2_{opaque_id}_input.png",
                f"PHASEB2_{opaque_id}_unet_overlay.png",
                f"PHASEB2_{opaque_id}_colour_overlay.png",
            }
        )
    if {path.name for path in packet_files} != expected_packet_names:
        raise ValueError("Unblinded packet contents do not match expected files.")
    rating_form = read_csv(UNBLINDED_DIR / "PHASEB2_POST_ANNOTATION_RATING_FORM.csv")
    if (
        len(rating_form) != 20
        or {row["opaque_id"] for row in rating_form} != opaque_ids
        or any(
        row[column]
        for row in rating_form
        for column in (
            "reviewer_id",
            "unet_overlay_score_1_to_5",
            "colour_baseline_overlay_score_1_to_5",
            "preferred_overlay",
            "main_error_type",
            "free_text",
        )
        )
    ):
        raise ValueError("Post-annotation rating form is not blank or complete.")

    result = {
        "status": "verified",
        "selected_regions": 20,
        "regions_per_colour_stratum": 5,
        "selected_participant_ids": len({row["participant_id"] for row in key}),
        "seeded_selection_matches_key": True,
        "raw_blinded_tiles_pixel_hashes_verified": checked_hashes,
        "raw_pngs_have_no_embedded_metadata": True,
        "annotator_visible_files": len(package_files),
        "annotator_prediction_or_baseline_files": 0,
        "annotator_filenames_use_opaque_ids_only": True,
        "private_key_separate_from_annotator_package": True,
        "unblinded_packet_files": len(packet_files),
        "unblinded_packet_is_separate": True,
        "post_annotation_rating_rows_blank": len(rating_form),
        "real_annotations_read": False,
    }
    OUTPUT_PATH.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
