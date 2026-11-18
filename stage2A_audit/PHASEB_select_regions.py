"""Select fixed-scale KPMP TRI regions without running model inference."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import re
from pathlib import Path
from typing import Any

import numpy as np
import openslide
from PIL import Image

ROOT = Path(r"D:\patent")
AUDIT_DIR = ROOT / "stage2A_audit"
DATA_DIR = ROOT / "data"
CATALOG = ROOT / "atlas_repository_filelist-20261105.csv"
SEED = 20261118
TARGET_MPP = 4.1
REGION_SIZE = 512
MIN_TISSUE_FRACTION = 0.50
TISSUE_MEAN_RGB_THRESHOLD = 245.0
REGIONS_PER_STRATUM = 10
MAX_REGIONS_PER_SLIDE = 3

MANIFEST_PATH = AUDIT_DIR / "PHASEB_region_manifest.csv"
SLIDE_AUDIT_PATH = AUDIT_DIR / "PHASEB_slide_audit.csv"
SELECTION_JSON_PATH = AUDIT_DIR / "PHASEB_region_selection.json"
IMAGE_DIR = AUDIT_DIR / "PHASEB_region_images"
OUTPUT_PATHS = (MANIFEST_PATH, SLIDE_AUDIT_PATH, SELECTION_JSON_PATH, IMAGE_DIR)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def slide_identifier(filename: str) -> str:
    match = re.search(r"(S-\d{4}-\d{6})", filename)
    if match is None:
        raise ValueError(f"Cannot parse slide identifier from {filename!r}")
    return match.group(1)


def local_slide_path(row: dict[str, str]) -> Path | None:
    candidates = (
        ROOT / row["File Name"],
        DATA_DIR / row["Participant ID"] / "wsi" / row["File Name"],
    )
    return next((path for path in candidates if path.is_file()), None)


def slide_color_stat(thumbnail: Image.Image) -> tuple[float, int]:
    pixels = np.asarray(thumbnail.convert("RGB"), dtype=np.uint8)
    tissue = pixels.mean(axis=2) < TISSUE_MEAN_RGB_THRESHOLD
    if not tissue.any():
        return math.nan, 0
    blue_minus_red = (
        pixels[:, :, 2].astype(np.int16) - pixels[:, :, 0].astype(np.int16)
    )
    return float(np.median(blue_minus_red[tissue])), int(tissue.sum())


def collect_open_slides() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not CATALOG.is_file():
        raise FileNotFoundError(f"Local repository inventory is missing: {CATALOG}")
    if any(path.exists() for path in OUTPUT_PATHS):
        raise FileExistsError(
            "Refusing to overwrite existing Phase B selection outputs."
        )

    eligible: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    with CATALOG.open(newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))

    for row in rows:
        if not (
            row["Access"].strip().lower() == "open"
            and row["Data Category"] == "Pathology"
            and row["Data Format"].strip().lower() == "svs"
            and row["Workflow Type / Panel"] == "TRI stain"
        ):
            continue
        path = local_slide_path(row)
        if path is None:
            continue
        normalized_path = str(path.resolve()).casefold()
        if normalized_path in seen_paths:
            continue
        seen_paths.add(normalized_path)

        base_audit: dict[str, Any] = {
            "participant_id": row["Participant ID"],
            "slide_id": slide_identifier(row["File Name"]),
            "slide_filename": row["File Name"],
            "slide_path": str(path),
            "catalog_access": row["Access"],
            "catalog_size": row["Size"],
            "reuse_terms_in_catalog": "not stated",
            "local_file_bytes": path.stat().st_size,
        }
        try:
            slide = openslide.OpenSlide(str(path))
        except openslide.OpenSlideError as error:
            audit.append(
                {
                    **base_audit,
                    "eligible": False,
                    "exclusion_reason": f"OpenSlide read error: {error}",
                }
            )
            continue

        properties = slide.properties
        try:
            mpp_x = float(properties["openslide.mpp-x"])
            mpp_y = float(properties["openslide.mpp-y"])
        except (KeyError, ValueError):
            slide.close()
            audit.append(
                {
                    **base_audit,
                    "eligible": False,
                    "exclusion_reason": "Missing or invalid microns-per-pixel metadata",
                }
            )
            continue
        if mpp_x <= 0 or mpp_y <= 0:
            slide.close()
            audit.append(
                {
                    **base_audit,
                    "eligible": False,
                    "exclusion_reason": "Non-positive microns-per-pixel metadata",
                }
            )
            continue

        level = min(
            range(slide.level_count),
            key=lambda index: abs(
                math.sqrt(mpp_x * mpp_y) * slide.level_downsamples[index]
                - TARGET_MPP
            ),
        )
        downsample = float(slide.level_downsamples[level])
        level_mpp_x = mpp_x * downsample
        level_mpp_y = mpp_y * downsample
        thumbnail = slide.get_thumbnail((2048, 2048)).convert("RGB")
        colour_stat, thumbnail_tissue_pixels = slide_color_stat(thumbnail)
        dimensions = slide.level_dimensions[level]
        slide.close()

        if not math.isfinite(colour_stat) or thumbnail_tissue_pixels == 0:
            audit.append(
                {
                    **base_audit,
                    "eligible": False,
                    "exclusion_reason": "No tissue pixels in the slide thumbnail",
                    "mpp_x": mpp_x,
                    "mpp_y": mpp_y,
                }
            )
            continue

        source_width = max(
            1, round(REGION_SIZE * TARGET_MPP / level_mpp_x)
        )
        source_height = max(
            1, round(REGION_SIZE * TARGET_MPP / level_mpp_y)
        )
        candidates = [
            (x, y)
            for y in range(0, dimensions[1] - source_height + 1, source_height)
            for x in range(0, dimensions[0] - source_width + 1, source_width)
        ]
        if not candidates:
            audit.append(
                {
                    **base_audit,
                    "eligible": False,
                    "exclusion_reason": "Slide has no complete target-size grid cells",
                    "mpp_x": mpp_x,
                    "mpp_y": mpp_y,
                }
            )
            continue

        eligible.append(
            {
                **base_audit,
                "mpp_x": mpp_x,
                "mpp_y": mpp_y,
                "level": level,
                "level_downsample": downsample,
                "level_mpp_x": level_mpp_x,
                "level_mpp_y": level_mpp_y,
                "level_width": dimensions[0],
                "level_height": dimensions[1],
                "source_region_width": source_width,
                "source_region_height": source_height,
                "colour_stat_median_blue_minus_red": colour_stat,
                "thumbnail_tissue_pixels": thumbnail_tissue_pixels,
                "candidate_grid_cells": len(candidates),
                "candidates": candidates,
                "selected_count": 0,
            }
        )
        audit.append(
            {
                **eligible[-1],
                "eligible": True,
                "exclusion_reason": "",
            }
        )

    if len(eligible) < 4:
        raise RuntimeError(
            f"Only {len(eligible)} eligible open local TRI slides were found."
        )
    return eligible, audit


def read_candidate(
    slide_record: dict[str, Any], location: tuple[int, int]
) -> tuple[np.ndarray, float]:
    slide = openslide.OpenSlide(slide_record["slide_path"])
    x_level, y_level = location
    downsample = slide_record["level_downsample"]
    x0 = round(x_level * downsample)
    y0 = round(y_level * downsample)
    source_size = (
        slide_record["source_region_width"],
        slide_record["source_region_height"],
    )
    region = slide.read_region(
        (x0, y0), slide_record["level"], source_size
    ).convert("RGBA")
    slide.close()

    white = Image.new("RGBA", region.size, (255, 255, 255, 255))
    rgb = Image.alpha_composite(white, region).convert("RGB")
    rgb = rgb.resize(
        (REGION_SIZE, REGION_SIZE), Image.Resampling.LANCZOS
    )
    array = np.asarray(rgb, dtype=np.uint8).copy()
    tissue_fraction = float(
        np.mean(array.mean(axis=2) < TISSUE_MEAN_RGB_THRESHOLD)
    )
    return array, tissue_fraction


def assign_colour_strata(
    slides: list[dict[str, Any]], rng: random.Random
) -> None:
    ordered = sorted(
        slides,
        key=lambda item: (
            item["colour_stat_median_blue_minus_red"],
            item["slide_id"],
            item["slide_filename"],
        ),
    )
    strata = np.array_split(np.arange(len(ordered)), 4)
    for quartile, indexes in enumerate(strata, start=1):
        for index in indexes:
            ordered[int(index)]["colour_stratum"] = quartile
    for item in slides:
        rng.shuffle(item["candidates"])


def choose_regions(
    slides: list[dict[str, Any]], rng: random.Random
) -> tuple[list[dict[str, Any]], dict[str, np.ndarray]]:
    participant_counts: dict[str, int] = {}
    selected: list[dict[str, Any]] = []
    selected_images: dict[str, np.ndarray] = {}
    slide_counts: dict[str, int] = {}
    per_stratum_counts = {quartile: 0 for quartile in range(1, 5)}

    for quartile in range(1, 5):
        while per_stratum_counts[quartile] < REGIONS_PER_STRATUM:
            available = [
                slide
                for slide in slides
                if slide["colour_stratum"] == quartile
                and slide["selected_count"] < MAX_REGIONS_PER_SLIDE
                and slide["candidates"]
            ]
            if not available:
                raise RuntimeError(
                    f"Cannot fill colour stratum {quartile} to "
                    f"{REGIONS_PER_STRATUM} qualifying regions."
                )

            participant_candidates = sorted(
                {slide["participant_id"] for slide in available}
            )
            least_selected = min(
                participant_counts.get(participant, 0)
                for participant in participant_candidates
            )
            participant = rng.choice(
                [
                    participant
                    for participant in participant_candidates
                    if participant_counts.get(participant, 0) == least_selected
                ]
            )
            participant_slides = [
                slide
                for slide in available
                if slide["participant_id"] == participant
            ]
            least_from_slide = min(
                slide_counts.get(slide["slide_id"], 0)
                for slide in participant_slides
            )
            slide_record = rng.choice(
                [
                    slide
                    for slide in participant_slides
                    if slide_counts.get(slide["slide_id"], 0) == least_from_slide
                ]
            )

            x_level, y_level = slide_record["candidates"].pop()
            image, tissue_fraction = read_candidate(
                slide_record, (x_level, y_level)
            )
            if tissue_fraction < MIN_TISSUE_FRACTION:
                continue

            region_number = len(selected) + 1
            region_id = f"PHASEB_REGION_{region_number:03d}"
            image_name = f"PHASEB_region_{region_number:03d}_input.png"
            selected.append(
                {
                    "region_id": region_id,
                    "participant_id": slide_record["participant_id"],
                    "slide_id": slide_record["slide_id"],
                    "slide_filename": slide_record["slide_filename"],
                    "slide_path": slide_record["slide_path"],
                    "catalog_access": slide_record["catalog_access"],
                    "catalog_size": slide_record["catalog_size"],
                    "reuse_terms_in_catalog": slide_record[
                        "reuse_terms_in_catalog"
                    ],
                    "seed": SEED,
                    "colour_stat_median_blue_minus_red": slide_record[
                        "colour_stat_median_blue_minus_red"
                    ],
                    "colour_stratum": quartile,
                    "pyramid_level": slide_record["level"],
                    "level_downsample": slide_record["level_downsample"],
                    "mpp_x_at_level": slide_record["level_mpp_x"],
                    "mpp_y_at_level": slide_record["level_mpp_y"],
                    "target_mpp": TARGET_MPP,
                    "x_level_pixels": x_level,
                    "y_level_pixels": y_level,
                    "x_level0_pixels": round(
                        x_level * slide_record["level_downsample"]
                    ),
                    "y_level0_pixels": round(
                        y_level * slide_record["level_downsample"]
                    ),
                    "source_width_at_level": slide_record[
                        "source_region_width"
                    ],
                    "source_height_at_level": slide_record[
                        "source_region_height"
                    ],
                    "output_width_pixels": REGION_SIZE,
                    "output_height_pixels": REGION_SIZE,
                    "tissue_fraction": tissue_fraction,
                    "input_image": f"PHASEB_region_images/{image_name}",
                    "input_sha256": sha256_bytes(
                        Image.fromarray(image).tobytes()
                    ),
                }
            )
            selected_images[image_name] = image
            slide_record["selected_count"] += 1
            participant_counts[participant] = (
                participant_counts.get(participant, 0) + 1
            )
            slide_counts[slide_record["slide_id"]] = (
                slide_counts.get(slide_record["slide_id"], 0) + 1
            )
            per_stratum_counts[quartile] += 1

    if len(selected) != 40:
        raise AssertionError(f"Expected 40 selected regions, got {len(selected)}.")
    if max(slide_counts.values()) > MAX_REGIONS_PER_SLIDE:
        raise AssertionError("Selected more than three regions from a slide.")
    return selected, selected_images


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write an empty CSV: {path.name}")
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rng = random.Random(SEED)
    slides, audit = collect_open_slides()
    assign_colour_strata(slides, rng)
    regions, images = choose_regions(slides, rng)

    if any(path.exists() for path in OUTPUT_PATHS):
        raise FileExistsError(
            "A Phase B selection output appeared during selection; refusing to overwrite."
        )
    IMAGE_DIR.mkdir()
    for name, pixels in images.items():
        Image.fromarray(pixels).save(IMAGE_DIR / name)

    selected_by_filename = {
        row["slide_filename"]: sum(
            region["slide_filename"] == row["slide_filename"] for region in regions
        )
        for row in audit
        if row.get("eligible")
    }
    slide_by_filename = {slide["slide_filename"]: slide for slide in slides}
    audit_rows: list[dict[str, Any]] = []
    for row in audit:
        selected_slide = slide_by_filename.get(row["slide_filename"])
        audit_rows.append(
            {
                key: value
                for key, value in row.items()
                if key != "candidates"
            }
            | {
                "selected_regions": selected_by_filename.get(
                    row["slide_filename"], 0
                ),
                "colour_stratum": (
                    selected_slide.get("colour_stratum", "")
                    if selected_slide is not None
                    else ""
                ),
            }
        )
    write_csv(SLIDE_AUDIT_PATH, audit_rows)
    write_csv(MANIFEST_PATH, regions)
    selection = {
        "status": "regions_selected_before_model_inference",
        "seed": SEED,
        "requested_regions": 40,
        "selected_regions": len(regions),
        "regions_per_colour_stratum": {
            str(q): sum(row["colour_stratum"] == q for row in regions)
            for q in range(1, 5)
        },
        "eligible_open_local_tri_slides": len(slides),
        "participants_in_eligible_slides": len(
            {slide["participant_id"] for slide in slides}
        ),
        "participants_selected": len(
            {row["participant_id"] for row in regions}
        ),
        "maximum_regions_per_slide": max(
            sum(row["slide_id"] == slide["slide_id"] for row in regions)
            for slide in slides
        ),
        "tissue_fraction_minimum": MIN_TISSUE_FRACTION,
        "target_mpp": TARGET_MPP,
        "region_size_pixels": REGION_SIZE,
        "model_inference_performed": False,
        "region_selection_used_model_outputs": False,
        "input_image_hash": "SHA-256 of decoded 512x512 RGB pixel bytes",
    }
    SELECTION_JSON_PATH.write_text(
        json.dumps(selection, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(selection, indent=2))


if __name__ == "__main__":
    main()
