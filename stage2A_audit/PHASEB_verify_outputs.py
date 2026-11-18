"""Recompute Phase B selection, area, and objective-flag checks from saved files."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

ROOT = Path(r"D:\patent\stage2A_audit")
IMAGE_DIR = ROOT / "PHASEB_region_images"
MANIFEST_PATH = ROOT / "PHASEB_region_manifest.csv"
METRICS_PATH = ROOT / "PHASEB_region_metrics.csv"
FAILURES_PATH = ROOT / "PHASEB_failure_flags.csv"
TOP_PATH = ROOT / "PHASEB_top10_disagreement.csv"
SUMMARY_PATH = ROOT / "PHASEB_inference_summary.json"
CONTACT_PATH = ROOT / "PHASEB_contact_sheet.png"
REVIEW_PATH = ROOT / "PHASEB_REVIEW_FORM.csv"
OUTPUT_PATH = ROOT / "PHASEB_VERIFICATION.json"
TISSUE_THRESHOLD = 245.0
PALE_THRESHOLD = 225.0
SATURATION_THRESHOLD = 0.8
COLOUR_THRESHOLD = 2


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def read_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        if image.mode != "RGB" or image.size != (512, 512):
            raise ValueError(f"Unexpected image format: {path}")
        return np.asarray(image, dtype=np.uint8).copy()


def flag_values(image: np.ndarray, prediction: np.ndarray) -> dict[str, bool]:
    tissue = image.mean(axis=2) < TISSUE_THRESHOLD
    predicted_count = int(prediction.sum())
    tissue_count = int(tissue.sum())
    tissue_area = (
        float(np.logical_and(prediction, tissue).sum() / tissue_count)
        if tissue_count
        else 0.0
    )
    outside_fraction = (
        float(np.logical_and(prediction, ~tissue).sum() / predicted_count)
        if predicted_count
        else None
    )
    values = image[prediction]
    pale_fraction = (
        float(np.mean(values.mean(axis=1) >= PALE_THRESHOLD))
        if predicted_count
        else None
    )
    if predicted_count:
        maximum = values.max(axis=1).astype(np.float32)
        minimum = values.min(axis=1).astype(np.float32)
        saturation = np.divide(
            maximum - minimum,
            maximum,
            out=np.zeros(maximum.shape, dtype=np.float32),
            where=maximum > 0,
        )
        saturation_fraction = float(np.mean(saturation >= SATURATION_THRESHOLD))
    else:
        saturation_fraction = None

    gray = np.asarray(Image.fromarray(image).convert("L"), dtype=np.float32)
    centre = gray[1:-1, 1:-1]
    laplacian = (
        gray[:-2, 1:-1]
        + gray[2:, 1:-1]
        + gray[1:-1, :-2]
        + gray[1:-1, 2:]
        - 4.0 * centre
    )
    focus_variance = float(np.var(laplacian))
    return {
        "extreme_predicted_area": (
            predicted_count == 0 or tissue_area < 0.01 or tissue_area > 0.80
        ),
        "prediction_outside_tissue": (
            outside_fraction is not None and outside_fraction > 0.05
        ),
        "very_pale_predicted_pixels": (
            pale_fraction is not None and pale_fraction >= 0.20
        ),
        "highly_saturated_predicted_pixels": (
            saturation_fraction is not None and saturation_fraction >= 0.20
        ),
        "low_focus_heuristic": focus_variance < 50.0,
    }


def close(actual: float, expected: float, label: str) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(f"{label} mismatch: {actual} != {expected}")


def main() -> None:
    if OUTPUT_PATH.exists():
        raise FileExistsError(f"Refusing to overwrite {OUTPUT_PATH}")
    manifest = read_csv(MANIFEST_PATH)
    metric_rows = read_csv(METRICS_PATH)
    failure_rows = read_csv(FAILURES_PATH)
    top_rows = read_csv(TOP_PATH)
    review_rows = read_csv(REVIEW_PATH)
    summary: dict[str, Any] = json.loads(
        SUMMARY_PATH.read_text(encoding="utf-8")
    )
    if not (
        len(manifest)
        == len(metric_rows)
        == len(failure_rows)
        == len(review_rows)
        == 40
    ):
        raise ValueError("Phase B row counts do not reconcile to 40 regions.")

    ids = [row["region_id"] for row in manifest]
    if len(set(ids)) != 40:
        raise ValueError("Region IDs are not unique.")
    if {row["region_id"] for row in metric_rows} != set(ids):
        raise ValueError("Metric rows do not match selected region IDs.")
    if {row["region_id"] for row in failure_rows} != set(ids):
        raise ValueError("Failure rows do not match selected region IDs.")
    if any(
        any(row[column] for column in row if column != "region_id")
        for row in review_rows
    ):
        raise ValueError("The reviewer form contains a nonblank review field.")

    stratum_counts = Counter(row["colour_stratum"] for row in manifest)
    slide_counts = Counter(row["slide_id"] for row in manifest)
    participant_count = len({row["participant_id"] for row in manifest})
    expected_image_count = 0
    recomputed_flags: Counter[str] = Counter()
    recomputed_differences: list[tuple[str, float]] = []
    metric_by_id = {row["region_id"]: row for row in metric_rows}
    failure_by_id = {row["region_id"]: row for row in failure_rows}
    flag_names = (
        "extreme_predicted_area",
        "prediction_outside_tissue",
        "very_pale_predicted_pixels",
        "highly_saturated_predicted_pixels",
        "low_focus_heuristic",
    )

    for row in manifest:
        region_id = row["region_id"]
        image_path = IMAGE_DIR / f"{region_id}_input.png"
        image = read_rgb(image_path)
        tissue = image.mean(axis=2) < TISSUE_THRESHOLD
        unet_path = IMAGE_DIR / f"{region_id}_unet_mask.png"
        colour_path = IMAGE_DIR / f"{region_id}_colour_mask.png"
        with Image.open(unet_path) as unet_image:
            unet_mask = np.asarray(unet_image.convert("L"), dtype=np.uint8) == 255
        with Image.open(colour_path) as colour_image:
            colour_mask = (
                np.asarray(colour_image.convert("L"), dtype=np.uint8) == 255
            )
        if unet_mask.shape != (512, 512) or colour_mask.shape != (512, 512):
            raise ValueError(f"Prediction dimensions differ: {region_id}")
        if tissue.sum() == 0:
            raise ValueError(f"No tissue pixels in selected region {region_id}")
        unet_area = float(np.logical_and(unet_mask, tissue).sum() / tissue.sum())
        colour_area = float(
            np.logical_and(colour_mask, tissue).sum() / tissue.sum()
        )
        difference = abs(unet_area - colour_area) * 100.0
        metric_row = metric_by_id[region_id]
        close(
            unet_area,
            float(metric_row["unet_predicted_area_fraction_of_tissue"]),
            f"{region_id} U-Net area",
        )
        close(
            colour_area,
            float(metric_row["colour_predicted_area_fraction_of_tissue"]),
            f"{region_id} colour area",
        )
        close(
            difference,
            float(metric_row["absolute_area_difference_percentage_points"]),
            f"{region_id} area difference",
        )

        measured_flags = flag_values(image, unet_mask)
        stored_flags = failure_by_id[region_id]
        for name in flag_names:
            if measured_flags[name] != (stored_flags[name].lower() == "true"):
                raise ValueError(f"{region_id} flag mismatch: {name}")
            recomputed_flags[name] += int(measured_flags[name])
        recomputed_differences.append((region_id, difference))
        expected_image_count += 4

    expected_top = [
        region_id
        for region_id, _ in sorted(
            recomputed_differences, key=lambda value: (-value[1], value[0])
        )[:10]
    ]
    if [row["region_id"] for row in top_rows] != expected_top:
        raise ValueError("Top-10 colour/U-Net disagreement ranking does not match.")

    with Image.open(CONTACT_PATH) as contact_sheet:
        contact_size = list(contact_sheet.size)
    derivative_png_count = len(
        list(IMAGE_DIR.glob("*_unet_mask.png"))
        + list(IMAGE_DIR.glob("*_unet_overlay.png"))
        + list(IMAGE_DIR.glob("*_colour_mask.png"))
        + list(IMAGE_DIR.glob("*_colour_overlay.png"))
    )
    if derivative_png_count != expected_image_count:
        raise ValueError(
            f"Expected {expected_image_count} derived panel images, got "
            f"{derivative_png_count}"
        )
    if dict(recomputed_flags) != summary["objective_failure_flag_counts"]:
        raise ValueError("Recomputed objective flag totals differ from summary.")
    if (
        dict(stratum_counts) != summary["regions_per_colour_stratum"]
        or participant_count != summary["participants"]
        or len(slide_counts) != summary["slides"]
        or max(slide_counts.values()) != summary["maximum_regions_per_slide"]
    ):
        raise ValueError("Selection counts differ from the inference summary.")

    verification = {
        "status": "verified",
        "regions_reconciled": len(manifest),
        "regions_per_colour_stratum_recomputed": dict(sorted(stratum_counts.items())),
        "participants_recomputed": participant_count,
        "slides_recomputed": len(slide_counts),
        "maximum_regions_per_slide_recomputed": max(slide_counts.values()),
        "derived_region_pngs_recomputed": derivative_png_count,
        "contact_sheet_dimensions_pixels": contact_size,
        "objective_flag_counts_recomputed_from_saved_pixels": dict(
            sorted(recomputed_flags.items())
        ),
        "top10_disagreement_order_recomputed_from_saved_masks": expected_top,
        "review_form_rows_blank": len(review_rows),
        "reference_based_metrics": "not applicable; no independent aligned reference",
    }
    OUTPUT_PATH.write_text(
        json.dumps(verification, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(verification, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
