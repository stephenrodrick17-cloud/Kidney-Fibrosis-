from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import PIL
from PIL import Image

PROTO_ROOT = Path(__file__).resolve().parent
CHECKPOINT = Path(
    r"D:\patent\stage2A_audit\renfast_baseline_run\checkpoint_best.pt"
)
OOD_STATS = Path(r"D:\patent\stage2A_audit\PHASEC_ood_feature_stats.json")
EXPECTED_CHECKPOINT_SHA256 = (
    "674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb"
)
TARGET_MPP = 4.1
MIN_SCALE_FACTOR = 0.5
MAX_SCALE_FACTOR = 1.5
MIN_TISSUE_FRACTION = 0.20
MAX_INPUT_BYTES = 100 * 1024 * 1024
MAX_INPUT_PIXELS = 100_000_000
ALLOWED_FORMATS = {"PNG", "JPEG", "TIFF"}


class ValidationError(ValueError):
    def __init__(self, message: str, *, status: str = "REFUSED") -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class ImageAssessment:
    source_name: str
    image_format: str
    original_rgb: np.ndarray
    scaled_rgb: np.ndarray
    input_sha256: str
    input_bytes: int
    input_mpp: float
    scale_factor: float
    tissue_fraction: float
    rgb_features: dict[str, float]
    feature_z_scores: dict[str, float]
    status: str
    reasons: tuple[str, ...]
    stats_sha256: str


def load_warnings() -> list[str]:
    path = PROTO_ROOT / "PROTO_WARNINGS.md"
    if not path.is_file():
        raise FileNotFoundError(f"Required warnings file is missing: {path}")
    warnings: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r'W[1-5] "(.*)"', line.strip())
        if match:
            warnings.append(match.group(1))
    if len(warnings) != 5:
        raise ValueError("PROTO_WARNINGS.md must contain exactly W1 through W5.")
    return warnings


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_checkpoint_hash() -> str:
    if not CHECKPOINT.is_file():
        raise FileNotFoundError(f"Frozen checkpoint is missing: {CHECKPOINT}")
    observed = sha256_file(CHECKPOINT)
    if observed != EXPECTED_CHECKPOINT_SHA256:
        raise ValidationError(
            "Frozen checkpoint SHA-256 does not match the required value; refusing to run."
        )
    return observed


def read_rgb_input(source: str | Path | bytes, source_name: str | None = None
                   ) -> tuple[np.ndarray, str, bytes, str]:
    if isinstance(source, bytes):
        image_bytes = source
        name = source_name or "uploaded image"
    else:
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(f"Input image is missing: {path}")
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
            raise ValidationError("Input file must be PNG, JPEG, or TIFF.")
        name = source_name or path.name
        if path.stat().st_size > MAX_INPUT_BYTES:
            raise ValidationError("Input file exceeds the 100 MB size limit.")
        image_bytes = path.read_bytes()

    if len(image_bytes) > MAX_INPUT_BYTES:
        raise ValidationError("Input file exceeds the 100 MB size limit.")
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            image_format = (image.format or "").upper()
            if image_format not in ALLOWED_FORMATS:
                raise ValidationError("Input file must be PNG, JPEG, or TIFF.")
            if image.mode != "RGB":
                raise ValidationError(
                    f"Input must be readable RGB; this file is {image.mode}."
                )
            width, height = image.size
            if width <= 0 or height <= 0 or width * height > MAX_INPUT_PIXELS:
                raise ValidationError(
                    "Input exceeds the 100 megapixel size limit or has invalid dimensions."
                )
            image.load()
            rgb = np.asarray(image, dtype=np.uint8).copy()
    except (OSError, PIL.UnidentifiedImageError) as error:
        raise ValidationError(f"Input image cannot be read: {error}") from error
    return rgb, image_format, image_bytes, name


def _read_ood_stats() -> tuple[dict[str, Any], str]:
    if not OOD_STATS.is_file():
        raise FileNotFoundError(f"Training-only RGB reference data is missing: {OOD_STATS}")
    raw = OOD_STATS.read_bytes()
    stats = json.loads(raw.decode("utf-8"))
    required = ("feature_names", "mean", "sd")
    if any(key not in stats for key in required):
        raise ValueError("Training-only RGB reference data has an invalid shape.")
    if len(stats["feature_names"]) != 6 or len(stats["mean"]) != 6 or len(stats["sd"]) != 6:
        raise ValueError("Training-only RGB reference data must contain six features.")
    return stats, sha256_bytes(raw)


