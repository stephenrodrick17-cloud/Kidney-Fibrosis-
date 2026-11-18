from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import platform
import random
import sys
import tarfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True

import numpy as np
import PIL
import scipy
import torch
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt

ROOT = Path(r"D:\patent")
OUT = ROOT / "stage_FA"
ALIGNMENT = ROOT / "stage_G2" / "GENE2_ALIGNMENT_AUDIT.csv"
CHECKPOINT = ROOT / "stage2A_audit" / "renfast_baseline_run" / "checkpoint_best.pt"
MODEL_SOURCE = ROOT / "stage2A_audit"
EXPECTED_CHECKPOINT = "674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb"
ANALYSIS_LABEL = "EXPLORATORY, NOT CONFIRMATORY"
MASK_LABEL = "UNVALIDATED MASKS"
ASSET_STATUS = "RESEARCH-ONLY"
EXPECTED_LIBRARIES = 41
EXPECTED_PARTICIPANTS = 40
TARGET_MPP = 4.1
NOMINAL_SPOT_UM = 55.0
SPOT_DIAMETER_PX = NOMINAL_SPOT_UM / TARGET_MPP
TILE_SIZE = 512
COLOUR_THRESHOLD = 2
PROBABILITY_THRESHOLD = 0.5
MAX_RUNTIME_SECONDS = 95 * 60
MAX_OUTPUT_BYTES = 8 * 1024**3
SEED = 20261117


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def directory_size(path: Path) -> int:
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def split_reference(value: str) -> tuple[Path, str | None]:
    if "::" in value:
        archive, member = value.split("::", 1)
        return resolve_path(archive), member.replace("\\", "/")
    return resolve_path(value), None


def read_reference(value: str) -> tuple[bytes, Path, str | None]:
    source_path, member = split_reference(value)
    if not source_path.is_file():
        raise FileNotFoundError(f"Required source file is missing: {source_path}")
    if member is None:
        return source_path.read_bytes(), source_path, None
    if source_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(source_path) as archive:
            return archive.read(member), source_path, member
    if source_path.name.lower().endswith((".tar.gz", ".tgz")):
        with tarfile.open(source_path, "r:gz") as archive:
            extracted = archive.extractfile(member)
            if extracted is None:
                raise FileNotFoundError(f"Archive member is missing: {member}")
            return extracted.read(), source_path, member
    raise ValueError(f"Unsupported archive type: {source_path}")


def sibling_reference(value: str, sibling: str) -> str:
    source_path, member = split_reference(value)
    if member is None:
        return str(source_path.parent / sibling)
    return str(source_path) + "::" + str(PurePosixPath(member).parent / sibling)


def resolve_row_reference(value: str, row: dict[str, str]) -> str:
    source_path, member = split_reference(value)
    if member is not None and not source_path.is_file():
        spatial_path, _ = split_reference(row["spatial_record"])
        if spatial_path.is_file() and spatial_path.name == source_path.name:
            return str(spatial_path) + "::" + member
    return value


def read_positions(data: bytes) -> list[dict[str, object]]:
    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
    if not rows:
        raise ValueError("The spatial positions file is empty.")
    normalized = [value.strip().lower() for value in rows[0]]
    if "barcode" in normalized:
        header = normalized
        data_rows = rows[1:]
        barcode_index = header.index("barcode")
        in_tissue_index = header.index("in_tissue")
        row_index = header.index("array_row")
        col_index = header.index("array_col")
        pixel_row_index = header.index("pxl_row_in_fullres")
        pixel_col_index = header.index("pxl_col_in_fullres")
    else:
        data_rows = rows
        barcode_index, in_tissue_index = 0, 1
        row_index, col_index = 2, 3
        pixel_row_index, pixel_col_index = 4, 5

    positions = []
    for row in data_rows:
        if len(row) <= max(barcode_index, pixel_col_index):
            continue
        positions.append(
            {
                "barcode": row[barcode_index].strip(),
                "in_tissue": int(float(row[in_tissue_index])),
                "array_row": int(float(row[row_index])),
                "array_col": int(float(row[col_index])),
                "pixel_row_fullres": float(row[pixel_row_index]),
                "pixel_col_fullres": float(row[pixel_col_index]),
            }
        )
    if not positions:
        raise ValueError("No spot positions could be read.")
    barcodes = [str(row["barcode"]) for row in positions]
    if len(barcodes) != len(set(barcodes)):
        raise ValueError("Duplicate barcode in spatial positions file.")
    return positions


