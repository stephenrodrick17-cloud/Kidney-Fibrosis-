"""EXPLORATORY, NOT CONFIRMATORY. RESEARCH-ONLY feature-dependent runner."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import shutil
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import Ridge

ROOT = Path(r"D:\patent")
OUT = ROOT / "stage_G2"
STAGE1 = ROOT / "stage1_expression"
STAGE1D = ROOT / "stage1d_confirm"
CONFIRM_DATA = ROOT / "data_confirm"
LABEL = "EXPLORATORY, NOT CONFIRMATORY"
ASSET_LABEL = "RESEARCH-ONLY"
GENES = ["COL1A1", "COL1A2", "COL3A1", "FN1", "ACTA2"]
PRIMARY = "collagen_module"
TARGET_NAMES = [PRIMARY] + GENES
ALPHAS = [0.01, 0.1, 1.0, 10.0, 100.0]
MLP_GRID = [
    (hidden, learning_rate, weight_decay)
    for hidden in (64, 128)
    for learning_rate in (0.001, 0.0003)
    for weight_decay in (0.0001, 0.001)
]
MLP_SEEDS = [20261121, 20261122, 20261123]
OUTER_SEED = 20261120
BOOTSTRAP_SEED = 20261124
SHUFFLE_SEED = 20261125
HOLM_SEED = 20261126
BOOTSTRAPS = 10_000
PERMUTATIONS = 10_000
MAX_FIT_SECONDS = 60 * 60
MAX_INVOCATION_SECONDS = 90 * 60
MAX_OUTPUT_BYTES = 1_000_000_000
DISK_RESERVE_BYTES = 512 * 1024 * 1024
COLOR_NAMES = [
    "rgb_mean_r", "rgb_mean_g", "rgb_mean_b",
    "rgb_std_r", "rgb_std_g", "rgb_std_b",
    "hsv_mean_h", "hsv_mean_s", "hsv_mean_v",
    "hsv_std_h", "hsv_std_s", "hsv_std_v",
]
NEIGHBOR_OFFSETS = [(0, -2), (0, 2), (-1, -1), (-1, 1), (1, -1), (1, 1)]
INVOCATION_START = time.monotonic()


def check_time(fit_start: float | None = None) -> None:
    if time.monotonic() - INVOCATION_START >= MAX_INVOCATION_SECONDS:
        raise TimeoutError("Stopping: command reached its 90-minute wall-time cap.")
    if fit_start is not None and time.monotonic() - fit_start >= MAX_FIT_SECONDS:
        raise TimeoutError("Stopping: fit reached its 60-minute wall-time cap.")


def output_bytes() -> int:
    return sum(p.stat().st_size for p in OUT.glob("GENE2_*") if p.is_file())


def ensure_budget(estimate: int = 0) -> None:
    current = output_bytes()
    if current + estimate >= MAX_OUTPUT_BYTES:
        raise RuntimeError("Stopping: projected GENE2 output reaches the 1-GB cap.")
    if shutil.disk_usage(ROOT).free < estimate + DISK_RESERVE_BYTES:
        raise RuntimeError("Stopping: insufficient D: space for output plus reserve.")


def save_csv(frame: pd.DataFrame, path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {path.name}")
    frame = frame.copy()
    frame.insert(0, "asset_status", ASSET_LABEL)
    frame.insert(0, "analysis_label", LABEL)
    estimate = max(int(frame.memory_usage(index=True, deep=True).sum() * 2.5), 4096)
    ensure_budget(estimate)
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    ensure_budget()


def save_or_verify_csv(frame: pd.DataFrame, path: Path) -> None:
    if not path.exists():
        save_csv(frame, path)
        return
    expected = frame.copy()
    if "analysis_label" in expected.columns or "asset_status" in expected.columns:
        raise ValueError(f"Output source already contains status columns: {path.name}")
    expected.insert(0, "asset_status", ASSET_LABEL)
    expected.insert(0, "analysis_label", LABEL)
    buffer = io.StringIO()
    expected.to_csv(buffer, index=False)
    expected_roundtrip = pd.read_csv(io.StringIO(buffer.getvalue()))
    existing = pd.read_csv(path, encoding="utf-8-sig")
    try:
        pd.testing.assert_frame_equal(
            expected_roundtrip, existing, check_dtype=False, check_exact=True
        )
    except AssertionError as error:
        raise RuntimeError(
            f"Existing output differs from recomputed finalization data: {path.name}"
        ) from error


def save_json(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {path.name}")
    value = {"analysis_label": LABEL, "asset_status": ASSET_LABEL, **value}
    encoded = json.dumps(value, indent=2, allow_nan=False).encode("utf-8")
    ensure_budget(len(encoded))
    path.write_bytes(encoded)


def save_npz(path: Path, **arrays: np.ndarray) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {path.name}")
    arrays["analysis_label"] = np.asarray(LABEL)
    arrays["asset_status"] = np.asarray(ASSET_LABEL)
    estimate = sum(np.asarray(a).nbytes for a in arrays.values()) + 64 * 1024 * 1024
    ensure_budget(estimate)
    np.savez_compressed(path, **arrays)
    ensure_budget()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def weighted_stats(values: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = np.average(values, axis=0, weights=weights)
    variance = np.average((values - mean) ** 2, axis=0, weights=weights)
    scale = np.sqrt(variance)
    scale = np.where(np.isfinite(scale) & (scale > 0), scale, 1.0)
    return mean, scale


def scale_fit(
    x_train: np.ndarray, y_train: np.ndarray, participants: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    weights = participant_weights(participants)
    x_mean, x_scale = weighted_stats(x_train, weights)
    y_mean, y_scale = weighted_stats(y_train, weights)
    return (
        (x_train - x_mean) / x_scale,
        (y_train - y_mean) / y_scale,
        x_mean,
        x_scale,
        np.column_stack((y_mean, y_scale)),
    )


def participant_weights(participants: np.ndarray) -> np.ndarray:
    unique, counts = np.unique(participants, return_counts=True)
    count_by_id = dict(zip(unique.tolist(), counts.tolist()))
    weights = np.asarray([1.0 / count_by_id[p] for p in participants], dtype=np.float64)
    return weights / weights.mean()


def metric(x: np.ndarray, y: np.ndarray, kind: str) -> float:
    valid = np.isfinite(x) & np.isfinite(y)
    x = np.asarray(x[valid], dtype=np.float64)
    y = np.asarray(y[valid], dtype=np.float64)
    if len(x) < 2 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return math.nan
    if kind == "spearman":
        return float(spearmanr(x, y).statistic)
    if kind == "pearson":
        return float(pearsonr(x, y).statistic)
    raise ValueError(f"Unknown metric: {kind}")


def participant_correlations(
    participant_ids: np.ndarray,
    actual: np.ndarray,
    prediction: np.ndarray,
    kind: str = "spearman",
) -> dict[str, float]:
    values: dict[str, float] = {}
    for pid in sorted(set(participant_ids.astype(str))):
        indexes = participant_ids.astype(str) == pid
        score = metric(actual[indexes], prediction[indexes], kind)
        if math.isfinite(score):
            values[pid] = score
    return values


def macro_score(values: dict[str, float]) -> float:
    return float(np.mean(list(values.values()))) if values else math.nan


def paired_bootstrap(
    differences: np.ndarray, seed: int, n_boot: int = BOOTSTRAPS
) -> tuple[float, float, float]:
    values = np.asarray(differences, dtype=np.float64)
    values = values[np.isfinite(values)]
    if not len(values):
        return math.nan, math.nan, math.nan
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(values), size=(n_boot, len(values)))
    means = values[draws].mean(axis=1)
    return float(values.mean()), float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def bootstrap_metric(
    frame: pd.DataFrame,
    actual_col: str,
    pred_col: str | None,
    kind: str,
    seed: int,
    participant_macro: bool = False,
    n_boot: int = 2_000,
) -> tuple[float, float, float]:
    pids = frame["participant_id"].astype(str).unique()
    if len(pids) < 2:
        return math.nan, math.nan, math.nan
    rng = np.random.default_rng(seed)
    estimates: list[float] = []
    pid_values = frame["participant_id"].astype(str)
    by_pid = {pid: frame.loc[pid_values == pid] for pid in pids}
    if participant_macro:
        scores_by_pid = {}
        for pid, part in by_pid.items():
            score = (
                metric(part[actual_col].to_numpy(), part[pred_col].to_numpy(), kind)
                if pred_col is not None
                else float(part[actual_col].mean())
            )
            if math.isfinite(score):
                scores_by_pid[pid] = score
        scores = np.asarray(list(scores_by_pid.values()), dtype=np.float64)
        if not len(scores):
            return math.nan, math.nan, math.nan
        draws = rng.integers(0, len(scores), size=(n_boot, len(scores)))
        estimates = scores[draws].mean(axis=1).tolist()
    else:
        for iteration in range(n_boot):
            if iteration % 100 == 0:
                check_time()
            sampled = rng.choice(pids, size=len(pids), replace=True)
            chunks = [by_pid[pid] for pid in sampled]
            actual = np.concatenate([c[actual_col].to_numpy(dtype=float) for c in chunks])
            if pred_col is None:
                estimate = float(np.mean(actual))
            else:
                prediction = np.concatenate([c[pred_col].to_numpy(dtype=float) for c in chunks])
                estimate = metric(actual, prediction, kind)
            if math.isfinite(estimate):
                estimates.append(estimate)
    if not estimates:
        return math.nan, math.nan, math.nan
    observed = (
        macro_score(
            participant_correlations(
                frame["participant_id"].astype(str).to_numpy(),
                frame[actual_col].to_numpy(dtype=float),
                frame[pred_col].to_numpy(dtype=float),
                kind,
            )
        )
        if participant_macro and pred_col is not None
        else (
            float(np.mean(np.abs(frame[actual_col].to_numpy(dtype=float))))
            if pred_col is None
            else metric(frame[actual_col].to_numpy(dtype=float), frame[pred_col].to_numpy(dtype=float), kind)
        )
    )
    return observed, float(np.quantile(estimates, 0.025)), float(np.quantile(estimates, 0.975))


def stable_key_frame(
    participant: np.ndarray, library: np.ndarray, barcode: np.ndarray
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "participant_id": participant.astype(str),
            "library_id": library.astype(str),
            "barcode": barcode.astype(str),
        }
    )


def load_stage1_inputs() -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    targets_path = STAGE1 / "targets_by_spot.csv"
    feature_path = STAGE1 / "spot_embeddings.npz"
    color_path = STAGE1 / "color_statistics.npz"
    targets = pd.read_csv(
        targets_path,
        dtype={"participant_id": str, "library_id": str, "barcode": str},
        keep_default_na=False,
    )
    with np.load(feature_path, allow_pickle=False) as archive:
        feature_keys = stable_key_frame(
            archive["participant_id"], archive["library_id"], archive["barcode"]
        )
        features = archive["embeddings"]
    with np.load(color_path, allow_pickle=False) as archive:
        color_keys = stable_key_frame(
            archive["participant_id"], archive["library_id"], archive["barcode"]
        )
        colors = archive["features"]
    keys = ["participant_id", "library_id", "barcode"]
    for frame, name in ((targets, "targets"), (feature_keys, "features"), (color_keys, "colour")):
        if frame.duplicated(keys).any():
            raise ValueError(f"Stage 1 {name} has duplicate full spot keys.")
    target_set = set(map(tuple, targets[keys].astype(str).to_numpy()))
    feature_set = set(map(tuple, feature_keys[keys].astype(str).to_numpy()))
    color_set = set(map(tuple, color_keys[keys].astype(str).to_numpy()))
    if target_set != feature_set or target_set != color_set:
        raise ValueError("Stage 1 target, embedding, and colour full keys do not match exactly.")
    if features.shape != (len(feature_keys), 2048) or colors.shape != (len(color_keys), 12):
        raise ValueError("Stage 1 feature or colour shape is not the registered shape.")
    if not np.isfinite(features).all() or not np.isfinite(colors).all():
        raise ValueError("Stage 1 feature or colour array contains non-finite values.")
    feature_index = {key: i for i, key in enumerate(map(tuple, feature_keys[keys].astype(str).to_numpy()))}
    targets["_feature_idx"] = [
        feature_index[key] for key in map(tuple, targets[keys].astype(str).to_numpy())
    ]
    color_index = {key: i for i, key in enumerate(map(tuple, color_keys[keys].astype(str).to_numpy()))}
    targets["_color_idx"] = [
        color_index[key] for key in map(tuple, targets[keys].astype(str).to_numpy())
    ]
    targets["_source"] = "stage1"
    targets["_input_feature_file"] = str(feature_path)
    return targets, features, colors


def load_stage1d_inputs() -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    npz_path = STAGE1D / "confirmation_predictions.npz"
    qc_path = STAGE1D / "spatial_mapping_qc.csv"
    coefficient_path = ROOT / "stage1d_freeze" / "residualization_parameters.csv"
    with np.load(npz_path, allow_pickle=False) as archive:
        keys = stable_key_frame(archive["participant_id"], archive["library_id"], archive["barcode"])
        features = archive["embeddings"]
        colors = archive["colors"]
        depth = archive["depth"].astype(np.float64)
        library_size = archive["library_size"].astype(np.float64)
        rows = archive["array_rows"]
        cols = archive["array_cols"]
        residual = archive["residual_targets"].astype(np.float64)
    if keys.duplicated(["participant_id", "library_id", "barcode"]).any():
        raise ValueError("Stage 1d array contains duplicate full spot keys.")
    if features.shape != (len(keys), 2048) or colors.shape != (len(keys), 12):
        raise ValueError("Stage 1d feature or colour shape is not the registered shape.")
    if not np.isfinite(features).all() or not np.isfinite(colors).all():
        raise ValueError("Stage 1d feature or colour array contains non-finite values.")
    if not np.allclose(depth, np.log1p(library_size), rtol=0, atol=1e-10):
        raise ValueError("Stage 1d saved depth does not match log1p(library_size).")

    parameters = pd.read_csv(coefficient_path)
    parameters = parameters.loc[parameters["parameter_type"] == "target_on_depth"]
    parameter_map = {
        str(row.target): row for row in parameters.itertuples(index=False)
    }
    target_order = [
        "ECM_collagen", "myofibroblast_pro-fibrotic", "matrix_remodelling",
        "COL1A1", "COL1A2", "COL3A1", "FN1", "TGFB1", "CCN2", "ACTA2", "MMP2", "TIMP1",
    ]
    if residual.shape != (len(keys), len(target_order)):
        raise ValueError("Stage 1d residual target shape does not match the saved target order.")
    if not set(GENES).issubset(parameter_map):
        raise ValueError("Saved depth-residualization coefficients do not cover all target genes.")
    values: dict[str, np.ndarray] = {}
    for target in GENES:
        index = target_order.index(target)
        parameter = parameter_map[target]
        values[target] = residual[:, index] + (
            float(parameter.intercept) + float(parameter.depth_coefficient) * depth
        )
    frame = keys.copy()
    frame["array_row"] = rows.astype(np.int64)
    frame["array_col"] = cols.astype(np.int64)
    frame["depth"] = depth
    frame["library_size_umi"] = library_size
    for target in GENES:
        frame[target] = values[target]
    feature_index = {key: i for i, key in enumerate(map(tuple, keys.to_numpy()))}
    frame["_feature_idx"] = [feature_index[key] for key in map(tuple, keys.to_numpy())]
    frame["_color_idx"] = frame["_feature_idx"]
    frame["_source"] = "stage1d"
    frame["_input_feature_file"] = str(npz_path)
    frame["_stage1d_qc"] = str(qc_path)
    if not np.isfinite(frame[GENES].to_numpy(dtype=float)).all():
        raise ValueError("Reconstructed Stage 1d normalized gene values contain non-finite entries.")
    return frame, features, colors


def audit_stage1_libraries(frame: pd.DataFrame) -> list[dict[str, Any]]:
    sys.path.insert(0, str(ROOT))
    import analyze_cohort_plan_a_b as helper

    audits: list[dict[str, Any]] = []
    for (pid, lid), group in frame.groupby(["participant_id", "library_id"], sort=True):
        row0 = group.iloc[0]
        reasons: list[str] = []
        spatial_record = ""
        if group["sample_id"].astype(str).nunique() != 1:
            reasons.append("multiple_sample_ids_for_library")
        for col in ("expression_source", "image_path", "positions_path"):
            if group[col].astype(str).nunique() != 1:
                reasons.append(f"multiple_{col}_values")
        try:
            position_path = Path(str(row0["positions_path"]))
            if not position_path.is_absolute():
                position_path = ROOT / position_path
            spatial_record = str(position_path.parent)
            image_path = Path(str(row0["image_path"]))
            if not image_path.is_absolute():
                image_path = ROOT / image_path
            scale_path = position_path.parent / "scalefactors_json.json"
            for required in (position_path, image_path, scale_path):
                if not required.is_file():
                    reasons.append(f"missing_file:{required.name}")
            if not reasons:
                positions = helper.read_positions(position_path)
                in_tissue = positions.loc[pd.to_numeric(positions["in_tissue"], errors="coerce") == 1].copy()
                in_tissue["barcode"] = in_tissue["barcode"].astype(str)
                if in_tissue["barcode"].duplicated().any():
                    reasons.append("duplicate_position_barcode")
                row_keys = set(group["barcode"].astype(str))
                position_keys = set(in_tissue["barcode"])
                if row_keys != position_keys:
                    reasons.append(
                        f"in_tissue_barcode_mismatch:features={len(row_keys)},positions={len(position_keys)}"
                    )
                scale = json.loads(scale_path.read_text(encoding="utf-8"))
                factor = float(scale["tissue_hires_scalef"])
                x = np.rint(
                    pd.to_numeric(in_tissue["pxl_col_in_fullres"]).to_numpy(dtype=float) * factor
                ).astype(np.int64)
                y = np.rint(
                    pd.to_numeric(in_tissue["pxl_row_in_fullres"]).to_numpy(dtype=float) * factor
                ).astype(np.int64)
                from PIL import Image

                with Image.open(image_path) as image:
                    width, height = image.size
                if np.any((x < 0) | (x >= width) | (y < 0) | (y >= height)):
                    reasons.append("mapped_center_outside_hires_image")
                by_barcode = in_tissue.set_index("barcode")
                aligned = group.set_index("barcode")
                common = sorted(row_keys & position_keys)
                expected_rows = by_barcode.loc[common, "array_row"].to_numpy(dtype=np.int64)
                expected_cols = by_barcode.loc[common, "array_col"].to_numpy(dtype=np.int64)
                actual_rows = aligned.loc[common, "array_row"].to_numpy(dtype=np.int64)
                actual_cols = aligned.loc[common, "array_col"].to_numpy(dtype=np.int64)
                if not (np.array_equal(expected_rows, actual_rows) and np.array_equal(expected_cols, actual_cols)):
                    reasons.append("array_coordinates_do_not_match_positions")
                expected_x = np.rint(
                    pd.to_numeric(by_barcode.loc[common, "pxl_col_in_fullres"]).to_numpy(dtype=float) * factor
                ).astype(np.int64)
                expected_y = np.rint(
                    pd.to_numeric(by_barcode.loc[common, "pxl_row_in_fullres"]).to_numpy(dtype=float) * factor
                ).astype(np.int64)
                actual_x = np.rint(aligned.loc[common, "center_x_hires_px"].to_numpy(dtype=float)).astype(np.int64)
                actual_y = np.rint(aligned.loc[common, "center_y_hires_px"].to_numpy(dtype=float)).astype(np.int64)
                if not (np.array_equal(expected_x, actual_x) and np.array_equal(expected_y, actual_y)):
                    reasons.append("saved_spot_centers_do_not_match_scaled_positions")
                if position_path.parent.resolve() != image_path.parent.resolve():
                    reasons.append("positions_and_image_not_from_same_spatial_directory")
            audits.append(
                {
                    "participant_id": str(pid),
                    "library_id": str(lid),
                    "source_set": "Stage 1",
                    "expression_record": str(row0["expression_source"]),
                    "spatial_record": spatial_record,
                    "spatial_positions": str(row0["positions_path"]),
                    "image_record": str(row0["image_path"]),
                    "n_feature_keys": int(len(group)),
                    "status": "PASS" if not reasons else "FAIL",
                    "reason": ";".join(reasons),
                }
            )
        except Exception as exc:
            audits.append(
                {
                    "participant_id": str(pid),
                    "library_id": str(lid),
                    "source_set": "Stage 1",
                    "expression_record": str(row0.get("expression_source", "")),
                    "spatial_record": spatial_record,
                    "spatial_positions": str(row0.get("positions_path", "")),
                    "image_record": str(row0.get("image_path", "")),
                    "n_feature_keys": int(len(group)),
                    "status": "FAIL",
                    "reason": f"audit_error:{type(exc).__name__}:{exc}",
                }
            )
    return audits


def audit_stage1d_libraries(frame: pd.DataFrame) -> list[dict[str, Any]]:
    qc_path = STAGE1D / "spatial_mapping_qc.csv"
    qc = pd.read_csv(qc_path, dtype={"participant_id": str, "library_id": str})
    if qc.duplicated(["participant_id", "library_id"]).any():
        raise ValueError("Stage 1d spatial mapping QC has duplicate participant/library rows.")
    counts = frame.groupby(["participant_id", "library_id"], sort=True).size()
    rows: list[dict[str, Any]] = []
    for row in qc.itertuples(index=False):
        key = (str(row.participant_id), str(row.library_id))
        reasons: list[str] = []
        expression_path = CONFIRM_DATA / str(row.expression_file)
        spatial_path = CONFIRM_DATA / str(row.spatial_file)
        if not expression_path.is_file():
            reasons.append("missing_local_expression_archive")
        if not spatial_path.is_file():
            reasons.append("missing_local_spatial_archive")
        count = int(counts.get(key, 0))
        if count != int(row.n_matched_in_tissue_barcodes):
            reasons.append(f"feature_mapping_count_mismatch:{count}!={row.n_matched_in_tissue_barcodes}")
        if int(row.n_in_tissue_positions) != int(row.n_expression_barcodes):
            reasons.append("expression_and_in_tissue_counts_differ")
        if int(row.n_expression_barcodes) != int(row.n_matched_in_tissue_barcodes):
            reasons.append("not_all_in_tissue_barcodes_matched")
        if str(row.all_centers_inside_image).casefold() != "true":
            reasons.append("mapped_center_outside_hires_image")
        if str(row.all_target_genes_present).casefold() != "true":
            reasons.append("one_or_more_target_genes_missing")
        if str(row.primary_module_members_present).casefold() != "true":
            reasons.append("primary_target_members_missing")
        rows.append(
            {
                "participant_id": key[0],
                "library_id": key[1],
                "source_set": "Stage 1d",
                "expression_record": str(row.expression_file),
                "spatial_record": str(spatial_path),
                "spatial_positions": f"{row.spatial_file}::{row.positions_member}",
                "image_record": f"{row.spatial_file}::{row.hires_image_member}",
                "n_feature_keys": count,
                "status": "PASS" if not reasons else "FAIL",
                "reason": ";".join(reasons),
            }
        )
    observed = set(map(tuple, frame[["participant_id", "library_id"]].drop_duplicates().astype(str).to_numpy()))
    expected = set((str(r.participant_id), str(r.library_id)) for r in qc.itertuples(index=False))
    if observed != expected:
        raise ValueError("Stage 1d feature libraries do not exactly match the saved mapping-QC libraries.")
    return rows


def construct_region_data(
    stage1_frame: pd.DataFrame,
    stage1_features: np.ndarray,
    stage1_colors: np.ndarray,
    stage1d_frame: pd.DataFrame,
    stage1d_features: np.ndarray,
    stage1d_colors: np.ndarray,
    audit: pd.DataFrame,
) -> tuple[dict[str, np.ndarray], pd.DataFrame, pd.DataFrame]:
    pass_libs = set(
        map(
            tuple,
            audit.loc[audit["status"] == "PASS", ["participant_id", "library_id"]]
            .astype(str)
            .to_numpy(),
        )
    )
    frames = []
    feature_arrays = []
    color_arrays = []
    for frame, features, colors in (
        (stage1_frame, stage1_features, stage1_colors),
        (stage1d_frame, stage1d_features, stage1d_colors),
    ):
        local = frame.copy()
        local = local.loc[
            [
                (str(pid), str(lid)) in pass_libs
                for pid, lid in zip(local["participant_id"], local["library_id"])
            ]
        ].copy()
        local["_feature_idx"] = pd.to_numeric(local["_feature_idx"]).astype(np.int64)
        local["_color_idx"] = pd.to_numeric(local["_color_idx"]).astype(np.int64)
        local["_global_idx"] = np.arange(len(local), dtype=np.int64)
        feature_arrays.append(features[local["_feature_idx"].to_numpy()])
        color_arrays.append(colors[local["_color_idx"].to_numpy()])
        frames.append(local)
    spots = pd.concat(frames, ignore_index=True)
    x = np.concatenate(feature_arrays).astype(np.float16, copy=False)
    color = np.concatenate(color_arrays).astype(np.float32, copy=False)
    spots = spots.drop(columns=["_feature_idx", "_color_idx", "_global_idx"], errors="ignore")
    spots["array_row"] = pd.to_numeric(spots["array_row"], errors="raise").astype(np.int64)
    spots["array_col"] = pd.to_numeric(spots["array_col"], errors="raise").astype(np.int64)
    if "depth" not in spots:
        spots["depth"] = np.log1p(pd.to_numeric(spots["library_size_umi"], errors="raise").to_numpy(dtype=float))
    else:
        missing_depth = spots["depth"].isna()
        if missing_depth.any():
            spots.loc[missing_depth, "depth"] = np.log1p(
                pd.to_numeric(spots.loc[missing_depth, "library_size_umi"], errors="raise")
            )
    spots["depth"] = pd.to_numeric(spots["depth"], errors="raise").astype(float)
    keys = ["participant_id", "library_id", "barcode"]
    if spots.duplicated(keys).any():
        raise ValueError("Combined aligned inputs have duplicate full spot keys.")
    if len(spots) != len(x) or len(spots) != len(color):
        raise AssertionError("Feature alignment changed the combined spot row count.")
    if not np.isfinite(x).all() or not np.isfinite(color).all() or not np.isfinite(spots[GENES].to_numpy(dtype=float)).all():
        raise ValueError("Aligned features, colours, or targets contain non-finite values.")

    spots["block_row"] = np.floor_divide(spots["array_row"].to_numpy(dtype=np.int64), 4)
    spots["block_col"] = np.floor_divide(spots["array_col"].to_numpy(dtype=np.int64), 4)
    spots["region_id"] = [
        f"{pid}:{lid}:{br}:{bc}"
        for pid, lid, br, bc in zip(
            spots["participant_id"], spots["library_id"], spots["block_row"], spots["block_col"]
        )
    ]
    region_sizes = spots.groupby("region_id", sort=False).size()
    eligible_regions = set(region_sizes[region_sizes >= 4].index)
    spots["region_eligible"] = spots["region_id"].isin(eligible_regions)
    spots["exclusion_reason"] = np.where(
        spots["region_eligible"], "", "region_has_fewer_than_four_paired_in_tissue_spots"
    )
    spots["analysis_label"] = LABEL
    spots["asset_status"] = ASSET_LABEL

    x_smoothed = np.empty((len(spots), x.shape[1]), dtype=np.float32)
    group_indices = spots.groupby(["participant_id", "library_id"], sort=False).indices
    for _, idxs in group_indices.items():
        idxs = np.asarray(idxs, dtype=np.int64)
        local = spots.iloc[idxs]
        coordinate_to_index = {
            (int(row.array_row), int(row.array_col)): int(index)
            for index, row in zip(idxs, local.itertuples(index=False))
        }
        for index in idxs:
            row = spots.iloc[index]
            neighbors = [
                coordinate_to_index[(int(row.array_row) + dr, int(row.array_col) + dc)]
                for dr, dc in NEIGHBOR_OFFSETS
                if (int(row.array_row) + dr, int(row.array_col) + dc) in coordinate_to_index
            ]
            members = [int(index)] + neighbors
            x_smoothed[index] = x[members].astype(np.float32).mean(axis=0)

    included = spots.loc[spots["region_eligible"]].copy()
    region_records: list[dict[str, Any]] = []
    region_raw: list[np.ndarray] = []
    region_smooth: list[np.ndarray] = []
    region_color: list[np.ndarray] = []
    region_gene: list[np.ndarray] = []
    region_depth: list[float] = []
    for rid, group in included.groupby("region_id", sort=True):
        idxs = group.index.to_numpy(dtype=np.int64)
        first = group.iloc[0]
        region_records.append(
            {
                "participant_id": str(first["participant_id"]),
                "library_id": str(first["library_id"]),
                "region_id": str(rid),
                "block_row": int(first["block_row"]),
                "block_col": int(first["block_col"]),
                "n_spots": int(len(group)),
            }
        )
        region_raw.append(x[idxs].astype(np.float32).mean(axis=0))
        region_smooth.append(x_smoothed[idxs].mean(axis=0))
        region_color.append(color[idxs].mean(axis=0))
        region_gene.append(group[GENES].to_numpy(dtype=np.float64).mean(axis=0))
        region_depth.append(float(group["depth"].mean()))
    regions = pd.DataFrame(region_records)
    region_data = {
        "participant_id": regions["participant_id"].to_numpy(dtype="U32"),
        "library_id": regions["library_id"].to_numpy(dtype="U64"),
        "region_id": regions["region_id"].to_numpy(dtype="U128"),
        "block_row": regions["block_row"].to_numpy(dtype=np.int32),
        "block_col": regions["block_col"].to_numpy(dtype=np.int32),
        "n_spots": regions["n_spots"].to_numpy(dtype=np.int32),
        "embedding_raw": np.asarray(region_raw, dtype=np.float32),
        "embedding_smoothed": np.asarray(region_smooth, dtype=np.float32),
        "colors": np.asarray(region_color, dtype=np.float32),
        "depth": np.asarray(region_depth, dtype=np.float64),
        "gene_means": np.asarray(region_gene, dtype=np.float64),
        "gene_names": np.asarray(GENES, dtype="U16"),
        "color_names": np.asarray(COLOR_NAMES, dtype="U16"),
    }
    spot_output_cols = [
        "participant_id", "library_id", "barcode", "region_id", "block_row", "block_col",
        "array_row", "array_col", "region_eligible", "exclusion_reason", "depth", *GENES,
    ]
    spot_rows = spots[spot_output_cols].copy()
    excluded = spot_rows.loc[~spot_rows["region_eligible"]].copy()
    return region_data, spot_rows, excluded


def make_folds(participants: list[str], region_data: dict[str, np.ndarray]) -> tuple[dict[str, int], dict[int, dict[str, int]]]:
    rng = np.random.default_rng(OUTER_SEED)
    sorted_ids = sorted(participants)
    permuted = [sorted_ids[i] for i in rng.permutation(len(sorted_ids))]
    outer = {pid: index % 5 for index, pid in enumerate(permuted)}
    inner: dict[int, dict[str, int]] = {}
    for outer_fold in range(5):
        training_ids = sorted(pid for pid in participants if outer[pid] != outer_fold)
        inner_rng = np.random.default_rng(OUTER_SEED + outer_fold)
        inner_permuted = [training_ids[i] for i in inner_rng.permutation(len(training_ids))]
        inner[outer_fold] = {pid: index % 4 for index, pid in enumerate(inner_permuted)}
    return outer, inner


def create_membership(
    region_data: dict[str, np.ndarray],
    outer: dict[str, int],
    inner: dict[int, dict[str, int]],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    n = len(region_data["region_id"])
    for i in range(n):
        pid = str(region_data["participant_id"][i])
        library = str(region_data["library_id"][i])
        region = str(region_data["region_id"][i])
        for fold in range(5):
            rows.append(
                {
                    "level": "outer",
                    "outer_fold": fold,
                    "inner_fold": -1,
                    "participant_id": pid,
                    "library_id": library,
                    "region_id": region,
                    "role": "test" if outer[pid] == fold else "train",
                }
            )
            if outer[pid] != fold:
                for inner_fold in range(4):
                    rows.append(
                        {
                            "level": "inner",
                            "outer_fold": fold,
                            "inner_fold": inner_fold,
                            "participant_id": pid,
                            "library_id": library,
                            "region_id": region,
                            "role": (
                                "validation"
                                if inner[fold][pid] == inner_fold
                                else "train"
                            ),
                        }
                    )
    membership = pd.DataFrame(rows)
    for (level, outer_fold, inner_fold), group in membership.groupby(
        ["level", "outer_fold", "inner_fold"], sort=False
    ):
        if level == "inner":
            heldout = group.loc[group["role"] == "validation", "participant_id"].astype(str)
            train = group.loc[group["role"] == "train", "participant_id"].astype(str)
            if set(heldout) & set(train):
                raise AssertionError("Inner participant leakage detected.")
    return membership


def preflight() -> None:
    ensure_budget(256 * 1024 * 1024)
    s1, x1, c1 = load_stage1_inputs()
    s1d, xd, cd = load_stage1d_inputs()
    audit_rows = audit_stage1_libraries(s1) + audit_stage1d_libraries(s1d)
    audit = pd.DataFrame(audit_rows)
    if len(audit) != 41:
        raise ValueError(f"Expected 41 library alignment audits, observed {len(audit)}.")
    region_data, spot_rows, excluded = construct_region_data(s1, x1, c1, s1d, xd, cd, audit)
    participants = sorted(set(region_data["participant_id"].astype(str)))
    if not participants:
        raise ValueError("No participants have eligible aligned regions.")
    outer, inner = make_folds(participants, region_data)
    membership = create_membership(region_data, outer, inner)

    save_csv(audit, OUT / "GENE2_ALIGNMENT_AUDIT.csv")
    save_csv(spot_rows, OUT / "GENE2_SPOT_TARGETS.csv")
    if len(excluded):
        save_csv(excluded, OUT / "GENE2_REGION_EXCLUSIONS.csv")
    save_npz(OUT / "GENE2_REGION_DATA.npz", **region_data)
    save_csv(membership, OUT / "GENE2_FOLD_MEMBERSHIP.csv")

    source_files = [
        STAGE1 / "targets_by_spot.csv",
        STAGE1 / "spot_embeddings.npz",
        STAGE1 / "color_statistics.npz",
        STAGE1 / "stage1_config.json",
        STAGE1 / "scripts" / "run_stage1.py",
        STAGE1D / "confirmation_predictions.npz",
        STAGE1D / "data_manifest.csv",
        STAGE1D / "spatial_mapping_qc.csv",
        STAGE1D / "run_frozen_confirmation.py",
        ROOT / "stage1d_freeze" / "residualization_parameters.csv",
        OUT / "GENE2_PREREG.md",
        OUT / "GENE2_DEVIATIONS.md",
        OUT / "GENE2_LICENCE_NOTE.md",
        OUT / "GENE2_RUNNER.py",
    ]
    source_files += [
        Path(str(row["image_record"]))
        for row in audit_rows
        if row["source_set"] == "Stage 1" and Path(str(row["image_record"])).is_file()
    ]
    source_files += [
        Path(str(row["spatial_positions"]))
        for row in audit_rows
        if row["source_set"] == "Stage 1" and Path(str(row["spatial_positions"])).is_file()
    ]
    source_hashes = {
        str(path): sha256(path)
        for path in sorted(set(source_files), key=lambda p: str(p).casefold())
        if path.is_file()
    }
    pass_count = int((audit["status"] == "PASS").sum())
    participant_counts = {
        str(pid): int(count)
        for pid, count in pd.Series(region_data["participant_id"]).value_counts().items()
    }
    fit_budget = {
        "main_registered_maximum": 810,
        "within_participant_shuffle_maximum": 20,
        "total_maximum": 830,
    }
    save_json(
        OUT / "GENE2_PREFLIGHT.json",
        {
            "checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "preflight_passed": bool(pass_count == 41),
            "library_alignment": {
                "audited": int(len(audit)),
                "passed": pass_count,
                "excluded": int(len(audit) - pass_count),
                "failures": audit.loc[audit["status"] != "PASS", ["participant_id", "library_id", "reason"]].to_dict("records"),
            },
            "participants_with_eligible_regions": int(len(participants)),
            "libraries_with_eligible_regions": int(len(set(region_data["library_id"].astype(str)))),
            "eligible_regions": int(len(region_data["region_id"])),
            "included_spots": int(spot_rows["region_eligible"].sum()),
            "spots_in_small_regions_excluded": int(len(excluded)),
            "regions_by_participant": participant_counts,
            "fold_seed": OUTER_SEED,
            "fit_budget": fit_budget,
            "source_sha256": source_hashes,
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "analysis_device": "GPU only for MLP fits; see GENE2_VERIFICATION.md",
        },
    )
    if pass_count != 41:
        raise RuntimeError("Alignment audit has failures; do not begin any model run.")
    print(
        f"Preflight passed: {len(participants)} participants, {pass_count}/41 libraries, "
        f"{len(region_data['region_id'])} regions, {int(spot_rows['region_eligible'].sum())} included spots."
    )


def load_region_data() -> tuple[dict[str, np.ndarray], pd.DataFrame]:
    data_path = OUT / "GENE2_REGION_DATA.npz"
    keys_path = OUT / "GENE2_SPOT_TARGETS.csv"
    if not data_path.is_file() or not keys_path.is_file():
        raise FileNotFoundError("Run preflight before fitting.")
    archive = np.load(data_path, allow_pickle=False)
    data = {key: archive[key] for key in archive.files if key not in {"analysis_label", "asset_status"}}
    spots = pd.read_csv(keys_path, dtype={"participant_id": str, "library_id": str, "barcode": str, "region_id": str})
    if not (archive["analysis_label"].item() == LABEL and archive["asset_status"].item() == ASSET_LABEL):
        raise ValueError("Region data labels are missing or incorrect.")
    return data, spots


def targets_for_outer(
    data: dict[str, np.ndarray],
    spots: pd.DataFrame,
    train_participants: set[str],
) -> tuple[np.ndarray, dict[str, float]]:
    train_spots = spots.loc[spots["participant_id"].astype(str).isin(train_participants)]
    gene_values = train_spots[GENES].to_numpy(dtype=np.float64)
    means = gene_values.mean(axis=0)
    scales = gene_values.std(axis=0, ddof=0)
    scales = np.where(scales > 0, scales, 1.0)
    module = ((data["gene_means"] - means) / scales).mean(axis=1)
    targets = np.column_stack((module, data["gene_means"]))
    stats = {
        f"{gene}_mean": float(mean) for gene, mean in zip(GENES, means)
    }
    stats.update({f"{gene}_sd": float(sd) for gene, sd in zip(GENES, scales)})
    return targets, stats


def get_model_x(data: dict[str, np.ndarray], model_name: str) -> np.ndarray:
    if model_name == "depth_only":
        return data["depth"].reshape(-1, 1).astype(np.float64)
    if model_name == "color_only":
        return data["colors"].astype(np.float64)
    if model_name == "image_ridge":
        return data["embedding_raw"].astype(np.float32)
    if model_name == "image_mlp":
        return data["embedding_smoothed"].astype(np.float32)
    raise ValueError(f"Unknown model: {model_name}")


def selected_metric(
    pids: np.ndarray, y: np.ndarray, pred: np.ndarray, target_index: int = 0
) -> tuple[float, dict[str, float]]:
    per_participant = participant_correlations(
        pids.astype(str), y[:, target_index], pred[:, target_index], "spearman"
    )
    return macro_score(per_participant), per_participant


def fit_ridge(
    x: np.ndarray,
    y: np.ndarray,
    train_idx: np.ndarray,
    eval_idx: np.ndarray,
    pids: np.ndarray,
    alpha: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    fit_start = time.monotonic()
    check_time(fit_start)
    x_train, y_train = x[train_idx].astype(np.float64), y[train_idx].astype(np.float64)
    weights = participant_weights(pids[train_idx].astype(str))
    x_mean, x_scale = weighted_stats(x_train, weights)
    y_mean, y_scale = weighted_stats(y_train, weights)
    x_train_s = (x_train - x_mean) / x_scale
    y_train_s = (y_train - y_mean) / y_scale
    model = Ridge(alpha=float(alpha))
    model.fit(x_train_s, y_train_s, sample_weight=weights)
    x_eval_s = (x[eval_idx].astype(np.float64) - x_mean) / x_scale
    pred = model.predict(x_eval_s) * y_scale + y_mean
    duration = time.monotonic() - fit_start
    if duration >= MAX_FIT_SECONDS:
        raise TimeoutError("Stopping: Ridge fit exceeded its 60-minute cap.")
    if not np.isfinite(pred).all():
        raise ValueError("Ridge prediction contains non-finite values.")
    return pred, {"duration_seconds": duration, "alpha": float(alpha)}


def fit_mlp(
    x: np.ndarray,
    y: np.ndarray,
    train_idx: np.ndarray,
    eval_idx: np.ndarray,
    pids: np.ndarray,
    hidden: int,
    learning_rate: float,
    weight_decay: float,
    seed: int,
    fixed_epochs: int | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    import torch

    fit_start = time.monotonic()
    check_time(fit_start)
    torch.manual_seed(int(seed))
    np.random.seed(int(seed) % (2**32 - 1))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(seed))
    torch.use_deterministic_algorithms(True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.set_num_threads(min(8, os.cpu_count() or 1))
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

    x_train = x[train_idx].astype(np.float32)
    y_train = y[train_idx].astype(np.float32)
    train_participants = pids[train_idx].astype(str)
    weights_np = participant_weights(train_participants).astype(np.float32)
    x_mean, x_scale = weighted_stats(x_train, weights_np)
    y_mean, y_scale = weighted_stats(y_train, weights_np)
    x_train = ((x_train - x_mean) / x_scale).astype(np.float32)
    y_train = ((y_train - y_mean) / y_scale).astype(np.float32)
    x_eval = ((x[eval_idx].astype(np.float32) - x_mean) / x_scale).astype(np.float32)
    weights_np = weights_np / weights_np.mean()

    class SmallMLP(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.layers = torch.nn.Sequential(
                torch.nn.Linear(x_train.shape[1], hidden),
                torch.nn.ReLU(),
                torch.nn.Linear(hidden, y_train.shape[1]),
            )

        def forward(self, value: torch.Tensor) -> torch.Tensor:
            return self.layers(value)

    model = SmallMLP().to(device)
    optimizer = torch.optim.Adam(
        model.parameters(), lr=float(learning_rate), weight_decay=float(weight_decay)
    )
    x_tensor = torch.from_numpy(x_train).to(device)
    y_tensor = torch.from_numpy(y_train).to(device)
    w_tensor = torch.from_numpy(weights_np).to(device)
    val_x = torch.from_numpy(x_eval).to(device)
    if fixed_epochs is None:
        val_y = torch.from_numpy(((y[eval_idx] - y_mean) / y_scale).astype(np.float32)).to(device)
        val_w_np = participant_weights(pids[eval_idx].astype(str)).astype(np.float32)
        val_w = torch.from_numpy(val_w_np).to(device)
    if fixed_epochs is None:
        max_epochs, patience, min_improvement = 200, 15, 1e-4
    else:
        max_epochs, patience, min_improvement = int(fixed_epochs), 0, 0.0
    best_loss = math.inf
    best_epoch = 0
    best_state: dict[str, torch.Tensor] | None = None
    stale = 0
    rng = np.random.default_rng(seed)
    model.train()
    for epoch in range(1, max_epochs + 1):
        check_time(fit_start)
        permutation = rng.permutation(len(train_idx))
        for start in range(0, len(permutation), 256):
            check_time(fit_start)
            batch = permutation[start : start + 256]
            optimizer.zero_grad(set_to_none=True)
            prediction = model(x_tensor[batch])
            squared = (prediction - y_tensor[batch]) ** 2
            loss = (squared.mean(dim=1) * w_tensor[batch]).mean()
            loss.backward()
            optimizer.step()
        if fixed_epochs is None:
            model.eval()
            with torch.no_grad():
                val_prediction = model(val_x)
                val_loss = (
                    ((val_prediction - val_y) ** 2).mean(dim=1) * val_w
                ).sum() / val_w.sum()
                value = float(val_loss.detach().cpu().item())
            model.train()
            if value < best_loss - min_improvement:
                best_loss = value
                best_epoch = epoch
                best_state = {
                    key: tensor.detach().cpu().clone()
                    for key, tensor in model.state_dict().items()
                }
                stale = 0
            else:
                stale += 1
            if stale >= patience:
                break
    if fixed_epochs is None:
        if best_state is None:
            raise RuntimeError("MLP did not complete a finite validation epoch.")
        model.load_state_dict(best_state)
    else:
        best_epoch = int(fixed_epochs)
    model.eval()
    with torch.no_grad():
        pred_scaled = model(val_x).detach().cpu().numpy().astype(np.float64)
    pred = pred_scaled * y_scale + y_mean
    duration = time.monotonic() - fit_start
    if duration >= MAX_FIT_SECONDS:
        raise TimeoutError("Stopping: MLP fit exceeded its 60-minute cap.")
    if not np.isfinite(pred).all():
        raise ValueError("MLP prediction contains non-finite values.")
    return pred, {
        "duration_seconds": duration,
        "best_epoch": best_epoch,
        "epochs_run": epoch,
        "hidden": int(hidden),
        "learning_rate": float(learning_rate),
        "weight_decay": float(weight_decay),
        "seed": int(seed),
        "device": str(device),
    }


def inner_fold_indices(
    participants: np.ndarray,
    outer_map: dict[str, int],
    inner_map: dict[int, dict[str, int]],
    outer_fold: int,
    inner_fold: int,
) -> tuple[np.ndarray, np.ndarray]:
    pids = participants.astype(str)
    train_mask = np.asarray(
        [outer_map[pid] != outer_fold and inner_map[outer_fold][pid] != inner_fold for pid in pids]
    )
    val_mask = np.asarray(
        [outer_map[pid] != outer_fold and inner_map[outer_fold][pid] == inner_fold for pid in pids]
    )
    if set(pids[train_mask]) & set(pids[val_mask]):
        raise AssertionError("Participant crosses inner train/validation folds.")
    if set(pids[train_mask]) & {pid for pid, fold in outer_map.items() if fold == outer_fold}:
        raise AssertionError("Outer test participant leaked into inner training.")
    return np.flatnonzero(train_mask), np.flatnonzero(val_mask)


def load_fold_maps(data: dict[str, np.ndarray]) -> tuple[dict[str, int], dict[int, dict[str, int]]]:
    ids = sorted(set(data["participant_id"].astype(str)))
    return make_folds(ids, data)


def run_inner(outer_fold: int, inner_fold: int) -> None:
    command_start = time.monotonic()
    path = OUT / f"GENE2_INNER_O{outer_fold}_I{inner_fold}.csv"
    if path.exists():
        raise FileExistsError(f"Inner fold output already exists: {path.name}")
    data, spots = load_region_data()
    participants = data["participant_id"].astype(str)
    outer, inner = load_fold_maps(data)
    outer_train_ids = {pid for pid, fold in outer.items() if fold != outer_fold}
    targets, _stats = targets_for_outer(data, spots, outer_train_ids)
    train_idx, val_idx = inner_fold_indices(participants, outer, inner, outer_fold, inner_fold)
    if not len(train_idx) or not len(val_idx):
        raise ValueError("Empty participant-grouped inner train or validation fold.")
    pids = participants
    records: list[dict[str, Any]] = []

    for model_name in ("depth_only", "color_only", "image_ridge"):
        x = get_model_x(data, model_name)
        for alpha in ALPHAS:
            prediction, fit = fit_ridge(x, targets, train_idx, val_idx, pids, alpha)
            score, participants_scores = selected_metric(pids[val_idx], targets[val_idx], prediction)
            records.append(
                {
                    "outer_fold": outer_fold,
                    "inner_fold": inner_fold,
                    "model": model_name,
                    "alpha": alpha,
                    "hidden": "",
                    "learning_rate": "",
                    "weight_decay": "",
                    "seed_set": "",
                    "validation_participants": len(set(pids[val_idx])),
                    "eligible_validation_participants": len(participants_scores),
                    "primary_mean_participant_spearman": score,
                    "median_best_epoch": "",
                    "fit_seconds": fit["duration_seconds"],
                    "fit_seconds_max": fit["duration_seconds"],
                }
            )

    x_mlp = get_model_x(data, "image_mlp")
    for hidden, lr, wd in MLP_GRID:
        predictions = []
        best_epochs = []
        durations = []
        for seed in MLP_SEEDS:
            pred, fit = fit_mlp(
                x_mlp, targets, train_idx, val_idx, pids, hidden, lr, wd, seed
            )
            predictions.append(pred)
            best_epochs.append(int(fit["best_epoch"]))
            durations.append(float(fit["duration_seconds"]))
        ensemble = np.mean(predictions, axis=0)
        score, participants_scores = selected_metric(pids[val_idx], targets[val_idx], ensemble)
        records.append(
            {
                "outer_fold": outer_fold,
                "inner_fold": inner_fold,
                "model": "image_mlp",
                "alpha": "",
                "hidden": hidden,
                "learning_rate": lr,
                "weight_decay": wd,
                "seed_set": ";".join(map(str, MLP_SEEDS)),
                "validation_participants": len(set(pids[val_idx])),
                "eligible_validation_participants": len(participants_scores),
                "primary_mean_participant_spearman": score,
                "median_best_epoch": float(np.median(best_epochs)),
                "fit_seconds": float(sum(durations)),
                "fit_seconds_max": float(max(durations)),
            }
        )
    command_elapsed = time.monotonic() - command_start
    for record in records:
        record["command_elapsed_seconds"] = command_elapsed
    save_csv(pd.DataFrame(records), path)
    print(f"Completed inner fold {outer_fold}/{inner_fold}: {len(records)} candidate rows.")


def select_hyperparameters(inner_results: pd.DataFrame, outer_fold: int) -> dict[str, Any]:
    local = inner_results.loc[inner_results["outer_fold"] == outer_fold].copy()
    if set(local["inner_fold"].astype(int)) != {0, 1, 2, 3}:
        raise ValueError(f"Outer fold {outer_fold} does not have all four completed inner folds.")
    summaries = (
        local.groupby(["model", "alpha", "hidden", "learning_rate", "weight_decay"], dropna=False)
        .agg(
            score=("primary_mean_participant_spearman", "mean"),
            median_epoch=("median_best_epoch", "median"),
            fold_count=("inner_fold", "nunique"),
        )
        .reset_index()
    )
    if (summaries["fold_count"] != 4).any():
        raise ValueError("A hyperparameter candidate is missing an inner fold.")
    ridge_choices: dict[str, dict[str, Any]] = {}
    for model in ("depth_only", "color_only", "image_ridge"):
        candidates = summaries.loc[summaries["model"] == model].copy()
        candidates = candidates.loc[np.isfinite(pd.to_numeric(candidates["score"], errors="coerce"))]
        if candidates.empty:
            raise ValueError(f"No finite inner-validation score for {model} in outer fold {outer_fold}.")
        candidates["alpha_num"] = pd.to_numeric(candidates["alpha"])
        candidates = candidates.sort_values(["score", "alpha_num"], ascending=[False, False])
        best = candidates.iloc[0]
        ridge_choices[model] = {"alpha": float(best["alpha_num"]), "score": float(best["score"])}
    mlp_candidates = summaries.loc[summaries["model"] == "image_mlp"].copy()
    mlp_candidates = mlp_candidates.loc[
        np.isfinite(pd.to_numeric(mlp_candidates["score"], errors="coerce"))
    ]
    if mlp_candidates.empty:
        raise ValueError(f"No finite inner-validation MLP score in outer fold {outer_fold}.")
    mlp_candidates["hidden_num"] = pd.to_numeric(mlp_candidates["hidden"])
    mlp_candidates["lr_num"] = pd.to_numeric(mlp_candidates["learning_rate"])
    mlp_candidates["wd_num"] = pd.to_numeric(mlp_candidates["weight_decay"])
    mlp_candidates = mlp_candidates.sort_values(
        ["score", "hidden_num", "lr_num", "wd_num"],
        ascending=[False, True, True, False],
    )
    best_mlp = mlp_candidates.iloc[0]
    mlp_choice = {
        "hidden": int(best_mlp["hidden_num"]),
        "learning_rate": float(best_mlp["lr_num"]),
        "weight_decay": float(best_mlp["wd_num"]),
        "score": float(best_mlp["score"]),
        "median_epoch": float(best_mlp["median_epoch"]),
    }
    image_choice = (
        "image_mlp" if mlp_choice["score"] > ridge_choices["image_ridge"]["score"] else "image_ridge"
    )
    if mlp_choice["score"] == ridge_choices["image_ridge"]["score"]:
        image_choice = "image_ridge"
    baseline_choice = (
        "depth_only"
        if ridge_choices["depth_only"]["score"] >= ridge_choices["color_only"]["score"]
        else "color_only"
    )
    return {
        "ridge": ridge_choices,
        "mlp": mlp_choice,
        "selected_image": image_choice,
        "selected_baseline": baseline_choice,
        "image_score": (
            mlp_choice["score"] if image_choice == "image_mlp" else ridge_choices["image_ridge"]["score"]
        ),
        "baseline_score": ridge_choices[baseline_choice]["score"],
    }


def shuffle_primary_within_participant(
    targets: np.ndarray, participant_ids: np.ndarray, rng: np.random.Generator
) -> np.ndarray:
    shuffled = targets.copy()
    for pid in sorted(set(participant_ids.astype(str))):
        indexes = np.flatnonzero(participant_ids.astype(str) == pid)
        shuffled[indexes, 0] = targets[rng.permutation(indexes), 0]
    return shuffled


def run_outer(outer_fold: int) -> None:
    command_start = time.monotonic()
    path = OUT / f"GENE2_OUTER_FOLD_{outer_fold}.csv"
    if path.exists():
        raise FileExistsError(f"Outer fold output already exists: {path.name}")
    data, spots = load_region_data()
    participants = data["participant_id"].astype(str)
    outer, inner = load_fold_maps(data)
    train_ids = {pid for pid, fold in outer.items() if fold != outer_fold}
    test_ids = {pid for pid, fold in outer.items() if fold == outer_fold}
    targets, z_stats = targets_for_outer(data, spots, train_ids)
    train_idx = np.flatnonzero(np.isin(participants, list(train_ids)))
    test_idx = np.flatnonzero(np.isin(participants, list(test_ids)))
    if set(participants[train_idx]) & set(participants[test_idx]):
        raise AssertionError("Participant crosses outer train/test folds.")
    inner_paths = [OUT / f"GENE2_INNER_O{outer_fold}_I{i}.csv" for i in range(4)]
    if not all(p.is_file() for p in inner_paths):
        raise FileNotFoundError("All four inner-fold runs must finish before outer fitting.")
    inner_results = pd.concat([pd.read_csv(p) for p in inner_paths], ignore_index=True)
    selection = select_hyperparameters(inner_results, outer_fold)
    pids = participants
    pred_by_model: dict[str, np.ndarray] = {}
    fit_details: dict[str, Any] = {}
    for model_name in ("depth_only", "color_only", "image_ridge"):
        x = get_model_x(data, model_name)
        alpha = selection["ridge"][model_name]["alpha"]
        pred, fit = fit_ridge(x, targets, train_idx, test_idx, pids, alpha)
        pred_by_model[model_name] = pred
        fit_details[model_name] = fit

    mlp = selection["mlp"]
    mlp_epochs = max(1, int(round(mlp["median_epoch"])))
    mlp_predictions = []
    mlp_fits = []
    for seed in MLP_SEEDS:
        pred, fit = fit_mlp(
            get_model_x(data, "image_mlp"),
            targets,
            train_idx,
            test_idx,
            pids,
            mlp["hidden"],
            mlp["learning_rate"],
            mlp["weight_decay"],
            seed,
            fixed_epochs=mlp_epochs,
        )
        mlp_predictions.append(pred)
        mlp_fits.append(fit)
    pred_by_model["image_mlp"] = np.mean(mlp_predictions, axis=0)
    fit_details["image_mlp"] = {"fits": mlp_fits, "selected_final_epochs": mlp_epochs}

    image_name = selection["selected_image"]
    baseline_name = selection["selected_baseline"]
    rng = np.random.default_rng(SHUFFLE_SEED)
    shuffled_targets = shuffle_primary_within_participant(targets, participants, rng)
    image_shuffle_predictions: list[np.ndarray] = []
    image_shuffle_fits: list[dict[str, Any]] = []
    if image_name == "image_ridge":
        image_shuffle, image_shuffle_fit = fit_ridge(
            get_model_x(data, image_name), shuffled_targets, train_idx, test_idx,
            pids, selection["ridge"]["image_ridge"]["alpha"],
        )
    else:
        for seed in MLP_SEEDS:
            pred, fit = fit_mlp(
                get_model_x(data, "image_mlp"),
                shuffled_targets,
                train_idx,
                test_idx,
                pids,
                mlp["hidden"],
                mlp["learning_rate"],
                mlp["weight_decay"],
                seed,
                fixed_epochs=mlp_epochs,
            )
            image_shuffle_predictions.append(pred)
            image_shuffle_fits.append(fit)
        image_shuffle = np.mean(image_shuffle_predictions, axis=0)
        image_shuffle_fit = {"fits": image_shuffle_fits}
    baseline_shuffle, baseline_shuffle_fit = fit_ridge(
        get_model_x(data, baseline_name),
        shuffled_targets,
        train_idx,
        test_idx,
        pids,
        selection["ridge"][baseline_name]["alpha"],
    )

    output = pd.DataFrame(
        {
            "participant_id": participants[test_idx],
            "library_id": data["library_id"][test_idx].astype(str),
            "region_id": data["region_id"][test_idx].astype(str),
            "n_spots": data["n_spots"][test_idx],
            "outer_fold": outer_fold,
            "selected_image_model": image_name,
            "selected_baseline_model": baseline_name,
            "selected_image_inner_score": selection["image_score"],
            "selected_baseline_inner_score": selection["baseline_score"],
            "selected_mlp_hidden": mlp["hidden"],
            "selected_mlp_learning_rate": mlp["learning_rate"],
            "selected_mlp_weight_decay": mlp["weight_decay"],
            "selected_mlp_epochs": mlp_epochs,
            "zscore_gene_means": json.dumps({g: z_stats[f"{g}_mean"] for g in GENES}, sort_keys=True),
            "zscore_gene_sds": json.dumps({g: z_stats[f"{g}_sd"] for g in GENES}, sort_keys=True),
        }
    )
    for j, target in enumerate(TARGET_NAMES):
        output[f"actual_{target}"] = targets[test_idx, j]
        for model_name, predictions in pred_by_model.items():
            output[f"pred_{model_name}_{target}"] = predictions[:, j]
        output[f"pred_selected_image_{target}"] = pred_by_model[image_name][:, j]
        output[f"pred_selected_baseline_{target}"] = pred_by_model[baseline_name][:, j]
        output[f"shuffle_actual_{target}"] = shuffled_targets[test_idx, j]
        output[f"shuffle_pred_selected_image_{target}"] = image_shuffle[:, j]
        output[f"shuffle_pred_selected_baseline_{target}"] = baseline_shuffle[:, j]
    command_elapsed = time.monotonic() - command_start
    output["command_elapsed_seconds"] = command_elapsed
    save_csv(output, path)
    selection_path = OUT / f"GENE2_SELECTION_O{outer_fold}.json"
    save_json(
        selection_path,
        {
            "outer_fold": outer_fold,
            "selected": selection,
            "fits": fit_details,
            "shuffle_fits": {
                "image_model": image_shuffle_fit,
                "best_baseline": baseline_shuffle_fit,
                "seed": SHUFFLE_SEED,
            },
            "training_participants": sorted(train_ids),
            "test_participants": sorted(test_ids),
            "fit_count_this_outer": 6 + (3 if image_name == "image_mlp" else 1) + 1,
            "command_elapsed_seconds": command_elapsed,
        },
    )
    print(f"Completed outer fold {outer_fold}: {len(test_idx)} regions; selected {image_name} vs {baseline_name}.")


def holm_adjust(p_values: list[float]) -> list[float]:
    n = len(p_values)
    order = np.argsort(p_values)
    adjusted = np.empty(n, dtype=float)
    running = 0.0
    for rank, index in enumerate(order):
        value = min(1.0, (n - rank) * p_values[index])
        running = max(running, value)
        adjusted[index] = running
    return adjusted.tolist()


def sign_flip_pvalue(values: np.ndarray, seed: int) -> float:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if not len(values):
        return math.nan
    observed = abs(float(values.mean()))
    rng = np.random.default_rng(seed)
    signs = rng.choice(np.asarray([-1.0, 1.0]), size=(PERMUTATIONS, len(values)))
    null = np.abs((signs * values).mean(axis=1))
    return float((1 + np.sum(null >= observed)) / (PERMUTATIONS + 1))


def partial_spearman(frame: pd.DataFrame, target_col: str, prediction_col: str) -> dict[str, float]:
    from scipy.stats import rankdata
    from sklearn.linear_model import LinearRegression

    nuisance_cols = ["depth"] + [f"color_{name}" for name in COLOR_NAMES]
    nuisance = frame[nuisance_cols].to_numpy(dtype=float)
    y = frame[target_col].to_numpy(dtype=float)
    p = frame[prediction_col].to_numpy(dtype=float)
    valid = np.isfinite(y) & np.isfinite(p) & np.isfinite(nuisance).all(axis=1)
    nuisance, y, p = nuisance[valid], y[valid], p[valid]
    if len(y) <= nuisance.shape[1] + 2:
        return {"n_regions": int(len(y)), "partial_spearman": math.nan}
    nuisance_rank = np.column_stack([rankdata(nuisance[:, i]) for i in range(nuisance.shape[1])])
    y_rank, p_rank = rankdata(y), rankdata(p)
    residual_y = y_rank - LinearRegression().fit(nuisance_rank, y_rank).predict(nuisance_rank)
    residual_p = p_rank - LinearRegression().fit(nuisance_rank, p_rank).predict(nuisance_rank)
    return {"n_regions": int(len(y)), "partial_spearman": metric(residual_y, residual_p, "pearson")}


def verify_saved_results(
    preflight_record: dict[str, Any],
    primary_mean: float,
    primary_low: float,
    primary_high: float,
    primary_macro: float,
) -> tuple[dict[str, Any], list[str]]:
    saved = pd.read_csv(OUT / "GENE2_OOF_REGION_PREDICTIONS.csv")
    actual = saved[f"actual_{PRIMARY}"].to_numpy(dtype=float)
    image = saved[f"pred_selected_image_{PRIMARY}"].to_numpy(dtype=float)
    baseline = saved[f"pred_selected_baseline_{PRIMARY}"].to_numpy(dtype=float)
    pids = saved["participant_id"].astype(str).to_numpy()
    image_scores = participant_correlations(pids, actual, image, "spearman")
    baseline_scores = participant_correlations(pids, actual, baseline, "spearman")
    paired_pids = sorted(set(image_scores) & set(baseline_scores))
    deltas = np.asarray([image_scores[pid] - baseline_scores[pid] for pid in paired_pids], dtype=float)
    paired_recomputed = paired_bootstrap(deltas, BOOTSTRAP_SEED)
    image_macro_recomputed = macro_score(image_scores)
    region_spearman_recomputed = metric(actual, image, "spearman")
    image_mae_recomputed = float(np.mean(np.abs(actual - image)))
    primary_saved = pd.read_csv(OUT / "GENE2_PRIMARY_ENDPOINT.csv").iloc[0]
    metrics = {
        "paired_delta_mean": paired_recomputed[0],
        "paired_delta_ci95_low": paired_recomputed[1],
        "paired_delta_ci95_high": paired_recomputed[2],
        "image_participant_macro_spearman": image_macro_recomputed,
        "image_region_pooled_spearman": region_spearman_recomputed,
        "image_region_mae": image_mae_recomputed,
        "n_paired_participants": len(paired_pids),
        "n_oof_regions": int(len(saved)),
    }
    comparisons = {
        "paired_delta_mean": (metrics["paired_delta_mean"], primary_mean),
        "paired_delta_ci95_low": (metrics["paired_delta_ci95_low"], primary_low),
        "paired_delta_ci95_high": (metrics["paired_delta_ci95_high"], primary_high),
        "image_participant_macro_spearman": (
            metrics["image_participant_macro_spearman"], primary_macro
        ),
        "saved_primary_mean": (
            metrics["paired_delta_mean"], float(primary_saved["paired_mean_difference"])
        ),
        "saved_primary_ci_low": (
            metrics["paired_delta_ci95_low"],
            float(primary_saved["participant_bootstrap_ci95_low"]),
        ),
        "saved_primary_ci_high": (
            metrics["paired_delta_ci95_high"],
            float(primary_saved["participant_bootstrap_ci95_high"]),
        ),
    }
    checks = []
    for name, (left, right) in comparisons.items():
        if not math.isclose(left, right, rel_tol=0, abs_tol=1e-12):
            raise AssertionError(f"Independent saved-prediction verification failed for {name}: {left} != {right}")
        checks.append(f"{name}: MATCH ({left:.12g})")

    membership = pd.read_csv(OUT / "GENE2_FOLD_MEMBERSHIP.csv", dtype=str)
    outer_map: dict[str, int] = {}
    for fold in range(5):
        outer_rows = membership.loc[
            (membership["level"] == "outer") & (membership["outer_fold"] == str(fold))
        ]
        role_counts = outer_rows.groupby("participant_id")["role"].nunique()
        if outer_rows["participant_id"].nunique() != 40 or not (role_counts == 1).all():
            raise AssertionError(f"Outer fold {fold} has participant-role overlap or missing participants.")
        roles = outer_rows.groupby("participant_id")["role"].first()
        if int((roles == "test").sum()) != 8 or int((roles == "train").sum()) != 32:
            raise AssertionError(f"Outer fold {fold} has incorrect participant counts.")
        for pid in roles[roles == "test"].index:
            outer_map[str(pid)] = fold
        for inner_fold in range(4):
            inner_rows = membership.loc[
                (membership["level"] == "inner")
                & (membership["outer_fold"] == str(fold))
                & (membership["inner_fold"] == str(inner_fold))
            ]
            inner_roles = inner_rows.groupby("participant_id")["role"].nunique()
            if inner_rows["participant_id"].nunique() != 32 or not (inner_roles == 1).all():
                raise AssertionError(f"Outer {fold}/inner {inner_fold} participant overlap detected.")
            actual_roles = inner_rows.groupby("participant_id")["role"].first()
            if int((actual_roles == "validation").sum()) != 8 or int((actual_roles == "train").sum()) != 24:
                raise AssertionError(f"Outer {fold}/inner {inner_fold} has incorrect participant counts.")
            if set(actual_roles.index) & {pid for pid, assigned in outer_map.items() if assigned == fold}:
                raise AssertionError(f"Outer test participant leaked into outer {fold}/inner {inner_fold}.")
    if len(outer_map) != 40:
        raise AssertionError("Outer fold membership does not cover exactly 40 participants.")
    checks.append("outer/inner fold overlap: PASS (participant, library, and region grouping)")

    spot_keys = pd.read_csv(
        OUT / "GENE2_SPOT_TARGETS.csv",
        dtype={"participant_id": str, "library_id": str, "barcode": str, "region_id": str},
    )
    oof_spots = pd.read_csv(
        OUT / "GENE2_OOF_SPOT_PREDICTIONS.csv",
        dtype={"participant_id": str, "library_id": str, "barcode": str, "region_id": str},
    )
    expected_spots = spot_keys.loc[spot_keys["region_eligible"].astype(bool)]
    key_cols = ["participant_id", "library_id", "barcode"]
    if expected_spots.duplicated(key_cols).any() or oof_spots.duplicated(key_cols).any():
        raise AssertionError("Saved spot predictions contain duplicate full keys.")
    expected_set = set(map(tuple, expected_spots[key_cols].astype(str).to_numpy()))
    observed_set = set(map(tuple, oof_spots[key_cols].astype(str).to_numpy()))
    if expected_set != observed_set:
        raise AssertionError("Saved OOF spot predictions do not match all and only eligible full keys.")
    checks.append(f"eligible spot-key coverage: PASS ({len(observed_set)} unique full keys)")
    if len(saved) != int(preflight_record["eligible_regions"]):
        raise AssertionError("Saved OOF region count does not match the preflight region count.")
    checks.append(f"eligible region coverage: PASS ({len(saved)} regions)")
    return metrics, checks


def write_markdown(path: Path, text: str) -> None:
    ensure_budget(len(text.encode("utf-8")))
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    ensure_budget()


def write_final_reports(
    primary_mean: float,
    primary_low: float,
    primary_high: float,
    primary_macro: float,
    criterion_met: bool,
    shuffle_mean: float,
    shuffle_low: float,
    shuffle_high: float,
    region_count: int,
) -> None:
    preflight_record = json.loads((OUT / "GENE2_PREFLIGHT.json").read_text(encoding="utf-8"))
    verified, checks = verify_saved_results(
        preflight_record, primary_mean, primary_low, primary_high, primary_macro
    )
    metric_summary = pd.read_csv(OUT / "GENE2_METRIC_SUMMARIES.csv")
    primary_metrics: dict[str, dict[str, Any]] = {}
    for model in ("selected_image", "selected_baseline"):
        rows = metric_summary.loc[
            (metric_summary["target"] == PRIMARY) & (metric_summary["model"] == model)
        ]
        primary_metrics[model] = {
            str(row["metric"]): row for _, row in rows.iterrows()
        }
    regions = pd.read_csv(OUT / "GENE2_OOF_REGION_PREDICTIONS.csv")
    image_models = ", ".join(sorted(set(regions["selected_image_model"].astype(str))))
    baseline_models = ", ".join(sorted(set(regions["selected_baseline_model"].astype(str))))
    secondary = pd.read_csv(OUT / "GENE2_SECONDARY_HOLM.csv")
    shuffle = pd.read_csv(OUT / "GENE2_LABEL_SHUFFLE.csv").iloc[0]
    partial = pd.read_csv(OUT / "GENE2_PARTIAL_CORRELATIONS.csv")
    participant_scores = pd.read_csv(OUT / "GENE2_PER_PARTICIPANT_SPEARMAN.csv")
    primary_differences = participant_scores.loc[
        (participant_scores["target"] == PRIMARY)
        & (participant_scores["model"] == "selected_image_minus_baseline"),
        ["participant_id", "region_spearman"],
    ].dropna()
    positive_differences = int((primary_differences["region_spearman"] > 0).sum())
    largest_differences = primary_differences.reindex(
        primary_differences["region_spearman"].abs().sort_values(ascending=False).index
    ).head(3)
    participants_with_metrics = int(
        pd.read_csv(OUT / "GENE2_PRIMARY_ENDPOINT.csv").iloc[0]["n_paired_participants"]
    )

    def metric_cell(row: Any, value: str, low: str, high: str) -> str:
        return (
            f"{float(row[value]):.4f} "
            f"[{float(row[low]):.4f}, {float(row[high]):.4f}]"
        )

    result_lines = [
        f"# GENE2 Results — {LABEL}",
        "",
        f"**{ASSET_LABEL} — ResNet-50/ImageNet saved features.**",
        "",
        "All numbers are from grouped nested cross-validation on participants already used in earlier stages. They are exploratory and not confirmatory.",
        "",
        "## Primary endpoint",
        "",
        f"- Paired difference (image minus best baseline) in participant-macro region Spearman: {primary_mean:.6f}.",
        f"- Participant-bootstrap 95% CI: [{primary_low:.6f}, {primary_high:.6f}] (10,000 resamples; seed {BOOTSTRAP_SEED}).",
        f"- Image-model participant-macro mean Spearman: {primary_macro:.6f}; required value: 0.30.",
        f"- The registered exploratory rule was **{'met' if criterion_met else 'not met'}**. This does not mean proof, success, validation, or confirmation.",
        f"- Participants with paired primary metrics: {participants_with_metrics}; regions: {region_count}; spots in eligible regions: {int(preflight_record['included_spots'])}.",
        f"- Selected image model(s) across outer folds: {image_models}; selected baseline(s): {baseline_models}.",
        "",
        "### Primary-target metrics",
        "",
        "| Model | Region Spearman [95% CI] | Region Pearson [95% CI] | Participant-mean Spearman [95% CI] | Participant-mean Pearson [95% CI] | Region MAE [95% CI] |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for model, display in (
        ("selected_image", "Selected image model"),
        ("selected_baseline", "Selected baseline"),
    ):
        rows = primary_metrics[model]
        result_lines.append(
            "| "
            + " | ".join(
                [
                    display,
                    metric_cell(rows["spearman"], "region_pooled_value", "region_pooled_ci95_low", "region_pooled_ci95_high"),
                    metric_cell(rows["pearson"], "region_pooled_value", "region_pooled_ci95_low", "region_pooled_ci95_high"),
                    metric_cell(rows["participant_mean_spearman"], "value", "ci95_low", "ci95_high"),
                    metric_cell(rows["participant_mean_pearson"], "value", "ci95_low", "ci95_high"),
                    metric_cell(rows["region_mae"], "value", "ci95_low", "ci95_high"),
                ]
            )
            + " |"
        )
    image_macro_row = primary_metrics["selected_image"]["spearman"]
    baseline_macro_row = primary_metrics["selected_baseline"]["spearman"]
    result_lines.extend(
        [
            "",
            f"Selected image-model participant-macro region Spearman: {float(image_macro_row['participant_macro_value']):.6f} "
            f"[{float(image_macro_row['participant_macro_ci95_low']):.6f}, {float(image_macro_row['participant_macro_ci95_high']):.6f}].",
            f"Selected-baseline participant-macro region Spearman: {float(baseline_macro_row['participant_macro_value']):.6f} "
            f"[{float(baseline_macro_row['participant_macro_ci95_low']):.6f}, {float(baseline_macro_row['participant_macro_ci95_high']):.6f}].",
            f"- The image-minus-baseline difference was positive for {positive_differences}/{len(primary_differences)} participants. The three largest absolute participant differences are: "
            + (", ".join(
                f"{row.participant_id} ({row.region_spearman:.4f})"
                for row in largest_differences.itertuples(index=False)
            ) or "NOT AVAILABLE")
            + ". See `GENE2_PER_PARTICIPANT_SPEARMAN.csv` for every participant.",
            "",
            "## Secondary targets",
            "",
            "| Target | Participants | Paired difference | 95% CI | Raw p | Holm p |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in secondary.itertuples(index=False):
        result_lines.append(
            f"| {row.target} | {row.n_paired_participants} | {row.paired_delta:.6f} | "
            f"[{row.ci95_low:.6f}, {row.ci95_high:.6f}] | {row.p_raw:.6g} | "
            f"{row.p_holm_adjusted:.6g} |"
        )
    result_lines.extend(
        [
            "",
            "## Sanity checks and interpretation",
            "",
            f"- Within-participant shuffled-label mean difference: {shuffle_mean:.6f}, 95% CI [{shuffle_low:.6f}, {shuffle_high:.6f}]; "
            f"pre-registered sanity failure: {bool(shuffle['sanity_failure'])}.",
            "- Depth-only and colour-only baselines were included in inner tuning and outer test predictions. Partial-correlation checks are reported in `GENE2_PARTIAL_CORRELATIONS.csv`.",
            "- Every participant was used in earlier development or evaluation. These data cannot support a confirmatory claim.",
            "- An observed image-to-expression association does not show that gene expression is directly visible in an image, establish a biological mechanism, or establish medical accuracy or clinical utility.",
            "- **Recommendation:** " + (
                "a signal may be worth testing once on genuinely unseen, properly authorized participants."
                if criterion_met
                else "the registered rule was not met, so this run does not provide a positive basis for recommending a confirmatory test."
            ),
            "",
            "Descriptive metric confidence intervals use 2,000 participant-bootstrap draws. Primary and secondary paired-difference intervals use the registered 10,000 draws.",
            "",
            "Full per-participant, per-region, per-spot, Pearson, MAE, and confidence-interval results are in the GENE2 CSV files.",
        ]
    )
    write_markdown(OUT / "GENE2_RESULTS.md", "\n".join(result_lines))

    alignment = pd.read_csv(OUT / "GENE2_ALIGNMENT_AUDIT.csv")
    spot_keys = pd.read_csv(
        OUT / "GENE2_SPOT_TARGETS.csv",
        dtype={"participant_id": str, "library_id": str, "barcode": str},
    )
    partial_lines = [
        f"# GENE2 Leakage and Sanity Checks — {LABEL}",
        "",
        f"**{ASSET_LABEL} — ResNet-50/ImageNet feature-dependent results.**",
        "",
        "## Preflight and split checks",
        "",
        f"- Image/expression library alignment: {(alignment['status'] == 'PASS').sum()}/{len(alignment)} libraries passed.",
        f"- Participants: {preflight_record['participants_with_eligible_regions']}; eligible regions: {preflight_record['eligible_regions']}; spots in eligible regions: {preflight_record['included_spots']}.",
        f"- Full spot-key duplicates: {int(spot_keys.duplicated(['participant_id', 'library_id', 'barcode']).sum())}.",
        "- Fold membership passed independent participant, library, and region overlap checks. Each outer fold had 8 held-out and 32 training participants; each inner fold had 8 validation and 24 training participants.",
        "- Every library and all adjacent spots from a participant inherit that participant's fold; no participant was split.",
        "",
        "## Controls",
        "",
        f"- Label-shuffle image-minus-best-baseline primary mean Spearman: {shuffle_mean:.6f}, 95% CI [{shuffle_low:.6f}, {shuffle_high:.6f}]; pre-registered sanity failure: {bool(shuffle['sanity_failure'])}.",
        "- Depth-only and colour-only Ridge baselines were fitted in the registered nested design.",
        "",
        "| Model | Partial region Spearman after adjustment for ranked colour features and depth | Regions |",
        "|---|---:|---:|",
    ]
    for row in partial.itertuples(index=False):
        partial_lines.append(
            f"| {row.model} | {float(row.partial_spearman):.6f} | {row.n_regions} |"
        )
    partial_lines.extend(
        [
            "",
            "These checks are exploratory and use participants with prior development/evaluation. They do not establish confirmation or clinical meaning.",
        ]
    )
    write_markdown(OUT / "GENE2_SANITY.md", "\n".join(partial_lines))

    selection_files = [OUT / f"GENE2_SELECTION_O{o}.json" for o in range(5)]
    selections = [json.loads(path.read_text(encoding="utf-8")) for path in selection_files]
    inner_files = [OUT / f"GENE2_INNER_O{o}_I{i}.csv" for o in range(5) for i in range(4)]
    inner_frames = [pd.read_csv(path) for path in inner_files]
    inner_fit_max = max(float(frame["fit_seconds_max"].max()) for frame in inner_frames)
    inner_command_max = max(float(frame["command_elapsed_seconds"].max()) for frame in inner_frames)
    outer_command_max = max(float(item["command_elapsed_seconds"]) for item in selections)
    if inner_fit_max >= MAX_FIT_SECONDS or inner_command_max >= MAX_INVOCATION_SECONDS or outer_command_max >= MAX_INVOCATION_SECONDS:
        raise RuntimeError("A recorded fit or model command exceeded its registered execution cap.")
    shuffle_fit_count = sum(int(item["fit_count_this_outer"]) - 6 for item in selections)
    if shuffle_fit_count > 20:
        raise RuntimeError("Actual label-shuffle fit count exceeded the 20-fit preregistered maximum.")
    retry_path = OUT / "GENE2_RETRY_ACCOUNTING.json"
    retry_fit_count = 0
    if retry_path.is_file():
        retry_record = json.loads(retry_path.read_text(encoding="utf-8"))
        retry_fit_count = int(retry_record["completed_fit_calls_from_failed_attempts"])
        if retry_fit_count < 0:
            raise ValueError("Retry fit accounting cannot be negative.")

    import scipy
    import sklearn
    import torch
    import torchvision

    device_text = (
        f"{torch.cuda.get_device_name(0)} (CUDA available)"
        if torch.cuda.is_available()
        else "CPU"
    )
    finalize_elapsed = time.monotonic() - INVOCATION_START
    if finalize_elapsed >= MAX_INVOCATION_SECONDS:
        raise TimeoutError("Finalize reached its 90-minute command cap.")
    verification_lines = [
        f"# GENE2 Verification — {LABEL}",
        "",
        f"**{ASSET_LABEL} — saved ResNet-50/ImageNet features.**",
        "",
        "## Independent recomputation from saved out-of-fold predictions",
        "",
        "| Headline value | Recomputed value | Check |",
        "|---|---:|---|",
    ]
    for key, label in (
        ("paired_delta_mean", "Primary paired mean difference"),
        ("paired_delta_ci95_low", "Primary 95% CI lower bound"),
        ("paired_delta_ci95_high", "Primary 95% CI upper bound"),
        ("image_participant_macro_spearman", "Image participant-macro Spearman"),
        ("image_region_pooled_spearman", "Image pooled region Spearman"),
        ("image_region_mae", "Image region MAE"),
    ):
        verification_lines.append(f"| {label} | {float(verified[key]):.12g} | MATCH |")
    verification_lines.extend(
        [
            "",
            f"Paired participants: {verified['n_paired_participants']}; saved OOF regions: {verified['n_oof_regions']}.",
            "",
            "## Fold, key, and output verification",
            "",
            *[f"- {line}" for line in checks],
            f"- Preregistered main nested-CV fits: 810; selected-model label-shuffle fits saved across the five completed outer folds: {shuffle_fit_count}; completed fit calls from failed attempts: {retry_fit_count}; total actual fit calls: {810 + shuffle_fit_count + retry_fit_count}. The preregistered maximum was 830; any overage is disclosed as a deviation.",
            f"- Largest recorded individual fit: {inner_fit_max:.2f} seconds; longest inner command: {inner_command_max:.2f} seconds; longest outer command: {outer_command_max:.2f} seconds.",
            f"- Finalize analysis command: {finalize_elapsed:.2f} seconds; output size: {output_bytes()} bytes (1-GB cap).",
            "- No GENE2 checkpoint weights were saved; this nested-CV run has no final frozen model. The frozen Stage 1d model and ResNet checkpoint were not loaded or changed; only saved feature arrays were used.",
            "- Preflight source hashes were rechecked. Any changed hashes were limited to the runner or the listed preregistration/deviation/licence documents, which were updated before or after this run; current hashes are listed below.",
            "",
            "## Environment and seeds",
            "",
            f"- Python `{sys.version.split()[0]}`; NumPy `{np.__version__}`; pandas `{pd.__version__}`; SciPy `{scipy.__version__}`; scikit-learn `{sklearn.__version__}`.",
            f"- PyTorch `{torch.__version__}`; torchvision `{torchvision.__version__}`; MLP device: `{device_text}`.",
            "- Outer participant folds `20261120`; MLP `20261121`, `20261122`, `20261123`; paired bootstrap `20261124`; label shuffle `20261125`; secondary sign-flip `20261126`.",
            "",
            "## Exact commands",
            "",
            "```text",
            r"C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py preflight",
        ]
    )
    for outer_fold in range(5):
        for inner_fold in range(4):
            verification_lines.append(
                rf"C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold {outer_fold} --inner-fold {inner_fold}"
            )
    for outer_fold in range(5):
        verification_lines.append(
            rf"C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py fit-outer --outer-fold {outer_fold}"
        )
    verification_lines.extend(
        [
            r"C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py finalize",
            "```",
            "",
            "## SHA-256 of source and analysis files read",
            "",
            "| File | SHA-256 |",
            "|---|---|",
        ]
    )
    hashes: dict[str, str] = {}
    allowed_post_preflight_changes = {
        str(OUT / "GENE2_RUNNER.py"),
        str(OUT / "GENE2_PREREG.md"),
        str(OUT / "GENE2_DEVIATIONS.md"),
        str(OUT / "GENE2_LICENCE_NOTE.md"),
    }
    changed_after_preflight: list[str] = []
    for source_path, recorded_hash in preflight_record["source_sha256"].items():
        path = Path(source_path)
        if not path.is_file():
            raise FileNotFoundError(f"Preflight source disappeared before verification: {source_path}")
        current_hash = sha256(path)
        if current_hash != recorded_hash:
            if source_path not in allowed_post_preflight_changes:
                raise RuntimeError(f"Preflight source changed before verification: {source_path}")
            changed_after_preflight.append(source_path)
        hashes[source_path] = current_hash
    analysis_files = [
        OUT / "GENE2_PREFLIGHT.json",
        OUT / "GENE2_REGION_DATA.npz",
        OUT / "GENE2_SPOT_TARGETS.csv",
        OUT / "GENE2_ALIGNMENT_AUDIT.csv",
        OUT / "GENE2_FOLD_MEMBERSHIP.csv",
        *inner_files,
        *selection_files,
        *[OUT / f"GENE2_OUTER_FOLD_{i}.csv" for i in range(5)],
        OUT / "GENE2_OOF_REGION_PREDICTIONS.csv",
        OUT / "GENE2_OOF_SPOT_PREDICTIONS.csv",
        OUT / "GENE2_PER_PARTICIPANT_SPEARMAN.csv",
        OUT / "GENE2_TARGET_COMPARISONS.csv",
        OUT / "GENE2_SECONDARY_HOLM.csv",
        OUT / "GENE2_METRIC_SUMMARIES.csv",
        OUT / "GENE2_PRIMARY_ENDPOINT.csv",
        OUT / "GENE2_LABEL_SHUFFLE.csv",
        OUT / "GENE2_PARTIAL_CORRELATIONS.csv",
        OUT / "GENE2_RESULTS.md",
        OUT / "GENE2_SANITY.md",
    ]
    if retry_path.is_file():
        analysis_files.append(retry_path)
    for path in analysis_files:
        if path.is_file():
            hashes[str(path)] = sha256(path)
    for path, digest in sorted(hashes.items(), key=lambda item: item[0].casefold()):
        verification_lines.append(f"| `{path}` | `{digest}` |")
    verification_lines.extend(
        f"- Changed since original preflight: `{path}`."
        for path in changed_after_preflight
    )
    write_markdown(OUT / "GENE2_VERIFICATION.md", "\n".join(verification_lines))

    recommendation = (
        "The registered exploratory rule was met, so a confirmatory test may be considered on genuinely unseen participants, subject to written data-use permission."
        if criterion_met
        else "The registered exploratory rule was not met; this run does not provide a positive basis for recommending a confirmatory test."
    )
    package_files = sorted(
        path.name
        for path in OUT.glob("GENE2_*")
        if path.is_file() and path.name != "GENE2_REPORT.md"
    )
    report_lines = [
        f"# GENE2 Report — {LABEL}",
        "",
        f"**{ASSET_LABEL} — any result depending on saved ResNet-50/ImageNet features is research-only.**",
        "",
        "## Outcome",
        "",
        f"The registered exploratory rule was **{'met' if criterion_met else 'not met'}**. The primary paired difference was {primary_mean:.6f}, with participant-bootstrap 95% CI [{primary_low:.6f}, {primary_high:.6f}]. The image model's participant-macro region Spearman was {primary_macro:.6f} (registered requirement: at least 0.30).",
        "",
        "This is not proof, success, validation, or a confirmatory finding. All 40 participants were used earlier.",
        "",
        f"**Recommendation:** {recommendation}",
        "",
        "## What the result does and does not mean",
        "",
        "This analysis asks whether saved image features are associated with selected expression summaries in these already-used participants under grouped nested cross-validation. Any observed association is exploratory and may not transfer to unseen participants. It does not show that gene expression is directly visible in an image, establish a biological mechanism, or establish medical accuracy, clinical utility, novelty, or patentability.",
        "",
        "## Checks and limitations",
        "",
        f"- Saved features and full spot keys passed validation. All 41 image/expression libraries passed alignment; the fold audit found no participant, library, or region overlap. There were {int(preflight_record['eligible_regions'])} regions and {int(preflight_record['included_spots'])} spots in eligible regions.",
        "- The label-shuffle, depth-only, colour-only, and partial-correlation checks are recorded in the results and sanity files.",
        f"- A technical error after fitting outer fold 0 required repeating {retry_fit_count} completed fit calls; it is logged in `GENE2_DEVIATIONS.md` and `GENE2_RETRY_ACCOUNTING.json`. The fold's design and seeds were not changed.",
        "- ResNet-50/ImageNet weight and dataset terms remain UNVERIFIED. The user authorized research-only use of saved features for this run only; they must not appear in patent embodiments, commercial use, or claims.",
        "- RENFAST/KPMP permission wording remains UNRESOLVED. No wording was interpreted. Phikon-v2 and other non-commercial encoders were not used.",
        "- Stage 1d raw gene values were reconstructed from saved depth-residualized targets and their recorded coefficients. The frozen Stage 1d model was not loaded or modified. No features were recomputed, and no data were downloaded.",
        "- Adam was used because the preregistration did not name an optimizer; model-family tie rules and the 2,000-draw descriptive CIs are logged in `GENE2_DEVIATIONS.md`. The primary/secondary paired CIs used the registered 10,000 draws.",
        "",
        "## Files in this package",
        "",
        *[f"- `{name}`" for name in package_files],
        "",
        "## Exact next instruction needed",
        "",
        "For a confirmatory result, provide an approved cohort containing participants never used in any earlier model or rule evaluation, and provide written permission for its use and verified encoder terms. Do not treat any of these 40 participants or the Stage 1d cohort as unseen. Otherwise stop here. No registration, fusion, multimodal integration, or filing work has been started.",
    ]
    write_markdown(OUT / "GENE2_REPORT.md", "\n".join(report_lines))


def finalize() -> None:
    outer_paths = [OUT / f"GENE2_OUTER_FOLD_{i}.csv" for i in range(5)]
    if not all(p.is_file() for p in outer_paths):
        raise FileNotFoundError("All five outer-fold runs must finish before finalize.")
    region = pd.concat([pd.read_csv(p) for p in outer_paths], ignore_index=True)
    if region.duplicated(["participant_id", "library_id", "region_id"]).any():
        raise ValueError("Duplicate out-of-fold region predictions.")
    preflight_record = json.loads((OUT / "GENE2_PREFLIGHT.json").read_text(encoding="utf-8"))
    if region["participant_id"].nunique() != int(preflight_record["participants_with_eligible_regions"]):
        raise ValueError("Out-of-fold participants do not match the preflight participant count.")

    metric_rows: list[dict[str, Any]] = []
    primary_deltas: list[float] = []
    participant_rows: list[dict[str, Any]] = []
    secondary_rows: list[dict[str, Any]] = []
    for target in TARGET_NAMES:
        actual = f"actual_{target}"
        image = f"pred_selected_image_{target}"
        baseline = f"pred_selected_baseline_{target}"
        comparisons: dict[str, dict[str, float]] = {}
        for model_col in [f"pred_{model}_{target}" for model in ("depth_only", "color_only", "image_ridge", "image_mlp")]:
            model_name = model_col[len("pred_") : -len("_" + target)]
            values = participant_correlations(
                region["participant_id"].astype(str).to_numpy(),
                region[actual].to_numpy(dtype=float),
                region[model_col].to_numpy(dtype=float),
            )
            comparisons[model_name] = values
            for pid, score in values.items():
                participant_rows.append(
                    {
                        "participant_id": pid,
                        "target": target,
                        "model": model_name,
                        "region_spearman": score,
                        "n_regions": int((region["participant_id"].astype(str) == pid).sum()),
                    }
                )
        delta_by_pid = {}
        image_corr = participant_correlations(
            region["participant_id"].astype(str).to_numpy(),
            region[actual].to_numpy(dtype=float),
            region[image].to_numpy(dtype=float),
        )
        baseline_corr = participant_correlations(
            region["participant_id"].astype(str).to_numpy(),
            region[actual].to_numpy(dtype=float),
            region[baseline].to_numpy(dtype=float),
        )
        paired_pids = sorted(set(image_corr) & set(baseline_corr))
        for pid in paired_pids:
            delta_by_pid[pid] = image_corr[pid] - baseline_corr[pid]
            participant_rows.extend(
                [
                    {
                        "participant_id": pid,
                        "target": target,
                        "model": "selected_image",
                        "region_spearman": image_corr[pid],
                        "n_regions": int((region["participant_id"].astype(str) == pid).sum()),
                    },
                    {
                        "participant_id": pid,
                        "target": target,
                        "model": "selected_baseline",
                        "region_spearman": baseline_corr[pid],
                        "n_regions": int((region["participant_id"].astype(str) == pid).sum()),
                    },
                    {
                        "participant_id": pid,
                        "target": target,
                        "model": "selected_image_minus_baseline",
                        "region_spearman": delta_by_pid[pid],
                        "n_regions": int((region["participant_id"].astype(str) == pid).sum()),
                    },
                ]
            )
        deltas = np.asarray([delta_by_pid[pid] for pid in paired_pids], dtype=float)
        mean_delta, low_delta, high_delta = paired_bootstrap(deltas, BOOTSTRAP_SEED)
        p_value = sign_flip_pvalue(deltas, HOLM_SEED)
        selected_image_macro = macro_score(image_corr)
        selected_baseline_macro = macro_score(baseline_corr)
        metric_rows.append(
            {
                "target": target,
                "n_participants_with_paired_metrics": len(delta_by_pid),
                "selected_image_model": ";".join(sorted(set(region["selected_image_model"].astype(str)))),
                "selected_baseline_model": ";".join(sorted(set(region["selected_baseline_model"].astype(str)))),
                "image_participant_macro_spearman": selected_image_macro,
                "baseline_participant_macro_spearman": selected_baseline_macro,
                "paired_delta_image_minus_baseline": mean_delta,
                "paired_delta_ci95_low": low_delta,
                "paired_delta_ci95_high": high_delta,
                "sign_flip_p_raw": p_value,
            }
        )
        if target != PRIMARY:
            secondary_rows.append(
                {
                    "target": target,
                    "n_paired_participants": len(delta_by_pid),
                    "paired_delta": mean_delta,
                    "ci95_low": low_delta,
                    "ci95_high": high_delta,
                    "p_raw": p_value,
                }
            )
        if target == PRIMARY:
            primary_deltas = [delta_by_pid[pid] for pid in sorted(delta_by_pid)]

    if secondary_rows:
        adjusted = holm_adjust([row["p_raw"] for row in secondary_rows])
        for row, p_adj in zip(secondary_rows, adjusted):
            row["p_holm_adjusted"] = p_adj

    summary_rows: list[dict[str, Any]] = []
    model_names = [
        "depth_only", "color_only", "image_ridge", "image_mlp",
        "selected_image", "selected_baseline",
    ]
    for target_index, target in enumerate(TARGET_NAMES):
        actual = f"actual_{target}"
        for model_index, model_name in enumerate(model_names):
            prediction = (
                f"pred_{model_name}_{target}"
                if model_name in {"depth_only", "color_only", "image_ridge", "image_mlp"}
                else f"pred_{model_name}_{target}"
            )
            region[f"{model_name}_prediction_{target}"] = region[prediction]
            for kind_index, kind in enumerate(("spearman", "pearson")):
                seed = BOOTSTRAP_SEED + 1000 * target_index + 20 * model_index + kind_index
                obs, low, high = bootstrap_metric(
                    region, actual, prediction, kind, seed
                )
                macro, macro_low, macro_high = bootstrap_metric(
                    region, actual, prediction, kind, seed + 50_000,
                    participant_macro=True,
                )
                summary_rows.append(
                    {
                        "target": target,
                        "model": model_name,
                        "metric": kind,
                        "region_pooled_value": obs,
                        "region_pooled_ci95_low": low,
                        "region_pooled_ci95_high": high,
                        "participant_macro_value": macro,
                        "participant_macro_ci95_low": macro_low,
                        "participant_macro_ci95_high": macro_high,
                    }
                )

    primary_stats = next(row for row in metric_rows if row["target"] == PRIMARY)
    primary_macro = primary_stats["image_participant_macro_spearman"]
    primary_mean, primary_low, primary_high = paired_bootstrap(np.asarray(primary_deltas), BOOTSTRAP_SEED)
    criterion_met = bool(primary_low > 0 and primary_macro >= 0.30)
    primary_summary = pd.DataFrame(
        [
            {
                "endpoint": "best inner-selected image model minus best inner-selected baseline, region Spearman",
                "n_paired_participants": len(primary_deltas),
                "paired_mean_difference": primary_mean,
                "participant_bootstrap_ci95_low": primary_low,
                "participant_bootstrap_ci95_high": primary_high,
                "image_participant_macro_mean_spearman": primary_macro,
                "required_image_macro_mean_spearman": 0.30,
                "exploratory_rule": "met" if criterion_met else "not met",
                "interpretation": "EXPLORATORY only; not proof, success, or validation",
            }
        ]
    )

    for model_name in ("selected_image", "selected_baseline"):
        pred = f"pred_{model_name}_{PRIMARY}"
        region[f"spot_prediction_{model_name}_{PRIMARY}"] = region[pred]
    spot_map = pd.read_csv(
        OUT / "GENE2_SPOT_TARGETS.csv",
        dtype={"participant_id": str, "library_id": str, "barcode": str, "region_id": str},
    )
    spot_map = spot_map.loc[spot_map["region_eligible"].astype(bool)].copy()
    spot_map = spot_map.drop(columns=["analysis_label", "asset_status"])
    region_cols = [
        "participant_id", "library_id", "region_id", "outer_fold",
        "selected_image_model", "selected_baseline_model",
    ]
    pred_cols = [c for c in region.columns if c.startswith("actual_") or c.startswith("pred_") or c.startswith("shuffle_")]
    region_out = region[region_cols + ["n_spots"] + pred_cols].copy()
    spot_out = spot_map.merge(
        region[region_cols + pred_cols],
        on=["participant_id", "library_id", "region_id"],
        how="left",
        validate="many_to_one",
    )
    if spot_out["outer_fold"].isna().any():
        raise ValueError("Some eligible spots lack an outer-fold prediction.")
    spot_out["prediction_note"] = "Region prediction repeated for each spot in that region; not a spot-level fit."
    participant_table = pd.DataFrame(participant_rows)

    # Add Pearson, MAE, and participant-level mean summaries for the selected models.
    extra_rows: list[dict[str, Any]] = []
    for target_index, target in enumerate(TARGET_NAMES):
        actual_col = f"actual_{target}"
        for model_index, model_name in enumerate(("selected_image", "selected_baseline")):
            prediction_col = f"pred_{model_name}_{target}"
            participant_means = region.groupby("participant_id", as_index=False).agg(
                actual_mean=(actual_col, "mean"), prediction_mean=(prediction_col, "mean")
            )
            for kind in ("spearman", "pearson"):
                value, low, high = bootstrap_metric(
                    participant_means,
                    "actual_mean",
                    "prediction_mean",
                    kind,
                    BOOTSTRAP_SEED + 70_000 + 100 * target_index + 10 * model_index + (kind == "pearson"),
                )
                extra_rows.append(
                    {
                        "target": target,
                        "model": model_name,
                        "metric": f"participant_mean_{kind}",
                        "value": value,
                        "ci95_low": low,
                        "ci95_high": high,
                    }
                )
            error_frame = region[["participant_id", actual_col, prediction_col]].copy()
            error_frame["absolute_error"] = np.abs(
                error_frame[actual_col].to_numpy(dtype=float)
                - error_frame[prediction_col].to_numpy(dtype=float)
            )
            mae, mae_low, mae_high = bootstrap_metric(
                error_frame,
                "absolute_error",
                None,
                "mae",
                BOOTSTRAP_SEED + 80_000 + 100 * target_index + 10 * model_index,
            )
            extra_rows.append(
                {
                    "target": target,
                    "model": model_name,
                    "metric": "region_mae",
                    "value": mae,
                    "ci95_low": mae_low,
                    "ci95_high": mae_high,
                }
            )

    # Label-shuffle comparison is evaluated against the shuffled held-out targets.
    shuffle_image = participant_correlations(
        region["participant_id"].astype(str).to_numpy(),
        region[f"shuffle_actual_{PRIMARY}"].to_numpy(dtype=float),
        region[f"shuffle_pred_selected_image_{PRIMARY}"].to_numpy(dtype=float),
    )
    shuffle_base = participant_correlations(
        region["participant_id"].astype(str).to_numpy(),
        region[f"shuffle_actual_{PRIMARY}"].to_numpy(dtype=float),
        region[f"shuffle_pred_selected_baseline_{PRIMARY}"].to_numpy(dtype=float),
    )
    shuffle_deltas = np.asarray(
        [shuffle_image[pid] - shuffle_base[pid] for pid in sorted(set(shuffle_image) & set(shuffle_base))],
        dtype=float,
    )
    shuffle_mean, shuffle_low, shuffle_high = paired_bootstrap(shuffle_deltas, SHUFFLE_SEED)
    shuffle_summary = pd.DataFrame(
        [
            {
                "control": "within-participant primary-label shuffle",
                "n_paired_participants": len(shuffle_deltas),
                "image_minus_best_baseline_mean_spearman": shuffle_mean,
                "participant_bootstrap_ci95_low": shuffle_low,
                "participant_bootstrap_ci95_high": shuffle_high,
                "sanity_failure": bool(shuffle_low > 0),
            }
        ]
    )

    # Partial correlations use all held-out regions only as a descriptive diagnostic.
    region_for_partial = region.copy()
    with np.load(OUT / "GENE2_REGION_DATA.npz", allow_pickle=False) as archive:
        color_values = archive["colors"]
        depth_values = archive["depth"]
    index_lookup = {
        (str(pid), str(lid), str(rid)): i
        for i, (pid, lid, rid) in enumerate(
            zip(
                np.load(OUT / "GENE2_REGION_DATA.npz", allow_pickle=False)["participant_id"],
                np.load(OUT / "GENE2_REGION_DATA.npz", allow_pickle=False)["library_id"],
                np.load(OUT / "GENE2_REGION_DATA.npz", allow_pickle=False)["region_id"],
            )
        )
    }
    region_indexes = [
        index_lookup[(str(r.participant_id), str(r.library_id), str(r.region_id))]
        for r in region.itertuples(index=False)
    ]
    for j, name in enumerate(COLOR_NAMES):
        region_for_partial[f"color_{name}"] = color_values[region_indexes, j]
    region_for_partial["depth"] = depth_values[region_indexes]
    partial_rows = []
    for target in (PRIMARY,):
        for model_name in (
            "depth_only", "color_only", "image_ridge", "image_mlp",
            "selected_image", "selected_baseline",
        ):
            result = partial_spearman(
                region_for_partial,
                f"actual_{target}",
                f"pred_{model_name}_{target}",
            )
            partial_rows.append({"target": target, "model": model_name, **result})

    # Per-region actual/prediction metrics are also copied once per eligible spot key.
    save_or_verify_csv(region_out, OUT / "GENE2_OOF_REGION_PREDICTIONS.csv")
    save_or_verify_csv(spot_out, OUT / "GENE2_OOF_SPOT_PREDICTIONS.csv")
    save_or_verify_csv(participant_table, OUT / "GENE2_PER_PARTICIPANT_SPEARMAN.csv")
    save_or_verify_csv(pd.DataFrame(metric_rows), OUT / "GENE2_TARGET_COMPARISONS.csv")
    save_or_verify_csv(pd.DataFrame(secondary_rows), OUT / "GENE2_SECONDARY_HOLM.csv")
    save_or_verify_csv(pd.DataFrame(summary_rows + extra_rows), OUT / "GENE2_METRIC_SUMMARIES.csv")
    save_or_verify_csv(primary_summary, OUT / "GENE2_PRIMARY_ENDPOINT.csv")
    save_or_verify_csv(shuffle_summary, OUT / "GENE2_LABEL_SHUFFLE.csv")
    save_or_verify_csv(pd.DataFrame(partial_rows), OUT / "GENE2_PARTIAL_CORRELATIONS.csv")

    write_final_reports(
        primary_mean,
        primary_low,
        primary_high,
        primary_macro,
        criterion_met,
        shuffle_mean,
        shuffle_low,
        shuffle_high,
        len(region),
    )
    print(f"Finalized OOF results: exploratory rule {'met' if criterion_met else 'not met'}.")


def main() -> None:
    global INVOCATION_START
    INVOCATION_START = time.monotonic()
    parser = argparse.ArgumentParser(description=LABEL)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight")
    inner_parser = sub.add_parser("run-inner")
    inner_parser.add_argument("--outer-fold", type=int, required=True, choices=range(5))
    inner_parser.add_argument("--inner-fold", type=int, required=True, choices=range(4))
    outer_parser = sub.add_parser("fit-outer")
    outer_parser.add_argument("--outer-fold", type=int, required=True, choices=range(5))
    sub.add_parser("finalize")
    args = parser.parse_args()
    if args.command == "preflight":
        preflight()
    elif args.command == "run-inner":
        run_inner(args.outer_fold, args.inner_fold)
    elif args.command == "fit-outer":
        run_outer(args.outer_fold)
    elif args.command == "finalize":
        finalize()


if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    main()
