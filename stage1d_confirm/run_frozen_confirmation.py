"""Apply the frozen Stage 1d models to the registered new-participant cohort."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
sys.dont_write_bytecode = True

import cv2
import joblib
import numpy as np
import pandas as pd
import torch
from PIL import Image
from scipy.stats import rankdata, spearmanr
from torchvision.models import ResNet50_Weights, resnet50


ROOT = Path(r"D:\patent")
OUT = ROOT / "stage1d_confirm"
DATA_DIR = ROOT / "data_confirm"
FREEZE = ROOT / "stage1d_freeze"
BASELINES = ROOT / "stage1d_freeze_baselines"
STAGE1 = ROOT / "stage1_expression"
STAGE1B_SCRIPT = ROOT / "stage1b_expression" / "scripts" / "run_stage1b.py"
STAGE1_SCRIPT = STAGE1 / "scripts" / "run_stage1.py"
PAIRING_SCRIPT = ROOT / "analyze_cohort_plan_a_b.py"
QC_SCRIPT = ROOT / "qc_collagen" / "run_qc_collagen.py"
TRAINING_SCRIPT = FREEZE / "train_frozen_confirmation.py"
PREREG = ROOT / "stage1c_confirm" / "PREREG_CONFIRM.md"
DOWNLOAD_PLAN = OUT / "download_plan.csv"
DOWNLOAD_MANIFEST = OUT / "data_manifest.csv"
MLP_MANIFEST = FREEZE / "MODEL_MANIFEST.csv"
BASELINE_MANIFEST = BASELINES / "MODEL_MANIFEST.csv"
MLP_MODEL = FREEZE / "frozen_model_state.pt"
MLP_SCALERS = FREEZE / "frozen_scalers.npz"
FEATURE_NAMES = FREEZE / "input_feature_names.json"
RESIDUALIZATION = FREEZE / "residualization_parameters.csv"
ENCODER_REFERENCE = FREEZE / "encoder_reference.json"
ENCODER_CHECKPOINT = STAGE1 / "model_cache" / "checkpoints" / "resnet50-11ad3fa6.pth"
RIDGE_MODEL = BASELINES / "frozen_ridge_models.joblib"
RIDGE_SCALERS = BASELINES / "baseline_scalers.npz"
BASELINE_DEFINITIONS = BASELINES / "baseline_feature_definitions.json"
ORIGINAL_KEYS = FREEZE / "in_process_predictions.npz"
DATA_OUTPUT = OUT / "confirmation_predictions.npz"
PRIMARY_METRICS = OUT / "primary_participant_metrics.csv"
PRIMARY_SUMMARY = OUT / "primary_comparison_summary.csv"
SECONDARY_METRICS = OUT / "exploratory_secondary_participant_metrics.csv"
SECONDARY_SUMMARY = OUT / "exploratory_secondary_summary.csv"
BLOCK_METRICS = OUT / "exploratory_spatial_block_metrics.csv"
BLOCK_SUMMARY = OUT / "exploratory_spatial_block_summary.csv"
SPOT_EXCLUSIONS = OUT / "excluded_spots.csv"
PARTICIPANT_EXCLUSIONS = OUT / "participant_exclusions.csv"
MAPPING_QC = OUT / "spatial_mapping_qc.csv"
ARCHIVE_QC = OUT / "spatial_archive_contents.csv"
SOURCE_CHECKS = OUT / "source_integrity_checks.csv"
VERIFICATION = OUT / "metric_recomputation.json"
REPORT = OUT / "STAGE1D_REPORT.md"

PARTICIPANTS = (
    "164-10",
    "164-22",
    "27-10123",
    "27-10166",
    "27-10229",
    "29-10277",
    "29-10282",
    "30-11081",
    "34-11042",
    "34-11048",
    "933-10271",
    "933-11258",
)
TARGET_NAMES = [
    "ECM_collagen",
    "myofibroblast_pro-fibrotic",
    "matrix_remodelling",
    "COL1A1",
    "COL1A2",
    "COL3A1",
    "FN1",
    "TGFB1",
    "CCN2",
    "ACTA2",
    "MMP2",
    "TIMP1",
]
PRIMARY_TARGET = "myofibroblast_pro-fibrotic"
MODEL_COLUMNS = {
    "mlp_spot": "predictions_mlp_spot",
    "color_only_ridge": "predictions_color_only_ridge",
    "depth_only_ridge": "predictions_depth_only_ridge",
}
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20261114
MIN_ELIGIBLE_PARTICIPANTS = 10
MIN_FINITE_SPOTS = 10
MIN_DISTINCT_TARGETS = 3
BLOCK_WIDTH = 10
NEIGHBOR_OFFSETS = ((0, 2), (0, -2), (1, 1), (-1, -1), (1, -1), (-1, 1))


class ParticipantDataUnavailable(RuntimeError):
    """A registered participant lacks an unambiguous required input."""


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load required source module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = (
        list(rows[0])
        if rows
        else {
            PARTICIPANT_EXCLUSIONS: [
                "participant_id",
                "reason",
                "exclusion_stage",
            ],
            SPOT_EXCLUSIONS: [
                "participant_id",
                "library_id",
                "barcode",
                "target",
                "reason",
            ],
        }.get(path, [])
    )
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def verify_manifest_paths(
    manifest_path: Path, paths: list[Path], path_column: str, hash_column: str
) -> list[dict[str, Any]]:
    rows = read_csv(manifest_path)
    by_path = {row[path_column].casefold(): row for row in rows}
    checks = []
    for path in paths:
        expected = by_path.get(str(path).casefold())
        if expected is None:
            raise AssertionError(f"Required frozen file is absent from {manifest_path}: {path}")
        if not path.is_file():
            raise FileNotFoundError(path)
        actual_hash = sha256_file(path)
        actual_size = path.stat().st_size
        ok = (
            actual_hash == expected[hash_column]
            and actual_size == int(expected["size_bytes"])
        )
        checks.append(
            {
                "path": str(path),
                "expected_sha256": expected[hash_column],
                "actual_sha256": actual_hash,
                "size_bytes": actual_size,
                "matches_manifest": ok,
            }
        )
        if not ok:
            raise AssertionError(f"Frozen artifact checksum/size mismatch: {path}")
    return checks


def verify_inputs() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not REPORT.parent.is_dir():
        raise FileNotFoundError(OUT)
    if sha256_file(PREREG) != "23238d3727ab2a4102bfdc7a558df90100692d14bf8b014b05eef08253e0f729":
        raise AssertionError("Confirmation preregistration differs from the frozen version")

    mlp_paths = [
        MLP_MODEL,
        MLP_SCALERS,
        FEATURE_NAMES,
        RESIDUALIZATION,
        ENCODER_REFERENCE,
        ENCODER_CHECKPOINT,
    ]
    baseline_paths = [RIDGE_MODEL, RIDGE_SCALERS, BASELINE_DEFINITIONS]
    checks = verify_manifest_paths(MLP_MANIFEST, mlp_paths, "path", "sha256")
    checks.extend(
        verify_manifest_paths(
            BASELINE_MANIFEST, baseline_paths, "path", "sha256"
        )
    )
    checks.extend(
        [
            {
                "path": str(path),
                "expected_sha256": "",
                "actual_sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
                "matches_manifest": True,
            }
            for path in [
                Path(__file__).resolve(),
                OUT / "download_confirmation_inputs.py",
                STAGE1_SCRIPT,
                STAGE1B_SCRIPT,
                PAIRING_SCRIPT,
                QC_SCRIPT,
            ]
        ]
    )

    plan = read_csv(DOWNLOAD_PLAN)
    manifest = read_csv(DOWNLOAD_MANIFEST)
    plan_by_name = {row["file_name"]: row for row in plan}
    if len(plan) != 24 or len(manifest) != 24:
        raise AssertionError(
            f"Expected 24 planned and downloaded files; found {len(plan)} and {len(manifest)}"
        )
    if {row["participant_id"] for row in plan} != set(PARTICIPANTS):
        raise AssertionError("Download plan participant IDs differ from preregistration")
    if {row["participant_id"] for row in manifest} != set(PARTICIPANTS):
        raise AssertionError("Download manifest participant IDs differ from preregistration")
    if len({row["file_name"] for row in manifest}) != 24:
        raise AssertionError("Downloaded file names are not unique")
    if any(row["asset_type"] not in {"open_expression_matrix", "spatial_bundle"} for row in manifest):
        raise AssertionError("Download manifest contains an unauthorized asset type")
    if any(
        row["file_name"].lower().endswith((".tif", ".tiff", ".fastq", ".fq"))
        for row in manifest
    ):
        raise AssertionError("A forbidden TIFF or FASTQ file appears in the download manifest")
    for row in manifest:
        planned = plan_by_name.get(row["file_name"])
        if (
            planned is None
            or planned["participant_id"] != row["participant_id"]
            or planned["asset_type"] != row["asset_type"]
            or row["access"] != "open"
        ):
            raise AssertionError(f"Downloaded asset is not an exact open catalog plan row: {row}")
        path = DATA_DIR / row["file_name"]
        if (
            not path.is_file()
            or path.stat().st_size != int(row["size_bytes"])
            or sha256_file(path) != row["sha256"]
        ):
            raise AssertionError(f"Downloaded file failed size/SHA-256 check: {path}")
        if int(row["size_bytes"]) > 1_000_000_000:
            raise AssertionError(f"Downloaded file exceeds the 1 GB limit: {path}")

    original = np.load(ORIGINAL_KEYS, allow_pickle=False)
    original_participants = original["participant_id"].astype(str)
    original_libraries = original["library_id"].astype(str)
    original_barcodes = original["barcode"].astype(str)
    original_keys = list(zip(original_participants, original_libraries, original_barcodes))
    if (
        len(original_keys) != 25_104
        or len(set(original_keys)) != 25_104
        or len(set(original_participants)) != 28
        or len(set(original_libraries)) != 29
    ):
        raise AssertionError("Frozen original keys do not reconcile to 28/29/25,104")
    if set(PARTICIPANTS) & set(original_participants):
        raise AssertionError("A registered confirmation participant overlaps the original 28")
    if not DATA_DIR.is_dir():
        raise FileNotFoundError(DATA_DIR)
    free_bytes = shutil.disk_usage(ROOT.drive + "\\").free
    if free_bytes < 2_000_000_000:
        raise RuntimeError(f"Less than 2 GB remains free on D: ({free_bytes} bytes)")
    return checks, manifest


def archive_members(path: Path) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    """List a bundle and read only its registered positions, scale, and hires image."""
    entries: list[dict[str, Any]] = []
    payloads: dict[str, bytes] = {}
    candidates: dict[str, dict[str, str]] = {}
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                normalized = PurePosixPath(info.filename.replace("\\", "/"))
                if normalized.is_absolute() or ".." in normalized.parts:
                    raise ParticipantDataUnavailable(
                        f"Unsafe spatial archive member path: {info.filename}"
                    )
                entries.append(
                    {
                        "name": info.filename,
                        "size": int(info.file_size),
                        "suffix": normalized.suffix.lower() or "[none]",
                    }
                )
                leaf = normalized.name.lower()
                if leaf in {
                    "tissue_positions.csv",
                    "tissue_positions_list.csv",
                    "scalefactors_json.json",
                    "tissue_hires_image.png",
                }:
                    parent = str(normalized.parent)
                    candidates.setdefault(parent, {})[leaf] = info.filename
            complete = [
                (parent, files)
                for parent, files in candidates.items()
                if (
                    ("tissue_positions.csv" in files)
                    != ("tissue_positions_list.csv" in files)
                    and "scalefactors_json.json" in files
                    and "tissue_hires_image.png" in files
                )
            ]
            if len(complete) != 1:
                raise ParticipantDataUnavailable(
                    f"{path.name}: expected one unambiguous Visium spatial trio; found {len(complete)}"
                )
            parent, files = complete[0]
            position_name = files.get("tissue_positions.csv") or files["tissue_positions_list.csv"]
            for role, name in (
                ("positions", position_name),
                ("scalefactors", files["scalefactors_json.json"]),
                ("hires_image", files["tissue_hires_image.png"]),
            ):
                payloads[role] = archive.read(name)
                payloads[f"{role}_member"] = name.encode("utf-8")
    elif path.name.lower().endswith(".tar.gz"):
        with tarfile.open(path, mode="r:gz") as archive:
            for info in archive.getmembers():
                if not info.isfile():
                    continue
                normalized = PurePosixPath(info.name.replace("\\", "/"))
                if normalized.is_absolute() or ".." in normalized.parts:
                    raise ParticipantDataUnavailable(
                        f"Unsafe spatial archive member path: {info.name}"
                    )
                entries.append(
                    {
                        "name": info.name,
                        "size": int(info.size),
                        "suffix": normalized.suffix.lower() or "[none]",
                    }
                )
                leaf = normalized.name.lower()
                if leaf in {
                    "tissue_positions.csv",
                    "tissue_positions_list.csv",
                    "scalefactors_json.json",
                    "tissue_hires_image.png",
                }:
                    parent = str(normalized.parent)
                    candidates.setdefault(parent, {})[leaf] = info.name
            complete = [
                (parent, files)
                for parent, files in candidates.items()
                if (
                    ("tissue_positions.csv" in files)
                    != ("tissue_positions_list.csv" in files)
                    and "scalefactors_json.json" in files
                    and "tissue_hires_image.png" in files
                )
            ]
            if len(complete) != 1:
                raise ParticipantDataUnavailable(
                    f"{path.name}: expected one unambiguous Visium spatial trio; found {len(complete)}"
                )
            _parent, files = complete[0]
            position_name = files.get("tissue_positions.csv") or files["tissue_positions_list.csv"]
            for role, name in (
                ("positions", position_name),
                ("scalefactors", files["scalefactors_json.json"]),
                ("hires_image", files["tissue_hires_image.png"]),
            ):
                member = archive.getmember(name)
                stream = archive.extractfile(member)
                if stream is None:
                    raise ParticipantDataUnavailable(f"Cannot read {name} in {path.name}")
                payloads[role] = stream.read()
                payloads[f"{role}_member"] = name.encode("utf-8")
    else:
        raise ParticipantDataUnavailable(f"Unsupported spatial archive type: {path.name}")

    extension_counts = Counter(entry["suffix"] for entry in entries)
    payloads["archive_summary"] = json.dumps(
        {
            "file_count": len(entries),
            "uncompressed_bytes": sum(entry["size"] for entry in entries),
            "extension_counts": dict(sorted(extension_counts.items())),
        },
        sort_keys=True,
    ).encode("utf-8")
    return entries, payloads


def read_positions_bytes(name: str, data: bytes) -> pd.DataFrame:
    positions = pd.read_csv(io.BytesIO(data))
    if "barcode" not in positions.columns:
        if PurePosixPath(name.replace("\\", "/")).name.lower() != "tissue_positions_list.csv":
            raise ParticipantDataUnavailable(f"{name}: missing barcode column")
        positions = pd.read_csv(
            io.BytesIO(data),
            header=None,
            names=[
                "barcode",
                "in_tissue",
                "array_row",
                "array_col",
                "pxl_row_in_fullres",
                "pxl_col_in_fullres",
            ],
        )
    required = {
        "barcode",
        "in_tissue",
        "array_row",
        "array_col",
        "pxl_row_in_fullres",
        "pxl_col_in_fullres",
    }
    if not required.issubset(positions.columns):
        missing = sorted(required - set(positions.columns))
        raise ParticipantDataUnavailable(f"{name}: missing required columns {missing}")
    return positions


def matrix_triplet_is_unambiguous(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        files_by_parent: dict[str, set[str]] = {}
        for name in archive.namelist():
            if name.endswith("/"):
                continue
            normalized = PurePosixPath(name.replace("\\", "/"))
            if normalized.is_absolute() or ".." in normalized.parts:
                raise ParticipantDataUnavailable(f"Unsafe matrix archive member: {name}")
            leaf = normalized.name.lower()
            role = next(
                (
                    suffix
                    for suffix in (
                        "barcodes.tsv.gz",
                        "features.tsv.gz",
                        "matrix.mtx.gz",
                    )
                    if leaf.endswith(suffix)
                ),
                None,
            )
            if role is not None:
                files_by_parent.setdefault(str(normalized.parent), set()).add(role)
        complete = [
            parent
            for parent, names in files_by_parent.items()
            if {
                "barcodes.tsv.gz",
                "features.tsv.gz",
                "matrix.mtx.gz",
            }.issubset(names)
        ]
        if len(complete) != 1:
            raise ParticipantDataUnavailable(
                f"{path.name}: expected one expression matrix triplet; found {len(complete)}"
            )


def feature_count_matrix(
    source: dict[str, Any], qc: Any, column_indices: np.ndarray
) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray], dict[str, bool]]:
    matrix = source["matrix"].tocsr()
    selected = matrix[:, column_indices].tocsr()
    library_size = np.asarray(selected.sum(axis=0)).ravel().astype(np.float64)
    gene_values: dict[str, np.ndarray] = {}
    gene_present: dict[str, bool] = {}
    members = sorted(
        {
            gene
            for target_members in qc.MODULES.values()
            for gene in target_members
        }
        | set(TARGET_NAMES[3:])
    )
    for gene in members:
        matched_rows = [index for index, _ in qc.gene_match_rows(source["features"], gene)]
        if not matched_rows:
            gene_present[gene] = False
            gene_values[gene] = np.full(len(column_indices), np.nan, dtype=np.float64)
            continue
        gene_present[gene] = True
        counts = np.asarray(selected[matched_rows, :].sum(axis=0)).ravel().astype(np.float64)
        cp10k = np.divide(
            counts * 10000.0,
            library_size,
            out=np.full(len(column_indices), np.nan, dtype=np.float64),
            where=library_size > 0,
        )
        gene_values[gene] = np.log1p(cp10k)

    raw_targets = np.full((len(column_indices), len(TARGET_NAMES)), np.nan, dtype=np.float64)
    for index, target in enumerate(TARGET_NAMES):
        if target in qc.MODULES:
            module_members = list(qc.MODULES[target])
            if all(gene_present[gene] for gene in module_members):
                raw_targets[:, index] = np.mean(
                    np.vstack([gene_values[gene] for gene in module_members]),
                    axis=0,
                    dtype=np.float64,
                )
        elif gene_present.get(target, False):
            raw_targets[:, index] = gene_values[target]
    return library_size, raw_targets, gene_values, gene_present


def load_spatial_sample(
    participant_id: str,
    expression_path: Path,
    spatial_path: Path,
    helper: Any,
    stage1: Any,
    qc: Any,
    encoder: torch.nn.Module,
    transform: Any,
    device: torch.device,
    library_identifier: Any,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    matrix_triplet_is_unambiguous(expression_path)
    source = helper.read_expression_zip(expression_path)
    if source is None:
        raise ParticipantDataUnavailable(f"No readable Matrix Market triplet in {expression_path.name}")

    archive_rows, spatial = archive_members(spatial_path)
    positions_name = spatial["positions_member"].decode("utf-8")
    positions = read_positions_bytes(positions_name, spatial["positions"])
    positions["barcode"] = positions["barcode"].astype(str)
    if positions["barcode"].duplicated().any():
        raise ParticipantDataUnavailable("Spatial positions contain duplicate barcodes")
    in_tissue = positions[pd.to_numeric(positions["in_tissue"], errors="coerce") == 1].copy()
    if in_tissue.empty:
        raise ParticipantDataUnavailable("Spatial positions have no in-tissue spots")
    for column in ("array_row", "array_col", "pxl_row_in_fullres", "pxl_col_in_fullres"):
        in_tissue[column] = pd.to_numeric(in_tissue[column], errors="raise")
    if not np.isfinite(
        in_tissue[["array_row", "array_col", "pxl_row_in_fullres", "pxl_col_in_fullres"]].to_numpy(
            dtype=np.float64
        )
    ).all():
        raise ParticipantDataUnavailable("Spatial coordinates contain non-finite values")

    barcodes = [str(value) for value in source["barcodes"]]
    if len(set(barcodes)) != len(barcodes):
        raise ParticipantDataUnavailable("Expression matrix contains duplicate barcodes")
    barcode_to_column = {barcode: index for index, barcode in enumerate(barcodes)}
    tissue_barcodes = in_tissue["barcode"].tolist()
    missing = [barcode for barcode in tissue_barcodes if barcode not in barcode_to_column]
    if missing:
        raise ParticipantDataUnavailable(
            f"Incomplete expression match: {len(tissue_barcodes) - len(missing)}/{len(tissue_barcodes)} "
            "in-tissue barcodes have expression"
        )
    column_indices = np.asarray([barcode_to_column[barcode] for barcode in tissue_barcodes], dtype=np.int64)
    library_size, normalized_targets, _gene_values, gene_present = feature_count_matrix(
        source, qc, column_indices
    )

    scale = json.loads(spatial["scalefactors"].decode("utf-8"))
    hires_scale = float(scale["tissue_hires_scalef"])
    if not math.isfinite(hires_scale) or hires_scale <= 0:
        raise ParticipantDataUnavailable("Invalid tissue_hires_scalef")
    image_bgr = cv2.imdecode(
        np.frombuffer(spatial["hires_image"], dtype=np.uint8), cv2.IMREAD_COLOR
    )
    if image_bgr is None:
        raise ParticipantDataUnavailable("Cannot decode tissue_hires_image.png")
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    height, width = image_rgb.shape[:2]
    x = np.rint(
        in_tissue["pxl_col_in_fullres"].to_numpy(dtype=np.float64) * hires_scale
    ).astype(np.int64)
    y = np.rint(
        in_tissue["pxl_row_in_fullres"].to_numpy(dtype=np.float64) * hires_scale
    ).astype(np.int64)
    outside = (x < 0) | (x >= width) | (y < 0) | (y >= height)
    if outside.any():
        raise ParticipantDataUnavailable(
            f"{int(outside.sum())} mapped spot centers lie outside the hires image"
        )

    n_spots = len(in_tissue)
    embeddings = np.empty((n_spots, 2048), dtype=np.float16)
    colors = np.empty((n_spots, 12), dtype=np.float32)
    batch_size = 64
    with torch.inference_mode():
        for start in range(0, n_spots, batch_size):
            stop = min(start + batch_size, n_spots)
            tensors = []
            for index in range(start, stop):
                tile = stage1.crop_reflect(image_rgb, int(x[index]), int(y[index]), 224)
                colors[index] = stage1.color_statistics(tile)
                tensors.append(transform(Image.fromarray(tile).convert("RGB")))
            batch = torch.stack(tensors).to(device)
            embeddings[start:stop] = (
                encoder(batch).detach().cpu().numpy().astype(np.float16)
            )

    array_rows = in_tissue["array_row"].to_numpy(dtype=np.int64)
    array_cols = in_tissue["array_col"].to_numpy(dtype=np.int64)
    coordinates = list(zip(array_rows, array_cols))
    if len(set(coordinates)) != len(coordinates):
        raise ParticipantDataUnavailable("In-tissue array coordinates are not unique")
    neighbor_lookup = {coordinate: index for index, coordinate in enumerate(coordinates)}
    neighbor_indices: list[list[int]] = []
    neighbor_counts = np.zeros(n_spots, dtype=np.int16)
    for index, (array_row, array_col) in enumerate(coordinates):
        found = [
            neighbor_lookup[(array_row + drow, array_col + dcol)]
            for drow, dcol in NEIGHBOR_OFFSETS
            if (array_row + drow, array_col + dcol) in neighbor_lookup
        ]
        neighbor_indices.append(found)
        neighbor_counts[index] = len(found)

    depth = np.log1p(library_size)
    target_parameters = pd.read_csv(RESIDUALIZATION)
    target_parameters = target_parameters[
        target_parameters["parameter_type"] == "target_on_depth"
    ]
    parameter_by_target = {
        str(row.target): row for row in target_parameters.itertuples(index=False)
    }
    if set(parameter_by_target) != set(TARGET_NAMES):
        raise AssertionError("Frozen residualization parameters do not cover the target set")
    residual_targets = np.full_like(normalized_targets, np.nan, dtype=np.float64)
    for index, target in enumerate(TARGET_NAMES):
        parameter = parameter_by_target[target]
        residual_targets[:, index] = normalized_targets[:, index] - (
            float(parameter.intercept) + float(parameter.depth_coefficient) * depth
        )
    neighbor_targets = np.full_like(residual_targets, np.nan, dtype=np.float64)
    for index, found in enumerate(neighbor_indices):
        if found:
            neighbor_targets[index] = np.mean(
                residual_targets[found], axis=0, dtype=np.float64
            )

    relative_expression_path = expression_path.relative_to(ROOT)
    library_id = stage1.library_identifier(relative_expression_path)
    participant_ids = np.full(n_spots, participant_id, dtype="U32")
    library_ids = np.full(n_spots, library_id, dtype="U64")
    barcode_array = np.asarray(tissue_barcodes, dtype="U64")
    keys = list(zip(participant_ids.astype(str), library_ids.astype(str), barcode_array.astype(str)))
    if len(set(keys)) != n_spots:
        raise AssertionError(f"Non-unique (participant, library, barcode) keys for {participant_id}")

    sample = {
        "participant_id": participant_id,
        "library_id": library_id,
        "source_file": expression_path.name,
        "keys": keys,
        "participant_ids": participant_ids,
        "library_ids": library_ids,
        "barcodes": barcode_array,
        "embeddings": embeddings,
        "colors": colors,
        "depth": depth,
        "library_size": library_size,
        "raw_targets": normalized_targets,
        "residual_targets": residual_targets,
        "neighbor_targets": neighbor_targets,
        "neighbor_counts": neighbor_counts,
        "array_rows": array_rows,
        "array_cols": array_cols,
        "n_spots": n_spots,
        "n_finite_primary": int(np.isfinite(neighbor_targets[:, TARGET_NAMES.index(PRIMARY_TARGET)]).sum()),
    }
    map_row = {
        "participant_id": participant_id,
        "library_id": library_id,
        "expression_file": expression_path.name,
        "spatial_file": spatial_path.name,
        "positions_member": positions_name,
        "scalefactors_member": spatial["scalefactors_member"].decode("utf-8"),
        "hires_image_member": spatial["hires_image_member"].decode("utf-8"),
        "n_positions_rows": int(len(positions)),
        "n_in_tissue_positions": int(n_spots),
        "n_expression_barcodes": int(len(barcodes)),
        "n_matched_in_tissue_barcodes": int(n_spots),
        "hires_width_px": int(width),
        "hires_height_px": int(height),
        "tissue_hires_scalef": hires_scale,
        "min_center_x_px": int(x.min()),
        "max_center_x_px": int(x.max()),
        "min_center_y_px": int(y.min()),
        "max_center_y_px": int(y.max()),
        "all_centers_inside_image": True,
        "all_target_genes_present": all(gene_present.get(gene, False) for gene in TARGET_NAMES[3:]),
        "primary_module_members_present": all(
            gene_present.get(gene, False)
            for gene in qc.MODULES[PRIMARY_TARGET]
        ),
    }
    archive_row = {
        "participant_id": participant_id,
        "spatial_file": spatial_path.name,
        "archive_file_count": len(archive_rows),
        "archive_uncompressed_bytes": sum(int(row["size"]) for row in archive_rows),
        "extension_counts": spatial["archive_summary"].decode("utf-8"),
        "positions_member": positions_name,
        "scalefactors_member": spatial["scalefactors_member"].decode("utf-8"),
        "hires_image_member": spatial["hires_image_member"].decode("utf-8"),
        "extracted_files": 0,
    }
    return sample, map_row, [archive_row]


def load_frozen_models(
    stage1b: Any,
) -> tuple[Any, ...]:
    with np.load(MLP_SCALERS, allow_pickle=False) as archive:
        feature_mean = archive["feature_mean"]
        feature_scale = archive["feature_scale"]
        target_mean = archive["target_mean"]
        target_scale = archive["target_scale"]
        names = archive["feature_names"].astype(str).tolist()
        target_names = archive["target_names"].astype(str).tolist()
    feature_definition = json.loads(FEATURE_NAMES.read_text(encoding="utf-8"))
    declared_names = feature_definition.get("features_in_order", [])
    if names != declared_names or len(names) != 2048 or target_names != TARGET_NAMES:
        raise AssertionError("Frozen MLP scaler or feature/target order does not match")
    reference = json.loads(ENCODER_REFERENCE.read_text(encoding="utf-8"))
    if sha256_file(ENCODER_CHECKPOINT) != reference["sha256"]:
        raise AssertionError("ResNet-50 checkpoint does not match its frozen reference SHA-256")
    weights = ResNet50_Weights.IMAGENET1K_V2
    encoder = resnet50(weights=None)
    encoder_state = torch.load(ENCODER_CHECKPOINT, map_location="cpu", weights_only=True)
    encoder.load_state_dict(encoder_state, strict=True)
    encoder.fc = torch.nn.Identity()
    encoder.eval()

    device = stage1b.DEVICE
    torch.set_num_threads(min(8, os.cpu_count() or 1))
    encoder = encoder.to(device)
    transform = weights.transforms()

    stage1b.seed_torch(20261113)
    mlp = stage1b.SmallMLP(len(names), len(TARGET_NAMES))
    mlp_state = torch.load(MLP_MODEL, map_location="cpu", weights_only=True)
    mlp.load_state_dict(mlp_state, strict=True)
    mlp = mlp.to(device)
    mlp.eval()

    ridge_bundle = joblib.load(RIDGE_MODEL)
    baseline_definitions = json.loads(BASELINE_DEFINITIONS.read_text(encoding="utf-8"))
    if ridge_bundle["target_names"] != TARGET_NAMES or ridge_bundle["alpha"] != 1.0:
        raise AssertionError("Frozen Ridge baseline model metadata does not match")
    with np.load(RIDGE_SCALERS, allow_pickle=False) as archive:
        ridge_scalers = {name: archive[name] for name in archive.files}
    if ridge_scalers["target_names"].astype(str).tolist() != TARGET_NAMES:
        raise AssertionError("Frozen Ridge target scaler order does not match")
    if not np.allclose(ridge_scalers["target_mean"], target_mean, rtol=0, atol=1e-12):
        raise AssertionError("Frozen MLP and Ridge target means differ")
    if not np.allclose(ridge_scalers["target_scale"], target_scale, rtol=0, atol=1e-12):
        raise AssertionError("Frozen MLP and Ridge target scales differ")
    return (
        mlp,
        feature_mean,
        feature_scale,
        target_mean,
        target_scale,
        ridge_bundle,
        ridge_scalers,
        transform,
        device,
        encoder,
        baseline_definitions,
    )


def apply_models(
    samples: list[dict[str, Any]],
    models: tuple[Any, ...],
) -> None:
    (
        mlp,
        feature_mean,
        feature_scale,
        target_mean,
        target_scale,
        ridge_bundle,
        ridge_scalers,
        _transform,
        device,
        _encoder,
        _baseline_definitions,
    ) = models
    for sample in samples:
        embeddings = sample["embeddings"].astype(np.float32)
        standardized_features = ((embeddings - feature_mean) / feature_scale).astype(np.float32)
        output_batches = []
        with torch.inference_mode():
            for start in range(0, len(standardized_features), 1024):
                batch = torch.from_numpy(
                    np.ascontiguousarray(standardized_features[start : start + 1024])
                ).to(device)
                output_batches.append(mlp(batch).cpu().numpy())
        standardized_prediction = np.concatenate(output_batches, axis=0)
        sample["predictions_mlp_spot"] = (
            standardized_prediction * target_scale + target_mean
        )

        model_predictions = {}
        for model_name, input_values in (
            ("depth_only_ridge", sample["depth"].reshape(-1, 1).astype(np.float64)),
            ("color_only_ridge", sample["colors"].astype(np.float64)),
        ):
            feature_mean_for_model = ridge_scalers[f"{model_name}_feature_mean"]
            feature_scale_for_model = ridge_scalers[f"{model_name}_feature_scale"]
            standardized_input = (input_values - feature_mean_for_model) / feature_scale_for_model
            if ridge_bundle["feature_names"][model_name] != (
                ["log1p_total_spot_umi"]
                if model_name == "depth_only_ridge"
                else json.loads(BASELINE_DEFINITIONS.read_text(encoding="utf-8"))["models"][
                    "color_only_ridge"
                ]["feature_names"]
            ):
                raise AssertionError(f"Frozen feature order mismatch for {model_name}")
            standardized = ridge_bundle["models"][model_name].predict(standardized_input)
            model_predictions[model_name] = standardized * target_scale + target_mean
        sample["predictions_depth_only_ridge"] = model_predictions["depth_only_ridge"]
        sample["predictions_color_only_ridge"] = model_predictions["color_only_ridge"]


def load_registered_samples(
    plan: list[dict[str, str]],
    helper: Any,
    stage1: Any,
    qc: Any,
    models: tuple[Any, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    expression_by_participant = {
        row["participant_id"]: DATA_DIR / row["file_name"]
        for row in plan
        if row["asset_type"] == "open_expression_matrix"
    }
    spatial_by_participant = {
        row["participant_id"]: DATA_DIR / row["file_name"]
        for row in plan
        if row["asset_type"] == "spatial_bundle"
    }
    if set(expression_by_participant) != set(PARTICIPANTS) or set(spatial_by_participant) != set(PARTICIPANTS):
        raise AssertionError("Downloaded inputs do not contain one matrix and one spatial bundle per participant")
    (
        _mlp,
        _feature_mean,
        _feature_scale,
        _target_mean,
        _target_scale,
        _ridge_bundle,
        _ridge_scalers,
        transform,
        device,
        encoder,
        _definitions,
    ) = models

    samples: list[dict[str, Any]] = []
    mapping_rows: list[dict[str, Any]] = []
    archive_rows: list[dict[str, Any]] = []
    participant_exclusions: list[dict[str, Any]] = []
    for participant_id in PARTICIPANTS:
        try:
            sample, mapping, archive_summary = load_spatial_sample(
                participant_id,
                expression_by_participant[participant_id],
                spatial_by_participant[participant_id],
                helper,
                stage1,
                qc,
                encoder,
                transform,
                device,
                stage1.library_identifier,
            )
        except ParticipantDataUnavailable as error:
            participant_exclusions.append(
                {
                    "participant_id": participant_id,
                    "reason": str(error),
                    "exclusion_stage": "input_pairing_or_spatial_mapping",
                }
            )
            continue
        samples.append(sample)
        mapping_rows.append(mapping)
        archive_rows.extend(archive_summary)
    if samples:
        apply_models(samples, models)

    original_archive = np.load(ORIGINAL_KEYS, allow_pickle=False)
    original_libraries = set(original_archive["library_id"].astype(str))
    new_libraries = [sample["library_id"] for sample in samples]
    if len(set(new_libraries)) != len(new_libraries):
        raise AssertionError("Confirmation library IDs are not unique")
    overlap = set(new_libraries) & original_libraries
    if overlap:
        raise AssertionError(f"New library IDs overlap the original 29: {sorted(overlap)}")
    return samples, mapping_rows, archive_rows, participant_exclusions


def concatenate_samples(samples: list[dict[str, Any]]) -> dict[str, np.ndarray]:
    if not samples:
        return {}
    keys = [key for sample in samples for key in sample["keys"]]
    if len(keys) != len(set(keys)):
        raise AssertionError("Duplicate full confirmation spot keys")
    if len({key[0] for key in keys} & set(PARTICIPANTS)) != len({key[0] for key in keys}):
        raise AssertionError("Unexpected participant ID in confirmation keys")
    return {
        "participant_id": np.concatenate([sample["participant_ids"] for sample in samples]),
        "library_id": np.concatenate([sample["library_ids"] for sample in samples]),
        "barcode": np.concatenate([sample["barcodes"] for sample in samples]),
        "embeddings": np.concatenate([sample["embeddings"] for sample in samples]),
        "colors": np.concatenate([sample["colors"] for sample in samples]),
        "depth": np.concatenate([sample["depth"] for sample in samples]),
        "library_size": np.concatenate([sample["library_size"] for sample in samples]),
        "residual_targets": np.concatenate([sample["residual_targets"] for sample in samples]),
        "neighbor_targets": np.concatenate([sample["neighbor_targets"] for sample in samples]),
        "neighbor_counts": np.concatenate([sample["neighbor_counts"] for sample in samples]),
        "array_rows": np.concatenate([sample["array_rows"] for sample in samples]),
        "array_cols": np.concatenate([sample["array_cols"] for sample in samples]),
        "predictions_mlp_spot": np.concatenate(
            [sample["predictions_mlp_spot"] for sample in samples]
        ),
        "predictions_color_only_ridge": np.concatenate(
            [sample["predictions_color_only_ridge"] for sample in samples]
        ),
        "predictions_depth_only_ridge": np.concatenate(
            [sample["predictions_depth_only_ridge"] for sample in samples]
        ),
    }


def finite_spearman(target: np.ndarray, prediction: np.ndarray) -> float:
    valid = np.isfinite(target) & np.isfinite(prediction)
    y = target[valid]
    p = prediction[valid]
    if len(y) < 2 or np.unique(y).size < 2 or np.unique(p).size < 2:
        return math.nan
    return float(spearmanr(y, p).statistic)


def participant_eligibility(
    target: np.ndarray, predictions: dict[str, np.ndarray]
) -> tuple[np.ndarray, list[str]]:
    valid = np.isfinite(target)
    for values in predictions.values():
        valid &= np.isfinite(values)
    y = target[valid]
    reasons = []
    if len(y) < MIN_FINITE_SPOTS:
        reasons.append("fewer_than_10_finite_spots")
    if np.unique(y).size < MIN_DISTINCT_TARGETS:
        reasons.append("fewer_than_3_distinct_target_values")
    for model_name, values in predictions.items():
        if np.unique(values[valid]).size < 2:
            reasons.append(f"constant_predictions:{model_name}")
    return valid, reasons


def bootstrap_mean_ci(values: np.ndarray, rng: np.random.Generator) -> tuple[float, float, float]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return math.nan, math.nan, math.nan
    draws = rng.integers(0, finite.size, size=(BOOTSTRAP_REPLICATES, finite.size))
    means = finite[draws].mean(axis=1)
    low, high = np.quantile(means, [0.025, 0.975])
    return float(finite.mean()), float(low), float(high)


def primary_results(
    arrays: dict[str, np.ndarray], samples: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows = []
    exclusions = []
    participant_values: dict[str, dict[str, float]] = {}
    if not arrays:
        for participant_id in PARTICIPANTS:
            exclusions.append(
                {
                    "participant_id": participant_id,
                    "reason": "no usable paired inputs",
                    "exclusion_stage": "input_pairing_or_spatial_mapping",
                }
            )
        return rows, exclusions, []
    participant_array = arrays["participant_id"].astype(str)
    target_index = TARGET_NAMES.index(PRIMARY_TARGET)
    target_values = arrays["neighbor_targets"][:, target_index]
    predictions = {
        name: arrays[column][:, target_index]
        for name, column in MODEL_COLUMNS.items()
    }
    for participant_id in PARTICIPANTS:
        mask = participant_array == participant_id
        if not mask.any():
            rows.append(
                {
                    "participant_id": participant_id,
                    "n_in_tissue_spots": 0,
                    "n_finite_primary_target_spots": 0,
                    "n_scored_spots": 0,
                    "n_distinct_primary_target_values": 0,
                    "mlp_spot_spearman": math.nan,
                    "color_only_ridge_spearman": math.nan,
                    "depth_only_ridge_spearman": math.nan,
                    "mlp_minus_color_delta": math.nan,
                    "mlp_minus_depth_delta": math.nan,
                    "eligible_for_primary_metric": False,
                    "ineligibility_reason": "no usable paired inputs",
                }
            )
            continue
        local_target = target_values[mask]
        local_predictions = {name: values[mask] for name, values in predictions.items()}
        valid, reasons = participant_eligibility(local_target, local_predictions)
        values: dict[str, float] = {}
        if not reasons:
            for model_name, prediction in local_predictions.items():
                values[model_name] = float(
                    spearmanr(local_target[valid], prediction[valid]).statistic
                )
            participant_values[participant_id] = values
        rows.append(
            {
                "participant_id": participant_id,
                "n_in_tissue_spots": int(mask.sum()),
                "n_finite_primary_target_spots": int(np.isfinite(local_target).sum()),
                "n_scored_spots": int(valid.sum()),
                "n_distinct_primary_target_values": int(np.unique(local_target[valid]).size),
                "mlp_spot_spearman": values.get("mlp_spot", math.nan),
                "color_only_ridge_spearman": values.get("color_only_ridge", math.nan),
                "depth_only_ridge_spearman": values.get("depth_only_ridge", math.nan),
                "mlp_minus_color_delta": (
                    values.get("mlp_spot", math.nan)
                    - values.get("color_only_ridge", math.nan)
                    if values
                    else math.nan
                ),
                "mlp_minus_depth_delta": (
                    values.get("mlp_spot", math.nan)
                    - values.get("depth_only_ridge", math.nan)
                    if values
                    else math.nan
                ),
                "eligible_for_primary_metric": not reasons,
                "ineligibility_reason": ";".join(reasons),
            }
        )
        if reasons:
            exclusions.append(
                {
                    "participant_id": participant_id,
                    "reason": ";".join(reasons),
                    "exclusion_stage": "primary_metric_eligibility",
                }
            )

    eligible = sorted(participant_values)
    if eligible:
        delta_color = np.asarray(
            [
                participant_values[pid]["mlp_spot"]
                - participant_values[pid]["color_only_ridge"]
                for pid in eligible
            ],
            dtype=np.float64,
        )
        delta_depth = np.asarray(
            [
                participant_values[pid]["mlp_spot"]
                - participant_values[pid]["depth_only_ridge"]
                for pid in eligible
            ],
            dtype=np.float64,
        )
    else:
        delta_color = np.asarray([], dtype=np.float64)
        delta_depth = np.asarray([], dtype=np.float64)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    comparisons = []
    for name, deltas, baseline in (
        ("mlp_spot - color_only_ridge", delta_color, "color_only_ridge"),
        ("mlp_spot - depth_only_ridge", delta_depth, "depth_only_ridge"),
    ):
        mean, low, high = bootstrap_mean_ci(deltas, rng)
        comparisons.append(
            {
                "target": PRIMARY_TARGET,
                "metric": "paired participant-level Spearman delta",
                "comparison": name,
                "baseline": baseline,
                "n_eligible_participants": len(eligible),
                "mean_delta": mean,
                "ci95_low": low,
                "ci95_high": high,
                "bootstrap_replicates": BOOTSTRAP_REPLICATES,
                "bootstrap_seed": BOOTSTRAP_SEED,
            }
        )
    return rows, exclusions, comparisons


def secondary_results(
    arrays: dict[str, np.ndarray]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not arrays:
        return [], []
    participants = arrays["participant_id"].astype(str)
    prediction_arrays = {
        name: arrays[column]
        for name, column in MODEL_COLUMNS.items()
    }
    variants = {
        "depth_residualized_neighbor_mean": arrays["neighbor_targets"],
        "depth_residualized_unsmoothed": arrays["residual_targets"],
    }
    rows = []
    summaries = []
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    for variant, target_matrix in variants.items():
        for target_index, target_name in enumerate(TARGET_NAMES):
            per_participant: dict[str, dict[str, float]] = {}
            for participant_id in PARTICIPANTS:
                mask = participants == participant_id
                if not mask.any():
                    continue
                local_target = target_matrix[mask, target_index]
                local_predictions = {
                    name: values[mask, target_index]
                    for name, values in prediction_arrays.items()
                }
                valid, reasons = participant_eligibility(local_target, local_predictions)
                metric_values = {}
                if not reasons:
                    metric_values = {
                        model_name: float(
                            spearmanr(local_target[valid], values[valid]).statistic
                        )
                        for model_name, values in local_predictions.items()
                    }
                    per_participant[participant_id] = metric_values
                rows.append(
                    {
                        "label": "exploratory, post-hoc",
                        "target_variant": variant,
                        "target": target_name,
                        "participant_id": participant_id,
                        "n_finite_spots": int(np.isfinite(local_target).sum()),
                        "n_scored_spots": int(valid.sum()),
                        "mlp_spot_spearman": metric_values.get("mlp_spot", math.nan),
                        "color_only_ridge_spearman": metric_values.get(
                            "color_only_ridge", math.nan
                        ),
                        "depth_only_ridge_spearman": metric_values.get(
                            "depth_only_ridge", math.nan
                        ),
                        "eligible_under_primary_rule": not reasons,
                        "ineligibility_reason": ";".join(reasons),
                    }
                )
            eligible = sorted(per_participant)
            for model_name in MODEL_COLUMNS:
                rho_values = np.asarray(
                    [per_participant[pid][model_name] for pid in eligible],
                    dtype=np.float64,
                )
                mean, low, high = bootstrap_mean_ci(rho_values, rng)
                summaries.append(
                    {
                        "label": "exploratory, post-hoc",
                        "target_variant": variant,
                        "target": target_name,
                        "model": model_name,
                        "n_eligible_participants": len(eligible),
                        "mean_participant_spearman": mean,
                        "ci95_low": low,
                        "ci95_high": high,
                        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
                        "bootstrap_seed": BOOTSTRAP_SEED,
                    }
                )
            for baseline in ("color_only_ridge", "depth_only_ridge"):
                deltas = np.asarray(
                    [
                        per_participant[pid]["mlp_spot"]
                        - per_participant[pid][baseline]
                        for pid in eligible
                    ],
                    dtype=np.float64,
                )
                mean, low, high = bootstrap_mean_ci(deltas, rng)
                summaries.append(
                    {
                        "label": "exploratory, post-hoc",
                        "target_variant": variant,
                        "target": target_name,
                        "model": f"mlp_spot - {baseline}",
                        "n_eligible_participants": len(eligible),
                        "mean_participant_spearman": mean,
                        "ci95_low": low,
                        "ci95_high": high,
                        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
                        "bootstrap_seed": BOOTSTRAP_SEED,
                    }
                )
    return rows, summaries


def spatial_block_results(arrays: dict[str, np.ndarray]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not arrays:
        return [], []
    participants = arrays["participant_id"].astype(str)
    prediction_arrays = {
        name: arrays[column]
        for name, column in MODEL_COLUMNS.items()
    }
    variants = {
        "depth_residualized_neighbor_mean": arrays["neighbor_targets"],
        "depth_residualized_unsmoothed": arrays["residual_targets"],
    }
    rows = []
    summaries = []
    for variant, target_matrix in variants.items():
        for target_index, target_name in enumerate(TARGET_NAMES):
            for participant_id in PARTICIPANTS:
                participant_mask = participants == participant_id
                if not participant_mask.any():
                    continue
                local_indices = np.flatnonzero(participant_mask)
                for model_name, prediction_matrix in prediction_arrays.items():
                    y = target_matrix[local_indices, target_index]
                    p = prediction_matrix[local_indices, target_index]
                    valid = np.isfinite(y) & np.isfinite(p)
                    block_values: dict[tuple[str, int, int], list[float]] = {}
                    for local_index in np.flatnonzero(valid):
                        global_index = int(local_indices[local_index])
                        key = (
                            str(arrays["library_id"][global_index]),
                            int(arrays["array_rows"][global_index]) // BLOCK_WIDTH,
                            int(arrays["array_cols"][global_index]) // BLOCK_WIDTH,
                        )
                        pair = block_values.setdefault(key, [[], []])
                        pair[0].append(float(y[local_index]))
                        pair[1].append(float(p[local_index]))
                    block_y = np.asarray(
                        [np.mean(pair[0]) for pair in block_values.values()],
                        dtype=np.float64,
                    )
                    block_p = np.asarray(
                        [np.mean(pair[1]) for pair in block_values.values()],
                        dtype=np.float64,
                    )
                    reason = ""
                    rho = math.nan
                    if len(block_y) < 4:
                        reason = "fewer_than_4_blocks"
                    elif np.unique(block_y).size < 2:
                        reason = "constant_block_targets"
                    elif np.unique(block_p).size < 2:
                        reason = "constant_block_predictions"
                    else:
                        rho = float(spearmanr(block_y, block_p).statistic)
                    rows.append(
                        {
                            "label": "exploratory, post-hoc",
                            "target_variant": variant,
                            "target": target_name,
                            "participant_id": participant_id,
                            "model": model_name,
                            "block_width_array_coordinates": BLOCK_WIDTH,
                            "n_blocks": len(block_y),
                            "block_spearman": rho,
                            "skip_reason": reason,
                        }
                    )
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    frame = pd.DataFrame(rows)
    if not frame.empty:
        for (variant, target, model), group in frame.groupby(
            ["target_variant", "target", "model"], sort=False
        ):
            values = group["block_spearman"].to_numpy(dtype=np.float64)
            mean, low, high = bootstrap_mean_ci(values, rng)
            summaries.append(
                {
                    "label": "exploratory, post-hoc",
                    "target_variant": variant,
                    "target": target,
                    "model": model,
                    "n_eligible_participants": int(np.isfinite(values).sum()),
                    "mean_participant_block_spearman": mean,
                    "ci95_low": low,
                    "ci95_high": high,
                    "bootstrap_replicates": BOOTSTRAP_REPLICATES,
                    "bootstrap_seed": BOOTSTRAP_SEED,
                    "block_width_array_coordinates": BLOCK_WIDTH,
                }
            )
    return rows, summaries


def write_spot_exclusions(arrays: dict[str, np.ndarray]) -> list[dict[str, Any]]:
    rows = []
    if not arrays:
        return rows
    target_index = TARGET_NAMES.index(PRIMARY_TARGET)
    target = arrays["neighbor_targets"][:, target_index]
    residual = arrays["residual_targets"][:, target_index]
    counts = arrays["neighbor_counts"]
    for index, value in enumerate(target):
        reasons = []
        if counts[index] == 0:
            reasons.append("no_in_tissue_neighbor_at_registered_offsets")
        if not np.isfinite(residual[index]):
            reasons.append("nonfinite_depth_residualized_target")
        if counts[index] > 0 and not np.isfinite(value) and np.isfinite(residual[index]):
            reasons.append("nonfinite_neighbor_value_propagated_without_imputation")
        if reasons:
            rows.append(
                {
                    "participant_id": str(arrays["participant_id"][index]),
                    "library_id": str(arrays["library_id"][index]),
                    "barcode": str(arrays["barcode"][index]),
                    "target": PRIMARY_TARGET,
                    "reason": ";".join(reasons),
                }
            )
    return rows


def verify_metrics_fresh_process() -> dict[str, Any]:
    data = np.load(DATA_OUTPUT, allow_pickle=False)
    reported = pd.read_csv(PRIMARY_METRICS)
    participants = data["participant_id"].astype(str)
    target = data["neighbor_targets"][:, TARGET_NAMES.index(PRIMARY_TARGET)]
    model_values = {
        name: data[column][:, TARGET_NAMES.index(PRIMARY_TARGET)]
        for name, column in MODEL_COLUMNS.items()
    }
    recomputed = []
    for participant_id in PARTICIPANTS:
        row = reported[reported["participant_id"].astype(str) == participant_id]
        if len(row) != 1:
            raise AssertionError(f"Primary metric table does not have one row for {participant_id}")
        local = participants == participant_id
        if not local.any():
            continue
        valid = np.isfinite(target[local])
        for values in model_values.values():
            valid &= np.isfinite(values[local])
        eligible_value = row.iloc[0]["eligible_for_primary_metric"]
        eligible = bool(
            eligible_value
            if isinstance(eligible_value, (bool, np.bool_))
            else str(eligible_value).strip().casefold() == "true"
        )
        model_checks = {}
        for model_name, prediction in model_values.items():
            y = target[local][valid]
            p = prediction[local][valid]
            direct = (
                float(np.corrcoef(rankdata(y, method="average"), rankdata(p, method="average"))[0, 1])
                if eligible
                else math.nan
            )
            column_name = {
                "mlp_spot": "mlp_spot_spearman",
                "color_only_ridge": "color_only_ridge_spearman",
                "depth_only_ridge": "depth_only_ridge_spearman",
            }[model_name]
            saved = float(row.iloc[0][column_name])
            difference = abs(direct - saved) if eligible else 0.0
            if eligible and (not math.isfinite(difference) or difference > 1e-12):
                raise AssertionError(
                    f"Independent Spearman recomputation mismatch for {participant_id}/{model_name}"
                )
            model_checks[model_name] = {
                "recomputed_spearman": direct,
                "reported_spearman": saved,
                "absolute_difference": difference,
                "verified": bool(not eligible or difference <= 1e-12),
            }
        recomputed.append(
            {
                "participant_id": participant_id,
                "eligible": eligible,
                "models": model_checks,
            }
        )
    key_tuples = list(
        zip(
            data["participant_id"].astype(str),
            data["library_id"].astype(str),
            data["barcode"].astype(str),
        )
    )
    if len(key_tuples) != len(set(key_tuples)):
        raise AssertionError("Fresh-process confirmation keys are not unique")
    result = {
        "fresh_process": True,
        "metric": "participant-level spot Spearman; independently computed as Pearson correlation of average ranks",
        "metrics_recomputed": sum(
            len(row["models"]) for row in recomputed if row["eligible"]
        ),
        "eligible_participants": int(reported["eligible_for_primary_metric"].astype(bool).sum()),
        "unique_full_keys": len(key_tuples),
        "duplicate_full_keys": 0,
        "participant_checks": recomputed,
        "max_absolute_difference": max(
            (
                model["absolute_difference"]
                for row in recomputed
                for model in row["models"].values()
            ),
            default=0.0,
        ),
    }
    VERIFICATION.write_text(json.dumps(result, indent=2, allow_nan=True) + "\n", encoding="utf-8")
    return result


def make_report(
    samples: list[dict[str, Any]],
    mapping_rows: list[dict[str, Any]],
    exclusions: list[dict[str, Any]],
    primary_rows: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    source_checks: list[dict[str, Any]],
    spot_exclusions: list[dict[str, Any]],
    manifest: list[dict[str, str]],
    verification: dict[str, Any],
) -> None:
    eligible_count = sum(bool(row["eligible_for_primary_metric"]) for row in primary_rows)
    success = (
        eligible_count >= MIN_ELIGIBLE_PARTICIPANTS
        and len(comparisons) == 2
        and all(float(row["ci95_low"]) > 0 for row in comparisons)
    )
    if eligible_count < MIN_ELIGIBLE_PARTICIPANTS:
        decision = "INCONCLUSIVE — fewer than 10 participants were eligible; the success rule was not met."
    elif success:
        decision = "SUCCESS — the candidate's paired-delta 95% CIs were entirely above zero against both frozen baselines."
    else:
        decision = "FAIL — the image-only candidate did not show confirmatory improvement over both frozen baselines."

    def format_number(value: Any) -> str:
        if value is None or not np.isfinite(float(value)):
            return "NA"
        return f"{float(value):.4f}"

    table_lines = [
        "| Participant | Finite spots | Distinct target values | MLP Spearman | Colour Ridge Spearman | Depth Ridge Spearman | MLP−colour | MLP−depth | Eligible / reason |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    by_participant = {row["participant_id"]: row for row in primary_rows}
    for participant_id in PARTICIPANTS:
        row = by_participant.get(participant_id)
        if row is None:
            reason_row = next(
                (item for item in exclusions if item["participant_id"] == participant_id),
                {},
            )
            table_lines.append(
                f"| {participant_id} | 0 | 0 | NA | NA | NA | NA | NA | No paired inputs: {reason_row.get('reason', 'unavailable')} |"
            )
            continue
        label = "yes" if row["eligible_for_primary_metric"] else f"no: {row['ineligibility_reason']}"
        table_lines.append(
            "| {pid} | {n} | {unique} | {mlp} | {color} | {depth} | {dc} | {dd} | {label} |".format(
                pid=participant_id,
                n=row["n_scored_spots"],
                unique=row["n_distinct_primary_target_values"],
                mlp=format_number(row["mlp_spot_spearman"]),
                color=format_number(row["color_only_ridge_spearman"]),
                depth=format_number(row["depth_only_ridge_spearman"]),
                dc=format_number(row["mlp_minus_color_delta"]),
                dd=format_number(row["mlp_minus_depth_delta"]),
                label=label,
            )
        )

    ci_lines = [
        "| Comparison | Eligible participants | Mean paired delta | 95% participant-bootstrap CI |",
        "|---|---:|---:|---|",
    ]
    for row in comparisons:
        ci_lines.append(
            f"| {row['comparison']} | {row['n_eligible_participants']} | {format_number(row['mean_delta'])} | "
            f"[{format_number(row['ci95_low'])}, {format_number(row['ci95_high'])}] |"
        )

    total_bytes = sum(int(row["size_bytes"]) for row in manifest)
    actual_free = __import__("shutil").disk_usage(ROOT.drive + "\\").free
    n_spots = sum(sample["n_spots"] for sample in samples)
    n_libraries = len({sample["library_id"] for sample in samples})
    n_participants = len({sample["participant_id"] for sample in samples})
    sources = "\n".join(
        f"- `{row['path']}` — SHA-256 `{row['actual_sha256']}`"
        for row in source_checks
    )
    terms_note = (
        "The catalog marks all 24 selected records open. Sixteen records link to the two "
        "catalog DOI collections named in the protocol, which state CC BY 4.0; eight records "
        "have no catalog DOI, so their file-specific terms remain unverified."
    )
    secondary_note = (
        "Exploratory outputs evaluate the frozen three models on the other module/gene heads, "
        "the unsmoothed residual targets, and 10×10 array-coordinate blocks. The preregistered "
        "Elastic Net image and image-plus-depth models had no frozen weights in the authorized "
        "directories and were not refit or applied."
    )
    report_text = f"""# Stage 1d Confirmation Report

