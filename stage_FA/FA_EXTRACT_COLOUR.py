from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import platform
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np
import PIL
import torch
from PIL import Image

import FA_RUN_IMAGES as image_runner

ROOT = Path(r"D:\patent")
OUT = ROOT / "stage_FA"
ALIGNMENT = ROOT / "stage_G2" / "GENE2_ALIGNMENT_AUDIT.csv"
SCORE_FILE = OUT / "FA_SPOT_FIBROSIS_SCORES.csv"
ANALYSIS_LABEL = "EXPLORATORY, NOT CONFIRMATORY"
MASK_LABEL = "UNVALIDATED MASKS"
ASSET_STATUS = "RESEARCH-ONLY"
MAX_RUNTIME_SECONDS = 95 * 60
MAX_OUTPUT_BYTES = 8 * 1024**3


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def directory_size(path: Path) -> int:
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {path}")
    if not rows:
        raise ValueError(f"Refusing to write an empty output table: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    started = time.monotonic()
    deadline = started + MAX_RUNTIME_SECONDS
    started_utc = datetime.now(timezone.utc)
    if not SCORE_FILE.is_file() or not ALIGNMENT.is_file():
        raise FileNotFoundError("Required Stage FA spot scores or alignment audit are missing.")
    if directory_size(OUT) >= MAX_OUTPUT_BYTES:
        raise RuntimeError("Stage FA output folder already meets the registered size limit.")

    alignments = read_csv(ALIGNMENT)
    score_rows = read_csv(SCORE_FILE)
    score_by_key = {
        (row["participant_id"], row["library_id"], row["barcode"]): row
        for row in score_rows
    }
    if len(score_by_key) != len(score_rows):
        raise ValueError("Duplicate full spot keys in the saved mask-score table.")
    if any(row["analysis_label"] != ANALYSIS_LABEL for row in score_rows):
        raise ValueError("Saved mask-score table has an unexpected analysis label.")

    spot_colour_rows: list[dict[str, object]] = []
    slide_rows: list[dict[str, object]] = []
    hash_rows: list[dict[str, object]] = []
    archive_hash_cache: dict[Path, str] = {}

    def add_hash(source_path: Path, member: str | None, content: bytes, kind: str) -> None:
        if member is not None and source_path not in archive_hash_cache:
            archive_hash_cache[source_path] = sha256_file(source_path)
            hash_rows.append(
                {
                    "analysis_label": ANALYSIS_LABEL,
                    "mask_status": MASK_LABEL,
                    "asset_status": ASSET_STATUS,
                    "record_type": "input",
                    "source_kind": "source archive file",
                    "source_path": str(source_path),
                    "archive_member": "",
                    "sha256": archive_hash_cache[source_path],
                }
            )
        hash_rows.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "record_type": "input",
                "source_kind": kind,
                "source_path": str(source_path),
                "archive_member": member or "",
                "sha256": image_runner.sha256_bytes(content),
            }
        )

    for index, row in enumerate(alignments, start=1):
        if time.monotonic() >= deadline:
            raise TimeoutError("Stopped before the preregistered 100-minute process limit.")
        if directory_size(OUT) >= MAX_OUTPUT_BYTES:
            raise RuntimeError("Stopped before the preregistered 8 GB output limit.")
        participant = row["participant_id"]
        library = row["library_id"]
        key_prefix = (participant, library)
        image_ref = image_runner.resolve_row_reference(row["image_record"], row)
        positions_ref = image_runner.resolve_row_reference(row["spatial_positions"], row)
        scale_ref = image_runner.sibling_reference(image_ref, "scalefactors_json.json")
        image_bytes, image_source, image_member = image_runner.read_reference(image_ref)
        position_bytes, position_source, position_member = image_runner.read_reference(positions_ref)
        scale_bytes, scale_source, scale_member = image_runner.read_reference(scale_ref)
        add_hash(image_source, image_member, image_bytes, "slide image")
        add_hash(position_source, position_member, position_bytes, "spot positions")
        add_hash(scale_source, scale_member, scale_bytes, "scale factors")

        with Image.open(io.BytesIO(image_bytes)) as source_image:
            hires = np.asarray(source_image.convert("RGB"), dtype=np.uint8).copy()
        scale = json.loads(scale_bytes.decode("utf-8"))
        spot_diameter_fullres = float(scale["spot_diameter_fullres"])
        hires_scale = float(scale["tissue_hires_scalef"])
        source_mpp = image_runner.NOMINAL_SPOT_UM / (spot_diameter_fullres * hires_scale)
        factor = source_mpp / image_runner.TARGET_MPP
        old_height, old_width = hires.shape[:2]
        width = max(1, int(round(old_width * factor)))
        height = max(1, int(round(old_height * factor)))
        image = np.asarray(
            Image.fromarray(hires, mode="RGB").resize(
                (width, height), resample=Image.Resampling.LANCZOS
            ),
            dtype=np.uint8,
        ).copy()
        scale_x = width / old_width
        scale_y = height / old_height
        positions = image_runner.read_positions(position_bytes)
        tissue = image.mean(axis=2) < 245.0
        hsv = np.asarray(Image.fromarray(image, mode="RGB").convert("HSV"))
        tissue_pixels = int(tissue.sum())
        if tissue_pixels == 0:
            raise ValueError(f"No tissue pixels under the registered rule: {participant}/{library}")
        mask_path = OUT / f"FA_MASK_{participant}_{library}.npz"
        with np.load(mask_path, allow_pickle=False) as masks:
            unet_mask = masks["unet_mask"].astype(bool)
            colour_mask = masks["colour_mask"].astype(bool)
            if str(masks["analysis_label"].item()) != ANALYSIS_LABEL:
                raise ValueError(f"Unexpected label in mask file: {mask_path}")
            if str(masks["mask_status"].item()) != MASK_LABEL:
                raise ValueError(f"Unexpected mask status in mask file: {mask_path}")
        if unet_mask.shape != tissue.shape or colour_mask.shape != tissue.shape:
            raise ValueError(f"Mask/image dimensions differ for {participant}/{library}.")

        mask_values = {
            "unet": unet_mask,
            "colour": colour_mask,
        }
        fibrosis_percent = {
            name: 100.0 * float(np.logical_and(mask, tissue).sum()) / tissue_pixels
            for name, mask in mask_values.items()
        }
        hue_tissue = hsv[:, :, 0][tissue].astype(np.float64)
        slide_hue = float(np.median(hue_tissue))
        slide_saturation = float(hsv[:, :, 1][tissue].mean() / 255.0)
        slide_value = float(hsv[:, :, 2][tissue].mean() / 255.0)
        radius = image_runner.SPOT_DIAMETER_PX / 2.0
        score_recheck_max = 0.0
        included_count = 0

        for position in positions:
            key = (participant, library, str(position["barcode"]))
            score = score_by_key.get(key)
            if score is None:
                continue
            center_x = float(position["pixel_col_fullres"]) * hires_scale * scale_x
            center_y = float(position["pixel_row_fullres"]) * hires_scale * scale_y
            x0 = int(math.floor(center_x - radius))
            x1 = int(math.ceil(center_x + radius)) + 1
            y0 = int(math.floor(center_y - radius))
            y1 = int(math.ceil(center_y + radius)) + 1
            if x0 < 0 or y0 < 0 or x1 > width or y1 > height:
                if score["included"].lower() == "true":
                    raise ValueError(f"Saved included spot now maps outside the image: {key}")
                continue
            yy, xx = np.ogrid[y0:y1, x0:x1]
            footprint = (xx - center_x) ** 2 + (yy - center_y) ** 2 <= radius**2
            tissue_patch = tissue[y0:y1, x0:x1]
            denominator = int(footprint.sum())
            tissue_in_footprint = footprint & tissue_patch
            tissue_fraction = float(tissue_in_footprint.sum() / denominator)
            unet_score = float(unet_mask[y0:y1, x0:x1][footprint].mean())
            colour_score = float(colour_mask[y0:y1, x0:x1][footprint].mean())
            stored_included = score["included"].lower() == "true"
            is_included = (
                int(position["in_tissue"]) == 1
                and x0 >= 0
                and y0 >= 0
                and x1 <= width
                and y1 <= height
                and tissue_fraction > 0
            )
            if is_included != stored_included:
                raise ValueError(f"Spot inclusion differs from saved mask scores: {key}")
            if stored_included:
                score_recheck_max = max(
                    score_recheck_max,
                    abs(unet_score - float(score["unet_fibrosis_fraction"])),
                    abs(colour_score - float(score["colour_fibrosis_fraction"])),
                    abs(tissue_fraction - float(score["tissue_fraction"])),
                )
                pixels = hsv[y0:y1, x0:x1][tissue_in_footprint].astype(np.float64)
                hue_angle = pixels[:, 0] * (2.0 * math.pi / 256.0)
                mean_hue = float(
                    (math.atan2(float(np.sin(hue_angle).mean()), float(np.cos(hue_angle).mean())) % (2.0 * math.pi))
                    * 256.0
                    / (2.0 * math.pi)
                )
                included_count += 1
                spot_colour_rows.append(
                    {
                        "analysis_label": ANALYSIS_LABEL,
                        "mask_status": MASK_LABEL,
                        "asset_status": ASSET_STATUS,
                        "participant_id": participant,
                        "library_id": library,
                        "barcode": key[2],
                        "mean_hue": mean_hue,
                        "mean_saturation": float(pixels[:, 1].mean() / 255.0),
                        "mean_value": float(pixels[:, 2].mean() / 255.0),
                    }
                )
        if score_recheck_max > 1e-12:
            raise ValueError(
                f"Saved mask scores differ on the image-only recheck for {participant}/{library}: "
                f"{score_recheck_max}"
            )
        expected_included = sum(
            key[:2] == key_prefix and value["included"].lower() == "true"
            for key, value in score_by_key.items()
        )
        if included_count != expected_included:
            raise ValueError(
                f"Included spot count changed for {participant}/{library}: "
                f"{included_count} != {expected_included}"
            )
        slide_rows.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "participant_id": participant,
                "library_id": library,
                "tissue_pixels": tissue_pixels,
                "unet_positive_tissue_pixels": int(np.logical_and(unet_mask, tissue).sum()),
                "colour_positive_tissue_pixels": int(np.logical_and(colour_mask, tissue).sum()),
                "unet_fibrosis_percent_tissue": fibrosis_percent["unet"],
                "colour_fibrosis_percent_tissue": fibrosis_percent["colour"],
                "median_tissue_hue": slide_hue,
                "mean_tissue_saturation": slide_saturation,
                "mean_tissue_value": slide_value,
                "included_spots": included_count,
                "max_spot_score_recheck_difference": score_recheck_max,
                "spot_score_recheck": "PASS",
            }
        )
        print(f"Extracted colour features {index}/{len(alignments)}: {participant}/{library}")

    spot_keys = [
        (row["participant_id"], row["library_id"], row["barcode"])
        for row in spot_colour_rows
    ]
    if len(spot_keys) != len(set(spot_keys)):
        raise ValueError("Duplicate full spot key in extracted colour features.")
    expected_spot_keys = {
        key
        for key, row in score_by_key.items()
        if row["included"].lower() == "true"
    }
    if set(spot_keys) != expected_spot_keys:
        raise ValueError("Extracted colour spot keys do not exactly match included mask-score keys.")

    spot_path = OUT / "FA_SPOT_COLOUR.csv"
    slide_path = OUT / "FA_SLIDE_FIBROSIS_FRACTIONS.csv"
    write_csv(spot_path, spot_colour_rows)
    write_csv(slide_path, slide_rows)
    for path in (
        ALIGNMENT,
        SCORE_FILE,
        OUT / "FA_PREREG.md",
        OUT / "FA_DEVIATIONS.md",
        OUT / "FA_RUN_IMAGES.py",
        OUT / "FA_EXTRACT_COLOUR.py",
    ):
        hash_rows.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "record_type": "input",
                "source_kind": "alignment, image score, or protocol",
                "source_path": str(path),
                "archive_member": "",
                "sha256": sha256_file(path),
            }
        )
    for path in [OUT / f"FA_MASK_{row['participant_id']}_{row['library_id']}.npz" for row in alignments]:
        hash_rows.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "record_type": "input",
                "source_kind": "saved Stage FA mask",
                "source_path": str(path),
                "archive_member": "",
                "sha256": sha256_file(path),
            }
        )
    for path in (spot_path, slide_path):
        hash_rows.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "record_type": "output",
                "source_kind": "image-only Stage FA colour/fraction output",
                "source_path": str(path),
                "archive_member": "",
                "sha256": sha256_file(path),
            }
        )
    hash_path = OUT / "FA_COLOUR_HASHES.csv"
    write_csv(hash_path, hash_rows)
    metadata = {
        "analysis_label": ANALYSIS_LABEL,
        "mask_status": MASK_LABEL,
        "asset_status": ASSET_STATUS,
        "libraries": len(alignments),
        "included_spots": len(spot_colour_rows),
        "maximum_score_recheck_difference": max(
            float(row["max_spot_score_recheck_difference"]) for row in slide_rows
        ),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pillow": PIL.__version__,
        "pytorch": torch.__version__,
        "command": "python -B D:\\patent\\stage_FA\\FA_EXTRACT_COLOUR.py",
        "started_at_utc": started_utc.isoformat(),
        "runtime_seconds": round(time.monotonic() - started, 3),
        "outputs_bytes": directory_size(OUT),
        "expression_files_read": False,
    }
    metadata_path = OUT / "FA_COLOUR_RUN_METADATA.json"
    if metadata_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {metadata_path}")
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
