"""Compute boundary-distance metrics for the frozen RENFAST test predictions."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image
from scipy import ndimage
from torch.nn import functional as F

import run_renfast_baseline as baseline


ROOT = Path(r"D:\patent\stage2A_audit")
ARCHIVE = Path(r"D:\patent\m2t49zf6xr-1.zip")
OUTPUT_DIR = ROOT / "renfast_baseline_run"
CHECKPOINT = OUTPUT_DIR / "checkpoint_best.pt"
RUN_METADATA = OUTPUT_DIR / "run_metadata.json"
AUDIT_SUMMARY = OUTPUT_DIR / "audit_summary.json"
TEST_METRICS = OUTPUT_DIR / "test_metrics.json"
PAIR_MANIFEST = OUTPUT_DIR / "renfast_pair_manifest.csv"
OUTPUT_JSON = OUTPUT_DIR / "boundary_metrics.json"
OUTPUT_CSV = OUTPUT_DIR / "boundary_metrics_per_image.csv"


def boundary_distances(
    prediction: np.ndarray, target: np.ndarray
) -> dict[str, float | None]:
    """Return symmetric mean and 95th-percentile contour distances in pixels."""
    prediction = prediction.astype(bool)
    target = target.astype(bool)
    structure = np.ones((3, 3), dtype=bool)
    prediction_boundary = prediction & ~ndimage.binary_erosion(
        prediction, structure=structure, border_value=0
    )
    target_boundary = target & ~ndimage.binary_erosion(
        target, structure=structure, border_value=0
    )

    if not prediction_boundary.any() or not target_boundary.any():
        return {
            "assd_pixels": None,
            "hd95_pixels": None,
        }

    distance_to_target = ndimage.distance_transform_edt(~target_boundary)
    distance_to_prediction = ndimage.distance_transform_edt(~prediction_boundary)
    distances = np.concatenate(
        (
            distance_to_target[prediction_boundary],
            distance_to_prediction[target_boundary],
        )
    )
    return {
        "assd_pixels": float(np.mean(distances)),
        "hd95_pixels": float(np.percentile(distances, 95)),
    }


def read_manifest() -> dict[tuple[str, str], dict[str, str]]:
    with PAIR_MANIFEST.open(newline="", encoding="utf-8-sig") as file:
        rows = csv.DictReader(file)
        return {
            (row["image_member"], row["mask_member"]): row for row in rows
        }


def load_test_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    if OUTPUT_JSON.exists() or OUTPUT_CSV.exists():
        raise FileExistsError(
            "Boundary evaluation output already exists; refusing to overwrite it."
        )
    required = (
        ARCHIVE,
        CHECKPOINT,
        RUN_METADATA,
        AUDIT_SUMMARY,
        TEST_METRICS,
        PAIR_MANIFEST,
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Required baseline files are missing: {missing}")

    run_metadata = json.loads(RUN_METADATA.read_text(encoding="utf-8"))
    audit_summary = json.loads(AUDIT_SUMMARY.read_text(encoding="utf-8"))
    test_metrics = json.loads(TEST_METRICS.read_text(encoding="utf-8"))
    checkpoint_hash = baseline.sha256_file(CHECKPOINT)

    if run_metadata.get("status") != "completed":
        raise ValueError("The frozen training run is not marked completed.")
    if run_metadata.get("checkpoint_sha256") != checkpoint_hash:
        raise ValueError("Checkpoint hash differs from the frozen training record.")
    if test_metrics.get("checkpoint_sha256") != checkpoint_hash:
        raise ValueError("Checkpoint hash differs from the saved test evaluation.")
    if baseline.sha256_file(ARCHIVE) != audit_summary.get("archive_sha256"):
        raise ValueError("RENFAST archive hash differs from the audited archive.")
    if test_metrics.get("status") != "completed":
        raise ValueError("The saved test evaluation is not complete.")

    manifest = read_manifest()
    for record in test_metrics["per_image_metrics"]:
        key = (record["image_member"], record["mask_member"])
        if key not in manifest:
            raise ValueError(f"Test pair is missing from the manifest: {key}")
        row = manifest[key]
        if row.get("source_split") != "FIBROSIS_TEST":
            raise ValueError(f"Test pair is not from the official test split: {key}")

    return test_metrics, manifest


def main() -> None:
    test_metrics, manifest = load_test_inputs()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(CHECKPOINT, map_location=device, weights_only=True)
    if checkpoint.get("threshold") != baseline.THRESHOLD:
        raise ValueError("Checkpoint threshold differs from the saved evaluation.")

    model = baseline.UNet().to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    results: list[dict[str, Any]] = []
    with zipfile.ZipFile(ARCHIVE) as archive, torch.no_grad():
        for saved in test_metrics["per_image_metrics"]:
            key = (saved["image_member"], saved["mask_member"])
            manifest_row = manifest[key]
            image_bytes = archive.read(saved["image_member"])
            mask_bytes = archive.read(saved["mask_member"])
            if baseline.sha256_bytes(image_bytes) != manifest_row["image_sha256"]:
                raise ValueError(f"Test image hash mismatch: {saved['image_member']}")
            if baseline.sha256_bytes(mask_bytes) != manifest_row["mask_sha256"]:
                raise ValueError(f"Test mask hash mismatch: {saved['mask_member']}")

            with Image.open(io.BytesIO(image_bytes)) as image:
                image_array = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
            with Image.open(io.BytesIO(mask_bytes)) as mask:
                mask_array = np.asarray(mask.convert("L"), dtype=np.uint8).copy()
            if image_array.shape[:2] != mask_array.shape:
                raise ValueError(f"Image/mask dimensions differ: {saved['stem']}")

            height, width = mask_array.shape
            pad_height = (-height) % 16
            pad_width = (-width) % 16
            input_tensor = (
                torch.from_numpy(image_array)
                .permute(2, 0, 1)
                .float()
                .div_(255.0)
            )
            input_tensor = F.pad(
                input_tensor, (0, pad_width, 0, pad_height)
            )[None].to(device)
            probability = torch.sigmoid(model(input_tensor))[0, 0, :height, :width]
            prediction = (probability >= baseline.THRESHOLD).cpu().numpy()
            target = mask_array == 255
            pixel_metrics = baseline.pixel_metrics(prediction, target)
            for metric in ("dice", "iou", "sensitivity", "specificity"):
                saved_value = saved[metric]
                current_value = pixel_metrics[metric]
                if saved_value is None:
                    matches = current_value is None
                else:
                    matches = current_value is not None and np.isclose(
                        float(saved_value), current_value, rtol=0.0, atol=1e-12
                    )
                if not matches:
                    raise ValueError(
                        f"Recomputed {metric} differs from saved evaluation "
                        f"for {saved['stem']}: {current_value} vs {saved_value}"
                    )

            results.append(
                {
                    "stem": saved["stem"],
                    "family_id": saved["family_id"],
                    "image_member": saved["image_member"],
                    "mask_member": saved["mask_member"],
                    **pixel_metrics,
                    **boundary_distances(prediction, target),
                }
            )

    metric_names = ("assd_pixels", "hd95_pixels")
    summary = {
        "status": "completed",
        "checkpoint_sha256": test_metrics["checkpoint_sha256"],
        "archive_sha256": baseline.sha256_file(ARCHIVE),
        "threshold": baseline.THRESHOLD,
        "test_images": len(results),
        "reproduced_saved_pixel_metrics": True,
        "test_filename_families": sorted(
            {record["family_id"] for record in results}
        ),
        "family_ids_are_verified_patient_ids": False,
        "boundary_definition": (
            "Eight-connected contour: mask minus 3x3 binary erosion; "
            "Euclidean distances are pooled in both directions. ASSD is the "
            "mean and HD95 the 95th percentile of those distances."
        ),
        "distance_units": "pixels; physical pixel spacing is unavailable",
        "macro_per_image_metrics": {
            metric: float(
                np.mean(
                    [
                        record[metric]
                        for record in results
                        if record[metric] is not None
                    ]
                )
            )
            for metric in metric_names
        },
        "group_bootstrap_95_percent_confidence_intervals": {
            metric: baseline.bootstrap_ci(
                results, metric, baseline.BOOTSTRAP_SEED
            )
            for metric in metric_names
        },
        "bootstrap_resamples": 10_000,
        "bootstrap_seed": baseline.BOOTSTRAP_SEED,
        "images_with_undefined_boundary_metrics": sum(
            record["assd_pixels"] is None for record in results
        ),
        "per_image_metrics": results,
    }

    OUTPUT_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    print(
        json.dumps(
            {key: value for key, value in summary.items() if key != "per_image_metrics"},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