**Run timestamp:** {datetime.now().astimezone().isoformat(timespec="seconds")}  
**Protocol:** [`PREREG_CONFIRM.md`](../stage1c_confirm/PREREG_CONFIRM.md)  
**Stage 1 Gate A:** remains **FAIL**. Stage 1b remains **exploratory, post-hoc**.

## Result and decision

**Primary target:** depth-residualized immediate-neighbor-mean `myofibroblast_pro-fibrotic` module.  
**Decision:** **{decision}**

The candidate was the frozen ResNet-50 IMAGENET1K_V2 spot embedding plus the frozen one-hidden-layer MLP. It was compared only with the frozen colour-only Ridge (`alpha=1`) and depth-only Ridge (`alpha=1`). No model was refit, retuned, or reselected using the new participants. The success rule required at least 10 eligible participants and both paired participant-bootstrap 95% CIs entirely above zero.

### Per-participant primary metrics

{chr(10).join(table_lines)}

### Paired participant-level deltas

{chr(10).join(ci_lines)}

Bootstrap: {BOOTSTRAP_REPLICATES:,} resamples at the participant level; seed `{BOOTSTRAP_SEED}`; percentile 2.5th and 97.5th quantiles. The same eligible participant set was used for both comparisons.

## Cohort, downloads, and key integrity