def load_rgb(data: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(data)) as image:
        return np.asarray(image.convert("RGB"), dtype=np.uint8).copy()


def render_unet(model: torch.nn.Module, image: np.ndarray, device: torch.device, deadline: float) -> np.ndarray:
    height, width = image.shape[:2]
    output = np.zeros((height, width), dtype=np.bool_)
    pad_value = 255
    for top in range(0, height, TILE_SIZE):
        for left in range(0, width, TILE_SIZE):
            if time.monotonic() >= deadline:
                raise TimeoutError("The preregistered image-run time budget was reached.")
            tile_height = min(TILE_SIZE, height - top)
            tile_width = min(TILE_SIZE, width - left)
            tile = np.full((TILE_SIZE, TILE_SIZE, 3), pad_value, dtype=np.uint8)
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


def render_overlay(
    image: np.ndarray,
    unet_mask: np.ndarray,
    colour_mask: np.ndarray,
    spots: list[dict[str, object]],
    output_path: Path,
) -> None:
    base = Image.fromarray(image, mode="RGB")
    unet_rgb = image.astype(np.float32).copy()
    unet_rgb[unet_mask] = (
        0.55 * unet_rgb[unet_mask] + 0.45 * np.asarray([255, 40, 40], dtype=np.float32)
    )
    colour_rgb = image.astype(np.float32).copy()
    colour_rgb[colour_mask] = (
        0.55 * colour_rgb[colour_mask] + 0.45 * np.asarray([40, 120, 255], dtype=np.float32)
    )
    panels = [
        base,
        Image.fromarray(np.clip(unet_rgb, 0, 255).astype(np.uint8), mode="RGB"),
        Image.fromarray(np.clip(colour_rgb, 0, 255).astype(np.uint8), mode="RGB"),
    ]
    radius = SPOT_DIAMETER_PX / 2.0
    for panel in panels:
        draw = ImageDraw.Draw(panel)
        for spot in spots:
            if not bool(spot["included"]):
                continue
            x = float(spot["center_x_4p1px"])
            y = float(spot["center_y_4p1px"])
            bounds = (x - radius, y - radius, x + radius, y + radius)
            draw.ellipse(bounds, outline=(0, 255, 255), width=1)

    width, height = base.size
    banner_height = 56
    panel_height = 28
    canvas = Image.new("RGB", (width * 3, height + banner_height + panel_height), (255, 255, 255))
    canvas_draw = ImageDraw.Draw(canvas)
    canvas_draw.text(
        (8, 5),
        f"{ANALYSIS_LABEL} | {MASK_LABEL} | RESEARCH-ONLY | visual alignment only",
        fill=(0, 0, 0),
    )
    titles = ("Mapped spots on RGB image", "Frozen U-Net mask overlay", "B-R colour mask overlay")
    for index, (panel, title) in enumerate(zip(panels, titles)):
        x = index * width
        canvas_draw.text((x + 8, banner_height), title, fill=(0, 0, 0))
        canvas.paste(panel, (x, banner_height + panel_height))
    canvas.save(output_path, format="PNG")


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    started = time.monotonic()
    deadline = started + MAX_RUNTIME_SECONDS
    if directory_size(OUT) >= MAX_OUTPUT_BYTES:
        raise RuntimeError("Stage FA output folder already meets the registered size limit.")
    if not ALIGNMENT.is_file() or not CHECKPOINT.is_file():
        raise FileNotFoundError("Required alignment audit or frozen checkpoint is missing.")
    if sha256_file(CHECKPOINT) != EXPECTED_CHECKPOINT:
        raise ValueError("Frozen RENFAST checkpoint SHA-256 does not match the preregistered value.")

    with ALIGNMENT.open("r", encoding="utf-8-sig", newline="") as handle:
        libraries = list(csv.DictReader(handle))
    if len(libraries) != EXPECTED_LIBRARIES:
        raise ValueError(f"Expected {EXPECTED_LIBRARIES} libraries, found {len(libraries)}.")
    if len({row["participant_id"] for row in libraries}) != EXPECTED_PARTICIPANTS:
        raise ValueError("Participant count differs from the preregistered cohort.")
    if any(row["status"] != "PASS" for row in libraries):
        raise ValueError("At least one library failed the saved alignment audit.")
    if len({(row["participant_id"], row["library_id"]) for row in libraries}) != len(libraries):
        raise ValueError("Duplicate participant/library key in alignment audit.")
    libraries.sort(key=lambda row: (row["participant_id"], row["library_id"]))
    selected_indices = set(
        random.Random(SEED).sample(range(len(libraries)), 3)
    )
    selected = {
        (libraries[index]["participant_id"], libraries[index]["library_id"])
        for index in selected_indices
    }

    sys.path.insert(0, str(MODEL_SOURCE))
    import run_renfast_baseline as baseline

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(CHECKPOINT, map_location=device, weights_only=True)
    if checkpoint.get("threshold") != PROBABILITY_THRESHOLD:
        raise ValueError("Checkpoint probability threshold is not the frozen value 0.5.")
    model = baseline.UNet().to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    score_rows: list[dict[str, object]] = []
    run_rows: list[dict[str, object]] = []
    overlay_rows: list[dict[str, object]] = []
    input_hash_rows: list[dict[str, object]] = []
    mask_output_paths: list[Path] = []
    overlay_output_paths: list[Path] = []
    started_utc = datetime.now(timezone.utc)
    archive_hash_cache: dict[Path, str] = {}

    def record_hash(source_path: Path, member: str | None, content: bytes, kind: str) -> None:
        if member is not None:
            if source_path not in archive_hash_cache:
                archive_hash_cache[source_path] = sha256_file(source_path)
                input_hash_rows.append(
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
        input_hash_rows.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "record_type": "input",
                "source_kind": kind,
                "source_path": str(source_path),
                "archive_member": member or "",
                "sha256": sha256_bytes(content),
            }
        )

    for index, row in enumerate(libraries, start=1):
        if time.monotonic() >= deadline:
            raise TimeoutError("Stopped before the preregistered 100-minute process limit.")
        if directory_size(OUT) >= MAX_OUTPUT_BYTES:
            raise RuntimeError("Stopped before the preregistered 8 GB output limit.")
        participant = row["participant_id"]
        library = row["library_id"]
        image_ref = resolve_row_reference(row["image_record"], row)
        positions_ref = resolve_row_reference(row["spatial_positions"], row)
        image_bytes, image_source, image_member = read_reference(image_ref)
        positions_bytes, positions_source, positions_member = read_reference(positions_ref)
        scale_ref = sibling_reference(image_ref, "scalefactors_json.json")
        scale_bytes, scale_source, scale_member = read_reference(scale_ref)
        record_hash(image_source, image_member, image_bytes, "slide image")
        record_hash(positions_source, positions_member, positions_bytes, "spot positions")
        record_hash(scale_source, scale_member, scale_bytes, "scale factors")

        with Image.open(io.BytesIO(image_bytes)) as source_image:
            hires = np.asarray(source_image.convert("RGB"), dtype=np.uint8).copy()
        scale = json.loads(scale_bytes.decode("utf-8"))
        spot_diameter_fullres = float(scale["spot_diameter_fullres"])
        hires_scale = float(scale["tissue_hires_scalef"])
        if spot_diameter_fullres <= 0 or hires_scale <= 0:
            raise ValueError(f"Invalid scale factors for {participant}/{library}.")
        source_mpp = NOMINAL_SPOT_UM / (spot_diameter_fullres * hires_scale)
        resize_factor = source_mpp / TARGET_MPP
        old_height, old_width = hires.shape[:2]
        new_width = max(1, int(round(old_width * resize_factor)))
        new_height = max(1, int(round(old_height * resize_factor)))
        resized_image = Image.fromarray(hires, mode="RGB").resize(
            (new_width, new_height), resample=Image.Resampling.LANCZOS
        )
        image = np.asarray(resized_image, dtype=np.uint8).copy()
        height, width = image.shape[:2]
        x_scale = new_width / old_width
        y_scale = new_height / old_height
        positions = read_positions(positions_bytes)
        tissue = image.mean(axis=2) < 245.0
        tissue_depth = distance_transform_edt(tissue)
        unet_mask = render_unet(model, image, device, deadline)
        colour_mask = (
            image[:, :, 2].astype(np.int16) - image[:, :, 0].astype(np.int16)
        ) >= COLOUR_THRESHOLD
        hue_image = np.asarray(Image.fromarray(image, mode="RGB").convert("HSV"))[:, :, 0]
        median_hue = float(np.median(hue_image[tissue])) if tissue.any() else math.nan

        library_spots: list[dict[str, object]] = []
        radius = SPOT_DIAMETER_PX / 2.0
        for position in positions:
            center_x = float(position["pixel_col_fullres"]) * hires_scale * x_scale
            center_y = float(position["pixel_row_fullres"]) * hires_scale * y_scale
            x0 = int(math.floor(center_x - radius))
            x1 = int(math.ceil(center_x + radius)) + 1
            y0 = int(math.floor(center_y - radius))
            y1 = int(math.ceil(center_y + radius)) + 1
            reason = ""
            if int(position["in_tissue"]) != 1:
                reason = "outside Visium in_tissue area"
            elif x0 < 0 or y0 < 0 or x1 > width or y1 > height:
                reason = "footprint outside mapped image"
            if reason:
                footprint = None
                tissue_fraction = math.nan
                unet_score = math.nan
                colour_score = math.nan
                depth_um = math.nan
            else:
                yy, xx = np.ogrid[y0:y1, x0:x1]
                footprint = (xx - center_x) ** 2 + (yy - center_y) ** 2 <= radius**2
                if not footprint.any():
                    reason = "empty rasterized footprint"
                    tissue_fraction = math.nan
                    unet_score = math.nan
                    colour_score = math.nan
                    depth_um = math.nan
                else:
                    tissue_patch = tissue[y0:y1, x0:x1]
                    tissue_fraction = float(tissue_patch[footprint].mean())
                    if tissue_fraction <= 0:
                        reason = "footprint has no tissue pixels"
                    unet_score = float(unet_mask[y0:y1, x0:x1][footprint].mean())
                    colour_score = float(colour_mask[y0:y1, x0:x1][footprint].mean())
                    center_ix = min(width - 1, max(0, int(round(center_x))))
                    center_iy = min(height - 1, max(0, int(round(center_y))))
                    depth_um = float(tissue_depth[center_iy, center_ix] * TARGET_MPP)
            included = not reason
            spot_row = {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "participant_id": participant,
                "library_id": library,
                "barcode": position["barcode"],
                "array_row": position["array_row"],
                "array_col": position["array_col"],
                "in_tissue": position["in_tissue"],
                "center_x_4p1px": center_x,
                "center_y_4p1px": center_y,
                "spot_diameter_px": SPOT_DIAMETER_PX,
                "tissue_fraction": tissue_fraction,
                "tissue_depth_um": depth_um,
                "unet_fibrosis_fraction": unet_score,
                "colour_fibrosis_fraction": colour_score,
                "included": included,
                "exclusion_reason": reason,
                "library_median_hue": median_hue,
            }
            score_rows.append(spot_row)
            library_spots.append(spot_row)

        mask_path = OUT / f"FA_MASK_{participant}_{library}.npz"
        buffer = io.BytesIO()
        np.savez_compressed(
            buffer,
            unet_mask=unet_mask,
            colour_mask=colour_mask,
            analysis_label=np.asarray(ANALYSIS_LABEL),
            mask_status=np.asarray(MASK_LABEL),
            asset_status=np.asarray(ASSET_STATUS),
            participant_id=np.asarray(participant),
            library_id=np.asarray(library),
            target_mpp=np.asarray(TARGET_MPP),
            spot_diameter_px=np.asarray(SPOT_DIAMETER_PX),
            probability_threshold=np.asarray(PROBABILITY_THRESHOLD),
            colour_threshold=np.asarray(COLOUR_THRESHOLD),
        )
        payload = buffer.getvalue()
        if directory_size(OUT) + len(payload) > MAX_OUTPUT_BYTES:
            raise RuntimeError("Stopped before writing a mask that would exceed 8 GB.")
        if mask_path.exists():
            raise FileExistsError(f"Refusing to overwrite {mask_path}")
        mask_path.write_bytes(payload)
        mask_output_paths.append(mask_path)

        overlay_path = None
        if (participant, library) in selected:
            overlay_path = OUT / f"FA_OVERLAY_{participant}_{library}.png"
            if overlay_path.exists():
                raise FileExistsError(f"Refusing to overwrite {overlay_path}")
            render_overlay(image, unet_mask, colour_mask, library_spots, overlay_path)
            overlay_output_paths.append(overlay_path)
            overlay_rows.append(
                {
                    "analysis_label": ANALYSIS_LABEL,
                    "mask_status": MASK_LABEL,
                    "asset_status": ASSET_STATUS,
                    "participant_id": participant,
                    "library_id": library,
                    "overlay_path": str(overlay_path),
                    "visual_review": "PENDING",
                }
            )

        run_rows.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "participant_id": participant,
                "library_id": library,
                "source_set": row["source_set"],
                "mapping_status_from_existing_audit": row["status"],
                "image_width_4p1px": width,
                "image_height_4p1px": height,
                "spots_read": len(positions),
                "spots_included": sum(bool(item["included"]) for item in library_spots),
                "spots_excluded": sum(not bool(item["included"]) for item in library_spots),
                "median_hue": median_hue,
                "mask_file": str(mask_path),
                "mask_sha256": sha256_file(mask_path),
                "overlay_file": str(overlay_path) if overlay_path else "",
                "runtime_seconds_elapsed": round(time.monotonic() - started, 3),
            }
        )
        print(f"Processed {index}/{len(libraries)}: {participant}/{library}")

    score_path = OUT / "FA_SPOT_FIBROSIS_SCORES.csv"
    score_fields = list(score_rows[0])
    write_csv(score_path, score_rows, score_fields)
    run_path = OUT / "FA_LIBRARY_RUN_STATUS.csv"
    write_csv(run_path, run_rows, list(run_rows[0]))
    overlay_path = OUT / "FA_OVERLAY_SELECTION.csv"
    write_csv(overlay_path, overlay_rows, list(overlay_rows[0]))

    provenance_inputs = [
        ALIGNMENT,
        CHECKPOINT,
        OUT / "FA_PREREG.md",
        OUT / "FA_RUN_IMAGES.py",
        ROOT / "stage_G2" / "GENE2_DATA_AUDIT.md",
        ROOT / "qc_collagen" / "gene_detection_cohort_summary.csv",
        ROOT / "qc_collagen" / "review" / "reference_label_availability_summary.csv",
        ROOT / "stage2A_audit" / "PHASEB_REPORT.md",
        ROOT / "stage2A_audit" / "PHASEA_PERMISSION_RECORD.md",
        MODEL_SOURCE / "run_renfast_baseline.py",
        OUT / "FA_DATA_AUDIT.md",
        OUT / "FA_MASK_GATE.md",
    ]
    for path in provenance_inputs:
        if path.is_file():
            input_hash_rows.append(
                {
                    "analysis_label": ANALYSIS_LABEL,
                    "mask_status": MASK_LABEL,
                    "asset_status": ASSET_STATUS,
                    "record_type": "input",
                    "source_kind": "audit, protocol, or model source",
                    "source_path": str(path),
                    "archive_member": "",
                    "sha256": sha256_file(path),
                }
            )
    for path in (
        mask_output_paths
        + [score_path, run_path, overlay_path]
        + overlay_output_paths
    ):
        input_hash_rows.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "record_type": "output",
                "source_kind": "Stage FA mask, score, status, or overlay output",
                "source_path": str(path),
                "archive_member": "",
                "sha256": sha256_file(path),
            }
        )
    hash_path = OUT / "FA_IMAGE_HASHES.csv"
    write_csv(
        hash_path,
        input_hash_rows,
        [
            "analysis_label",
            "mask_status",
            "asset_status",
            "record_type",
            "source_kind",
            "source_path",
            "archive_member",
            "sha256",
        ],
    )
    metadata = {
        "analysis_label": ANALYSIS_LABEL,
        "mask_status": MASK_LABEL,
        "asset_status": ASSET_STATUS,
        "participants": EXPECTED_PARTICIPANTS,
        "libraries": EXPECTED_LIBRARIES,
        "checkpoint_sha256": EXPECTED_CHECKPOINT,
        "device": str(device),
        "python": platform.python_version(),
        "pytorch": torch.__version__,
        "numpy": np.__version__,
        "pillow": PIL.__version__,
        "scipy": scipy.__version__,
        "seed": SEED,
        "target_mpp": TARGET_MPP,
        "nominal_spot_um": NOMINAL_SPOT_UM,
        "spot_diameter_px": SPOT_DIAMETER_PX,
        "probability_threshold": PROBABILITY_THRESHOLD,
        "colour_threshold": COLOUR_THRESHOLD,
        "command": "python -B D:\\patent\\stage_FA\\FA_RUN_IMAGES.py",
        "started_at_utc": started_utc.isoformat(),
        "runtime_seconds": round(time.monotonic() - started, 3),
        "outputs_bytes": directory_size(OUT),
        "analysis_files_read": "Images, spatial positions, and scale factors only; no expression file was opened.",
    }
    metadata_path = OUT / "FA_IMAGE_RUN_METADATA.json"
    if metadata_path.exists():
        raise FileExistsError(f"Refusing to overwrite {metadata_path}")
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
