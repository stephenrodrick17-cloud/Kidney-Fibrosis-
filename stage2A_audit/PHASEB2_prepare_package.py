"""Select, blind, and export Phase B2 tiles and the held unblinded packet."""

from __future__ import annotations

import csv
import hashlib
import json
import random
import secrets
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

ROOT = Path(r"D:\patent\stage2A_audit")
SOURCE_MANIFEST = ROOT / "PHASEB_region_manifest.csv"
SOURCE_IMAGES = ROOT / "PHASEB_region_images"
ANNOTATOR_DIR = ROOT / "PHASEB2_ANNOTATOR_PACKAGE"
UNBLINDED_DIR = ROOT / "PHASEB2_UNBLINDED_REVIEW_PACKET"
KEY_PATH = ROOT / "PHASEB2_KEY_DO_NOT_SHARE.csv"
PACKAGE_AUDIT_PATH = ROOT / "PHASEB2_PACKAGE_AUDIT.json"
SELECTION_SEED = 20261119
REGIONS_PER_STRATUM = 5


def read_manifest() -> list[dict[str, str]]:
    with SOURCE_MANIFEST.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def select_regions(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if len(rows) != 40 or len({row["region_id"] for row in rows}) != 40:
        raise ValueError("Expected 40 unique Phase B source regions.")
    by_stratum: dict[str, list[dict[str, str]]] = {
        stratum: sorted(
            (row for row in rows if row["colour_stratum"] == stratum),
            key=lambda row: row["region_id"],
        )
        for stratum in ("1", "2", "3", "4")
    }
    if any(len(group) != 10 for group in by_stratum.values()):
        raise ValueError("Expected 10 Phase B regions in each colour stratum.")
    rng = random.Random(SELECTION_SEED)
    selected: list[dict[str, str]] = []
    for stratum in ("1", "2", "3", "4"):
        selected.extend(
            rng.sample(by_stratum[stratum], REGIONS_PER_STRATUM)
        )
    if len({row["region_id"] for row in selected}) != 20:
        raise ValueError("Seeded selection produced duplicate regions.")
    return selected


def load_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        if image.mode != "RGB" or image.size != (512, 512):
            raise ValueError(f"Unexpected source tile: {path}")
        return np.asarray(image, dtype=np.uint8).copy()


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if not SOURCE_MANIFEST.is_file() or not SOURCE_IMAGES.is_dir():
        raise FileNotFoundError("Phase B manifest or selected input image folder is missing.")
    if KEY_PATH.exists() or UNBLINDED_DIR.exists() or PACKAGE_AUDIT_PATH.exists():
        raise FileExistsError("Refusing to overwrite an existing Phase B2 key or packet.")
    if not ANNOTATOR_DIR.is_dir():
        raise FileNotFoundError(
            f"Annotator package instructions must exist first: {ANNOTATOR_DIR}"
        )
    existing_files = list(ANNOTATOR_DIR.iterdir())
    allowed_existing = {ANNOTATOR_DIR / "PHASEB2_ANNOTATOR_INSTRUCTIONS.md"}
    if set(existing_files) != allowed_existing:
        raise FileExistsError(
            "Annotator package contains unexpected files; refusing to overwrite."
        )

    selected = select_regions(read_manifest())
    opaque_ids: set[str] = set()
    key_rows: list[dict[str, str]] = []
    annotator_files: list[Path] = []
    completed = False
    UNBLINDED_DIR.mkdir()
    try:
        for row in selected:
            opaque_id = secrets.token_hex(8)
            while opaque_id in opaque_ids:
                opaque_id = secrets.token_hex(8)
            opaque_ids.add(opaque_id)
            source_input = SOURCE_IMAGES / f"{row['region_id']}_input.png"
            source_unet = SOURCE_IMAGES / f"{row['region_id']}_unet_overlay.png"
            source_colour = SOURCE_IMAGES / f"{row['region_id']}_colour_overlay.png"
            if not all(path.is_file() for path in (source_input, source_unet, source_colour)):
                raise FileNotFoundError(f"Missing Phase B panel for {row['region_id']}")

            rgb = load_rgb(source_input)
            pixel_hash = hashlib.sha256(rgb.tobytes()).hexdigest()
            if pixel_hash != row["input_sha256"]:
                raise ValueError(f"Input tile hash mismatch: {row['region_id']}")

            blinded_name = f"PHASEB2_{opaque_id}.png"
            blinded_path = ANNOTATOR_DIR / blinded_name
            Image.fromarray(rgb, mode="RGB").save(blinded_path, format="PNG")
            annotator_files.append(blinded_path)

            key_rows.append(
                {
                    "opaque_id": opaque_id,
                    "region_id": row["region_id"],
                    "participant_id": row["participant_id"],
                    "slide_id": row["slide_id"],
                    "slide_filename": row["slide_filename"],
                    "slide_path": row["slide_path"],
                    "colour_stratum": row["colour_stratum"],
                    "x_level_pixels": row["x_level_pixels"],
                    "y_level_pixels": row["y_level_pixels"],
                    "x_level0_pixels": row["x_level0_pixels"],
                    "y_level0_pixels": row["y_level0_pixels"],
                    "source_width_at_level": row["source_width_at_level"],
                    "source_height_at_level": row["source_height_at_level"],
                    "target_mpp": row["target_mpp"],
                    "input_sha256": pixel_hash,
                    "selection_seed": str(SELECTION_SEED),
                }
            )

            for source, suffix in (
                (source_input, "input"),
                (source_unet, "unet_overlay"),
                (source_colour, "colour_overlay"),
            ):
                target = UNBLINDED_DIR / f"PHASEB2_{opaque_id}_{suffix}.png"
                with Image.open(source) as image:
                    image.save(target, format="PNG")

        key_fields = list(key_rows[0])
        write_csv(KEY_PATH, key_fields, key_rows)

        template_fields = [
            "opaque_id",
            "mask_filename",
            "annotator_id",
            "gradable_yes_no",
            "comments",
        ]
        template_rows = [
            {
                "opaque_id": row["opaque_id"],
                "mask_filename": f"PHASEB2_{row['opaque_id']}.png",
                "annotator_id": "",
                "gradable_yes_no": "",
                "comments": "",
            }
            for row in key_rows
        ]
        write_csv(
            ANNOTATOR_DIR / "PHASEB2_ANNOTATION_RETURN_TEMPLATE.csv",
            template_fields,
            template_rows,
        )

        rating_fields = [
            "opaque_id",
            "reviewer_id",
            "unet_overlay_score_1_to_5",
            "colour_baseline_overlay_score_1_to_5",
            "preferred_overlay",
            "main_error_type",
            "free_text",
        ]
        rating_rows = [
            {
                "opaque_id": row["opaque_id"],
                "reviewer_id": "",
                "unet_overlay_score_1_to_5": "",
                "colour_baseline_overlay_score_1_to_5": "",
                "preferred_overlay": "",
                "main_error_type": "",
                "free_text": "",
            }
            for row in key_rows
        ]
        write_csv(
            UNBLINDED_DIR / "PHASEB2_POST_ANNOTATION_RATING_FORM.csv",
            rating_fields,
            rating_rows,
        )
        (UNBLINDED_DIR / "PHASEB2_HOLD_UNTIL_ANNOTATION_COMPLETE.md").write_text(
            "# Hold Until Annotation Is Complete\n\n"
            "Do not share this packet with annotators until all annotation masks "
            "and status forms have been returned and locked. This packet contains "
            "the frozen U-Net and colour-baseline overlays.\n",
            encoding="utf-8",
        )

        package_image_names = {path.name for path in annotator_files}
        expected_package_names = {
            "PHASEB2_ANNOTATOR_INSTRUCTIONS.md",
            "PHASEB2_ANNOTATION_RETURN_TEMPLATE.csv",
            *package_image_names,
        }
        actual_package_names = {path.name for path in ANNOTATOR_DIR.iterdir()}
        if actual_package_names != expected_package_names:
            raise ValueError("Unexpected file found in the blinded annotator package.")
        if len(annotator_files) != 20 or len(opaque_ids) != 20:
            raise ValueError("Expected exactly 20 unique blinded input tiles.")
        if any(
            not path.name.startswith("PHASEB2_")
            or any(token in path.name.lower() for token in ("unet", "colour", "baseline"))
            for path in annotator_files
        ):
            raise ValueError("Annotator-visible image filename is not opaque.")
        for path, row in zip(annotator_files, key_rows):
            exported = load_rgb(path)
            if hashlib.sha256(exported.tobytes()).hexdigest() != row["input_sha256"]:
                raise ValueError(f"Exported tile differs from source pixels: {path.name}")
        summary = {
            "status": "package_prepared",
            "selected_regions": 20,
            "seed": SELECTION_SEED,
            "regions_per_colour_stratum": {
                stratum: sum(row["colour_stratum"] == stratum for row in selected)
                for stratum in ("1", "2", "3", "4")
            },
            "selected_participant_ids": len(
                {row["participant_id"] for row in selected}
            ),
            "annotator_visible_files": sorted(actual_package_names),
            "unblinded_packet_files": len(list(UNBLINDED_DIR.iterdir())),
            "model_outputs_in_annotator_package": False,
            "source_ids_or_coordinates_in_annotator_filenames": False,
        }
        PACKAGE_AUDIT_PATH.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        completed = True
        print(json.dumps(summary, indent=2, sort_keys=True))
    finally:
        if not completed:
            for path in annotator_files:
                if path.exists():
                    path.unlink()
            template_path = ANNOTATOR_DIR / "PHASEB2_ANNOTATION_RETURN_TEMPLATE.csv"
            if template_path.exists():
                template_path.unlink()
            if KEY_PATH.exists():
                KEY_PATH.unlink()
            if PACKAGE_AUDIT_PATH.exists():
                PACKAGE_AUDIT_PATH.unlink()
            if UNBLINDED_DIR.exists():
                for path in UNBLINDED_DIR.iterdir():
                    if path.is_file():
                        path.unlink()
                UNBLINDED_DIR.rmdir()


if __name__ == "__main__":
    main()