- Fixed preregistered cohort: {len(PARTICIPANTS)} participants; no replacements.
- Downloaded and SHA-256 logged: {len(manifest)} files ({sum(row['asset_type'] == 'open_expression_matrix' for row in manifest)} expression matrices and {sum(row['asset_type'] == 'spatial_bundle' for row in manifest)} spatial bundles), {total_bytes:,} bytes in total. No TIFF, FASTQ, or whole-slide image file was downloaded.
- Successfully paired and processed: {n_participants} participants, {n_libraries} libraries, {n_spots:,} in-tissue spots. Each key is `(participant_id, library_id, barcode)`; keys are unique and none overlap the original 28 participants or 29 libraries. The original frozen key file reconciled to 28 participants, 29 libraries, and 25,104 unique spots.
- Confirmation inputs remain in `D:\\patent\\data_confirm\\`; no archive members were extracted to disk. Only positions, scalefactors, and the hires image were read from each spatial archive.
- Disk free after download and analysis: {actual_free:,} bytes on D: (required reserve: 2,000,000,000 bytes).
- {terms_note}

## Processing and frozen-model application

- Expression parsing used the existing Matrix Market ZIP reader. In-tissue spatial barcodes had to match the expression matrix completely, following the original pairing rule; no partial match or alternate matrix was substituted.
- The hires image was decoded as RGB, and spot centers were mapped from full-resolution coordinates using `tissue_hires_scalef`, rounded as in Stage 1. Mapping dimensions, coordinate bounds, and expression-barcode coverage are recorded in `spatial_mapping_qc.csv`.
- Spot inputs were 224×224 crops with `BORDER_REFLECT_101`. Colour features used the original `color_statistics(rgb)` function. ResNet-50 encoder features were stored as float16 before the frozen MLP scaler, matching Stage 1 embedding precision. No tile PNGs were written.
- Targets used the QC expression normalization `log1p(count / total_spot_UMI × 10,000)`. Module scores are unweighted means of member-gene log-normalized values. Stored original-cohort target-on-depth coefficients were applied to new participants; no new-cohort residual-centering, scaling, fitting, tuning, or imputation was performed. Neighbor means used exactly `(0, ±2)`, `(±1, ±1)`, within library and excluding the center spot.
- The frozen encoder checkpoint matched its recorded SHA-256. MLP and Ridge model/scaler checksums matched their manifests; source checks are listed in `source_integrity_checks.csv`.
- The MLP head produced all 12 registered target outputs. Only the single primary target determined the decision. Frozen predictions for other targets and unsmoothed targets are separately labelled exploratory in the secondary CSVs. {secondary_note}

