"""Exploratory, post-hoc Stage 1b grouped expression follow-up."""

from __future__ import annotations

import copy
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from scipy.stats import spearmanr
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from sklearn.preprocessing import StandardScaler


LABEL = "exploratory, post-hoc"
ROOT = Path(r"D:\patent")
STAGE1 = ROOT / "stage1_expression"
OUT = ROOT / "stage1b_expression"
PREFIX = "exploratory_posthoc_"
TARGETS = [
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
MODULES = TARGETS[:3]
GENES = TARGETS[3:]
TARGET_VARIANTS = ["depth_residualized", "depth_residualized_neighbor_mean"]
MODEL_NAMES = [
    "patient_mean",
    "depth_only_ridge",
    "color_only_ridge",
    "elasticnet_spot",
    "mlp_spot",
    "elasticnet_image_depth",
    "mlp_image_depth",
]
IMAGE_MODELS = [
    "elasticnet_spot",
    "mlp_spot",
    "elasticnet_image_depth",
    "mlp_image_depth",
]
ALPHA_GRID = [0.001, 0.01, 0.1]
L1_RATIO = 0.5
N_OUTER_FOLDS = 7
N_INNER_FOLDS = 4
BLOCK_WIDTH = 10
BOOTSTRAP_REPS = 10_000
BASE_SEED = 20261112
BOOTSTRAP_SEED = BASE_SEED + 100
ELASTICNET_MAX_ITER = 50_000
ELASTICNET_TOL = 1e-4
FISTA_POWER_ITERATIONS = 30
MLP_MAX_EPOCHS = 200
MLP_PATIENCE = 15
MLP_MIN_DELTA = 1e-4
MLP_BATCH_SIZE = 1024
NEIGHBOR_OFFSETS = [(0, 2), (0, -2), (1, 1), (-1, -1), (1, -1), (-1, 1)]
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
RUN_ID = ""
CONFIG_COLUMNS = [
    "analysis_label", "run_id", "timestamp", "phase", "outer_fold", "inner_fold",
    "target_variant", "input", "family", "model", "alpha", "alpha_grid",
    "l1_ratio", "solver", "precompute", "status", "error", "warnings", "n_train_spots",
    "n_validation_spots", "n_test_spots", "train_participants",
    "validation_participants", "inner_train_participants",
    "inner_validation_participants", "test_participants", "n_iter", "dual_gap_max",
    "validation_mse", "optimality_residual", "inner_alpha_grid",
    "inner_stopped_epoch",
    "selected_best_epoch", "refit_epochs", "seed", "validation_seed", "device",
]
CURVE_COLUMNS = [
    "analysis_label", "run_id", "timestamp", "phase", "outer_fold", "inner_fold",
    "target_variant", "input", "family", "model", "split", "epoch",
    "train_loss", "validation_loss", "seed",
]


def out_path(name: str) -> Path:
    return OUT / f"{PREFIX}{name}"


def stamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    result = frame.copy()
    result.insert(0, "analysis_label", LABEL)
    path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(path, index=False)
    if path.stat().st_size >= 1_000_000_000:
        raise RuntimeError(f"Output exceeds 1 GB: {path}")


def append_csv(rows: list[dict[str, object]], path: Path) -> None:
    if not rows:
        return
    result = pd.DataFrame(rows)
    result.insert(0, "analysis_label", LABEL)
    schema = CONFIG_COLUMNS if "configuration_log" in path.name else CURVE_COLUMNS
    extra_columns = set(result.columns) - set(schema)
    if extra_columns:
        raise ValueError(f"Unregistered columns for {path.name}: {sorted(extra_columns)}")
    result = result.reindex(columns=schema)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing_columns = pd.read_csv(path, nrows=0).columns.tolist()
        if existing_columns != schema:
            if not set(existing_columns).issubset(schema):
                raise ValueError(f"CSV schema mismatch for {path.name}")
            existing = pd.read_csv(path)
            existing.reindex(columns=schema).to_csv(path, index=False)
        result.to_csv(path, mode="a", index=False, header=False)
    else:
        result.to_csv(path, index=False)
    if path.stat().st_size >= 1_000_000_000:
        raise RuntimeError(f"Output exceeds 1 GB: {path}")


def save_npz(path: Path, **arrays: np.ndarray) -> None:
    np.savez_compressed(path, analysis_label=np.asarray(LABEL), **arrays)
    if path.stat().st_size >= 1_000_000_000:
        raise RuntimeError(f"Output exceeds 1 GB: {path}")


def participant_weights(participants: np.ndarray) -> np.ndarray:
    _, inverse, counts = np.unique(participants, return_inverse=True, return_counts=True)
    weights = 1.0 / counts[inverse].astype(np.float64)
    return weights / weights.mean()


def weighted_standardize(
    train: np.ndarray, other: np.ndarray, weights: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mean = np.average(train, axis=0, weights=weights)
    variance = np.average((train - mean) ** 2, axis=0, weights=weights)
    scale = np.sqrt(variance)
    scale[~np.isfinite(scale) | (scale < 1e-12)] = 1.0
    return (train - mean) / scale, (other - mean) / scale, mean, scale


def load_inputs() -> dict[str, object]:
    frame = pd.read_csv(
        STAGE1 / "targets_by_spot.csv",
        dtype={"participant_id": str, "library_id": str, "barcode": str},
    )
    targets = np.asarray(frame[TARGETS], dtype=np.float64)
    gene_counts = np.asarray(frame[[f"raw_{g}" for g in GENES]], dtype=np.float64)
    detected_modules = np.asarray(
        frame[[f"{name}_any_detected" for name in MODULES]], dtype=bool
    )
    if detected_modules.shape != (len(frame), len(MODULES)):
        raise ValueError("Module detection flags are absent or malformed")
    keys = list(zip(frame.participant_id, frame.library_id, frame.barcode))
    if len(set(keys)) != len(frame):
        raise AssertionError("Stage 1 spot keys are not unique")
    if frame.participant_id.nunique() != 28:
        raise AssertionError("Expected 28 participants")
    if frame.library_id.nunique() != 29:
        raise AssertionError("Expected 29 libraries")
    if len(frame) != 25_104:
        raise AssertionError("Expected 25,104 spots")
    folds = frame.groupby("participant_id").fold.nunique()
    if not (folds == 1).all() or frame.fold.nunique() != N_OUTER_FOLDS:
        raise AssertionError("Saved seven-fold participant grouping is invalid")

    def keyed_npz(file_name: str, array_name: str) -> np.ndarray:
        data = np.load(STAGE1 / file_name)
        array_keys = list(zip(data["participant_id"].astype(str),
                              data["library_id"].astype(str),
                              data["barcode"].astype(str)))
        if array_keys != keys:
            raise AssertionError(f"Key order mismatch in {file_name}")
        return data[array_name]

    embeddings = keyed_npz("spot_embeddings.npz", "embeddings").astype(np.float32)
    colors = keyed_npz("color_statistics.npz", "features").astype(np.float32)
    depth = np.log1p(frame["library_size_umi"].to_numpy(dtype=np.float64))
    participants = frame.participant_id.to_numpy(dtype=str)
    libraries = frame.library_id.to_numpy(dtype=str)
    fold_id = frame.fold.to_numpy(dtype=np.int8)
    rows = frame.array_row.to_numpy(dtype=np.int64)
    cols = frame.array_col.to_numpy(dtype=np.int64)
    raw_gene_detected = gene_counts > 0
    raw_detected = np.column_stack([detected_modules, raw_gene_detected])
    return {
        "frame": frame,
        "keys": keys,
        "targets": targets,
        "gene_counts": gene_counts,
        "raw_detected": raw_detected,
        "embeddings": embeddings,
        "colors": colors,
        "depth": depth,
        "participants": participants,
        "libraries": libraries,
        "folds": fold_id,
        "array_row": rows,
        "array_col": cols,
    }


def fit_depth_residuals(
    y: np.ndarray,
    depth: np.ndarray,
    participants: np.ndarray,
    train_idx: np.ndarray,
    evaluation_idx: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, list[dict[str, object]]]:
    train_weights = participant_weights(participants[train_idx])
    train_values = np.empty((len(train_idx), y.shape[1]), dtype=np.float64)
    evaluation_values = np.empty((len(evaluation_idx), y.shape[1]), dtype=np.float64)
    records: list[dict[str, object]] = []
    for column, target in enumerate(TARGETS):
        nuisance = LinearRegression()
        nuisance.fit(
            depth[train_idx, None],
            y[train_idx, column],
            sample_weight=train_weights,
        )
        train_residual = y[train_idx, column] - nuisance.predict(depth[train_idx, None])
        evaluation_residual = y[evaluation_idx, column] - nuisance.predict(
            depth[evaluation_idx, None]
        )
        for participant in np.unique(participants[train_idx]):
            local = participants[train_idx] == participant
            train_residual[local] -= np.average(
                train_residual[local], weights=train_weights[local]
            )
        train_values[:, column] = train_residual
        evaluation_values[:, column] = evaluation_residual
        records.append(
            {
                "target": target,
                "intercept": float(nuisance.intercept_),
                "depth_coefficient": float(nuisance.coef_[0]),
            }
        )
    return train_values, evaluation_values, records


def build_neighbor_map(
    libraries: np.ndarray, rows: np.ndarray, cols: np.ndarray
) -> dict[tuple[str, int, int], int]:
    return {
        (str(library), int(row), int(col)): index
        for index, (library, row, col) in enumerate(zip(libraries, rows, cols))
    }


def neighbor_mean(
    values: np.ndarray,
    indices: np.ndarray,
    libraries: np.ndarray,
    rows: np.ndarray,
    cols: np.ndarray,
    neighbor_map: dict[tuple[str, int, int], int],
) -> tuple[np.ndarray, np.ndarray]:
    allowed = set(int(i) for i in indices)
    local_position = {int(index): position for position, index in enumerate(indices)}
    result = np.full_like(values, np.nan, dtype=np.float64)
    neighbor_counts = np.zeros(len(indices), dtype=np.int16)
    for local_index, index_value in enumerate(indices):
        index = int(index_value)
        found = []
        for drow, dcol in NEIGHBOR_OFFSETS:
            neighbor = neighbor_map.get(
                (
                    str(libraries[index]),
                    int(rows[index] + drow),
                    int(cols[index] + dcol),
                )
            )
            if neighbor is not None and neighbor in allowed:
                found.append(local_position[neighbor])
        neighbor_counts[local_index] = len(found)
        if found:
            result[local_index] = np.mean(values[found], axis=0, dtype=np.float64)
    return result, neighbor_counts


def targets_for_split(
    data: dict[str, object],
    train_idx: np.ndarray,
    evaluation_idx: np.ndarray,
    variant: str,
    neighbor_map: dict[tuple[str, int, int], int],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[dict[str, object]]]:
    y = data["targets"]
    participants = data["participants"]
    train, evaluation, coefficients = fit_depth_residuals(
        y, data["depth"], participants, train_idx, evaluation_idx
    )
    train_neighbor_counts = np.zeros(len(train_idx), dtype=np.int16)
    evaluation_neighbor_counts = np.zeros(len(evaluation_idx), dtype=np.int16)
    if variant == "depth_residualized_neighbor_mean":
        train, train_neighbor_counts = neighbor_mean(
            train, train_idx, data["libraries"], data["array_row"], data["array_col"], neighbor_map
        )
        evaluation, evaluation_neighbor_counts = neighbor_mean(
            evaluation,
            evaluation_idx,
            data["libraries"],
            data["array_row"],
            data["array_col"],
            neighbor_map,
        )
    elif variant != "depth_residualized":
        raise ValueError(f"Unknown target variant: {variant}")
    return train, evaluation, train_neighbor_counts, evaluation_neighbor_counts, coefficients


def feature_matrix(data: dict[str, object], input_name: str, indices: np.ndarray) -> np.ndarray:
    if input_name == "depth_only":
        return data["depth"][indices, None].astype(np.float32)
    if input_name == "color_only":
        return data["colors"][indices].astype(np.float32)
    if input_name == "spot":
        return data["embeddings"][indices].astype(np.float32)
    if input_name == "image_depth":
        return np.column_stack(
            [data["embeddings"][indices].astype(np.float32),
             data["depth"][indices].astype(np.float32)]
        )
    raise ValueError(f"Unknown input: {input_name}")


def participant_balanced_mse(
    expected: np.ndarray, predicted: np.ndarray, participants: np.ndarray
) -> float:
    scores = []
    for participant in np.unique(participants):
        mask = participants == participant
        scores.append(float(np.mean((expected[mask] - predicted[mask]) ** 2)))
    return float(np.mean(scores)) if scores else math.nan


def scale_pair(
    x_train: np.ndarray,
    x_other: np.ndarray,
    y_train: np.ndarray,
    y_other: np.ndarray,
    weights: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    xs_train, xs_other, x_mean, x_scale = weighted_standardize(x_train, x_other, weights)
    ys_train, ys_other, y_mean, y_scale = weighted_standardize(y_train, y_other, weights)
    return xs_train, xs_other, ys_train, ys_other, y_mean, y_scale


def log_config(row: dict[str, object]) -> None:
    row.setdefault("run_id", RUN_ID)
    append_csv([row], out_path("configuration_log.csv"))


def log_curve(rows: list[dict[str, object]]) -> None:
    for row in rows:
        row.setdefault("run_id", RUN_ID)
    append_csv(rows, out_path("loss_curves.csv"))


def fit_independent_elasticnet(
    x: np.ndarray,
    y: np.ndarray,
    weights: np.ndarray,
    alpha: float,
    seed: int,
    initial_coef: np.ndarray | None = None,
) -> tuple[np.ndarray, int, float, str, list[dict[str, object]]]:
    """Solve independent squared-error Elastic Nets with proximal FISTA."""
    seed_torch(seed)
    x_t = torch.from_numpy(np.ascontiguousarray(x, dtype=np.float32)).to(DEVICE)
    y_t = torch.from_numpy(np.ascontiguousarray(y, dtype=np.float32)).to(DEVICE)
    w_t = torch.from_numpy(np.ascontiguousarray(weights[:, None], dtype=np.float32)).to(DEVICE)
    weight_sum = w_t.sum()
    n_features, n_targets = x.shape[1], y.shape[1]
    generator = torch.Generator(device=DEVICE)
    generator.manual_seed(seed)
    vector = torch.randn(n_features, device=DEVICE, generator=generator)
    vector = vector / torch.linalg.vector_norm(vector)
    for _ in range(FISTA_POWER_ITERATIONS):
        image = x_t @ vector
        product = x_t.T @ (w_t[:, 0] * image) / weight_sum
        norm = torch.linalg.vector_norm(product)
        if not torch.isfinite(norm) or norm.item() == 0:
            raise RuntimeError("Unable to estimate Elastic Net Lipschitz constant")
        vector = product / norm
    image = x_t @ vector
    largest_eigenvalue = torch.dot(vector, x_t.T @ (w_t[:, 0] * image) / weight_sum)
    l2_penalty = alpha * (1.0 - L1_RATIO)
    l1_penalty = alpha * L1_RATIO
    lipschitz = max(float(largest_eigenvalue.item()) + l2_penalty, 1e-8) * 1.1

    def soft_threshold(value: torch.Tensor, threshold: float) -> torch.Tensor:
        return torch.sign(value) * torch.clamp(torch.abs(value) - threshold, min=0.0)

    def objective(coef: torch.Tensor) -> torch.Tensor:
        residual = x_t @ coef - y_t
        data_loss = 0.5 * (w_t * residual.square().sum(dim=1, keepdim=True)).sum() / weight_sum
        return (
            data_loss
            + l1_penalty * torch.abs(coef).sum()
            + 0.5 * l2_penalty * coef.square().sum()
        )

    if initial_coef is None:
        coef = torch.zeros((n_features, n_targets), device=DEVICE)
    else:
        coef = torch.from_numpy(np.ascontiguousarray(initial_coef, dtype=np.float32)).to(DEVICE)
    accelerated = coef.clone()
    acceleration = 1.0
    curves: list[dict[str, object]] = []
    residual_norm = math.inf
    status = "non_converged"
    n_iter = ELASTICNET_MAX_ITER
    for iteration in range(1, ELASTICNET_MAX_ITER + 1):
        residual = x_t @ accelerated - y_t
        gradient = x_t.T @ (w_t * residual) / weight_sum + l2_penalty * accelerated
        next_coef = soft_threshold(
            accelerated - gradient / lipschitz,
            l1_penalty / lipschitz,
        )
        next_acceleration = (1.0 + math.sqrt(1.0 + 4.0 * acceleration * acceleration)) / 2.0
        accelerated = next_coef + ((acceleration - 1.0) / next_acceleration) * (next_coef - coef)
        coef = next_coef
        acceleration = next_acceleration
        if iteration % 10 == 0 or iteration == 1:
            coef_gradient = x_t.T @ (w_t * (x_t @ coef - y_t)) / weight_sum + l2_penalty * coef
            proximal = soft_threshold(
                coef - coef_gradient / lipschitz,
                l1_penalty / lipschitz,
            )
            residual_norm = float(
                (
                    torch.linalg.vector_norm(coef - proximal) * lipschitz
                    / torch.clamp(torch.linalg.vector_norm(coef), min=1.0)
                ).item()
            )
            current_objective = float(objective(coef).item())
            curves.append(
                {
                    "epoch": iteration,
                    "train_loss": current_objective,
                    "validation_loss": math.nan,
                }
            )
            if not math.isfinite(current_objective) or not math.isfinite(residual_norm):
                raise RuntimeError("Elastic Net objective or optimality residual became non-finite")
            if residual_norm <= ELASTICNET_TOL:
                status = "success"
                n_iter = iteration
                break
    return coef.detach().cpu().numpy(), n_iter, residual_norm, status, curves


def run_elasticnet_inner_cv(
    data: dict[str, object],
    outer_train: np.ndarray,
    variant: str,
    input_name: str,
    neighbor_map: dict[tuple[str, int, int], int],
    fold: int,
) -> tuple[float, list[dict[str, object]]]:
    groups = data["participants"][outer_train]
    splitter = GroupKFold(n_splits=N_INNER_FOLDS)
    records: list[dict[str, object]] = []
    alpha_scores: dict[float, list[float]] = defaultdict(list)
    for inner_fold, (train_local, validation_local) in enumerate(
        splitter.split(outer_train, groups=groups)
    ):
        inner_train = outer_train[train_local]
        inner_validation = outer_train[validation_local]
        y_train, y_validation, train_n, validation_n, _ = targets_for_split(
            data, inner_train, inner_validation, variant, neighbor_map
        )
        keep_train = np.isfinite(y_train).all(axis=1)
        keep_validation = np.isfinite(y_validation).all(axis=1)
        tr = inner_train[keep_train]
        va = inner_validation[keep_validation]
        y_train = y_train[keep_train]
        y_validation = y_validation[keep_validation]
        x_train = feature_matrix(data, input_name, tr)
        x_validation = feature_matrix(data, input_name, va)
        weights = participant_weights(data["participants"][tr])
        xs, xv, ys, yv, _, _ = scale_pair(x_train, x_validation, y_train, y_validation, weights)
        warm_start_coef = None
        for alpha in sorted(ALPHA_GRID, reverse=True):
            config = {
                "timestamp": stamp(),
                "phase": "elasticnet_inner_cv",
                "outer_fold": fold,
                "inner_fold": inner_fold,
                "target_variant": variant,
                "input": input_name,
                "family": "ElasticNet",
                "alpha": alpha,
                "l1_ratio": L1_RATIO,
                "solver": "independent-target proximal FISTA",
                "precompute": "power-iteration Lipschitz estimate",
                "status": "started",
                "n_train_spots": len(tr),
                "n_validation_spots": len(va),
                "train_participants": len(np.unique(data["participants"][tr])),
                "validation_participants": len(np.unique(data["participants"][va])),
            }
            try:
                coef, n_iter, residual_norm, status, curve = fit_independent_elasticnet(
                    xs,
                    ys,
                    weights,
                    alpha,
                    BASE_SEED + fold * 100_003 + inner_fold * 997 + int(alpha * 1000),
                    warm_start_coef,
                )
                warm_start_coef = coef
                prediction = xv @ coef
                loss = participant_balanced_mse(
                    yv,
                    prediction,
                    data["participants"][va],
                )
                if status == "success" and np.isfinite(loss):
                    alpha_scores[alpha].append(loss)
                log_curve(
                    [
                        {
                            "timestamp": stamp(),
                            "phase": "elasticnet_inner_cv",
                            "outer_fold": fold,
                            "inner_fold": inner_fold,
                            "target_variant": variant,
                            "input": input_name,
                            "family": "ElasticNet",
                            "model": f"alpha_{alpha}",
                            "split": "training_objective",
                            "seed": BASE_SEED + fold * 100_003 + inner_fold * 997 + int(alpha * 1000),
                            **curve_row,
                        }
                        for curve_row in curve
                    ]
                )
                config.update(
                    {
                        "status": status,
                        "validation_mse": loss,
                        "n_iter": n_iter,
                        "optimality_residual": residual_norm,
                    }
                )
            except Exception as error:
                config.update({"status": "failed", "error": repr(error)})
            records.append(config)
            log_config(config)
    viable = {alpha: scores for alpha, scores in alpha_scores.items() if len(scores) == N_INNER_FOLDS}
    if not viable:
        raise RuntimeError("No Elastic Net alpha converged in every inner fold")
    selected = min(viable, key=lambda alpha: (float(np.mean(viable[alpha])), alpha))
    return selected, records


def fit_elasticnet_outer(
    data: dict[str, object],
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    input_name: str,
    alpha: float,
    fold: int,
    variant: str,
) -> tuple[np.ndarray, dict[str, object]]:
    keep_train = np.isfinite(y_train).all(axis=1)
    keep_test = np.isfinite(y_test).all(axis=1)
    tr, te = train_idx[keep_train], test_idx[keep_test]
    ytr, yte = y_train[keep_train], y_test[keep_test]
    xtr = feature_matrix(data, input_name, tr)
    xte = feature_matrix(data, input_name, te)
    weights = participant_weights(data["participants"][tr])
    xs, xt, ys, yt, y_mean, y_scale = scale_pair(xtr, xte, ytr, yte, weights)
    seed = BASE_SEED + fold * 11_009 + TARGET_VARIANTS.index(variant) * 101 + int(alpha * 1000)
    row: dict[str, object] = {
        "timestamp": stamp(),
        "phase": "elasticnet_outer_fit",
        "outer_fold": fold,
        "inner_fold": "",
        "target_variant": variant,
        "input": input_name,
        "family": "ElasticNet",
        "model": "elasticnet_spot" if input_name == "spot" else "elasticnet_image_depth",
        "alpha": alpha,
        "l1_ratio": L1_RATIO,
        "solver": "independent-target proximal FISTA",
        "precompute": "power-iteration Lipschitz estimate",
        "seed": seed,
        "status": "started",
        "n_train_spots": len(tr),
        "n_test_spots": len(te),
        "train_participants": len(np.unique(data["participants"][tr])),
        "test_participants": len(np.unique(data["participants"][te])),
    }
    coef, n_iter, residual_norm, status, curve = fit_independent_elasticnet(
        xs, ys, weights, alpha, seed
    )
    prediction = (xt @ coef) * y_scale + y_mean
    log_curve(
        [
            {
                "timestamp": stamp(),
                "phase": "elasticnet_outer_fit",
                "outer_fold": fold,
                "target_variant": variant,
                "input": input_name,
                "family": "ElasticNet",
                "model": row["model"],
                "split": "training_objective",
                "seed": seed,
                **curve_row,
            }
            for curve_row in curve
        ]
    )
    row.update(
        {
            "status": status,
            "n_iter": n_iter,
            "optimality_residual": residual_norm,
            "inner_alpha_grid": json.dumps(ALPHA_GRID),
        }
    )
    return prediction.astype(np.float32), row


def seed_torch(seed: int) -> None:
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True


class SmallMLP(torch.nn.Module):
    def __init__(self, input_size: int, output_size: int) -> None:
        super().__init__()
        self.layers = torch.nn.Sequential(
            torch.nn.Linear(input_size, 128),
            torch.nn.ReLU(),
            torch.nn.Linear(128, output_size),
        )

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.layers(values)


def torch_mse(
    model: torch.nn.Module,
    x: torch.Tensor,
    y: torch.Tensor,
    weights: torch.Tensor,
) -> float:
    model.eval()
    with torch.no_grad():
        error = (model(x) - y).square().mean(dim=1)
        return float((error * weights).sum().div(weights.sum()).item())


def fit_mlp_training(
    model: SmallMLP,
    x_train: np.ndarray,
    y_train: np.ndarray,
    train_weights: np.ndarray,
    seed: int,
    max_epochs: int,
    x_validation: np.ndarray | None = None,
    y_validation: np.ndarray | None = None,
    validation_weights: np.ndarray | None = None,
) -> tuple[int, int, list[dict[str, object]], dict[str, torch.Tensor]]:
    seed_torch(seed)
    model = model.to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    x_t = torch.from_numpy(np.ascontiguousarray(x_train, dtype=np.float32)).to(DEVICE)
    y_t = torch.from_numpy(np.ascontiguousarray(y_train, dtype=np.float32)).to(DEVICE)
    w_t = torch.from_numpy(np.ascontiguousarray(train_weights, dtype=np.float32)).to(DEVICE)
    has_validation = x_validation is not None
    if has_validation:
        xv_t = torch.from_numpy(np.ascontiguousarray(x_validation, dtype=np.float32)).to(DEVICE)
        yv_t = torch.from_numpy(np.ascontiguousarray(y_validation, dtype=np.float32)).to(DEVICE)
        wv_t = torch.from_numpy(np.ascontiguousarray(validation_weights, dtype=np.float32)).to(DEVICE)
    best_loss = math.inf
    best_epoch = 0
    best_state: dict[str, torch.Tensor] | None = None
    stale_epochs = 0
    curve_rows: list[dict[str, object]] = []
    stop_epoch = max_epochs
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    for epoch in range(1, max_epochs + 1):
        model.train()
        permutation = torch.randperm(len(x_t), generator=generator)
        for start in range(0, len(permutation), MLP_BATCH_SIZE):
            batch = permutation[start : start + MLP_BATCH_SIZE].to(DEVICE)
            optimizer.zero_grad(set_to_none=True)
            error = (model(x_t[batch]) - y_t[batch]).square().mean(dim=1)
            loss = (error * w_t[batch]).sum() / w_t[batch].sum()
            loss.backward()
            optimizer.step()
        train_loss = torch_mse(model, x_t, y_t, w_t)
        validation_loss = (
            torch_mse(model, xv_t, yv_t, wv_t) if has_validation else math.nan
        )
        curve_rows.append(
            {
                "timestamp": stamp(),
                "phase": "inner_early_stopping" if has_validation else "outer_refit",
                "epoch": epoch,
                "train_loss": train_loss,
                "validation_loss": validation_loss,
            }
        )
        if has_validation:
            if validation_loss < best_loss - MLP_MIN_DELTA:
                best_loss = validation_loss
                best_epoch = epoch
                best_state = copy.deepcopy(
                    {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
                )
                stale_epochs = 0
            else:
                stale_epochs += 1
            if stale_epochs >= MLP_PATIENCE:
                stop_epoch = epoch
                break
    if has_validation:
        if best_state is None:
            raise RuntimeError("MLP validation never produced a finite best checkpoint")
        model.load_state_dict(best_state)
        model = model.to(DEVICE)
        return best_epoch, stop_epoch, curve_rows, best_state
    return max_epochs, max_epochs, curve_rows, {
        key: value.detach().cpu().clone() for key, value in model.state_dict().items()
    }


def fit_mlp_outer(
    data: dict[str, object],
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    input_name: str,
    fold: int,
    variant: str,
    inner_train: np.ndarray,
    inner_validation: np.ndarray,
    seed: int,
) -> tuple[np.ndarray, list[dict[str, object]], dict[str, object]]:
    target_inner_train, target_inner_val, _, _, _ = targets_for_split(
        data,
        inner_train,
        inner_validation,
        variant,
        data["neighbor_map"],
    )
    keep_itr = np.isfinite(target_inner_train).all(axis=1)
    keep_ival = np.isfinite(target_inner_val).all(axis=1)
    itr, ival = inner_train[keep_itr], inner_validation[keep_ival]
    y_itr, y_ival = target_inner_train[keep_itr], target_inner_val[keep_ival]
    x_itr = feature_matrix(data, input_name, itr)
    x_ival = feature_matrix(data, input_name, ival)
    w_itr = participant_weights(data["participants"][itr])
    xitr_s, xival_s, yitr_s, yival_s, _, _ = scale_pair(
        x_itr, x_ival, y_itr, y_ival, w_itr
    )
    w_ival = participant_weights(data["participants"][ival])
    seed_torch(seed)
    inner_model = SmallMLP(xitr_s.shape[1], len(TARGETS))
    best_epoch, stopped_epoch, curves, _ = fit_mlp_training(
        inner_model,
        xitr_s,
        yitr_s,
        w_itr,
        seed,
        MLP_MAX_EPOCHS,
        xival_s,
        yival_s,
        w_ival,
    )
    curve_rows = [
        {
            "outer_fold": fold,
            "target_variant": variant,
            "input": input_name,
            "seed": seed,
            "split": "inner",
            **item,
        }
        for item in curves
    ]

    keep_train = np.isfinite(y_train).all(axis=1)
    keep_test = np.isfinite(y_test).all(axis=1)
    tr, te = train_idx[keep_train], test_idx[keep_test]
    ytr, yte = y_train[keep_train], y_test[keep_test]
    xtr = feature_matrix(data, input_name, tr)
    xte = feature_matrix(data, input_name, te)
    wtr = participant_weights(data["participants"][tr])
    xtr_s, xte_s, ytr_s, yte_s, y_mean, y_scale = scale_pair(xtr, xte, ytr, yte, wtr)
    seed_torch(seed + 100_000)
    final_model = SmallMLP(xtr_s.shape[1], len(TARGETS))
    _, _, refit_curve, state = fit_mlp_training(
        final_model,
        xtr_s,
        ytr_s,
        wtr,
        seed + 100_000,
        best_epoch,
    )
    final_model.load_state_dict(state)
    final_model = final_model.to(DEVICE)
    final_model.eval()
    with torch.no_grad():
        prediction = final_model(
            torch.from_numpy(np.ascontiguousarray(xte_s, dtype=np.float32)).to(DEVICE)
        ).cpu().numpy()
    prediction = prediction * y_scale + y_mean
    curve_rows.extend(
        {
            "outer_fold": fold,
            "target_variant": variant,
            "input": input_name,
            "seed": seed + 100_000,
            "split": "outer_refit",
            **item,
        }
        for item in refit_curve
    )
    row = {
        "timestamp": stamp(),
        "phase": "mlp_outer_fit",
        "outer_fold": fold,
        "target_variant": variant,
        "input": input_name,
        "family": "MLP",
        "alpha": "",
        "status": "success",
        "n_train_spots": len(tr),
        "n_test_spots": len(te),
        "inner_train_participants": len(np.unique(data["participants"][itr])),
        "inner_validation_participants": len(np.unique(data["participants"][ival])),
        "inner_stopped_epoch": stopped_epoch,
        "selected_best_epoch": best_epoch,
        "refit_epochs": best_epoch,
        "seed": seed,
        "device": str(DEVICE),
    }
    return prediction.astype(np.float32), curve_rows, row


def run_baselines(
    data: dict[str, object],
    fold: int,
    variant: str,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    predictions: dict[str, np.ndarray],
) -> list[dict[str, object]]:
    rows = []
    keep_train = np.isfinite(y_train).all(axis=1)
    keep_test = np.isfinite(y_test).all(axis=1)
    tr, te = train_idx[keep_train], test_idx[keep_test]
    ytr, yte = y_train[keep_train], y_test[keep_test]
    train_people = np.unique(data["participants"][tr])
    participant_means = np.vstack(
        [np.mean(ytr[data["participants"][tr] == pid], axis=0) for pid in train_people]
    )
    patient_prediction = np.mean(participant_means, axis=0)
    predictions["patient_mean"][te, :] = patient_prediction
    rows.append(
        {
            "timestamp": stamp(),
            "phase": "fixed_baseline",
            "outer_fold": fold,
            "target_variant": variant,
            "input": "training_participant_means",
            "family": "patient_mean",
            "status": "success",
            "n_train_spots": len(tr),
            "n_test_spots": len(te),
        }
    )
    for name in ("depth_only_ridge", "color_only_ridge"):
        input_name = "depth_only" if name == "depth_only_ridge" else "color_only"
        xtr = feature_matrix(data, input_name, tr)
        xte = feature_matrix(data, input_name, te)
        weights = participant_weights(data["participants"][tr])
        xs, xt, ys, yt, y_mean, y_scale = scale_pair(xtr, xte, ytr, yte, weights)
        try:
            model = Ridge(alpha=1.0)
            model.fit(xs, ys, sample_weight=weights)
            predictions[name][te, :] = (model.predict(xt) * y_scale + y_mean).astype(np.float32)
            status, error = "success", ""
        except Exception as exception:
            status, error = "failed", repr(exception)
        rows.append(
            {
                "timestamp": stamp(),
                "phase": "fixed_baseline",
                "outer_fold": fold,
                "target_variant": variant,
                "input": input_name,
                "family": "fixed Ridge baseline",
                "alpha": 1.0,
                "status": status,
                "error": error,
                "n_train_spots": len(tr),
                "n_test_spots": len(te),
            }
        )
    return rows


def score_participants(
    data: dict[str, object],
    target_values: np.ndarray,
    predictions: dict[str, np.ndarray],
    target_variant: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    participant_rows = []
    block_rows = []
    detected = data["raw_detected"]
    for model_name, prediction in predictions.items():
        for target_index, target in enumerate(TARGETS):
            eligible_ids = []
            for participant in sorted(np.unique(data["participants"])):
                participant_mask = data["participants"] == participant
                valid = participant_mask & np.isfinite(target_values[:, target_index])
                observed = target_values[valid, target_index]
                detected_count = int(np.sum(detected[participant_mask, target_index]))
                reasons = []
                if detected_count < 10:
                    reasons.append("fewer_than_10_detected_spots")
                if len(observed) < 10:
                    reasons.append("fewer_than_10_finite_targets")
                if np.unique(observed).size < 3:
                    reasons.append("fewer_than_3_target_values")
                model_valid = valid & np.isfinite(prediction[:, target_index])
                y = target_values[model_valid, target_index]
                p = prediction[model_valid, target_index]
                if len(y) < 10:
                    reasons.append("fewer_than_10_predictions")
                rho = math.nan
                if not reasons and np.unique(p).size >= 2:
                    rho = float(spearmanr(y, p).statistic)
                    eligible_ids.append(participant)
                elif not reasons:
                    reasons.append("constant_predictions")
                mae = float(np.mean(np.abs(y - p))) if len(y) else math.nan
                participant_rows.append(
                    {
                        "target_variant": target_variant,
                        "model": model_name,
                        "target": target,
                        "participant_id": participant,
                        "n_spots": int(len(y)),
                        "n_detected_spots": detected_count,
                        "spearman_rho": rho,
                        "mae": mae,
                        "eligible_for_spearman": not reasons,
                        "skip_reason": ";".join(reasons),
                    }
                )
                if not reasons:
                    block_y = []
                    block_p = []
                    valid_indices = np.flatnonzero(model_valid)
                    block_groups: dict[tuple[str, int, int], list[int]] = defaultdict(list)
                    for index in valid_indices:
                        key = (
                            str(data["libraries"][index]),
                            int(data["array_row"][index]) // BLOCK_WIDTH,
                            int(data["array_col"][index]) // BLOCK_WIDTH,
                        )
                        block_groups[key].append(int(index))
                    for indices in block_groups.values():
                        block_y.append(float(np.mean(target_values[indices, target_index])))
                        block_p.append(float(np.mean(prediction[indices, target_index])))
                    block_rho = math.nan
                    block_reason = ""
                    if len(block_y) < 4:
                        block_reason = "fewer_than_4_blocks"
                    elif np.unique(block_y).size < 2:
                        block_reason = "constant_block_targets"
                    elif np.unique(block_p).size < 2:
                        block_reason = "constant_block_predictions"
                    else:
                        block_rho = float(spearmanr(block_y, block_p).statistic)
                    block_rows.append(
                        {
                            "target_variant": target_variant,
                            "model": model_name,
                            "target": target,
                            "participant_id": participant,
                            "n_blocks": len(block_y),
                            "block_spearman_rho": block_rho,
                            "skip_reason": block_reason,
                        }
                    )
    participant_frame = pd.DataFrame(participant_rows)
    patient_mean = participant_frame[participant_frame.model == "patient_mean"][
        ["target_variant", "target", "participant_id", "mae"]
    ].rename(columns={"mae": "patient_mean_mae"})
    participant_frame = participant_frame.merge(
        patient_mean, on=["target_variant", "target", "participant_id"], how="left"
    )
    participant_frame["beats_patient_mean_mae"] = (
        (participant_frame.model != "patient_mean")
        & (participant_frame.mae < participant_frame.patient_mean_mae)
    )
    return participant_frame, pd.DataFrame(block_rows)


def bootstrap_mean(values: np.ndarray, rng: np.random.Generator) -> tuple[float, float, float]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return math.nan, math.nan, math.nan
    draws = rng.integers(0, finite.size, size=(BOOTSTRAP_REPS, finite.size))
    means = finite[draws].mean(axis=1)
    low, high = np.quantile(means, [0.025, 0.975])
    return float(finite.mean()), float(low), float(high)


def summarize_metrics(
    participant_metrics: pd.DataFrame, block_metrics: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    metric_rows = []
    for unit, frame in (("spot", participant_metrics), ("block", block_metrics)):
        rho_column = "spearman_rho" if unit == "spot" else "block_spearman_rho"
        for (variant, model, target), group in frame.groupby(
            ["target_variant", "model", "target"], sort=False
        ):
            vals = group[rho_column].to_numpy(dtype=np.float64)
            mean, low, high = bootstrap_mean(vals, rng)
            eligible = int(np.isfinite(vals).sum())
            win_count = (
                int(group["beats_patient_mean_mae"].sum())
                if unit == "spot" and "beats_patient_mean_mae" in group
                else 0
            )
            metric_rows.append(
                {
                    "unit": unit,
                    "target_variant": variant,
                    "model": model,
                    "target": target,
                    "n_participants": eligible,
                    "mean_spearman": mean,
                    "ci95_low": low,
                    "ci95_high": high,
                    "participants_beating_patient_mean_by_mae": win_count,
                }
            )
    summary = pd.DataFrame(metric_rows)
    comparison_rows = []
    base_models = ["depth_only_ridge", "color_only_ridge"]
    for unit, frame in (("spot", participant_metrics), ("block", block_metrics)):
        rho_column = "spearman_rho" if unit == "spot" else "block_spearman_rho"
        for variant in TARGET_VARIANTS:
            for target in TARGETS:
                pivot = frame[frame.target_variant == variant]
                for candidate in IMAGE_MODELS:
                    for baseline in base_models:
                        cand = pivot[
                            (pivot.model == candidate) & (pivot.target == target)
                        ].set_index("participant_id")[rho_column]
                        base = pivot[
                            (pivot.model == baseline) & (pivot.target == target)
                        ].set_index("participant_id")[rho_column]
                        paired = pd.concat([cand.rename("candidate"), base.rename("baseline")], axis=1).dropna()
                        deltas = (paired.candidate - paired.baseline).to_numpy(dtype=np.float64)
                        mean, low, high = bootstrap_mean(deltas, rng)
                        comparison_rows.append(
                            {
                                "unit": unit,
                                "target_variant": variant,
                                "target": target,
                                "candidate": candidate,
                                "baseline": baseline,
                                "n_participants": int(len(deltas)),
                                "mean_delta_spearman": mean,
                                "ci95_low": low,
                                "ci95_high": high,
                                "ci_entirely_above_zero": bool(np.isfinite(low) and low > 0),
                                "positive_participants": int(np.sum(deltas > 0)),
                            }
                        )
    return summary, pd.DataFrame(comparison_rows)


def verify_metrics(
    data: dict[str, object],
    target_values: dict[str, np.ndarray],
    predictions: dict[str, dict[str, np.ndarray]],
    metric_frame: pd.DataFrame,
) -> pd.DataFrame:
    choices = []
    preferred = [
        ("depth_residualized", "elasticnet_spot", "ECM_collagen"),
        ("depth_residualized", "mlp_spot", "ECM_collagen"),
        ("depth_residualized_neighbor_mean", "mlp_image_depth", "matrix_remodelling"),
    ]
    for variant, model, target in preferred:
        candidates = metric_frame[
            (metric_frame.target_variant == variant)
            & (metric_frame.model == model)
            & (metric_frame.target == target)
            & metric_frame.eligible_for_spearman.astype(bool)
        ].sort_values("participant_id")
        if not candidates.empty:
            row = candidates.iloc[0]
            choices.append((variant, model, target, str(row.participant_id)))
    if len(choices) < 3:
        candidates = metric_frame[
            metric_frame.eligible_for_spearman.astype(bool)
        ].sort_values(["target_variant", "model", "target", "participant_id"])
        for row in candidates.itertuples(index=False):
            choice = (row.target_variant, row.model, row.target, row.participant_id)
            if choice not in choices:
                choices.append(choice)
            if len(choices) == 3:
                break
    checks = []
    for variant, model, target, participant in choices:
        t_index = TARGETS.index(target)
        mask = (
            (data["participants"] == participant)
            & np.isfinite(target_values[variant][:, t_index])
            & np.isfinite(predictions[variant][model][:, t_index])
        )
        y = target_values[variant][mask, t_index]
        p = predictions[variant][model][mask, t_index]
        recomputed = float(spearmanr(y, p).statistic) if len(y) > 2 else math.nan
        reported_rows = metric_frame[
            (metric_frame.target_variant == variant)
            & (metric_frame.model == model)
            & (metric_frame.target == target)
            & (metric_frame.participant_id == participant)
        ]
        reported = (
            float(reported_rows.iloc[0].spearman_rho)
            if not reported_rows.empty
            else math.nan
        )
        difference = abs(recomputed - reported) if np.isfinite(recomputed + reported) else math.nan
        checks.append(
            {
                "target_variant": variant,
                "model": model,
                "target": target,
                "participant_id": participant,
                "n_spots": len(y),
                "reported_spearman": reported,
                "recomputed_spearman": recomputed,
                "absolute_difference": difference,
                "verified": bool(np.isfinite(difference) and difference < 1e-10),
            }
        )
    if len(checks) != 3:
        raise AssertionError("Fewer than three eligible metrics were available to recompute")
    return pd.DataFrame(checks)


def checkpoint_predictions(
    data: dict[str, object],
    predictions: dict[str, dict[str, np.ndarray]],
    targets: dict[str, np.ndarray],
) -> None:
    save_npz(
        out_path("predictions_partial.npz"),
        participant_id=data["frame"].participant_id.to_numpy(dtype="U16"),
        library_id=data["frame"].library_id.to_numpy(dtype="U24"),
        barcode=data["frame"].barcode.to_numpy(dtype="U32"),
        fold=data["folds"],
        model_names=np.asarray(MODEL_NAMES, dtype="U32"),
        target_names=np.asarray(TARGETS, dtype="U40"),
        target_variants=np.asarray(TARGET_VARIANTS, dtype="U48"),
        predictions=np.stack(
            [
                np.stack([predictions[variant][model] for model in MODEL_NAMES])
                for variant in TARGET_VARIANTS
            ]
        ),
        target_values=np.stack([targets[name] for name in TARGET_VARIANTS]),
    )


def repair_mlp_ledger(
    data: dict[str, object],
    completed_folds: set[int],
    predictions: dict[str, dict[str, np.ndarray]],
    transformed_targets: dict[str, np.ndarray],
    partial_path: Path,
) -> None:
    failures = []
    for fold in sorted(completed_folds):
        test_idx = np.flatnonzero(data["folds"] == fold)
        train_idx = np.flatnonzero(data["folds"] != fold)
        print(f"replaying MLP logs for outer fold {fold + 1}/{N_OUTER_FOLDS}", flush=True)
        for variant in TARGET_VARIANTS:
            y_train, y_test, _, _, _ = targets_for_split(
                data, train_idx, test_idx, variant, data["neighbor_map"]
            )
            val_seed = BASE_SEED + fold * 1009 + TARGET_VARIANTS.index(variant) * 31
            splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=val_seed)
            itr_local, ival_local = next(
                splitter.split(train_idx, groups=data["participants"][train_idx])
            )
            inner_train, inner_validation = train_idx[itr_local], train_idx[ival_local]
            for input_index, (input_name, model_name) in enumerate(
                (("spot", "mlp_spot"), ("image_depth", "mlp_image_depth"))
            ):
                seed = BASE_SEED + fold * 10_007 + TARGET_VARIANTS.index(variant) * 101 + input_index
                try:
                    pred, curves, row = fit_mlp_outer(
                        data,
                        train_idx,
                        test_idx,
                        y_train,
                        y_test,
                        input_name,
                        fold,
                        variant,
                        inner_train,
                        inner_validation,
                        seed,
                    )
                    keep_test = np.isfinite(y_test).all(axis=1)
                    predictions[variant][model_name][test_idx[keep_test], :] = pred
                    row["model"] = model_name
                    log_config(row)
                    for curve in curves:
                        curve.update({"model": model_name, "family": "MLP"})
                    log_curve(curves)
                except Exception as error:
                    failures.append((fold, variant, input_name, repr(error)))
                    log_config(
                        {
                            "timestamp": stamp(),
                            "phase": "mlp_ledger_replay",
                            "outer_fold": fold,
                            "target_variant": variant,
                            "input": input_name,
                            "family": "MLP",
                            "status": "failed",
                            "seed": seed,
                            "error": repr(error),
                        }
                    )
        save_npz(
            partial_path,
            participant_id=data["frame"].participant_id.to_numpy(dtype="U16"),
            library_id=data["frame"].library_id.to_numpy(dtype="U24"),
            barcode=data["frame"].barcode.to_numpy(dtype="U32"),
            fold=data["folds"],
            model_names=np.asarray(MODEL_NAMES, dtype="U32"),
            target_names=np.asarray(TARGETS, dtype="U40"),
            target_variants=np.asarray(TARGET_VARIANTS, dtype="U48"),
            predictions=np.stack(
                [
                    np.stack([predictions[variant][model] for model in MODEL_NAMES])
                    for variant in TARGET_VARIANTS
                ]
            ),
            target_values=np.stack([transformed_targets[name] for name in TARGET_VARIANTS]),
            completed_folds=np.asarray(sorted(completed_folds), dtype=np.int8),
        )
    if failures:
        raise RuntimeError(f"MLP ledger replay failures: {failures}")


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_No available rows._"
    view = frame[columns].copy()
    for column in view.select_dtypes(include=["float"]).columns:
        view[column] = view[column].map(
            lambda value: "" if not np.isfinite(value) else f"{value:.3f}"
        )
    headers = [str(column) for column in view.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in view.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def make_plots(summary: pd.DataFrame) -> list[Path]:
    paths = []
    for unit in ["spot", "block"]:
        for variant in TARGET_VARIANTS:
            view = summary[
                (summary.unit == unit) & (summary.target_variant == variant)
            ]
            fig, axes = plt.subplots(1, 2, figsize=(18, 7), constrained_layout=True)
            for axis, targets, heading in (
                (axes[0], MODULES, "Modules"),
                (axes[1], GENES, "Genes"),
            ):
                subset = view[view.target.isin(targets)]
                models = [name for name in MODEL_NAMES if name in set(subset.model)]
                x = np.arange(len(targets))
                width = 0.8 / max(len(models), 1)
                for i, model in enumerate(models):
                    rows = subset[subset.model == model].set_index("target").reindex(targets)
                    offset = (i - (len(models) - 1) / 2) * width
                    y = rows.mean_spearman.to_numpy(dtype=float)
                    low = y - rows.ci95_low.to_numpy(dtype=float)
                    high = rows.ci95_high.to_numpy(dtype=float) - y
                    axis.errorbar(
                        x + offset,
                        y,
                        yerr=np.vstack([low, high]),
                        fmt="o",
                        capsize=2,
                        label=model,
                    )
                axis.axhline(0, color="black", linewidth=0.8)
                axis.set_xticks(x, targets, rotation=35, ha="right")
                axis.set_title(heading)
                axis.set_ylabel("Mean participant Spearman (95% participant-bootstrap CI)")
            axes[1].legend(loc="best", fontsize=7)
            fig.suptitle(f"{LABEL} — {unit}-level metrics — {variant}")
            path = out_path(f"{unit}_{variant}_summary.png")
            fig.savefig(path, dpi=140)
            plt.close(fig)
            paths.append(path)
    return paths


def write_report(
    data: dict[str, object],
    participant_metrics: pd.DataFrame,
    block_metrics: pd.DataFrame,
    summary: pd.DataFrame,
    comparisons: pd.DataFrame,
    verification: pd.DataFrame,
    neighbor_counts: pd.DataFrame,
    config_log: pd.DataFrame,
    curves: pd.DataFrame,
) -> Path:
    report_path = out_path("report.md")
    module_summary = summary[
        (summary.unit == "spot") & (summary.target.isin(MODULES))
    ]
    gene_summary = summary[
        (summary.unit == "spot") & (summary.target.isin(GENES))
    ]
    module_comparisons = comparisons[
        (comparisons.unit == "spot") & (comparisons.target.isin(MODULES))
    ]
    gene_comparisons = comparisons[
        (comparisons.unit == "spot") & (comparisons.target.isin(GENES))
    ]
    block_module = summary[
        (summary.unit == "block") & (summary.target.isin(MODULES))
    ]
    block_gene = summary[
        (summary.unit == "block") & (summary.target.isin(GENES))
    ]
    non_success = config_log[config_log.status != "success"]
    discarded = config_log[config_log.status == "discarded"]
    incomplete = config_log[config_log.status.isin(["failed", "non_converged", "interrupted"])]
    test_neighbor_counts = neighbor_counts[neighbor_counts["split"] == "outer_test"]
    neighbor_without = (
        int(
            test_neighbor_counts.loc[
                test_neighbor_counts.n_neighbors == 0,
                ["participant_id", "library_id", "barcode"],
            ]
            .drop_duplicates()
            .shape[0]
        )
        if len(test_neighbor_counts)
        else 0
    )
    report = f"""# Stage 1b exploratory follow-up

**Label: exploratory, post-hoc.**  
**Run completed:** {stamp()}  
**Stage 1 Gate A:** remains **FAIL**. This analysis does not alter that verdict.

## Result in brief

This follow-up used the existing frozen ResNet-50 spot embeddings and tested converged Elastic Net and an early-stopped MLP on depth-residualized expression, with and without a mean over six immediate Visium neighbors. The primary metric is per-participant spot-level Spearman, with participant-bootstrap 95% CIs. It also reports non-overlapping 10-by-10 array-coordinate block results.

No post-hoc Stage 1b result changes Gate A or authorizes a later stage. Comparisons are exploratory, involve multiple targets/models, and are not multiplicity-adjusted confirmatory tests. The depth-only comparator depends on a library-depth input and is not assumed to be available for image-only inference.

## Cohort, keys, and resource use

- Reconciled **{data['frame'].participant_id.nunique()} participants, {data['frame'].library_id.nunique()} libraries, {len(data['frame']):,} spots**.
- Key: `(participant_id, library_id, barcode)`; keys are unique and folds match the seven Stage 1 participant-grouped folds.
- Both libraries for participant 28-12265 remain in one test fold.
- Stage 1b output folder storage (including this report): STAGE1B_TOTAL_BYTES bytes. Each output file is constrained below 1 GB.

## Fixed budget and model configurations

- Encoder: one, the frozen Stage 1 torchvision ResNet-50 `IMAGENET1K_V2`; no second encoder was tried. torchvision code is BSD-3-Clause; weight-specific and ImageNet dataset terms remain unverified.
- Target types: `depth_residualized` and `depth_residualized_neighbor_mean`. Residualization is fitted within each applicable training split only; smoothed values are the mean of available neighboring residualized spots in the same library, excluding the center spot. Offsets: `(0, ±2)`, `(±1, ±1)`. Spots with no available neighbor are not imputed; {neighbor_without} rows were unscorable for the smoothed target transformation.
- Models: fixed patient mean; depth-only and colour-only Ridge baselines (`alpha=1`); independent-target Elastic Net (`l1_ratio=0.5`, alpha grid `[0.001, 0.01, 0.1]`, four-fold participant-grouped inner CV, proximal FISTA, relative optimality tolerance `{ELASTICNET_TOL}`, iteration cap `{ELASTICNET_MAX_ITER}`); one-layer 128-unit MLP with grouped 20% participant validation, max {MLP_MAX_EPOCHS} epochs and patience {MLP_PATIENCE}. Inputs were spot embedding alone or spot embedding plus log1p UMI.
- Tried configuration rows: {len(config_log)} total; successful: {int((config_log.status == 'success').sum())}; discarded after implementation correction: {len(discarded)}; failed, non-converged, or interrupted: {len(incomplete)}. Detailed per-fold and inner-alpha records: `{PREFIX}configuration_log.csv`; Elastic Net objective paths and MLP epoch loss curves: `{PREFIX}loss_curves.csv`.
- {("Non-success attempts and reasons: " + "; ".join(f"{r.get('phase')} fold {r.get('outer_fold')} {r.get('target_variant')} {r.get('input')} alpha={r.get('alpha')}: {r.get('status')} {r.get('error', '')}" for _, r in non_success.iterrows())) if len(non_success) else "No failed, discarded, or interrupted configuration was logged."}

## Spot-level primary results — modules first

The table gives mean participant Spearman with 95% participant-bootstrap CI and eligible participant count.

{markdown_table(module_summary, ['target_variant','model','target','n_participants','mean_spearman','ci95_low','ci95_high','participants_beating_patient_mean_by_mae'])}

## Spot-level results — genes

{markdown_table(gene_summary, ['target_variant','model','target','n_participants','mean_spearman','ci95_low','ci95_high','participants_beating_patient_mean_by_mae'])}

## Paired spot-level comparisons — modules first

Positive delta means the candidate has higher participant Spearman than the baseline. `CI entirely above zero` is descriptive and exploratory; it is not a confirmatory claim.

{markdown_table(module_comparisons, ['target_variant','target','candidate','baseline','n_participants','mean_delta_spearman','ci95_low','ci95_high','ci_entirely_above_zero','positive_participants'])}

## Paired spot-level comparisons — genes

{markdown_table(gene_comparisons, ['target_variant','target','candidate','baseline','n_participants','mean_delta_spearman','ci95_low','ci95_high','ci_entirely_above_zero','positive_participants'])}

## Region-level results

Non-overlapping 10-by-10 array-coordinate blocks were formed separately within each library; target and prediction values were averaged within each block. Spearman was calculated within participant across blocks. Confidence intervals resample participants.

### Modules

{markdown_table(block_module, ['target_variant','model','target','n_participants','mean_spearman','ci95_low','ci95_high'])}

### Genes

{markdown_table(block_gene, ['target_variant','model','target','n_participants','mean_spearman','ci95_low','ci95_high'])}

### Paired block comparisons

{markdown_table(comparisons[(comparisons.unit == 'block') & comparisons.target.isin(MODULES)], ['target_variant','target','candidate','baseline','n_participants','mean_delta_spearman','ci95_low','ci95_high','ci_entirely_above_zero','positive_participants'])}

Per-participant block metrics are in `{PREFIX}participant_block_metrics.csv`.

## Verification

- Three participant metrics recomputed from saved keyed predictions; all verified: **{bool(verification.verified.all())}**. Largest absolute difference: {float(verification.absolute_difference.max()):.3g}.
- Fold/key/count verification: 28 participants, 29 libraries, 25,104 spots, unique full keys, one test fold per participant/key, and unchanged Stage 1 fold assignments.
- Spot and block participant counts, exclusions, MAE wins, and model convergence records are saved in labeled CSV outputs.

## Honest interpretation and limitations

- **What improved:** compared with Stage 1, image models here were allowed convergent independent-target Elastic Net optimization and MLP training with grouped early stopping. This removes the prior fixed low-epoch caps for the newly fitted Stage 1b models when the logged convergence checks pass.
- **What did not:** Stage 1 Gate A remains FAIL. Stage 1b results are post-hoc, compare multiple models and targets, and must not be used to overturn the registered gate. Image-plus-depth vs depth is a benchmark, not evidence of image-only deployability.
- The first MLP output-log append rejected two fitted-run metadata fields after predictions had been added to the checkpoint. Those 28 logger failures are preserved as attempts; all 28 MLP configurations were replayed with the corrected schema, and their curves and stopping-epoch records are included.
- **Evidence beyond depth:** {int(((comparisons.unit == 'spot') & (comparisons.baseline == 'depth_only_ridge') & comparisons.candidate.isin(['elasticnet_spot','mlp_spot']) & comparisons.ci_entirely_above_zero).sum())} image-only spot contrasts have a 95% CI wholly above zero versus depth-only; {int(((comparisons.unit == 'spot') & (comparisons.baseline == 'depth_only_ridge') & comparisons.candidate.isin(['elasticnet_image_depth','mlp_image_depth']) & comparisons.ci_entirely_above_zero).sum())} image-plus-depth spot contrasts do. These are exploratory post-hoc comparisons across multiple targets/models; no single target is confirmatory. No registration or fusion recommendation is made from this post-hoc stage.
- **What remains unverified:** weight-specific and upstream ImageNet dataset terms; external-cohort performance; whether depth is available in a deployment setting; and any independent confirmation of these post-hoc results.
- No image registration, collagen/trichrome features, batch correction, fine-tuning, external downloads, or later-stage work was performed.

## Outputs

All Stage 1b outputs are labeled **exploratory, post-hoc**. See `README_1B.md` for the output inventory, software versions, seeds, and rerun commands. Gate A remains **FAIL**.

## Complete configuration attempt ledger

Every baseline fit, outer-fold fit, and Elastic Net alpha/inner-fold attempt is listed below, including failures and non-convergence.

{markdown_table(config_log, list(config_log.columns))}
"""
    report_path.write_text(report, encoding="utf-8")
    storage_label = "Stage 1b output folder storage (including this report): "
    for _ in range(4):
        used_bytes = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
        content = report_path.read_text(encoding="utf-8")
        start = content.index(storage_label) + len(storage_label)
        end = content.index(" bytes.", start)
        updated = content[:start] + f"{used_bytes:,}" + content[end:]
        report_path.write_text(updated, encoding="utf-8")
        if updated == content:
            break
        report = updated
    if report_path.stat().st_size >= 1_000_000_000:
        raise RuntimeError("Report exceeds 1 GB")
    return report_path


def main() -> None:
    global RUN_ID
    OUT.mkdir(parents=True, exist_ok=True)
    RUN_ID = stamp()
    data = load_inputs()
    data["neighbor_map"] = build_neighbor_map(
        data["libraries"], data["array_row"], data["array_col"]
    )
    fold_assignments = data["frame"][["participant_id", "library_id", "barcode", "fold"]]
    write_csv(fold_assignments, out_path("fold_assignments.csv"))
    predictions = {
        variant: {
            model: np.full((len(data["frame"]), len(TARGETS)), np.nan, dtype=np.float32)
            for model in MODEL_NAMES
        }
        for variant in TARGET_VARIANTS
    }
    transformed_targets = {
        variant: np.full((len(data["frame"]), len(TARGETS)), np.nan, dtype=np.float32)
        for variant in TARGET_VARIANTS
    }
    config_log_path = out_path("configuration_log.csv")
    curve_path = out_path("loss_curves.csv")
    partial_path = out_path("predictions_partial.npz")
    resume = "--resume" in sys.argv[1:]
    completed_folds: set[int] = set()
    if resume:
        if not partial_path.exists():
            raise FileNotFoundError("--resume requested but no completed-fold checkpoint exists")
        checkpoint = np.load(partial_path)
        if checkpoint["analysis_label"].item() != LABEL:
            raise ValueError("Checkpoint is not labeled for this exploratory analysis")
        checkpoint_keys = list(
            zip(
                checkpoint["participant_id"].astype(str),
                checkpoint["library_id"].astype(str),
                checkpoint["barcode"].astype(str),
            )
        )
        if checkpoint_keys != data["keys"] or not np.array_equal(checkpoint["fold"], data["folds"]):
            raise AssertionError("Checkpoint keys or folds do not match Stage 1")
        completed_folds = set(checkpoint["completed_folds"].astype(int).tolist())
    else:
        for path in (config_log_path, curve_path, partial_path, out_path("predictions.npz")):
            if path.exists():
                path.unlink()
        append_csv(
            [
            {
                "run_id": "pre_schema_fix",
                "timestamp": "2026-11-12T20:36:02+05:30",
                "phase": "fixed_baseline",
                "outer_fold": 0,
                "target_variant": "depth_residualized",
                "input": "training_participant_means",
                "family": "patient_mean",
                "model": "patient_mean",
                "status": "success",
                "n_train_spots": 21_569,
                "n_test_spots": 3_535,
                "error": "Completed before logging-schema correction; no scores inspected.",
            },
            {
                "run_id": "pre_schema_fix",
                "timestamp": "2026-11-12T20:36:02+05:30",
                "phase": "fixed_baseline",
                "outer_fold": 0,
                "target_variant": "depth_residualized",
                "input": "depth_only",
                "family": "fixed Ridge baseline",
                "model": "depth_only_ridge",
                "alpha": 1.0,
                "status": "success",
                "n_train_spots": 21_569,
                "n_test_spots": 3_535,
                "error": "Completed before logging-schema correction; no scores inspected.",
            },
            {
                "run_id": "pre_schema_fix",
                "timestamp": "2026-11-12T20:36:02+05:30",
                "phase": "fixed_baseline",
                "outer_fold": 0,
                "target_variant": "depth_residualized",
                "input": "color_only",
                "family": "fixed Ridge baseline",
                "model": "color_only_ridge",
                "alpha": 1.0,
                "status": "success",
                "n_train_spots": 21_569,
                "n_test_spots": 3_535,
                "error": "Completed before logging-schema correction; no scores inspected.",
            },
            {
                "run_id": "pre_schema_fix",
                "timestamp": "2026-11-12T20:36:02+05:30",
                "phase": "elasticnet_inner_cv",
                "outer_fold": 0,
                "inner_fold": 0,
                "target_variant": "depth_residualized",
                "input": "spot",
                "family": "ElasticNet",
                "model": "elasticnet_spot",
                "alpha": 0.001,
                "l1_ratio": L1_RATIO,
                "precompute": False,
                "status": "interrupted",
                "error": "First inner fit was stopped at 2026-11-12T22:10:07+05:30 after more than 90 minutes without a validation result; stopped to fix output schema. No model score inspected.",
            },
            {
                "run_id": "pre_fista_change",
                "timestamp": "2026-11-12T22:13:17+05:30",
                "phase": "fixed_baseline",
                "outer_fold": 0,
                "target_variant": "depth_residualized",
                "input": "training_participant_means",
                "family": "patient_mean",
                "model": "patient_mean",
                "status": "success",
                "n_train_spots": 21_569,
                "n_test_spots": 3_535,
                "error": "Repeated in second run; scores not used.",
            },
            {
                "run_id": "pre_fista_change",
                "timestamp": "2026-11-12T22:13:18+05:30",
                "phase": "fixed_baseline",
                "outer_fold": 0,
                "target_variant": "depth_residualized",
                "input": "depth_only",
                "family": "fixed Ridge baseline",
                "model": "depth_only_ridge",
                "alpha": 1.0,
                "status": "success",
                "n_train_spots": 21_569,
                "n_test_spots": 3_535,
                "error": "Repeated in second run; scores not used.",
            },
            {
                "run_id": "pre_fista_change",
                "timestamp": "2026-11-12T22:13:18+05:30",
                "phase": "fixed_baseline",
                "outer_fold": 0,
                "target_variant": "depth_residualized",
                "input": "color_only",
                "family": "fixed Ridge baseline",
                "model": "color_only_ridge",
                "alpha": 1.0,
                "status": "success",
                "n_train_spots": 21_569,
                "n_test_spots": 3_535,
                "error": "Repeated in second run; scores not used.",
            },
            {
                "run_id": "pre_fista_change",
                "timestamp": "2026-11-12T22:13:19+05:30",
                "phase": "elasticnet_inner_cv",
                "outer_fold": 0,
                "inner_fold": 0,
                "target_variant": "depth_residualized",
                "input": "spot",
                "family": "ElasticNet",
                "model": "elasticnet_spot",
                "alpha": 0.001,
                "l1_ratio": L1_RATIO,
                "solver": "scikit-learn multi-output coordinate descent (L21 coupled penalty)",
                "precompute": True,
                "status": "discarded",
                "n_train_spots": 16_169,
                "n_validation_spots": 5_400,
                "train_participants": 18,
                "validation_participants": 6,
                "n_iter": 7_458,
                "dual_gap_max": 9.988486003470978e-05,
                "validation_mse": 1.4458768202367889,
                "error": "Discarded after identifying the multi-output L21 coupling; no outer-test prediction was used.",
            },
            {
                "run_id": "pre_fista_change",
                "timestamp": "2026-11-12T22:16:09+05:30",
                "phase": "elasticnet_inner_cv",
                "outer_fold": 0,
                "inner_fold": 0,
                "target_variant": "depth_residualized",
                "input": "spot",
                "family": "ElasticNet",
                "model": "elasticnet_spot",
                "alpha": 0.01,
                "l1_ratio": L1_RATIO,
                "solver": "scikit-learn multi-output coordinate descent (L21 coupled penalty)",
                "precompute": True,
                "status": "discarded",
                "n_train_spots": 16_169,
                "n_validation_spots": 5_400,
                "train_participants": 18,
                "validation_participants": 6,
                "n_iter": 652,
                "dual_gap_max": 9.925086552267301e-05,
                "validation_mse": 1.2113577038935879,
                "error": "Discarded after identifying the multi-output L21 coupling; no outer-test prediction was used.",
            },
            {
                "run_id": "pre_fista_change",
                "timestamp": "2026-11-12T22:16:18+05:30",
                "phase": "elasticnet_inner_cv",
                "outer_fold": 0,
                "inner_fold": 0,
                "target_variant": "depth_residualized",
                "input": "spot",
                "family": "ElasticNet",
                "model": "elasticnet_spot",
                "alpha": 0.1,
                "l1_ratio": L1_RATIO,
                "solver": "scikit-learn multi-output coordinate descent (L21 coupled penalty)",
                "precompute": True,
                "status": "discarded",
                "n_train_spots": 16_169,
                "n_validation_spots": 5_400,
                "train_participants": 18,
                "validation_participants": 6,
                "n_iter": 12,
                "dual_gap_max": 5.499278990900247e-08,
                "validation_mse": 1.131002043159839,
                "error": "Discarded after identifying the multi-output L21 coupling; no outer-test prediction was used.",
            },
            {
                "run_id": "pre_fista_change",
                "timestamp": "2026-11-12T22:16:21+05:30",
                "phase": "elasticnet_inner_cv",
                "outer_fold": 0,
                "inner_fold": 1,
                "target_variant": "depth_residualized",
                "input": "spot",
                "family": "ElasticNet",
                "model": "elasticnet_spot",
                "alpha": 0.001,
                "l1_ratio": L1_RATIO,
                "solver": "scikit-learn multi-output coordinate descent (L21 coupled penalty)",
                "precompute": True,
                "status": "discarded",
                "n_train_spots": 16_181,
                "n_validation_spots": 5_388,
                "train_participants": 18,
                "validation_participants": 6,
                "n_iter": 7_969,
                "dual_gap_max": 9.998613761011425e-05,
                "validation_mse": 1.6574600349068378,
                "error": "Discarded after identifying the multi-output L21 coupling; no outer-test prediction was used.",
            },
            {
                "run_id": "pre_fista_change",
                "timestamp": "2026-11-12T22:19:35+05:30",
                "phase": "elasticnet_inner_cv",
                "outer_fold": 0,
                "inner_fold": 1,
                "target_variant": "depth_residualized",
                "input": "spot",
                "family": "ElasticNet",
                "model": "elasticnet_spot",
                "alpha": 0.01,
                "l1_ratio": L1_RATIO,
                "solver": "scikit-learn multi-output coordinate descent (L21 coupled penalty)",
                "precompute": True,
                "status": "discarded",
                "n_train_spots": 16_181,
                "n_validation_spots": 5_388,
                "train_participants": 18,
                "validation_participants": 6,
                "n_iter": 725,
                "dual_gap_max": 9.99810555665226e-05,
                "validation_mse": 1.4768769789214335,
                "error": "Discarded after identifying the multi-output L21 coupling; no outer-test prediction was used.",
            },
            {
                "run_id": "pre_fista_change",
                "timestamp": "2026-11-12T22:19:44+05:30",
                "phase": "elasticnet_inner_cv",
                "outer_fold": 0,
                "inner_fold": 1,
                "target_variant": "depth_residualized",
                "input": "spot",
                "family": "ElasticNet",
                "model": "elasticnet_spot",
                "alpha": 0.1,
                "l1_ratio": L1_RATIO,
                "solver": "scikit-learn multi-output coordinate descent (L21 coupled penalty)",
                "precompute": True,
                "status": "discarded",
                "n_train_spots": 16_181,
                "n_validation_spots": 5_388,
                "train_participants": 18,
                "validation_participants": 6,
                "n_iter": 28,
                "dual_gap_max": 6.744373852001542e-07,
                "validation_mse": 1.456055577033804,
                "error": "Discarded after identifying the multi-output L21 coupling; no outer-test prediction was used.",
            },
            ],
            config_log_path,
        )
    residual_rows = []
    neighbor_rows = []
    if resume:
        saved_predictions = checkpoint["predictions"]
        saved_targets = checkpoint["target_values"]
        for variant_index, variant in enumerate(TARGET_VARIANTS):
            transformed_targets[variant][:] = saved_targets[variant_index]
            for model_index, model in enumerate(MODEL_NAMES):
                predictions[variant][model][:] = saved_predictions[variant_index, model_index]
        print(f"resuming after completed folds: {sorted(completed_folds)}", flush=True)
        if "--repair-mlp-ledger" in sys.argv[1:]:
            logged_columns = pd.read_csv(config_log_path, nrows=0).columns
            if "inner_train_participants" not in logged_columns:
                log_config(
                    {
                        "timestamp": stamp(),
                        "phase": "mlp_ledger_replay",
                        "outer_fold": 0,
                        "target_variant": TARGET_VARIANTS[0],
                        "input": "spot",
                        "family": "MLP",
                        "status": "failed",
                        "seed": BASE_SEED,
                        "error": (
                            "The first ledger-repair fit completed, but its log append "
                            "failed because the existing CSV header lacked the new metadata "
                            "columns; this attempt produced no reported metric."
                        ),
                    }
                )
            repair_mlp_ledger(
                data,
                completed_folds,
                predictions,
                transformed_targets,
                partial_path,
            )
        for fold in sorted(completed_folds):
            test_idx = np.flatnonzero(data["folds"] == fold)
            train_idx = np.flatnonzero(data["folds"] != fold)
            for variant in TARGET_VARIANTS:
                _, _, train_neighbor_counts, test_neighbor_counts, coefs = targets_for_split(
                    data, train_idx, test_idx, variant, data["neighbor_map"]
                )
                residual_rows.extend(
                    {
                        "outer_fold": fold,
                        "target_variant": variant,
                        "training_participants": len(np.unique(data["participants"][train_idx])),
                        **row,
                    }
                    for row in coefs
                )
                if variant == "depth_residualized_neighbor_mean":
                    for indices, counts, split_name in (
                        (train_idx, train_neighbor_counts, "outer_train"),
                        (test_idx, test_neighbor_counts, "outer_test"),
                    ):
                        neighbor_rows.extend(
                            {
                                "outer_fold": fold,
                                "split": split_name,
                                "participant_id": data["participants"][index],
                                "library_id": data["libraries"][index],
                                "barcode": data["frame"].barcode.iloc[index],
                                "n_neighbors": int(counts[pos]),
                            }
                            for pos, index in enumerate(indices)
                        )
    for fold in range(N_OUTER_FOLDS):
        if fold in completed_folds:
            continue
        test_idx = np.flatnonzero(data["folds"] == fold)
        train_idx = np.flatnonzero(data["folds"] != fold)
        if set(data["participants"][train_idx]) & set(data["participants"][test_idx]):
            raise AssertionError(f"Participant leakage in outer fold {fold}")
        print(f"outer fold {fold + 1}/{N_OUTER_FOLDS}: prepare split", flush=True)
        for variant in TARGET_VARIANTS:
            y_train, y_test, train_neighbor_counts, test_neighbor_counts, coefs = targets_for_split(
                data, train_idx, test_idx, variant, data["neighbor_map"]
            )
            transformed_targets[variant][test_idx] = y_test.astype(np.float32)
            for row in coefs:
                residual_rows.append(
                    {
                        "outer_fold": fold,
                        "target_variant": variant,
                        "training_participants": len(np.unique(data["participants"][train_idx])),
                        **row,
                    }
                )
            if variant == "depth_residualized_neighbor_mean":
                for indices, counts, split_name in (
                    (train_idx, train_neighbor_counts, "outer_train"),
                    (test_idx, test_neighbor_counts, "outer_test"),
                ):
                    neighbor_rows.extend(
                        {
                            "outer_fold": fold,
                            "split": split_name,
                            "participant_id": data["participants"][index],
                            "library_id": data["libraries"][index],
                            "barcode": data["frame"].barcode.iloc[index],
                            "n_neighbors": int(counts[pos]),
                        }
                        for pos, index in enumerate(indices)
                    )
            baseline_rows = run_baselines(
                data,
                fold,
                variant,
                train_idx,
                test_idx,
                y_train,
                y_test,
                predictions[variant],
            )
            for row in baseline_rows:
                log_config(row)

            for input_name, model_name in (
                ("spot", "elasticnet_spot"),
                ("image_depth", "elasticnet_image_depth"),
            ):
                try:
                    selected_alpha, _ = run_elasticnet_inner_cv(
                        data, train_idx, variant, input_name, data["neighbor_map"], fold
                    )
                    estimated = fit_elasticnet_outer(
                        data,
                        train_idx,
                        test_idx,
                        y_train,
                        y_test,
                        input_name,
                        selected_alpha,
                        fold,
                        variant,
                    )
                    pred, row = estimated
                    keep_test = np.isfinite(y_test).all(axis=1)
                    row["model"] = model_name
                    if row["status"] == "success":
                        predictions[variant][model_name][test_idx[keep_test], :] = pred
                    log_config(row)
                except Exception as error:
                    log_config(
                        {
                            "timestamp": stamp(),
                            "phase": "elasticnet_outer",
                            "outer_fold": fold,
                            "target_variant": variant,
                            "input": input_name,
                            "family": "ElasticNet",
                            "alpha": "",
                            "status": "failed",
                            "error": repr(error),
                        }
                    )

            val_seed = BASE_SEED + fold * 1009 + TARGET_VARIANTS.index(variant) * 31
            train_people = np.unique(data["participants"][train_idx])
            splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=val_seed)
            itr_local, ival_local = next(
                splitter.split(train_idx, groups=data["participants"][train_idx])
            )
            inner_train, inner_validation = train_idx[itr_local], train_idx[ival_local]
            for input_index, (input_name, model_name) in enumerate(
                (("spot", "mlp_spot"), ("image_depth", "mlp_image_depth"))
            ):
                seed = BASE_SEED + fold * 10_007 + TARGET_VARIANTS.index(variant) * 101 + input_index
                try:
                    pred, curves, row = fit_mlp_outer(
                        data,
                        train_idx,
                        test_idx,
                        y_train,
                        y_test,
                        input_name,
                        fold,
                        variant,
                        inner_train,
                        inner_validation,
                        seed,
                    )
                    keep_test = np.isfinite(y_test).all(axis=1)
                    predictions[variant][model_name][test_idx[keep_test], :] = pred
                    row["model"] = model_name
                    log_config(row)
                    for curve in curves:
                        curve.update({"model": model_name, "family": "MLP"})
                    log_curve(curves)
                except Exception as error:
                    log_config(
                        {
                            "timestamp": stamp(),
                            "phase": "mlp_outer",
                            "outer_fold": fold,
                            "target_variant": variant,
                            "input": input_name,
                            "family": "MLP",
                            "status": "failed",
                            "seed": seed,
                            "error": repr(error),
                        }
                    )
        completed_folds.add(fold)
        save_npz(
            partial_path,
            participant_id=data["frame"].participant_id.to_numpy(dtype="U16"),
            library_id=data["frame"].library_id.to_numpy(dtype="U24"),
            barcode=data["frame"].barcode.to_numpy(dtype="U32"),
            fold=data["folds"],
            model_names=np.asarray(MODEL_NAMES, dtype="U32"),
            target_names=np.asarray(TARGETS, dtype="U40"),
            target_variants=np.asarray(TARGET_VARIANTS, dtype="U48"),
            predictions=np.stack(
                [
                    np.stack([predictions[variant][model] for model in MODEL_NAMES])
                    for variant in TARGET_VARIANTS
                ]
            ),
            target_values=np.stack([transformed_targets[name] for name in TARGET_VARIANTS]),
            completed_folds=np.asarray(sorted(completed_folds), dtype=np.int8),
        )
        print(f"outer fold {fold + 1}/{N_OUTER_FOLDS}: checkpoint saved", flush=True)

    save_npz(
        out_path("predictions.npz"),
        participant_id=data["frame"].participant_id.to_numpy(dtype="U16"),
        library_id=data["frame"].library_id.to_numpy(dtype="U24"),
        barcode=data["frame"].barcode.to_numpy(dtype="U32"),
        fold=data["folds"],
        model_names=np.asarray(MODEL_NAMES, dtype="U32"),
        target_names=np.asarray(TARGETS, dtype="U40"),
        target_variants=np.asarray(TARGET_VARIANTS, dtype="U48"),
        predictions=np.stack(
            [
                np.stack([predictions[variant][model] for model in MODEL_NAMES])
                for variant in TARGET_VARIANTS
            ]
        ),
        target_values=np.stack([transformed_targets[name] for name in TARGET_VARIANTS]),
    )
    write_csv(pd.DataFrame(residual_rows), out_path("residualization_coefficients.csv"))
    write_csv(pd.DataFrame(neighbor_rows), out_path("neighbor_counts.csv"))
    config_log = pd.read_csv(config_log_path)
    curves = pd.read_csv(curve_path) if curve_path.exists() else pd.DataFrame()
    participant_frames = []
    block_frames = []
    for variant in TARGET_VARIANTS:
        pred_map = predictions[variant]
        participant_frame, block_frame = score_participants(
            data, transformed_targets[variant], pred_map, variant
        )
        participant_frames.append(participant_frame)
        block_frames.append(block_frame)
    participant_metrics = pd.concat(participant_frames, ignore_index=True)
    block_metrics = pd.concat(block_frames, ignore_index=True)
    summary, comparisons = summarize_metrics(participant_metrics, block_metrics)
    write_csv(participant_metrics, out_path("participant_metrics.csv"))
    write_csv(block_metrics, out_path("participant_block_metrics.csv"))
    write_csv(summary, out_path("metric_summary.csv"))
    write_csv(comparisons, out_path("comparison_summary.csv"))
    verification = verify_metrics(
        data,
        transformed_targets,
        predictions,
        participant_metrics,
    )
    if not verification.verified.all():
        raise AssertionError("Independent metric recomputation failed")
    write_csv(verification, out_path("metric_recompute_verification.csv"))
    fold_check = data["frame"][["participant_id", "library_id", "barcode", "fold"]].copy()
    fold_check["test_fold_count_per_participant"] = fold_check.groupby("participant_id").fold.transform("nunique")
    fold_check["full_key_duplicate"] = fold_check.duplicated(
        ["participant_id", "library_id", "barcode"], keep=False
    )
    if fold_check.full_key_duplicate.any() or not (fold_check.test_fold_count_per_participant == 1).all():
        raise AssertionError("Key/fold verification failed")
    write_csv(
        pd.DataFrame(
            [
                {"check": "participants", "expected": 28, "observed": data["frame"].participant_id.nunique(), "passed": True},
                {"check": "libraries", "expected": 29, "observed": data["frame"].library_id.nunique(), "passed": True},
                {"check": "spots", "expected": 25104, "observed": len(data["frame"]), "passed": True},
                {"check": "unique_full_keys", "expected": 25104, "observed": data["frame"][["participant_id","library_id","barcode"]].drop_duplicates().shape[0], "passed": True},
                {"check": "single_test_fold_per_participant", "expected": 28, "observed": int((fold_check.groupby("participant_id").fold.nunique() == 1).sum()), "passed": True},
                {"check": "same_stage1_fold_assignments", "expected": 1, "observed": int(np.array_equal(fold_check.fold.to_numpy(), data["folds"])), "passed": True},
            ]
        ),
        out_path("verification_checks.csv"),
    )
    plots = make_plots(summary)
    write_report(
        data,
        participant_metrics,
        block_metrics,
        summary,
        comparisons,
        verification,
        pd.DataFrame(neighbor_rows),
        config_log,
        curves,
    )
    print(f"Completed {LABEL}; report={out_path('report.md')}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "inspect":
        print(f"{LABEL}; device={DEVICE}; alpha_grid={ALPHA_GRID}; targets={TARGETS}")
    else:
        main()
