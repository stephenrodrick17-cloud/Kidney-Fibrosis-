from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import platform
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import scipy
from scipy.io import mmread
from scipy.sparse import csc_matrix

import PROTO_QUANTIFY as quantify
import PROTO_VALIDATE as validate

GENES = (
    "COL1A1",
    "COL1A2",
    "COL3A1",
    "FN1",
    "TGFB1",
    "CCN2",
    "ACTA2",
    "MMP2",
    "TIMP1",
)
MODULE_GENES = ("COL1A1", "COL1A2", "COL3A1")
TARGETS = ("collagen_module",) + GENES
BOOTSTRAPS = 10_000
BOOTSTRAP_SEED = 20261117
BLOCK_SIDE = 4
NOMINAL_SPOT_DIAMETER_UM = 55.0
MAX_RUNTIME_SECONDS = quantify.MAX_RUNTIME_SECONDS


def _read_text_or_gzip(path: Path) -> list[str]:
    opener = gzip.open if path.name.lower().endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8-sig", newline="") as handle:
        return handle.read().splitlines()


def _matrix_directory(path: Path) -> Path:
    if path.is_dir():
        return path
    if path.name.lower().endswith(("matrix.mtx", "matrix.mtx.gz")):
        return path.parent
    raise ValueError(
        "Counts must be a 10x Matrix Market folder/file or a PROTO count CSV."
    )


def _find_10x_file(folder: Path, stems: tuple[str, ...]) -> Path:
    for stem in stems:
        for suffix in ("", ".gz"):
            candidate = folder / f"{stem}{suffix}"
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(f"Could not find any of {stems} under {folder}.")


def _load_10x_matrix(matrix_path: Path) -> dict[str, Any]:
    folder = _matrix_directory(matrix_path)
    mtx = _find_10x_file(folder, ("matrix.mtx",))
    barcodes_path = _find_10x_file(folder, ("barcodes.tsv",))
    features_path = _find_10x_file(folder, ("features.tsv", "genes.tsv"))
    matrix_opener = gzip.open if mtx.name.lower().endswith(".gz") else open
    with matrix_opener(mtx, "rb") as handle:
        matrix = mmread(handle).tocsr()
    barcodes = _read_text_or_gzip(barcodes_path)
    feature_rows = [line.split("\t") for line in _read_text_or_gzip(features_path)]
    if matrix.shape != (len(feature_rows), len(barcodes)):
        raise ValueError(
            "The count matrix dimensions do not match its feature and barcode files."
        )
    if len(barcodes) != len(set(barcodes)):
        raise ValueError("Counts contain duplicate barcodes.")

    selected_features: dict[str, list[int]] = defaultdict(list)
    gene_expression_rows: list[int] = []
    for index, feature in enumerate(feature_rows):
        if not feature:
            continue
        if len(feature) >= 3 and feature[2].strip().lower() not in (
            "gene expression",
            "",
        ):
            continue
        gene_expression_rows.append(index)
        name = feature[1].strip().upper() if len(feature) > 1 else feature[0].strip().upper()
        if name in GENES:
            selected_features[name].append(index)
    if not gene_expression_rows:
        raise ValueError("The count matrix has no gene-expression features.")
    gene_expression = matrix[gene_expression_rows, :]
    library_sizes = np.asarray(gene_expression.sum(axis=0)).ravel().astype(np.float64)
    raw_counts: dict[str, np.ndarray] = {}
    for gene in GENES:
        rows = selected_features.get(gene, [])
        raw_counts[gene] = (
            np.asarray(matrix[rows, :].sum(axis=0)).ravel().astype(np.float64)
            if rows
            else np.zeros(len(barcodes), dtype=np.float64)
        )
    return {
        "barcodes": [barcode.strip() for barcode in barcodes],
        "library_sizes": library_sizes,
        "raw_counts": raw_counts,
        "missing_genes": [gene for gene in GENES if not selected_features.get(gene)],
        "files": [mtx, barcodes_path, features_path],
    }


