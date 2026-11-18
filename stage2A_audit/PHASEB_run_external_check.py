"""Apply the frozen Phase A model to preregistered KPMP TRI regions."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image, ImageDraw

ROOT = Path(r"D:\patent\stage2A_audit")
sys.path.insert(0, str(ROOT))
import PHASEA_run_audit as phase_a  # noqa: E402

CHECKPOINT = ROOT / "renfast_baseline_run" / "checkpoint_best.pt"
RUN_METADATA = ROOT / "renfast_baseline_run" / "run_metadata.json"
PHASEA_METRICS = ROOT / "PHASEA_final_metrics.json"
MANIFEST = ROOT / "PHASEB_region_manifest.csv"
IMAGE_DIR = ROOT / "PHASEB_region_images"
EXPECTED_CHECKPOINT_SHA256 = (
    "674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb"
)
TISSUE_THRESHOLD = 245.0
PALE_THRESHOLD = 225.0
SATURATION_THRESHOLD = 0.8
PREDICTION_THRESHOLD = 0.5

METRICS_PATH = ROOT / "PHASEB_region_metrics.csv"
FAILURES_PATH = ROOT / "PHASEB_failure_flags.csv"
TOP_DISAGREEMENT_PATH = ROOT / "PHASEB_top10_disagreement.csv"
CONTACT_SHEET_PATH = ROOT / "PHASEB_contact_sheet.png"
SUMMARY_PATH = ROOT / "PHASEB_inference_summary.json"
REVIEW_FORM_PATH = ROOT / "PHASEB_REVIEW_FORM.csv"
OUTPUT_PATHS = (
    METRICS_PATH,
    FAILURES_PATH,
    TOP_DISAGREEMENT_PATH,
    CONTACT_SHEET_PATH,
    SUMMARY_PATH,
    REVIEW_FORM_PATH,
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_manifest() -> list[dict[str, str]]:
    with MANIFEST.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def validate_manifest(rows: list[dict[str, str]]) -> None:
    if len(rows) != 40 or len({row["region_id"] for row in rows}) != 40:
        raise ValueError("Expected 40 unique preregistered regions.")
    if any(row["catalog_access"].lower() != "open" for row in rows):
        raise ValueError("A selected slide is not marked open in the local catalog.")
    if any(float(row["tissue_fraction"]) < 0.50 for row in rows):
        raise ValueError("A selected region is below the registered tissue fraction.")
    if any(float(row["target_mpp"]) != 4.1 for row in rows):
        raise ValueError("A selected region differs from the preregistered target MPP.")
    stratum_counts = Counter(row["colour_stratum"] for row in rows)
    if stratum_counts != Counter({"1": 10, "2": 10, "3": 10, "4": 10}):
        raise ValueError(f"Unexpected colour-stratum allocation: {stratum_counts}")
    slide_counts = Counter(row["slide_id"] for row in rows)
    if max(slide_counts.values()) > 3:
        raise ValueError("More than 3 regions were selected from a slide.")


def load_input(row: dict[str, str]) -> np.ndarray:
    image_path = ROOT / row["input_image"].replace("/", "\\")
    if not image_path.is_file():
        raise FileNotFoundError(f"Selected input tile is missing: {image_path}")
    with Image.open(image_path) as image:
        if image.mode != "RGB" or image.size != (512, 512):
            raise ValueError(f"Unexpected model input format: {image_path}")
        array = np.asarray(image, dtype=np.uint8).copy()
    actual_hash = hashlib.sha256(array.tobytes()).hexdigest()
    if actual_hash != row["input_sha256"]:
        raise ValueError(f"Selected input pixel hash mismatch: {row['region_id']}")
    return array


def overlay(
    image: np.ndarray, mask: np.ndarray, colour: tuple[int, int, int]
) -> np.ndarray:
    result = image.astype(np.float32).copy()
    result[mask] = 0.55 * result[mask] + 0.45 * np.asarray(colour, dtype=np.float32)
    return np.clip(result, 0, 255).astype(np.uint8)


def laplacian_variance(image: np.ndarray) -> float:
    grayscale = np.asarray(Image.fromarray(image).convert("L"), dtype=np.float32)
    centre = grayscale[1:-1, 1:-1]
    laplacian = (
        grayscale[:-2, 1:-1]
        + grayscale[2:, 1:-1]
        + grayscale[1:-1, :-2]
        + grayscale[1:-1, 2:]
        - 4.0 * centre
    )
    return float(np.var(laplacian))


def failure_measurements(
    image: np.ndarray, prediction: np.ndarray, tissue: np.ndarray
) -> dict[str, Any]:
    positive_count = int(prediction.sum())
    tissue_count = int(tissue.sum())
    positive_tissue_fraction = (
        float(np.logical_and(prediction, tissue).sum() / tissue_count)
        if tissue_count
        else 0.0
    )
    outside_fraction = (
        float(np.logical_and(prediction, ~tissue).sum() / positive_count)
        if positive_count
        else None
    )
    positive_pixels = image[prediction]
    pale_fraction = (
        float(np.mean(positive_pixels.mean(axis=1) >= PALE_THRESHOLD))
        if positive_count
        else None
    )
    maxima = positive_pixels.max(axis=1) if positive_count else np.array([])
    minima = positive_pixels.min(axis=1) if positive_count else np.array([])
    saturation = np.divide(
        maxima.astype(np.float32) - minima.astype(np.float32),
        maxima.astype(np.float32),
        out=np.zeros(maxima.shape, dtype=np.float32),
        where=maxima > 0,
    )
    saturated_fraction = (
        float(np.mean(saturation >= SATURATION_THRESHOLD))
        if positive_count
        else None
    )
    focus_variance = laplacian_variance(image)
    flags = {
        "extreme_predicted_area": (
            positive_count == 0
            or positive_tissue_fraction < 0.01
            or positive_tissue_fraction > 0.80
        ),
        "prediction_outside_tissue": (
            outside_fraction is not None and outside_fraction > 0.05
        ),
        "very_pale_predicted_pixels": (
            pale_fraction is not None and pale_fraction >= 0.20
        ),
        "highly_saturated_predicted_pixels": (
            saturated_fraction is not None and saturated_fraction >= 0.20
        ),
        "low_focus_heuristic": focus_variance < 50.0,
    }
    return {
        "predicted_positive_pixels": positive_count,
        "tissue_pixels": tissue_count,
        "predicted_area_fraction_of_tissue": positive_tissue_fraction,
        "predicted_positive_outside_tissue_fraction": outside_fraction,
        "pale_fraction_of_predicted_pixels": pale_fraction,
        "saturated_fraction_of_predicted_pixels": saturated_fraction,
        "laplacian_variance": focus_variance,
        **flags,
    }


def write_contact_sheet(
    entries: list[dict[str, Any]], output_path: Path
) -> None:
    panel_size = 160
    row_height = 182
    header_height = 32
    labels = (
        "Input",
        "U-Net mask",
        "U-Net overlay",
        "Colour mask",
        "Colour overlay",
    )
    sheet = Image.new(
        "RGB",
        (panel_size * len(labels), header_height + row_height * len(entries)),
        "white",
    )
    draw = ImageDraw.Draw(sheet)
    for column, label in enumerate(labels):
        draw.text((column * panel_size + 4, 8), label, fill="black")
    for index, entry in enumerate(entries):
        y = header_height + index * row_height
        draw.text((4, y + 1), entry["region_id"], fill="black")
        for column, panel in enumerate(entry["panels"]):
            tile = Image.fromarray(panel).resize(
                (panel_size, panel_size), Image.Resampling.LANCZOS
            )
            sheet.paste(tile, (column * panel_size, y + 20))
    sheet.save(output_path)


def main() -> None:
    existing = [str(path) for path in OUTPUT_PATHS if path.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite Phase B outputs: {existing}")
    required = (CHECKPOINT, RUN_METADATA, PHASEA_METRICS, MANIFEST)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Required frozen Phase B inputs are missing: {missing}")
    if not IMAGE_DIR.is_dir():
        raise FileNotFoundError(f"Selected input image folder is missing: {IMAGE_DIR}")

    rows = read_manifest()
    validate_manifest(rows)
    checkpoint_hash = phase_a.baseline.sha256_file(CHECKPOINT)
    run_metadata = read_json(RUN_METADATA)
    phase_a_metrics = read_json(PHASEA_METRICS)
    if checkpoint_hash != EXPECTED_CHECKPOINT_SHA256:
        raise ValueError("Frozen checkpoint hash differs from the registered value.")
    if run_metadata.get("checkpoint_sha256") != checkpoint_hash:
        raise ValueError("Checkpoint hash differs from the frozen run metadata.")
    if phase_a_metrics.get("hashes", {}).get("checkpoint_sha256") != checkpoint_hash:
        raise ValueError("Checkpoint hash differs from the Phase A report.")
    if run_metadata.get("threshold") != PREDICTION_THRESHOLD:
        raise ValueError("Frozen run metadata differs from the registered threshold.")
    colour_threshold = int(
        phase_a_metrics["colour_threshold"]["selected_t"]
    )
    if colour_threshold != 2:
        raise ValueError("Phase A colour baseline threshold is not the frozen value 2.")

    output_images = [
        IMAGE_DIR / f"{row['region_id']}_{suffix}.png"
        for row in rows
        for suffix in (
            "unet_mask",
            "unet_overlay",
            "colour_mask",
            "colour_overlay",
        )
    ]
    existing_images = [str(path) for path in output_images if path.exists()]
    if existing_images:
        raise FileExistsError(
            f"Refusing to overwrite Phase B region outputs: {existing_images[:5]}"
        )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(CHECKPOINT, map_location=device, weights_only=True)
    if checkpoint.get("threshold") != PREDICTION_THRESHOLD:
        raise ValueError("Checkpoint threshold differs from frozen threshold 0.5.")
    model = phase_a.baseline.UNet().to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    metrics_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    contact_entries: list[dict[str, Any]] = []
    with torch.no_grad():
        for row in rows:
            image = load_input(row)
            unet_prediction = phase_a.run_unet(image, model, device)
            colour_prediction = (
                image[:, :, 2].astype(np.int16)
                - image[:, :, 0].astype(np.int16)
                >= colour_threshold
            )
            tissue = image.mean(axis=2) < TISSUE_THRESHOLD
            measurements = failure_measurements(image, unet_prediction, tissue)
            colour_area_fraction = (
                float(np.logical_and(colour_prediction, tissue).sum() / tissue.sum())
                if tissue.any()
                else 0.0
            )
            area_difference = abs(
                measurements["predicted_area_fraction_of_tissue"]
                - colour_area_fraction
            )
            unet_mask = unet_prediction.astype(np.uint8) * 255
            colour_mask = colour_prediction.astype(np.uint8) * 255
            unet_overlay = overlay(image, unet_prediction, (255, 0, 0))
            colour_overlay = overlay(image, colour_prediction, (0, 100, 255))

            panels = {
                "unet_mask": unet_mask,
                "unet_overlay": unet_overlay,
                "colour_mask": colour_mask,
                "colour_overlay": colour_overlay,
            }
            for suffix, panel in panels.items():
                Image.fromarray(panel).save(
                    IMAGE_DIR / f"{row['region_id']}_{suffix}.png"
                )

            metric_row = {
                "region_id": row["region_id"],
                "participant_id": row["participant_id"],
                "slide_id": row["slide_id"],
                "colour_stratum": row["colour_stratum"],
                "tissue_fraction": float(row["tissue_fraction"]),
                "unet_predicted_area_fraction_of_tissue": measurements[
                    "predicted_area_fraction_of_tissue"
                ],
                "colour_predicted_area_fraction_of_tissue": colour_area_fraction,
                "absolute_area_difference_percentage_points": area_difference * 100.0,
                "predicted_positive_pixels": measurements[
                    "predicted_positive_pixels"
                ],
                "threshold": PREDICTION_THRESHOLD,
                "colour_threshold": colour_threshold,
            }
            metrics_rows.append(metric_row)
            failure_rows.append(
                {
                    "region_id": row["region_id"],
                    "participant_id": row["participant_id"],
                    "slide_id": row["slide_id"],
                    **measurements,
                }
            )
            contact_entries.append(
                {
                    "region_id": row["region_id"],
                    "panels": [
                        image,
                        unet_mask,
                        unet_overlay,
                        colour_mask,
                        colour_overlay,
                    ],
                }
            )

    write_contact_sheet(contact_entries, CONTACT_SHEET_PATH)
    top_disagreements = sorted(
        metrics_rows,
        key=lambda item: (
            -float(item["absolute_area_difference_percentage_points"]),
            item["region_id"],
        ),
    )[:10]

    with METRICS_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(metrics_rows[0]))
        writer.writeheader()
        writer.writerows(metrics_rows)
    with FAILURES_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(failure_rows[0]))
        writer.writeheader()
        writer.writerows(failure_rows)
    with TOP_DISAGREEMENT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(top_disagreements[0]))
        writer.writeheader()
        writer.writerows(top_disagreements)
    with REVIEW_FORM_PATH.open("w", newline="", encoding="utf-8") as file:
        fields = (
            "region_id",
            "reviewer_id",
            "fibrosis_present_yes_no",
            "model_outline_ok_1_to_5",
            "main_error_type",
            "free_text",
        )
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(
            {
                "region_id": row["region_id"],
                "reviewer_id": "",
                "fibrosis_present_yes_no": "",
                "model_outline_ok_1_to_5": "",
                "main_error_type": "",
                "free_text": "",
            }
            for row in rows
        )

    flag_names = (
        "extreme_predicted_area",
        "prediction_outside_tissue",
        "very_pale_predicted_pixels",
        "highly_saturated_predicted_pixels",
        "low_focus_heuristic",
    )
    flag_counts = {
        name: sum(bool(row[name]) for row in failure_rows) for name in flag_names
    }
    summary = {
        "status": "completed_research_only_external_sanity_check",
        "checkpoint_sha256": checkpoint_hash,
        "device": str(device),
        "colour_threshold": colour_threshold,
        "probability_threshold": PREDICTION_THRESHOLD,
        "regions": len(rows),
        "participants": len({row["participant_id"] for row in rows}),
        "slides": len({row["slide_id"] for row in rows}),
        "regions_per_colour_stratum": dict(
            sorted(Counter(row["colour_stratum"] for row in rows).items())
        ),
        "maximum_regions_per_slide": max(
            Counter(row["slide_id"] for row in rows).values()
        ),
        "objective_failure_flag_counts": flag_counts,
        "glomeruli_vessels_pen_marks": (
            "not assessable: no exact slide-matched spatially aligned annotations "
            "were identified before inference"
        ),
        "reference_based_metrics": "not computed; no independent aligned reference",
        "model_was_retrained_or_tuned": False,
        "regions_selected_using_model_outputs": False,
        "predicted_area_difference_unit": (
            "absolute percentage-point difference in predicted area fraction "
            "of tissue"
        ),
    }
    SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
