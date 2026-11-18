from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import PIL
import torch
from PIL import Image, PngImagePlugin

sys.dont_write_bytecode = True

import PROTO_VALIDATE as validate

MODEL_SOURCE = Path(r"D:\patent\stage2A_audit\run_renfast_baseline.py")
MODEL_SOURCE_DIR = MODEL_SOURCE.parent
TARGET_MPP = 4.1
TILE_SIZE = 512
PROBABILITY_THRESHOLD = 0.5
COLOUR_THRESHOLD = 2
MAX_RUNTIME_SECONDS = 7_190
MAX_OUTPUT_BYTES = 10 * 1024**3


@dataclass(frozen=True)
class QuantificationResult:
    assessment: validate.ImageAssessment
    unet_mask_scaled: np.ndarray
    colour_mask_scaled: np.ndarray
    unet_mask_original: np.ndarray
    colour_mask_original: np.ndarray
    unet_percent_tissue: float
    colour_percent_tissue: float
    tissue_pixels: int
    differing_by_more_than_15_pp: bool
    checkpoint_sha256: str
    runtime_seconds: float


def _load_model_class() -> type[torch.nn.Module]:
    if not MODEL_SOURCE.is_file():
        raise FileNotFoundError(f"Read-only Phase A model source is missing: {MODEL_SOURCE}")
    spec = importlib.util.spec_from_file_location("proto_phase_a_model", MODEL_SOURCE)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load the read-only model definition: {MODEL_SOURCE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if getattr(module, "THRESHOLD", None) != PROBABILITY_THRESHOLD:
        raise ValueError("Phase A source threshold differs from the frozen threshold.")
    return module.UNet


def load_frozen_model(device: torch.device | None = None
                      ) -> tuple[torch.nn.Module, torch.device, str]:
    checkpoint_hash = validate.verify_checkpoint_hash()
    chosen_device = device or torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )
    checkpoint = torch.load(
        validate.CHECKPOINT, map_location=chosen_device, weights_only=True
    )
    if checkpoint.get("threshold") != PROBABILITY_THRESHOLD:
        raise ValueError("Frozen checkpoint threshold is not 0.5; refusing to run.")
    unet_class = _load_model_class()
    model = unet_class().to(chosen_device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model, chosen_device, checkpoint_hash


def run_unet(
    model: torch.nn.Module,
    image: np.ndarray,
    device: torch.device,
    deadline: float,
) -> np.ndarray:
    height, width = image.shape[:2]
    output = np.zeros((height, width), dtype=np.bool_)
    for top in range(0, height, TILE_SIZE):
        for left in range(0, width, TILE_SIZE):
            if time.monotonic() >= deadline:
                raise TimeoutError("Stopped before the two-hour run limit.")
            tile_height = min(TILE_SIZE, height - top)
            tile_width = min(TILE_SIZE, width - left)
            tile = np.full((TILE_SIZE, TILE_SIZE, 3), 255, dtype=np.uint8)
            tile[:tile_height, :tile_width] = image[
                top : top + tile_height, left : left + tile_width
            ]
            tensor = (
                torch.from_numpy(tile)
                .permute(2, 0, 1)
                .float()
                .div_(255.0)
                .unsqueeze(0)
                .to(device)
            )
            with torch.inference_mode():
                probability = torch.sigmoid(model(tensor))[0, 0, :tile_height, :tile_width]
            output[top : top + tile_height, left : left + tile_width] = (
                probability.cpu().numpy() >= PROBABILITY_THRESHOLD
            )
    return output


def _map_mask_to_original(mask: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    binary = Image.fromarray((mask.astype(np.uint8) * 255), mode="L")
    mapped = binary.resize(size, resample=Image.Resampling.NEAREST)
    return np.asarray(mapped, dtype=np.uint8) == 255


def _percent_within_tissue(mask: np.ndarray, tissue: np.ndarray) -> tuple[float, int]:
    tissue_pixels = int(tissue.sum())
    if tissue_pixels == 0:
        raise ValueError("No tissue pixels are available for the percentage.")
    positive_tissue_pixels = int(np.logical_and(mask, tissue).sum())
    return 100.0 * positive_tissue_pixels / tissue_pixels, tissue_pixels


def quantify_arrays(
    assessment: validate.ImageAssessment,
    model: torch.nn.Module,
    device: torch.device,
    checkpoint_sha256: str,
    started_monotonic: float | None = None,
) -> QuantificationResult:
    started = time.monotonic() if started_monotonic is None else started_monotonic
    deadline = started + MAX_RUNTIME_SECONDS
    unet_mask = run_unet(model, assessment.scaled_rgb, device, deadline)
    colour_mask = (
        assessment.scaled_rgb[:, :, 2].astype(np.int16)
        - assessment.scaled_rgb[:, :, 0].astype(np.int16)
        >= COLOUR_THRESHOLD
    )
    tissue = assessment.scaled_rgb.mean(axis=2) < 245.0
    unet_percent, tissue_pixels = _percent_within_tissue(unet_mask, tissue)
    colour_percent, _ = _percent_within_tissue(colour_mask, tissue)
    height, width = assessment.original_rgb.shape[:2]
    unet_original = _map_mask_to_original(unet_mask, (width, height))
    colour_original = _map_mask_to_original(colour_mask, (width, height))
    return QuantificationResult(
        assessment=assessment,
        unet_mask_scaled=unet_mask,
        colour_mask_scaled=colour_mask,
        unet_mask_original=unet_original,
        colour_mask_original=colour_original,
        unet_percent_tissue=unet_percent,
        colour_percent_tissue=colour_percent,
        tissue_pixels=tissue_pixels,
        differing_by_more_than_15_pp=abs(unet_percent - colour_percent) > 15.0,
        checkpoint_sha256=checkpoint_sha256,
        runtime_seconds=time.monotonic() - started,
    )


def resolve_output_dir(value: str | Path) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = validate.PROTO_ROOT / candidate
    resolved_root = validate.PROTO_ROOT.resolve()
    resolved = candidate.resolve()
    try:
        relative = resolved.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError("Output folder must be inside D:\\patent\\prototype.") from error
    if not relative.parts:
        raise ValueError("Choose a subfolder below D:\\patent\\prototype.")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _directory_size(path: Path) -> int:
    total = 0
    if path.exists():
        for item in path.rglob("*"):
            if item.is_file():
                total += item.stat().st_size
    return total


def _safe_stem(value: str) -> str:
    stem = Path(value).stem
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    return safe[:80] or "image"


def _write_png(path: Path, image: Image.Image, warnings: list[str]) -> None:
    pnginfo = PngImagePlugin.PngInfo()
    for index, warning in enumerate(warnings, start=1):
        pnginfo.add_text(f"W{index}", warning)
    with path.open("xb") as handle:
        image.save(handle, format="PNG", pnginfo=pnginfo)


def _overlay_image(result: QuantificationResult) -> Image.Image:
    base = result.assessment.original_rgb.astype(np.float32)
    overlay = base.copy()
    overlay[result.unet_mask_original] = (
        0.55 * overlay[result.unet_mask_original]
        + 0.45 * np.asarray([255, 40, 40], dtype=np.float32)
    )
    overlay[result.colour_mask_original] = (
        0.55 * overlay[result.colour_mask_original]
        + 0.45 * np.asarray([40, 120, 255], dtype=np.float32)
    )
    return Image.fromarray(np.clip(overlay, 0, 255).astype(np.uint8), mode="RGB")


def _software_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pillow": PIL.__version__,
        "pytorch": torch.__version__,
    }


def write_quantification_outputs(
    result: QuantificationResult, output_folder: str | Path
) -> dict[str, Any]:
    output_dir = resolve_output_dir(output_folder)
    source_name = _safe_stem(result.assessment.source_name)
    stem = f"PROTO_{source_name}"
    mask_path = output_dir / f"{stem}_MASK.png"
    overlay_path = output_dir / f"{stem}_OVERLAY.png"
    report_path = output_dir / f"{stem}_REPORT.json"
    output_paths = (mask_path, overlay_path, report_path)
    existing = [str(path) for path in output_paths if path.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite existing outputs: {existing}")
    pixels = result.unet_mask_original.size
    required_budget = 8 * pixels + 2 * 1024 * 1024
    if _directory_size(validate.PROTO_ROOT) + required_budget > MAX_OUTPUT_BYTES:
        raise RuntimeError("Stopped before outputs could exceed the 10 GB limit.")

    warnings = validate.load_warnings()
    mask_image = Image.fromarray(
        (result.unet_mask_original.astype(np.uint8) * 255), mode="L"
    )
    _write_png(mask_path, mask_image, warnings)
    _write_png(overlay_path, _overlay_image(result), warnings)
    report: dict[str, Any] = {
        "status": "RESEARCH USE ONLY",
        "analysis_label": "EXPLORATORY, NOT CONFIRMATORY",
        "mask_status": "UNVALIDATED MASKS",
        "validation_status": result.assessment.status,
        "input_name": result.assessment.source_name,
        "input_format": result.assessment.image_format,
        "input_sha256": result.assessment.input_sha256,
        "checkpoint_sha256": result.checkpoint_sha256,
        "training_rgb_stats_sha256": result.assessment.stats_sha256,
        "validation_details": validate.assessment_report(result.assessment),
        "software_versions": _software_versions(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input_micrometres_per_pixel": result.assessment.input_mpp,
        "target_micrometres_per_pixel": TARGET_MPP,
        "scale_factor": result.assessment.scale_factor,
        "probability_threshold": PROBABILITY_THRESHOLD,
        "colour_rule": "B - R >= 2",
        "input_dimensions": [
            int(result.assessment.original_rgb.shape[1]),
            int(result.assessment.original_rgb.shape[0]),
        ],
        "scaled_dimensions": [
            int(result.assessment.scaled_rgb.shape[1]),
            int(result.assessment.scaled_rgb.shape[0]),
        ],
        "tissue_mask_definition": "RGB channel mean < 245",
        "tissue_pixels_at_target_scale": result.tissue_pixels,
        "unet_positive_pixels_in_tissue_percent": result.unet_percent_tissue,
        "colour_rule_positive_pixels_in_tissue_percent": result.colour_percent_tissue,
        "mask_difference_over_15_percentage_points": result.differing_by_more_than_15_pp,
        "run_runtime_seconds": result.runtime_seconds,
        "mask_file": mask_path.name,
        "overlay_file": overlay_path.name,
        "report_file": report_path.name,
        "warnings": warnings,
        "screening_note": (
            "The RGB check is a screening heuristic. It flagged 0 of 50 RENFAST test "
            "images and has not been validated as an out-of-distribution detector."
        ),
    }
    with report_path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return report


def process_image(
    image_path: str | Path,
    input_mpp: float,
    output_folder: str | Path,
) -> dict[str, Any]:
    report, _ = run_quantification(image_path, input_mpp, output_folder)
    return report


def run_quantification(
    image_path: str | Path,
    input_mpp: float,
    output_folder: str | Path,
) -> tuple[dict[str, Any], QuantificationResult]:
    return run_quantification_data(
        image_path,
        input_mpp,
        output_folder,
        source_name=Path(image_path).name,
    )


def run_quantification_data(
    source: str | Path | bytes,
    input_mpp: float,
    output_folder: str | Path,
    *,
    source_name: str | None = None,
) -> tuple[dict[str, Any], QuantificationResult]:
    started = time.monotonic()
    checkpoint_sha256 = validate.verify_checkpoint_hash()
    if _directory_size(validate.PROTO_ROOT) >= MAX_OUTPUT_BYTES:
        raise RuntimeError("Stopped before the prototype output folder reaches 10 GB.")
    assessment = validate.validate_image(source, input_mpp, source_name)
    estimated_output_bytes = (
        8 * assessment.original_rgb.shape[0] * assessment.original_rgb.shape[1]
        + 2 * 1024 * 1024
    )
    if _directory_size(validate.PROTO_ROOT) + estimated_output_bytes > MAX_OUTPUT_BYTES:
        raise RuntimeError("Stopped before the projected outputs could exceed 10 GB.")
    if time.monotonic() - started >= MAX_RUNTIME_SECONDS:
        raise TimeoutError("Stopped before the two-hour run limit.")
    model, device, loaded_hash = load_frozen_model()
    if loaded_hash != checkpoint_sha256:
        raise ValueError("Checkpoint changed during startup; refusing to run.")
    result = quantify_arrays(
        assessment, model, device, checkpoint_sha256, started_monotonic=started
    )
    if result.runtime_seconds >= MAX_RUNTIME_SECONDS:
        raise TimeoutError("Stopped before the two-hour run limit.")
    report = write_quantification_outputs(result, output_folder)
    return report, result


def main(argv: list[str] | None = None) -> int:
    print("\n".join(validate.load_warnings()))
    parser = argparse.ArgumentParser(description="Measure marked tissue pixels locally.")
    parser.add_argument("--image", required=True, help="PNG, JPEG, or TIFF image path.")
    parser.add_argument("--mpp", required=True, type=float, help="Measured input micrometres per pixel.")
    parser.add_argument(
        "--output",
        required=True,
        help="Output subfolder inside D:\\patent\\prototype.",
    )
    parser.add_argument(
        "--accept-research-use",
        action="store_true",
        help="Confirm that this run is for local research use only.",
    )
    args = parser.parse_args(argv)
    if not args.accept_research_use:
        print("Stop: add --accept-research-use only after reading all warnings.")
        return 2
    try:
        report = process_image(args.image, args.mpp, args.output)
    except (OSError, ValueError, RuntimeError, TimeoutError) as error:
        print(json.dumps({"status": "REFUSED", "message": str(error), "warnings": validate.load_warnings()}, indent=2))
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