def _load_count_csv(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or "barcode" not in rows[0]:
        raise ValueError("Count CSV must have a barcode column and data rows.")
    required = {"library_size_umi"} | {f"raw_{gene}" for gene in GENES}
    missing_columns = required - set(rows[0])
    if missing_columns:
        raise ValueError(
            f"Count CSV is missing required columns: {sorted(missing_columns)}."
        )
    barcodes = [row["barcode"].strip() for row in rows]
    if len(barcodes) != len(set(barcodes)):
        raise ValueError("Counts contain duplicate barcodes.")
    library_sizes = np.asarray(
        [float(row["library_size_umi"]) for row in rows], dtype=np.float64
    )
    raw_counts = {
        gene: np.asarray([float(row[f"raw_{gene}"]) for row in rows], dtype=np.float64)
        for gene in GENES
    }
    if (
        np.any(~np.isfinite(library_sizes))
        or np.any(library_sizes <= 0)
        or any(np.any(~np.isfinite(values)) or np.any(values < 0) for values in raw_counts.values())
    ):
        raise ValueError("Count CSV has invalid counts or library sizes.")
    return {
        "barcodes": barcodes,
        "library_sizes": library_sizes,
        "raw_counts": raw_counts,
        "missing_genes": [],
        "files": [path],
    }


def load_counts(path: str | Path) -> dict[str, Any]:
    count_path = Path(path)
    if not count_path.exists():
        raise FileNotFoundError(f"Count input is missing: {count_path}")
    if count_path.is_file() and count_path.suffix.lower() == ".csv":
        return _load_count_csv(count_path)
    if count_path.is_file() and count_path.suffix.lower() in {".h5", ".hdf5"}:
        try:
            import h5py
        except ImportError as error:
            raise ImportError(
                "Reading 10x HDF5 counts requires the already-installed h5py package."
            ) from error
        with h5py.File(count_path, "r") as handle:
            group = handle["matrix"]
            shape = tuple(int(value) for value in group["shape"][:])
            matrix = csc_matrix(
                (
                    group["data"][:],
                    group["indices"][:],
                    group["indptr"][:],
                ),
                shape=shape,
            ).tocsr()
            barcodes = [
                value.decode("utf-8") if isinstance(value, bytes) else str(value)
                for value in group["barcodes"][:]
            ]
            features = group["features"]
            names = [
                value.decode("utf-8") if isinstance(value, bytes) else str(value)
                for value in features["name"][:]
            ]
            feature_types = [
                value.decode("utf-8") if isinstance(value, bytes) else str(value)
                for value in features["feature_type"][:]
            ]
        if matrix.shape != (len(names), len(barcodes)):
            raise ValueError("10x HDF5 dimensions do not match its feature/barcode lists.")
        selected_features: dict[str, list[int]] = defaultdict(list)
        gene_expression_rows: list[int] = []
        for index, (name, feature_type) in enumerate(zip(names, feature_types)):
            if feature_type.lower() != "gene expression":
                continue
            gene_expression_rows.append(index)
            if name.upper() in GENES:
                selected_features[name.upper()].append(index)
        if not gene_expression_rows:
            raise ValueError("The count matrix has no gene-expression features.")
        gene_expression = matrix[gene_expression_rows, :]
        library_sizes = np.asarray(gene_expression.sum(axis=0)).ravel().astype(np.float64)
        raw_counts = {
            gene: (
                np.asarray(matrix[indexes, :].sum(axis=0)).ravel().astype(np.float64)
                if indexes
                else np.zeros(len(barcodes), dtype=np.float64)
            )
            for gene in GENES
            for indexes in (selected_features.get(gene, []),)
        }
        return {
            "barcodes": barcodes,
            "library_sizes": library_sizes,
            "raw_counts": raw_counts,
            "missing_genes": [
                gene for gene in GENES if not selected_features.get(gene)
            ],
            "files": [count_path],
        }
    return _load_10x_matrix(count_path)


def read_positions(path: str | Path) -> dict[str, dict[str, Any]]:
    position_path = Path(path)
    if not position_path.is_file():
        raise FileNotFoundError(f"Spot positions file is missing: {position_path}")
    with position_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        raise ValueError("Spot positions file is empty.")
    normalized = [value.strip().lower() for value in rows[0]]
    if "barcode" in normalized:
        header = normalized
        content = rows[1:]
        indexes = {
            key: header.index(key)
            for key in (
                "barcode",
                "in_tissue",
                "array_row",
                "array_col",
                "pxl_row_in_fullres",
                "pxl_col_in_fullres",
            )
        }
    else:
        content = rows
        indexes = {
            "barcode": 0,
            "in_tissue": 1,
            "array_row": 2,
            "array_col": 3,
            "pxl_row_in_fullres": 4,
            "pxl_col_in_fullres": 5,
        }
    result: dict[str, dict[str, Any]] = {}
    for row in content:
        if not row or len(row) <= max(indexes.values()):
            continue
        barcode = row[indexes["barcode"]].strip()
        if not barcode:
            continue
        if barcode in result:
            raise ValueError(f"Spot positions contain duplicate barcode {barcode}.")
        try:
            pixel_row = float(row[indexes["pxl_row_in_fullres"]])
            pixel_col = float(row[indexes["pxl_col_in_fullres"]])
            array_row = int(float(row[indexes["array_row"]]))
            array_col = int(float(row[indexes["array_col"]]))
            in_tissue = int(float(row[indexes["in_tissue"]]))
            if not math.isfinite(pixel_row) or not math.isfinite(pixel_col):
                raise ValueError("non-finite pixel coordinate")
            result[barcode] = {
                "barcode": barcode,
                "in_tissue": in_tissue,
                "array_row": array_row,
                "array_col": array_col,
                "pixel_row_fullres": pixel_row,
                "pixel_col_fullres": pixel_col,
            }
        except (ValueError, IndexError) as error:
            raise ValueError(f"Invalid coordinate for barcode {barcode}.") from error
    if not result:
        raise ValueError("No spot positions could be read.")
    return result


def _validate_scale_factors(path: str | Path) -> tuple[dict[str, float], str]:
    scale_path = Path(path)
    if not scale_path.is_file():
        raise FileNotFoundError(f"Scale-factor JSON is missing: {scale_path}")
    raw = scale_path.read_bytes()
    values = json.loads(raw.decode("utf-8"))
    required = ("tissue_hires_scalef", "spot_diameter_fullres")
    if any(key not in values for key in required):
        raise ValueError("Scale-factor JSON is missing Visium high-resolution fields.")
    result = {key: float(values[key]) for key in required}
    if any(not math.isfinite(value) or value <= 0 for value in result.values()):
        raise ValueError("Visium scale factors must be positive finite values.")
    return result, hashlib.sha256(raw).hexdigest()


def validate_barcode_match(
    count_barcodes: list[str], positions: dict[str, dict[str, Any]]
) -> None:
    missing_positions = sorted(set(count_barcodes) - set(positions))
    if missing_positions:
        raise ValueError(
            f"{len(missing_positions)} count barcodes have no spatial position; refusing mismatched inputs."
        )
    non_tissue_counts = [
        barcode for barcode in count_barcodes if positions[barcode]["in_tissue"] != 1
    ]
    if non_tissue_counts:
        raise ValueError(
            f"{len(non_tissue_counts)} count barcodes are marked outside tissue; refusing mismatched inputs."
        )


def _prepare_expression(counts: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    barcodes = counts["barcodes"]
    library_sizes = np.asarray(counts["library_sizes"], dtype=np.float64)
    if np.any(~np.isfinite(library_sizes)) or np.any(library_sizes <= 0):
        raise ValueError("Count matrix has a zero or invalid library size.")
    normalized: dict[str, np.ndarray] = {}
    unavailable = set(counts["missing_genes"])
    for gene in GENES:
        raw = np.asarray(counts["raw_counts"][gene], dtype=np.float64)
        if len(raw) != len(barcodes):
            raise ValueError(f"Count vector length differs for {gene}.")
        log_values = np.log1p(10_000.0 * raw / library_sizes)
        deviation = float(log_values.std(ddof=0))
        if not math.isfinite(deviation) or deviation == 0:
            unavailable.add(gene)
        else:
            normalized[gene] = (log_values - float(log_values.mean())) / deviation

    rows: list[dict[str, Any]] = []
    for index, barcode in enumerate(barcodes):
        row: dict[str, Any] = {
            "barcode": barcode,
            "library_size_umi": float(library_sizes[index]),
            "log_library_size": float(math.log1p(library_sizes[index])),
        }
        for gene in GENES:
            row[gene] = (
                float(normalized[gene][index]) if gene in normalized else math.nan
            )
        if all(gene not in unavailable for gene in MODULE_GENES):
            row["collagen_module"] = float(
                np.mean([row[gene] for gene in MODULE_GENES])
            )
        else:
            row["collagen_module"] = math.nan
        rows.append(row)
    return rows, sorted(unavailable)


def _make_spot_rows(
    result: quantify.QuantificationResult,
    counts: dict[str, Any],
    positions: dict[str, dict[str, Any]],
    scale: dict[str, float],
    tissue_depth: dict[str, float] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    expression_rows, unavailable = _prepare_expression(counts)
    validate_barcode_match(counts["barcodes"], positions)

    image = result.assessment.scaled_rgb
    height, width = image.shape[:2]
    tissue = image.mean(axis=2) < 245.0
    unet_mask = result.unet_mask_scaled
    colour_mask = result.colour_mask_scaled
    spot_diameter_px = NOMINAL_SPOT_DIAMETER_UM / validate.TARGET_MPP
    radius = spot_diameter_px / 2.0
    resize_factor = result.assessment.scale_factor
    hires_scale = scale["tissue_hires_scalef"]
    expression_by_barcode = {row["barcode"]: row for row in expression_rows}
    output: list[dict[str, Any]] = []
    for barcode in counts["barcodes"]:
        position = positions[barcode]
        center_x = position["pixel_col_fullres"] * hires_scale * resize_factor
        center_y = position["pixel_row_fullres"] * hires_scale * resize_factor
        x0 = int(math.floor(center_x - radius))
        x1 = int(math.ceil(center_x + radius)) + 1
        y0 = int(math.floor(center_y - radius))
        y1 = int(math.ceil(center_y + radius)) + 1
        if x0 < 0 or y0 < 0 or x1 > width or y1 > height:
            continue
        yy, xx = np.ogrid[y0:y1, x0:x1]
        footprint = (xx - center_x) ** 2 + (yy - center_y) ** 2 <= radius**2
        if not footprint.any():
            continue
        tissue_patch = tissue[y0:y1, x0:x1]
        spot_tissue = tissue_patch[footprint]
        tissue_fraction = float(spot_tissue.mean())
        if tissue_fraction <= 0:
            continue
        pixel_rows = image[y0:y1, x0:x1][footprint]
        local_tissue_pixels = pixel_rows[spot_tissue]
        if not len(local_tissue_pixels):
            continue
        spot_row = {
            **expression_by_barcode[barcode],
            "array_row": position["array_row"],
            "array_col": position["array_col"],
            "center_x_4p1px": center_x,
            "center_y_4p1px": center_y,
            "spot_diameter_px": spot_diameter_px,
            "tissue_fraction": tissue_fraction,
            "unet_fibrosis_fraction": float(unet_mask[y0:y1, x0:x1][footprint].mean()),
            "colour_fibrosis_fraction": float(colour_mask[y0:y1, x0:x1][footprint].mean()),
            "mean_blue_minus_red": float(
                local_tissue_pixels[:, 2].astype(np.float64).mean()
                - local_tissue_pixels[:, 0].astype(np.float64).mean()
            ),
            "mean_brightness": float(local_tissue_pixels.mean(axis=1).mean()),
        }
        if tissue_depth is not None:
            spot_row["tissue_depth_um"] = tissue_depth.get(barcode, math.nan)
        output.append(spot_row)
    if not output:
        raise ValueError("No count barcodes had a valid mapped tissue footprint.")
    if len(output) != len(counts["barcodes"]):
        raise ValueError(
            "Some count barcodes did not have a valid tissue footprint; refusing partial matching."
        )
    return output, unavailable


def make_groups(rows: list[dict[str, Any]], score_column: str) -> list[dict[str, Any]]:
    ranked = sorted(rows, key=lambda row: (float(row[score_column]), str(row["barcode"])))
    tertile_n = len(ranked) // 3
    if tertile_n < 20:
        raise ValueError(
            f"At least 20 spots are required in each group; this input has {tertile_n}."
        )
    grouped = []
    for index, row in enumerate(ranked):
        group = "low" if index < tertile_n else "high" if index >= len(ranked) - tertile_n else "middle"
        grouped.append({**row, "group": group})
    return grouped


def _design(rows: list[dict[str, Any]], include_count: bool) -> np.ndarray:
    columns = [np.ones(len(rows), dtype=np.float64)]
    if any("tissue_depth_um" in row for row in rows):
        depth = np.asarray([float(row["tissue_depth_um"]) for row in rows])
        if np.any(~np.isfinite(depth)):
            raise ValueError("Supplied tissue-depth values must be finite for every spot.")
        columns.append(depth)
    if include_count:
        columns.append(
            np.asarray([float(row["log_library_size"]) for row in rows], dtype=np.float64)
        )
    columns.append(
        np.asarray([float(row["tissue_fraction"]) for row in rows], dtype=np.float64)
    )
    base = np.column_stack(columns)
    keep = [0] + [
        index for index in range(1, base.shape[1]) if float(np.ptp(base[:, index])) > 0.0
    ]
    return base[:, keep]


def fit_adjusted(
    rows: list[dict[str, Any]],
    target: str,
    *,
    include_count: bool = True,
) -> dict[str, Any]:
    selected = [row for row in rows if row.get("group") in ("low", "high")]
    if not selected:
        return {"valid": False, "reason": "no high/low spots"}
    y = np.asarray([float(row[target]) for row in selected], dtype=np.float64)
    if np.any(~np.isfinite(y)):
        return {"valid": False, "reason": f"{target} is NOT AVAILABLE"}
    high = np.asarray([row["group"] == "high" for row in selected], dtype=np.float64)
    if len(np.unique(high)) != 2:
        return {"valid": False, "reason": "both groups are required"}
    base = _design(selected, include_count)
    if len(y) <= base.shape[1]:
        return {"valid": False, "reason": "too few spots for the adjusted model"}
    design = np.column_stack((base, high))
    coefficient, _, rank, _ = np.linalg.lstsq(design, y, rcond=None)
    if rank != design.shape[1]:
        return {"valid": False, "reason": "adjusted model is rank deficient"}
    fitted = design @ coefficient
    total = float(np.sum((y - y.mean()) ** 2))
    return {
        "valid": True,
        "effect": float(coefficient[-1]),
        "r_squared": 0.0 if total == 0.0 else 1.0 - float(np.sum((y - fitted) ** 2)) / total,
        "n_spots": len(y),
        "n_low": int((high == 0).sum()),
        "n_high": int((high == 1).sum()),
        "reason": "",
    }


def _bootstrap_ci(
    rows: list[dict[str, Any]],
    target: str,
    seed: int,
    deadline: float,
    *,
    include_count: bool = True,
) -> tuple[float, float]:
    selected = [row for row in rows if row.get("group") in ("low", "high")]
    if any(not math.isfinite(float(row[target])) for row in selected):
        raise ValueError(f"Cannot bootstrap unavailable target {target}.")
    blocks: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in selected:
        block = (
            int(row["array_row"]) // BLOCK_SIDE,
            int(row["array_col"]) // BLOCK_SIDE,
        )
        blocks[block].append(row)
    block_ids = sorted(blocks)
    if len(block_ids) < 2:
        raise ValueError("At least two spatial blocks are required for an interval.")
    rng = np.random.default_rng(seed)
    estimates: list[float] = []
    attempts = 0
    max_attempts = BOOTSTRAPS * 10
    while len(estimates) < BOOTSTRAPS and attempts < max_attempts:
        if attempts % 100 == 0 and time.monotonic() >= deadline:
            raise TimeoutError("Stopped before the two-hour run limit.")
        attempts += 1
        sampled = rng.choice(len(block_ids), size=len(block_ids), replace=True)
        sample_rows = [
            row
            for sampled_block in sampled
            for row in blocks[block_ids[int(sampled_block)]]
        ]
        fit = fit_adjusted(sample_rows, target, include_count=include_count)
        if fit["valid"]:
            estimates.append(float(fit["effect"]))
    if len(estimates) != BOOTSTRAPS:
        raise RuntimeError(
            f"Could not obtain 10,000 valid block-bootstrap estimates for {target}."
        )
    low, high = np.quantile(np.asarray(estimates), [0.025, 0.975])
    return float(low), float(high)


def _group_colour_check(rows: list[dict[str, Any]]) -> dict[str, float]:
    low = [row for row in rows if row["group"] == "low"]
    high = [row for row in rows if row["group"] == "high"]
    if not low or not high:
        raise ValueError("Both groups are required for the image-colour check.")
    return {
        "low_mean_blue_minus_red": float(np.mean([row["mean_blue_minus_red"] for row in low])),
        "high_mean_blue_minus_red": float(np.mean([row["mean_blue_minus_red"] for row in high])),
        "low_mean_brightness": float(np.mean([row["mean_brightness"] for row in low])),
        "high_mean_brightness": float(np.mean([row["mean_brightness"] for row in high])),
    }


def _with_warnings(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    warning_text = " | ".join(validate.load_warnings())
    return [{**row, "warnings": warning_text} for row in rows]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write an empty result table: {path.name}")
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def analyze(
    image_path: str | Path,
    input_mpp: float,
    positions_path: str | Path,
    scale_factors_path: str | Path,
    counts_path: str | Path,
    output_folder: str | Path,
    tissue_depth_path: str | Path | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    validate.verify_checkpoint_hash()
    output_dir = quantify.resolve_output_dir(output_folder)
    quant_report, image_result = quantify.run_quantification(
        image_path, input_mpp, output_dir
    )
    counts = load_counts(counts_path)
    positions = read_positions(positions_path)
    scale, scale_hash = _validate_scale_factors(scale_factors_path)
    depth: dict[str, float] | None = None
    if tissue_depth_path is not None:
        depth_path = Path(tissue_depth_path)
        with depth_path.open("r", encoding="utf-8-sig", newline="") as handle:
            depth_rows = list(csv.DictReader(handle))
        if not depth_rows or not {"barcode", "tissue_depth_um"}.issubset(depth_rows[0]):
            raise ValueError("Tissue-depth CSV needs barcode and tissue_depth_um columns.")
        depth = {row["barcode"]: float(row["tissue_depth_um"]) for row in depth_rows}
        if len(depth) != len(depth_rows):
            raise ValueError("Tissue-depth CSV contains duplicate barcodes.")

    spot_rows, unavailable_genes = _make_spot_rows(
        image_result, counts, positions, scale, depth
    )
    report_rows: list[dict[str, Any]] = []
    group_details: dict[str, dict[str, Any]] = {}
    for mask_index, (mask_name, score_column) in enumerate(
        (
            ("unet", "unet_fibrosis_fraction"),
            ("colour", "colour_fibrosis_fraction"),
        )
    ):
        grouped = make_groups(spot_rows, score_column)
        low_n = sum(row["group"] == "low" for row in grouped)
        high_n = sum(row["group"] == "high" for row in grouped)
        colour_check = _group_colour_check(grouped)
        group_details[mask_name] = {
            "low_spots": low_n,
            "high_spots": high_n,
            "colour_intensity_check": colour_check,
            "more_blue_in_high_group": (
                colour_check["high_mean_blue_minus_red"]
                > colour_check["low_mean_blue_minus_red"]
            ),
            "darker_in_high_group": (
                colour_check["high_mean_brightness"]
                < colour_check["low_mean_brightness"]
            ),
        }
        for target_index, target in enumerate(TARGETS):
            fit = fit_adjusted(grouped, target)
            if fit["valid"]:
                low_ci, high_ci = _bootstrap_ci(
                    grouped,
                    target,
                    BOOTSTRAP_SEED + 100 * mask_index + target_index,
                    started + MAX_RUNTIME_SECONDS,
                )
                interval_status = (
                    "higher"
                    if low_ci > 0
                    else "no clear difference"
                )
                effect = float(fit["effect"])
            else:
                low_ci = high_ci = "NOT AVAILABLE"
                interval_status = "NOT AVAILABLE"
                effect = "NOT AVAILABLE"
            without_count = (
                fit_adjusted(grouped, target, include_count=False)
                if fit["valid"]
                else {"valid": False, "reason": fit.get("reason", "")}
            )
            report_rows.append(
                {
                    "mask": mask_name,
                    "target": target,
                    "high_minus_low_adjusted_difference": effect,
                    "approx_spatial_block_ci95_low": low_ci,
                    "approx_spatial_block_ci95_high": high_ci,
                    "interval_label": interval_status,
                    "low_spots": low_n,
                    "high_spots": high_n,
                    "adjustment": (
                        "log library size and tissue fraction"
                        + (" and tissue depth" if depth is not None else "")
                    ),
                    "high_minus_low_without_library_size_adjustment": (
                        float(without_count["effect"])
                        if without_count["valid"]
                        else "NOT AVAILABLE"
                    ),
                    "model_r_squared": (
                        fit.get("r_squared", "NOT AVAILABLE")
                        if fit["valid"]
                        else "NOT AVAILABLE"
                    ),
                }
            )
        if time.monotonic() - started >= MAX_RUNTIME_SECONDS:
            raise TimeoutError("Stopped before the two-hour run limit.")

    unet_directions = {
        row["target"]: (
            float(row["high_minus_low_adjusted_difference"])
            if isinstance(row["high_minus_low_adjusted_difference"], (int, float))
            and math.isfinite(float(row["high_minus_low_adjusted_difference"]))
            else math.nan
        )
        for row in report_rows
        if row["mask"] == "unet"
    }
    colour_directions = {
        row["target"]: (
            float(row["high_minus_low_adjusted_difference"])
            if isinstance(row["high_minus_low_adjusted_difference"], (int, float))
            and math.isfinite(float(row["high_minus_low_adjusted_difference"]))
            else math.nan
        )
        for row in report_rows
        if row["mask"] == "colour"
    }
    for row in report_rows:
        row["mask_directions_agree"] = (
            unet_directions[row["target"]] * colour_directions[row["target"]] > 0
            if math.isfinite(unet_directions[row["target"]])
            and math.isfinite(colour_directions[row["target"]])
            else "NOT AVAILABLE"
        )
        row.update(group_details[row["mask"]]["colour_intensity_check"])
    high_genes = [
        row["target"]
        for row in report_rows
        if row["mask"] == "unet"
        and row["target"] in GENES
        and row["interval_label"] == "higher"
    ]
    no_clear_difference = [
        gene for gene in GENES if gene not in high_genes
    ]
    warnings = validate.load_warnings()
    mpp_from_scale_factors = NOMINAL_SPOT_DIAMETER_UM / (
        scale["spot_diameter_fullres"] * scale["tissue_hires_scalef"]
    )
    report: dict[str, Any] = {
        "status": "EXPLORATORY, NOT CONFIRMATORY",
        "mask_status": "UNVALIDATED MASKS",
        "asset_status": "RESEARCH-ONLY",
        "validation_status": quant_report["validation_status"],
        "input_sha256": quant_report["input_sha256"],
        "checkpoint_sha256": quant_report["checkpoint_sha256"],
        "quantification_report": quant_report["report_file"],
        "positions_sha256": validate.sha256_file(Path(positions_path)),
        "scale_factors_sha256": scale_hash,
        "count_input_files": [
            {"path": str(path), "sha256": validate.sha256_file(path)}
            for path in counts["files"]
        ],
        "tissue_depth_sha256": (
            validate.sha256_file(Path(tissue_depth_path))
            if tissue_depth_path is not None
            else "NOT AVAILABLE"
        ),
        "software_versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "spot_diameter_um": NOMINAL_SPOT_DIAMETER_UM,
        "spot_diameter_px_at_target_scale": NOMINAL_SPOT_DIAMETER_UM / validate.TARGET_MPP,
        "input_mpp_from_visium_scale_factors": mpp_from_scale_factors,
        "user_supplied_input_mpp": float(input_mpp),
        "mpp_difference_percent": (
            100.0 * (float(input_mpp) - mpp_from_scale_factors) / mpp_from_scale_factors
        ),
        "spatial_bootstrap": {
            "method": "resample 4-by-4 array-coordinate blocks with replacement",
            "block_side": BLOCK_SIDE,
            "resamples": BOOTSTRAPS,
            "seed": BOOTSTRAP_SEED,
            "interval_note": "Intervals are approximate.",
        },
        "missing_or_constant_genes": unavailable_genes,
        "group_sizes": group_details,
        "higher_expression_in_regions_marked_as_fibrotic_in_this_sample": high_genes,
        "genes_with_no_clear_difference": no_clear_difference,
        "wording": [
            "Genes with higher expression in regions marked as fibrotic in this sample",
            "Genes with no clear difference",
            "This sample alone cannot show that these genes cause fibrosis.",
        ],
        "results": report_rows,
        "warnings": warnings,
        "runtime_seconds": time.monotonic() - started,
    }
    report_path = output_dir / "PROTO_ASSOCIATION_REPORT.json"
    table_path = output_dir / "PROTO_ASSOCIATION_RESULTS.csv"
    for path in (report_path, table_path):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite existing output: {path}")
    if quantify._directory_size(validate.PROTO_ROOT) + 10_000_000 > quantify.MAX_OUTPUT_BYTES:
        raise RuntimeError("Stopped before outputs could exceed the 10 GB limit.")
    _write_csv(table_path, _with_warnings(report_rows))
    with report_path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return report


def main(argv: list[str] | None = None) -> int:
    print("\n".join(validate.load_warnings()))
    parser = argparse.ArgumentParser(
        description="Make an optional within-sample gene-association report locally."
    )
    parser.add_argument("--image", required=True, help="Matching RGB PNG, JPEG, or TIFF image.")
    parser.add_argument("--mpp", required=True, type=float, help="Measured input micrometres per pixel.")
    parser.add_argument("--positions", required=True, help="Visium tissue_positions CSV.")
    parser.add_argument("--scalefactors", required=True, help="Visium scalefactors JSON.")
    parser.add_argument("--counts", required=True, help="10x count folder, Matrix Market file, or PROTO count CSV.")
    parser.add_argument("--tissue-depth", help="Optional CSV with barcode,tissue_depth_um.")
    parser.add_argument(
        "--output",
        required=True,
        help="Output subfolder inside D:\\patent\\prototype.",
    )
    parser.add_argument("--accept-research-use", action="store_true")
    args = parser.parse_args(argv)
    if not args.accept_research_use:
        print("Stop: add --accept-research-use only after reading all warnings.")
        return 2
    try:
        report = analyze(
            args.image,
            args.mpp,
            args.positions,
            args.scalefactors,
            args.counts,
            args.output,
            args.tissue_depth,
        )
    except (OSError, ValueError, RuntimeError, TimeoutError) as error:
        print(json.dumps({"status": "REFUSED", "message": str(error), "warnings": validate.load_warnings()}, indent=2))
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