## Exclusions and verification

- Primary-score spot exclusions: {len(spot_exclusions)} spots; reasons and full keys are in `excluded_spots.csv`. No missing neighbor was imputed.
- Participant input or primary-metric exclusions: {len(exclusions)}; details are in `participant_exclusions.csv`. Primary metric eligibility was restricted to at least 10 finite spots, at least three distinct target values, and nonconstant predictions from all three models.
- Spatial mapping audit: {len(mapping_rows)} successful mappings; all listed in-tissue centers were inside their hires images. Archive-member summaries are in `spatial_archive_contents.csv`.
- Fresh-process independent metric recomputation checked {verification['metrics_recomputed']} model/participant Spearman values using Pearson correlation of average ranks. Maximum absolute difference from the primary table: {verification['max_absolute_difference']:.3g}. Full evidence is in `metric_recomputation.json`.
- Key audit: {verification['unique_full_keys']:,} unique full keys; {verification['duplicate_full_keys']} duplicate keys. No cross-validation folds were used in this external-cohort test.

## Deviations and what could not be verified

- **Deviations from the primary preregistration:** none. Network retries, if any, used the same catalog URLs and exact 24 authorized open files.
- The eight catalog records without a DOI do not have file-specific license terms verified in the catalog.
- Atlas did not provide server checksums for these transfers; the manifest records locally computed SHA-256 values and actual byte sizes.
- The exploratory Elastic Net image and image-plus-depth models were not available as frozen artifacts; applying them would require fitting/refitting, which this task forbids. Their results are therefore not reported.
- Optional secondary analyses cannot alter the primary success/failure decision or Stage 1 Gate A.

