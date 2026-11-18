"""Fit the preregistered full-cohort Stage 1d confirmation candidate once."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch


ROOT = Path(r"D:\patent")
OUT = ROOT / "stage1d_freeze"
STAGE1 = ROOT / "stage1_expression"
STAGE1B = ROOT / "stage1b_expression"
STAGE1B_SCRIPT = STAGE1B / "scripts" / "run_stage1b.py"
CONFIG_LOG = STAGE1B / "exploratory_posthoc_configuration_log.csv"
CONFIRM_PREREG = ROOT / "stage1c_confirm" / "PREREG_CONFIRM.md"
ENCODER_CHECKPOINT = (
    STAGE1 / "model_cache" / "checkpoints" / "resnet50-11ad3fa6.pth"
)

TARGET_VARIANT = "depth_residualized_neighbor_mean"
MODEL_NAME = "mlp_spot"
INPUT_NAME = "spot"
SEED = 20261113
EPOCHS = 1
BATCH_SIZE = 1024
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

MODEL_PATH = OUT / "frozen_model_state.pt"
SCALERS_PATH = OUT / "frozen_scalers.npz"
RESIDUALIZATION_PATH = OUT / "residualization_parameters.csv"
FEATURE_NAMES_PATH = OUT / "input_feature_names.json"
ENCODER_REFERENCE_PATH = OUT / "encoder_reference.json"
METADATA_PATH = OUT / "training_metadata.json"
IN_PROCESS_PREDICTIONS_PATH = OUT / "in_process_predictions.npz"
RELOAD_PREDICTIONS_PATH = OUT / "reload_predictions.npz"
RELOAD_VERIFICATION_PATH = OUT / "reload_verification.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_stage1b() -> Any:
    spec = importlib.util.spec_from_file_location("stage1b_frozen_source", STAGE1B_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load Stage 1b source: {STAGE1B_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def assert_registered_epoch_rule() -> dict[str, Any]:
    ledger = pd.read_csv(CONFIG_LOG, dtype=str, keep_default_na=False)
    matching = ledger[
        (ledger["target_variant"] == TARGET_VARIANT)
        & (ledger["input"] == INPUT_NAME)
        & (ledger["model"] == MODEL_NAME)
        & (ledger["phase"] == "mlp_outer_fit")
        & (ledger["status"] == "success")
    ].copy()
    if len(matching) != 7:
        raise AssertionError(
            "Expected exactly seven successful matching outer-fit records; "
            f"found {len(matching)}"
        )
    matching["outer_fold"] = matching["outer_fold"].astype(int)
    matching["selected_best_epoch"] = matching["selected_best_epoch"].astype(int)
    matching = matching.sort_values("outer_fold")
    if matching["outer_fold"].tolist() != list(range(7)):
        raise AssertionError("Matching epoch records do not cover outer folds 0-6 once")
    epochs = matching["selected_best_epoch"].tolist()
    median_epoch = int(np.rint(np.median(epochs)))
    if median_epoch != EPOCHS:
        raise AssertionError(
            f"Registered epoch rule yields {median_epoch}, expected fixed {EPOCHS}"
        )
    return {
        "matching_outer_folds": matching["outer_fold"].tolist(),
        "selected_best_epoch_by_fold": epochs,
        "median_selected_best_epoch": float(np.median(epochs)),
        "rounded_epoch_count": median_epoch,
    }


def prepare_original_cohort(stage1b: Any) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    data = stage1b.load_inputs()
    frame = data["frame"]
    if (
        frame["participant_id"].nunique() != 28
        or frame["library_id"].nunique() != 29
        or len(frame) != 25_104
        or len(set(data["keys"])) != 25_104
    ):
        raise AssertionError("Original Stage 1 cohort/key reconciliation failed")
    if list(stage1b.TARGETS) != TARGET_NAMES:
        raise AssertionError("Stage 1b target order differs from frozen addendum")
    embeddings = data["embeddings"]
    if embeddings.shape != (25_104, 2048):
        raise AssertionError(f"Unexpected spot embedding shape: {embeddings.shape}")
    data["neighbor_map"] = stage1b.build_neighbor_map(
        data["libraries"], data["array_row"], data["array_col"]
    )
    indices = np.arange(len(frame), dtype=np.int64)
    transformed, _, neighbor_counts, _, coefficients = stage1b.targets_for_split(
        data, indices, indices, TARGET_VARIANT, data["neighbor_map"]
    )
    finite_rows = np.isfinite(transformed).all(axis=1)
    if not finite_rows.any():
        raise AssertionError("No complete finite neighbor-mean target rows")
    included_participants = set(data["participants"][finite_rows])
    all_participants = set(data["participants"])
    if included_participants != all_participants:
        raise AssertionError(
            "At least one original participant has no finite neighbor-mean training rows"
        )
    if not np.isfinite(embeddings).all():
        raise AssertionError("Non-finite spot embedding encountered")
    return {
        **data,
        "residualization_coefficients": coefficients,
        "neighbor_counts": neighbor_counts,
    }, transformed, finite_rows


def save_residualization_parameters(
    data: dict[str, Any], path: Path
) -> None:
    participants = data["participants"]
    targets = data["targets"]
    depth = data["depth"]
    weights = load_stage1b().participant_weights(participants)
    records: list[dict[str, Any]] = []
    coefficients_by_name = {
        row["target"]: row for row in data["residualization_coefficients"]
    }
    for column, target in enumerate(TARGET_NAMES):
        coefficient = coefficients_by_name[target]
        raw_residual = targets[:, column] - (
            float(coefficient["intercept"])
            + float(coefficient["depth_coefficient"]) * depth
        )
        records.append(
            {
                "parameter_type": "target_on_depth",
                "target": target,
                "participant_id": "",
                "intercept": coefficient["intercept"],
                "depth_coefficient": coefficient["depth_coefficient"],
                "participant_center": "",
                "depth_definition": "log1p(library_size_umi)",
            }
        )
        for participant in np.unique(participants):
            mask = participants == participant
            center = np.average(raw_residual[mask], weights=weights[mask])
            records.append(
                {
                    "parameter_type": "participant_residual_center",
                    "target": target,
                    "participant_id": str(participant),
                    "intercept": "",
                    "depth_coefficient": "",
                    "participant_center": float(center),
                    "depth_definition": "log1p(library_size_umi)",
                }
            )
    pd.DataFrame(records).to_csv(path, index=False)


def predict(
    stage1b: Any,
    model: torch.nn.Module,
    embeddings: np.ndarray,
    feature_mean: np.ndarray,
    feature_scale: np.ndarray,
    target_mean: np.ndarray,
    target_scale: np.ndarray,
) -> np.ndarray:
    x_scaled = ((embeddings - feature_mean) / feature_scale).astype(np.float32)
    model.eval()
    outputs = []
    with torch.inference_mode():
        for start in range(0, len(x_scaled), BATCH_SIZE):
            batch = torch.from_numpy(
                np.ascontiguousarray(x_scaled[start : start + BATCH_SIZE])
            ).to(stage1b.DEVICE)
            outputs.append(model(batch).cpu().numpy())
    standardized = np.concatenate(outputs, axis=0)
    return standardized * target_scale + target_mean


def save_keyed_predictions(
    path: Path, keys: list[tuple[str, str, str]], predictions: np.ndarray
) -> None:
    np.savez_compressed(
        path,
        participant_id=np.asarray([key[0] for key in keys], dtype="U32"),
        library_id=np.asarray([key[1] for key in keys], dtype="U64"),
        barcode=np.asarray([key[2] for key in keys], dtype="U64"),
        target_names=np.asarray(TARGET_NAMES, dtype="U40"),
        predictions=predictions,
    )


def verify_reload() -> None:
    stage1b = load_stage1b()
    data = stage1b.load_inputs()
    if len(data["frame"]) != 25_104 or data["frame"].participant_id.nunique() != 28:
        raise AssertionError("Reload process did not load exactly the original cohort")
    with np.load(SCALERS_PATH, allow_pickle=False) as archive:
        feature_mean = archive["feature_mean"]
        feature_scale = archive["feature_scale"]
        target_mean = archive["target_mean"]
        target_scale = archive["target_scale"]
        saved_feature_names = archive["feature_names"].astype(str).tolist()
        saved_target_names = archive["target_names"].astype(str).tolist()
    if saved_target_names != TARGET_NAMES or len(saved_feature_names) != 2048:
        raise AssertionError("Reloaded scaler feature/target order does not match")
    stage1b.seed_torch(SEED)
    model = stage1b.SmallMLP(len(saved_feature_names), len(TARGET_NAMES))
    state = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model = model.to(stage1b.DEVICE)
    predictions = predict(
        stage1b,
        model,
        data["embeddings"],
        feature_mean,
        feature_scale,
        target_mean,
        target_scale,
    )
    save_keyed_predictions(RELOAD_PREDICTIONS_PATH, data["keys"], predictions)
    with np.load(IN_PROCESS_PREDICTIONS_PATH, allow_pickle=False) as reference:
        reference_keys = list(
            zip(
                reference["participant_id"].astype(str),
                reference["library_id"].astype(str),
                reference["barcode"].astype(str),
            )
        )
        reference_predictions = reference["predictions"]
    if reference_keys != data["keys"]:
        raise AssertionError("Fresh-process key order differs from in-process output")
    max_abs_difference = float(np.max(np.abs(predictions - reference_predictions)))
    report = {
        "fresh_process": True,
        "participant_count": int(data["frame"].participant_id.nunique()),
        "library_count": int(data["frame"].library_id.nunique()),
        "spot_count": int(len(data["frame"])),
        "prediction_shape": list(predictions.shape),
        "max_absolute_difference": max_abs_difference,
        "bitwise_identical": bool(np.array_equal(predictions, reference_predictions)),
        "performance_evaluation_performed": False,
    }
    RELOAD_VERIFICATION_PATH.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    if not report["bitwise_identical"]:
        raise AssertionError(
            "Fresh-process predictions are not identical; "
            f"max absolute difference={max_abs_difference}"
        )


def train_once() -> None:
    epoch_rule = assert_registered_epoch_rule()
    stage1b = load_stage1b()
    data, transformed_targets, finite_rows = prepare_original_cohort(stage1b)
    participants = data["participants"][finite_rows]
    weights = stage1b.participant_weights(participants)
    x = data["embeddings"][finite_rows].astype(np.float64)
    y = transformed_targets[finite_rows].astype(np.float64)
    x_scaled, _, feature_mean, feature_scale = stage1b.weighted_standardize(
        x, x, weights
    )
    y_scaled, _, target_mean, target_scale = stage1b.weighted_standardize(
        y, y, weights
    )
    feature_names = [f"resnet50_spot_embedding_{i:04d}" for i in range(x.shape[1])]
    np.savez_compressed(
        SCALERS_PATH,
        feature_mean=feature_mean,
        feature_scale=feature_scale,
        target_mean=target_mean,
        target_scale=target_scale,
        feature_names=np.asarray(feature_names, dtype="U64"),
        target_names=np.asarray(TARGET_NAMES, dtype="U40"),
    )
    scaler_rows = [
        {
            "kind": "feature",
            "index": i,
            "name": name,
            "weighted_mean": float(feature_mean[i]),
            "weighted_scale": float(feature_scale[i]),
        }
        for i, name in enumerate(feature_names)
    ]
    scaler_rows.extend(
        {
            "kind": "target",
            "index": i,
            "name": name,
            "weighted_mean": float(target_mean[i]),
            "weighted_scale": float(target_scale[i]),
        }
        for i, name in enumerate(TARGET_NAMES)
    )
    pd.DataFrame(scaler_rows).to_csv(OUT / "frozen_scalers.csv", index=False)
    save_residualization_parameters(data, RESIDUALIZATION_PATH)
    FEATURE_NAMES_PATH.write_text(
        json.dumps(
            {
                "embedding": "torchvision ResNet-50 IMAGENET1K_V2 spot embedding",
                "dimension": len(feature_names),
                "features_in_order": feature_names,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    encoder_sha256 = sha256_file(ENCODER_CHECKPOINT)
    ENCODER_REFERENCE_PATH.write_text(
        json.dumps(
            {
                "checkpoint_path": str(ENCODER_CHECKPOINT),
                "size_bytes": ENCODER_CHECKPOINT.stat().st_size,
                "sha256": encoder_sha256,
                "weights": "torchvision ResNet-50 IMAGENET1K_V2",
                "role": "frozen encoder; Stage 1 spot embeddings already computed",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    stage1b.seed_torch(SEED)
    model = stage1b.SmallMLP(x.shape[1], len(TARGET_NAMES))
    selected_epoch, stopped_epoch, _curves, state = stage1b.fit_mlp_training(
        model,
        x_scaled.astype(np.float32),
        y_scaled.astype(np.float32),
        weights,
        SEED,
        EPOCHS,
    )
    if selected_epoch != EPOCHS or stopped_epoch != EPOCHS:
        raise AssertionError("Training did not follow the fixed single-epoch rule")
    model.load_state_dict(state)
    model = model.to(stage1b.DEVICE)
    model.eval()
    torch.save(
        {name: tensor.detach().cpu() for name, tensor in model.state_dict().items()},
        MODEL_PATH,
    )
    all_predictions = predict(
        stage1b,
        model,
        data["embeddings"],
        feature_mean,
        feature_scale,
        target_mean,
        target_scale,
    )
    save_keyed_predictions(IN_PROCESS_PREDICTIONS_PATH, data["keys"], all_predictions)
    frame = data["frame"]
    residual_params = pd.read_csv(RESIDUALIZATION_PATH)
    if len(residual_params) != len(TARGET_NAMES) * (1 + frame.participant_id.nunique()):
        raise AssertionError("Residualization parameter table is incomplete")
    metadata = {
        "registered_timestamp": "2026-11-13T10:25:53+05:30",
        "target_variant": TARGET_VARIANT,
        "model": MODEL_NAME,
        "input": INPUT_NAME,
        "architecture": {
            "input_features": 2048,
            "hidden_units": 128,
            "activation": "ReLU",
            "output_features": 12,
            "target_order": TARGET_NAMES,
        },
        "optimizer": "AdamW",
        "learning_rate": 1e-3,
        "weight_decay": 1e-4,
        "batch_size": BATCH_SIZE,
        "loss": "participant-balanced weighted MSE over 12 standardized outputs",
        "seed": SEED,
        "epochs": EPOCHS,
        "epoch_rule": epoch_rule,
        "training_cohort": {
            "participants": int(frame.participant_id.nunique()),
            "libraries": int(frame.library_id.nunique()),
            "input_spots": int(len(frame)),
            "finite_target_fit_rows": int(finite_rows.sum()),
            "spots_omitted_for_no_neighbor": int((~finite_rows).sum()),
            "unique_key": ["participant_id", "library_id", "barcode"],
        },
        "device": str(stage1b.DEVICE),
        "software": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": __import__("sklearn").__version__,
            "torch": torch.__version__,
        },
        "stage1b_source_sha256": sha256_file(STAGE1B_SCRIPT),
        "stage1b_configuration_log_sha256": sha256_file(CONFIG_LOG),
        "confirmation_preregistration_sha256": sha256_file(CONFIRM_PREREG),
        "encoder_checkpoint_sha256": encoder_sha256,
        "performance_evaluation_performed": False,
        "training_predictions_are_for_reload_equivalence_only": True,
    }
    (OUT / "training_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    command = [sys.executable, str(Path(__file__).resolve()), "--verify-reload"]
    subprocess.run(command, cwd=str(OUT), check=True)


def preflight() -> None:
    epoch_rule = assert_registered_epoch_rule()
    stage1b = load_stage1b()
    data, transformed_targets, finite_rows = prepare_original_cohort(stage1b)
    print(
        json.dumps(
            {
                "training_cohort": {
                    "participants": int(data["frame"].participant_id.nunique()),
                    "libraries": int(data["frame"].library_id.nunique()),
                    "input_spots": int(len(data["frame"])),
                    "finite_target_fit_rows": int(finite_rows.sum()),
                    "spots_omitted_for_no_neighbor": int((~finite_rows).sum()),
                },
                "embedding_shape": list(data["embeddings"].shape),
                "target_shape": list(transformed_targets.shape),
                "epoch_rule": epoch_rule,
                "training_performed": False,
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--verify-reload", action="store_true")
    group.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    if args.verify_reload:
        verify_reload()
    elif args.preflight:
        preflight()
    else:
        train_once()


if __name__ == "__main__":
    main()