def validate_image(
    source: str | Path | bytes,
    input_mpp: float | None,
    source_name: str | None = None,
) -> ImageAssessment:
    if input_mpp is None or not math.isfinite(float(input_mpp)) or float(input_mpp) <= 0:
        raise ValidationError(
            "Micrometres per pixel is required. Enter the measured value; the tool will not guess."
        )
    original_rgb, image_format, image_bytes, name = read_rgb_input(source, source_name)
    scale_factor = float(input_mpp) / TARGET_MPP
    if not MIN_SCALE_FACTOR <= scale_factor <= MAX_SCALE_FACTOR:
        raise ValidationError(
            f"Scale factor {scale_factor:.6g} is outside the allowed 0.5x to 1.5x range."
        )

    original_height, original_width = original_rgb.shape[:2]
    scaled_width = max(1, int(round(original_width * scale_factor)))
    scaled_height = max(1, int(round(original_height * scale_factor)))
    if scaled_width * scaled_height > MAX_INPUT_PIXELS:
        raise ValidationError("Rescaled input exceeds the 100 megapixel size limit.")
    scaled_image = Image.fromarray(original_rgb, mode="RGB").resize(
        (scaled_width, scaled_height), resample=Image.Resampling.LANCZOS
    )
    scaled_rgb = np.asarray(scaled_image, dtype=np.uint8).copy()
    tissue = scaled_rgb.mean(axis=2) < 245.0
    tissue_fraction = float(tissue.mean())
    if tissue_fraction < MIN_TISSUE_FRACTION:
        raise ValidationError(
            f"Tissue fraction {tissue_fraction:.6f} is below 0.20; refusing this image."
        )

    channels = np.moveaxis(original_rgb.astype(np.float64), 2, 0)
    values = np.asarray(
        [channel.mean() for channel in channels]
        + [channel.std() for channel in channels],
        dtype=np.float64,
    )
    stats, stats_hash = _read_ood_stats()
    means = np.asarray(stats["mean"], dtype=np.float64)
    deviations = np.asarray(stats["sd"], dtype=np.float64)
    if np.any(~np.isfinite(means)) or np.any(~np.isfinite(deviations)) or np.any(deviations <= 0):
        raise ValueError("Training-only RGB reference values are invalid.")
    z_values = (values - means) / deviations
    feature_names = [str(name) for name in stats["feature_names"]]
    features = {key: float(value) for key, value in zip(feature_names, values)}
    z_scores = {key: float(value) for key, value in zip(feature_names, z_values)}
    unusual = [key for key, value in z_scores.items() if abs(value) > 3.0]
    reasons = tuple(
        f"RGB feature {key} is more than 3 training SDs from the training reference."
        for key in unusual
    )
    status = "UNUSUAL" if unusual else "IN RANGE"
    return ImageAssessment(
        source_name=name,
        image_format=image_format,
        original_rgb=original_rgb,
        scaled_rgb=scaled_rgb,
        input_sha256=sha256_bytes(image_bytes),
        input_bytes=len(image_bytes),
        input_mpp=float(input_mpp),
        scale_factor=scale_factor,
        tissue_fraction=tissue_fraction,
        rgb_features=features,
        feature_z_scores=z_scores,
        status=status,
        reasons=reasons,
        stats_sha256=stats_hash,
    )


def assessment_report(assessment: ImageAssessment) -> dict[str, Any]:
    return {
        "status": assessment.status,
        "source_name": assessment.source_name,
        "file_format": assessment.image_format,
        "input_dimensions": [
            int(assessment.original_rgb.shape[1]),
            int(assessment.original_rgb.shape[0]),
        ],
        "scaled_dimensions": [
            int(assessment.scaled_rgb.shape[1]),
            int(assessment.scaled_rgb.shape[0]),
        ],
        "input_bytes": assessment.input_bytes,
        "input_sha256": assessment.input_sha256,
        "input_micrometres_per_pixel": assessment.input_mpp,
        "scale_factor": assessment.scale_factor,
        "tissue_fraction": assessment.tissue_fraction,
        "tissue_rule": "RGB channel mean < 245",
        "rgb_features": assessment.rgb_features,
        "rgb_feature_measurement_scale": "original input RGB pixels, before resizing",
        "feature_z_scores": assessment.feature_z_scores,
        "screening_note": (
            "This is a screening heuristic. It flagged 0 of 50 RENFAST test images "
            "and has not been validated as an out-of-distribution detector."
        ),
        "reasons": list(assessment.reasons),
        "training_stats_sha256": assessment.stats_sha256,
        "warnings": load_warnings(),
    }


def main(argv: list[str] | None = None) -> int:
    print("\n".join(load_warnings()))
    parser = argparse.ArgumentParser(description="Check one image locally before processing.")
    parser.add_argument("--image", required=True, help="PNG, JPEG, or TIFF image path.")
    parser.add_argument(
        "--mpp",
        required=True,
        type=float,
        help="Measured input micrometres per pixel; the value is required.",
    )
    args = parser.parse_args(argv)
    try:
        verify_checkpoint_hash()
        assessment = validate_image(args.image, args.mpp)
    except (OSError, ValueError) as error:
        result = {
            "status": getattr(error, "status", "REFUSED"),
            "message": str(error),
            "warnings": load_warnings(),
        }
        print(json.dumps(result, indent=2))
        return 2
    print(json.dumps(assessment_report(assessment), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