## Output files

- Download log: `data_manifest.csv`
- Primary participant values and decision inputs: `primary_participant_metrics.csv`, `primary_comparison_summary.csv`
- Exploratory target outputs: `exploratory_secondary_participant_metrics.csv`, `exploratory_secondary_summary.csv`
- Exploratory spatial blocks: `exploratory_spatial_block_metrics.csv`, `exploratory_spatial_block_summary.csv`
- Input and integrity audits: `spatial_mapping_qc.csv`, `spatial_archive_contents.csv`, `source_integrity_checks.csv`
- Exclusions and verification: `excluded_spots.csv`, `participant_exclusions.csv`, `metric_recomputation.json`

### Verified frozen artifacts and source code

{sources}
"""
    REPORT.write_text(report_text, encoding="utf-8")


def run_verifier_subprocess() -> dict[str, Any]:
    command = [sys.executable, str(Path(__file__).resolve()), "--verify-only"]
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    if process.returncode != 0:
        raise RuntimeError(
            "Fresh-process metric verification failed.\n"
            f"stdout:\n{process.stdout}\nstderr:\n{process.stderr}"
        )
    return json.loads(VERIFICATION.read_text(encoding="utf-8"))


def finalize_existing_outputs() -> None:
    required = [
        DATA_OUTPUT,
        PRIMARY_METRICS,
        PRIMARY_SUMMARY,
        SECONDARY_METRICS,
        SECONDARY_SUMMARY,
        BLOCK_METRICS,
        BLOCK_SUMMARY,
        SPOT_EXCLUSIONS,
        PARTICIPANT_EXCLUSIONS,
        MAPPING_QC,
        ARCHIVE_QC,
        SOURCE_CHECKS,
    ]
    missing = [path for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Cannot finalize; saved confirmation outputs are missing: "
            + ", ".join(str(path) for path in missing)
        )
    source_checks = read_csv(SOURCE_CHECKS)
    for row in source_checks:
        path = Path(row["path"])
        if not path.is_file():
            raise FileNotFoundError(path)
        actual_hash = sha256_file(path)
        if row.get("expected_sha256") and actual_hash != row["expected_sha256"]:
            raise AssertionError(f"Source integrity check failed during finalization: {path}")
        row["actual_sha256"] = actual_hash
        row["size_bytes"] = str(path.stat().st_size)
        row["matches_manifest"] = "True"
    write_csv(SOURCE_CHECKS, source_checks)

    primary_frame = pd.read_csv(PRIMARY_METRICS).fillna("")
    primary_frame["eligible_for_primary_metric"] = primary_frame[
        "eligible_for_primary_metric"
    ].map(lambda value: str(value).strip().casefold() == "true")
    primary_rows = primary_frame.to_dict(orient="records")
    comparisons_frame = pd.read_csv(PRIMARY_SUMMARY).fillna(np.nan)
    comparisons = comparisons_frame.to_dict(orient="records")
    mapping_frame = pd.read_csv(MAPPING_QC)
    mapping_rows = mapping_frame.to_dict(orient="records")
    samples = [
        {
            "participant_id": str(row["participant_id"]),
            "library_id": str(row["library_id"]),
            "n_spots": int(row["n_in_tissue_positions"]),
        }
        for row in mapping_rows
    ]
    participant_exclusions = read_csv(PARTICIPANT_EXCLUSIONS)
    if not participant_exclusions:
        write_csv(PARTICIPANT_EXCLUSIONS, [])
    spot_exclusions = read_csv(SPOT_EXCLUSIONS)
    if not spot_exclusions:
        write_csv(SPOT_EXCLUSIONS, [])
    manifest = read_csv(DOWNLOAD_MANIFEST)
    verification = run_verifier_subprocess()
    make_report(
        samples,
        mapping_rows,
        participant_exclusions,
        primary_rows,
        comparisons,
        source_checks,
        spot_exclusions,
        manifest,
        verification,
    )
    if not REPORT.is_file() or REPORT.stat().st_size == 0:
        raise AssertionError("Stage 1d report was not written")
    eligible_count = sum(bool(row["eligible_for_primary_metric"]) for row in primary_rows)
    if eligible_count < MIN_ELIGIBLE_PARTICIPANTS:
        decision = "INCONCLUSIVE"
    elif all(float(row["ci95_low"]) > 0 for row in comparisons):
        decision = "SUCCESS"
    else:
        decision = "FAIL"
    print(
        json.dumps(
            {
                "report": str(REPORT),
                "participants_processed": len(samples),
                "spots": sum(int(sample["n_spots"]) for sample in samples),
                "eligible_primary_participants": sum(
                    bool(row["eligible_for_primary_metric"]) for row in primary_rows
                ),
                "decision": decision,
                "max_recomputed_metric_difference": verification["max_absolute_difference"],
            },
            indent=2,
        )
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    expected_outputs = [
        DATA_OUTPUT,
        PRIMARY_METRICS,
        PRIMARY_SUMMARY,
        SECONDARY_METRICS,
        SECONDARY_SUMMARY,
        BLOCK_METRICS,
        BLOCK_SUMMARY,
        SPOT_EXCLUSIONS,
        PARTICIPANT_EXCLUSIONS,
        MAPPING_QC,
        ARCHIVE_QC,
        SOURCE_CHECKS,
        VERIFICATION,
        REPORT,
    ]
    existing = [path for path in expected_outputs if path.exists()]
    if existing:
        raise FileExistsError(
            "Refusing to overwrite existing confirmation outputs: "
            + ", ".join(str(path) for path in existing)
        )

    source_checks, download_manifest = verify_inputs()
    plan = read_csv(DOWNLOAD_PLAN)
    helper = load_module("stage1d_pairing_source", PAIRING_SCRIPT)
    stage1 = load_module("stage1d_stage1_source", STAGE1_SCRIPT)
    qc = load_module("stage1d_qc_source", QC_SCRIPT)
    training = load_module("stage1d_frozen_training_source", TRAINING_SCRIPT)
    stage1b = training.load_stage1b()
    models = load_frozen_models(stage1b)

    samples, mapping_rows, archive_rows, participant_exclusions = load_registered_samples(
        plan, helper, stage1, qc, models
    )
    arrays = concatenate_samples(samples)
    if arrays:
        save_values = {
            "participant_id": arrays["participant_id"],
            "library_id": arrays["library_id"],
            "barcode": arrays["barcode"],
            "embeddings": arrays["embeddings"],
            "colors": arrays["colors"],
            "depth": arrays["depth"],
            "library_size": arrays["library_size"],
            "residual_targets": arrays["residual_targets"],
            "neighbor_targets": arrays["neighbor_targets"],
            "neighbor_counts": arrays["neighbor_counts"],
            "array_rows": arrays["array_rows"],
            "array_cols": arrays["array_cols"],
            "predictions_mlp_spot": arrays["predictions_mlp_spot"],
            "predictions_color_only_ridge": arrays["predictions_color_only_ridge"],
            "predictions_depth_only_ridge": arrays["predictions_depth_only_ridge"],
        }
        np.savez_compressed(DATA_OUTPUT, **save_values)
    else:
        raise RuntimeError("No confirmation participants had usable paired inputs")

    primary_rows, metric_exclusions, comparisons = primary_results(arrays, samples)
    participant_exclusions.extend(metric_exclusions)
    secondary_rows, secondary_summary = secondary_results(arrays)
    block_rows, block_summary = spatial_block_results(arrays)
    spot_exclusions = write_spot_exclusions(arrays)
    write_csv(PRIMARY_METRICS, primary_rows)
    write_csv(PRIMARY_SUMMARY, comparisons)
    write_csv(SECONDARY_METRICS, secondary_rows)
    write_csv(SECONDARY_SUMMARY, secondary_summary)
    write_csv(BLOCK_METRICS, block_rows)
    write_csv(BLOCK_SUMMARY, block_summary)
    write_csv(SPOT_EXCLUSIONS, spot_exclusions)
    write_csv(PARTICIPANT_EXCLUSIONS, participant_exclusions)
    write_csv(MAPPING_QC, mapping_rows)
    write_csv(ARCHIVE_QC, archive_rows)
    write_csv(SOURCE_CHECKS, source_checks)

    verification = run_verifier_subprocess()
    make_report(
        samples,
        mapping_rows,
        participant_exclusions,
        primary_rows,
        comparisons,
        source_checks,
        spot_exclusions,
        download_manifest,
        verification,
    )
    if not REPORT.is_file() or REPORT.stat().st_size == 0:
        raise AssertionError("Stage 1d report was not written")
    eligible_count = sum(bool(row["eligible_for_primary_metric"]) for row in primary_rows)
    if eligible_count < MIN_ELIGIBLE_PARTICIPANTS:
        decision = "INCONCLUSIVE"
    elif all(float(row["ci95_low"]) > 0 for row in comparisons):
        decision = "SUCCESS"
    else:
        decision = "FAIL"
    print(
        json.dumps(
            {
                "report": str(REPORT),
                "participants_processed": len({sample["participant_id"] for sample in samples}),
                "libraries_processed": len({sample["library_id"] for sample in samples}),
                "spots": len(arrays["participant_id"]),
                "eligible_primary_participants": sum(
                    bool(row["eligible_for_primary_metric"]) for row in primary_rows
                ),
                "decision": decision,
                "max_recomputed_metric_difference": verification["max_absolute_difference"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    if "--verify-only" in sys.argv:
        result = verify_metrics_fresh_process()
        print(json.dumps(result, indent=2, allow_nan=True))
    elif "--finalize-existing" in sys.argv:
        finalize_existing_outputs()
    else:
        main()
