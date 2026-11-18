"""Fit and freeze Stage 1d comparison Ridge baselines on the original cohort only."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge


ROOT = Path(r"D:\patent")
OUT = ROOT / "stage1d_freeze_baselines"
STAGE1 = ROOT / "stage1_expression"
STAGE1B = ROOT / "stage1b_expression"
STAGE1D = ROOT / "stage1d_freeze"
STAGE1B_SCRIPT = STAGE1B / "scripts" / "run_stage1b.py"
STAGE1_SCRIPT = STAGE1 / "scripts" / "run_stage1.py"
ADDENDUM_PATH = OUT / "PREREG_ADDENDUM_2.md"
MODEL_PATH = OUT / "frozen_ridge_models.joblib"
SCALERS_PATH = OUT / "baseline_scalers.npz"
FEATURES_PATH = OUT / "baseline_feature_definitions.json"
COEFFICIENTS_PATH = OUT / "baseline_coefficients.csv"
SCALER_TABLE_PATH = OUT / "baseline_scaler_values.csv"
TARGET_PARAMS_PATH = OUT / "target_residualization_parameters.csv"
IN_PROCESS_PATH = OUT / "in_process_predictions.npz"
RELOAD_PATH = OUT / "reload_predictions.npz"
VERIFICATION_PATH = OUT / "reload_verification.json"
REPORT_PATH = OUT / "STAGE1D_PREP2_REPORT.md"
MANIFEST_PATH = OUT / "MODEL_MANIFEST.csv"
NOTEBOOK_PATH = STAGE1D / "LAB_NOTEBOOK.md"
FROZEN_RESIDUALIZATION_PATH = STAGE1D / "residualization_parameters.csv"
FROZEN_SCALERS_PATH = STAGE1D / "frozen_scalers.npz"
CONFIRM_PATH = ROOT / "stage1c_confirm" / "PREREG_CONFIRM.md"
TARGET_VARIANT = "depth_residualized_neighbor_mean"
MODEL_INPUTS = {
    "depth_only_ridge": ("depth_only", ["log1p_total_spot_umi"]),
    "color_only_ridge": (
        "color_only",
        [
            "rgb_mean_r",
            "rgb_mean_g",
            "rgb_mean_b",
            "rgb_std_r",
            "rgb_std_g",
            "rgb_std_b",
            "hsv_mean_h",
            "hsv_mean_s",
            "hsv_mean_v",
            "hsv_std_h",
            "hsv_std_s",
            "hsv_std_v",
        ],
    ),
}
EXPECTED_HASHES = {
    str(CONFIRM_PATH): "23238d3727ab2a4102bfdc7a558df90100692d14bf8b014b05eef08253e0f729",
    str(STAGE1B_SCRIPT): "2a92cc16250d963c30b71375d6ace22f4d54bda547433bd31621029ad81d89d0",
    str(STAGE1_SCRIPT): "fc4a8e1eeee18b79b029aa5ecf1fb97ccf4a99d4fbe11f16a28d2e766a9b8d4c",
    str(STAGE1 / "targets_by_spot.csv"): "8dade8a328018e49c2c4bc6d5e63aed1347c18d03eba6ce295356add27fd2aa6",
    str(STAGE1 / "color_statistics.npz"): "f0d5d4ecf14f646f8347ba2374bc645f22973d1e824038cac984e2d9736d6264",
    str(FROZEN_SCALERS_PATH): "bdf441fb6d6640bfa419799d43ba50bd33965856770ec6e8a27e54daf6ce5409",
    str(FROZEN_RESIDUALIZATION_PATH): "d3be232fc951b36b33fccf68ecfe4c6d4e6d2914e4015208d58084ce2d9c5157",
}
BASELINE_MODELS = ("depth_only_ridge", "color_only_ridge")


def now_text() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_stage1b() -> Any:
    spec = importlib.util.spec_from_file_location("stage1b_baseline_source", STAGE1B_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load Stage 1b source: {STAGE1B_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def assert_fixed_sources() -> dict[str, str]:
    actual: dict[str, str] = {}
    for path_text, expected in EXPECTED_HASHES.items():
        path = Path(path_text)
        if not path.is_file():
            raise FileNotFoundError(f"Required fixed source is missing: {path}")
        actual[path_text] = sha256_file(path)
        if actual[path_text] != expected:
            raise AssertionError(f"Fixed source hash changed: {path}")
    prereg = CONFIRM_PATH.read_text(encoding="utf-8")
    prereg_lower = prereg.casefold()
    if "depth-only baseline" not in prereg_lower or "color-only baseline" not in prereg_lower:
        raise AssertionError("Confirmation protocol no longer names both frozen baselines")
    return actual


def prepare_data(stage1b: Any) -> tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray]:
    data = stage1b.load_inputs()
    frame = data["frame"]
    keys = data["keys"]
    if (
        frame["participant_id"].nunique() != 28
        or frame["library_id"].nunique() != 29
        or len(frame) != 25_104
        or len(set(keys)) != 25_104
    ):
        raise AssertionError("Original Stage 1 cohort/key reconciliation failed")
    if list(stage1b.TARGETS) != [
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
    ]:
        raise AssertionError("Stage 1b target order differs from the frozen addendum")
    if set(frame["participant_id"].astype(str)) != set(data["participants"]):
        raise AssertionError("Loaded rows do not reconcile to their participant identifiers")
    color_archive = np.load(STAGE1 / "color_statistics.npz", allow_pickle=False)
    if color_archive["feature_names"].astype(str).tolist() != MODEL_INPUTS["color_only_ridge"][1]:
        raise AssertionError("Saved colour feature names/order differ from registration")
    if color_archive["features"].shape != (25_104, 12):
        raise AssertionError("Unexpected Stage 1 colour-statistic shape")

    all_indices = np.arange(len(frame), dtype=np.int64)
    neighbor_map = stage1b.build_neighbor_map(
        data["libraries"], data["array_row"], data["array_col"]
    )
    transformed, _, _, _, coefficients = stage1b.targets_for_split(
        data,
        all_indices,
        all_indices,
        TARGET_VARIANT,
        neighbor_map,
    )
    finite_rows = np.isfinite(transformed).all(axis=1)
    if int(finite_rows.sum()) != 25_092 or (~finite_rows).sum() != 12:
        raise AssertionError(
            f"Finite target mask differs from frozen MLP: {int(finite_rows.sum())} rows"
        )
    if set(data["participants"][finite_rows]) != set(data["participants"]):
        raise AssertionError("At least one original participant has no fit rows")

    participants = data["participants"][finite_rows]
    weights = stage1b.participant_weights(participants)
    target_scaled, _, target_mean, target_scale = stage1b.weighted_standardize(
        transformed[finite_rows].astype(np.float64),
        transformed[finite_rows].astype(np.float64),
        weights,
    )
    with np.load(FROZEN_SCALERS_PATH, allow_pickle=False) as frozen:
        if frozen["target_names"].astype(str).tolist() != list(stage1b.TARGETS):
            raise AssertionError("Frozen MLP target names/order differ")
        differences = [
            float(np.max(np.abs(frozen["target_mean"] - target_mean))),
            float(np.max(np.abs(frozen["target_scale"] - target_scale))),
        ]
    if max(differences) > 1e-12:
        raise AssertionError(
            "Baseline target scaling does not match the frozen MLP; "
            f"max mean/scale differences={differences}"
        )
    return (
        {**data, "target_residualization_coefficients": coefficients},
        transformed,
        finite_rows,
        target_scaled,
    )


def save_target_residualization_parameters() -> None:
    shutil.copy2(FROZEN_RESIDUALIZATION_PATH, TARGET_PARAMS_PATH)
    if sha256_file(TARGET_PARAMS_PATH) != sha256_file(FROZEN_RESIDUALIZATION_PATH):
        raise AssertionError("Copied target residualization parameters changed")


def fit_models(
    stage1b: Any,
    data: dict[str, Any],
    transformed: np.ndarray,
    finite_rows: np.ndarray,
    target_scaled: np.ndarray,
) -> dict[str, Any]:
    finite_indices = np.flatnonzero(finite_rows)
    participants = data["participants"][finite_rows]
    weights = stage1b.participant_weights(participants)
    target_values = transformed[finite_rows].astype(np.float64)
    _, _, target_mean, target_scale = stage1b.weighted_standardize(
        target_values, target_values, weights
    )
    target_names = list(stage1b.TARGETS)
    models: dict[str, Ridge] = {}
    scaler_arrays: dict[str, np.ndarray] = {
        "target_mean": target_mean,
        "target_scale": target_scale,
        "target_names": np.asarray(target_names, dtype="U40"),
    }
    scaler_rows: list[dict[str, Any]] = []
    coefficient_rows: list[dict[str, Any]] = []
    predictions: dict[str, np.ndarray] = {}
    feature_names_by_model: dict[str, list[str]] = {}

    for model_name, (input_name, feature_names) in MODEL_INPUTS.items():
        x_all = stage1b.feature_matrix(data, input_name, np.arange(len(data["frame"])))
        x_train = x_all[finite_rows].astype(np.float64)
        x_scaled, _, x_mean, x_scale = stage1b.weighted_standardize(
            x_train, x_train, weights
        )
        model = Ridge(alpha=1.0)
        model.fit(x_scaled, target_scaled, sample_weight=weights)
        models[model_name] = model
        feature_names_by_model[model_name] = list(feature_names)
        scaler_arrays[f"{model_name}_feature_mean"] = x_mean
        scaler_arrays[f"{model_name}_feature_scale"] = x_scale
        for index, name in enumerate(feature_names):
            scaler_rows.append(
                {
                    "model": model_name,
                    "kind": "input",
                    "feature_or_target": name,
                    "weighted_mean": float(x_mean[index]),
                    "weighted_scale": float(x_scale[index]),
                }
            )
        for index, name in enumerate(target_names):
            scaler_rows.append(
                {
                    "model": model_name,
                    "kind": "target",
                    "feature_or_target": name,
                    "weighted_mean": float(target_mean[index]),
                    "weighted_scale": float(target_scale[index]),
                }
            )
        for output_index, target_name in enumerate(target_names):
            coefficient_rows.append(
                {
                    "model": model_name,
                    "target": target_name,
                    "feature": "__intercept__",
                    "coefficient_standardized_space": float(model.intercept_[output_index]),
                }
            )
            for feature_index, feature_name in enumerate(feature_names):
                coefficient_rows.append(
                    {
                        "model": model_name,
                        "target": target_name,
                        "feature": feature_name,
                        "coefficient_standardized_space": float(
                            model.coef_[output_index, feature_index]
                        ),
                    }
                )
        x_scaled_all = (x_all.astype(np.float64) - x_mean) / x_scale
        predictions[model_name] = (
            model.predict(x_scaled_all) * target_scale + target_mean
        )

    joblib.dump(
        {
            "models": models,
            "feature_names": feature_names_by_model,
            "target_names": target_names,
            "alpha": 1.0,
            "target_variant": TARGET_VARIANT,
        },
        MODEL_PATH,
        compress=3,
    )
    np.savez_compressed(SCALERS_PATH, **scaler_arrays)
    pd.DataFrame(scaler_rows).to_csv(SCALER_TABLE_PATH, index=False)
    pd.DataFrame(coefficient_rows).to_csv(COEFFICIENTS_PATH, index=False)
    np.savez_compressed(
        IN_PROCESS_PATH,
        participant_id=np.asarray([key[0] for key in data["keys"]], dtype="U32"),
        library_id=np.asarray([key[1] for key in data["keys"]], dtype="U64"),
        barcode=np.asarray([key[2] for key in data["keys"]], dtype="U64"),
        target_names=np.asarray(target_names, dtype="U40"),
        predictions_depth_only_ridge=predictions["depth_only_ridge"],
        predictions_color_only_ridge=predictions["color_only_ridge"],
    )
    return {
        "models": models,
        "feature_names": feature_names_by_model,
        "target_names": target_names,
        "scalers": scaler_arrays,
        "predictions": predictions,
        "fit_rows": int(len(finite_indices)),
    }


def predict_from_saved(stage1b: Any) -> tuple[list[tuple[str, str, str]], dict[str, np.ndarray]]:
    data = stage1b.load_inputs()
    keys = data["keys"]
    all_indices = np.arange(len(data["frame"]))
    bundle = joblib.load(MODEL_PATH)
    with np.load(SCALERS_PATH, allow_pickle=False) as scalers:
        output: dict[str, np.ndarray] = {}
        for model_name, (input_name, feature_names) in MODEL_INPUTS.items():
            if bundle["feature_names"][model_name] != feature_names:
                raise AssertionError(f"Reloaded feature order differs for {model_name}")
            x = stage1b.feature_matrix(data, input_name, all_indices).astype(np.float64)
            mean = scalers[f"{model_name}_feature_mean"]
            scale = scalers[f"{model_name}_feature_scale"]
            standardized = (x - mean) / scale
            standardized_prediction = bundle["models"][model_name].predict(standardized)
            output[model_name] = (
                standardized_prediction * scalers["target_scale"] + scalers["target_mean"]
            )
    np.savez_compressed(
        RELOAD_PATH,
        participant_id=np.asarray([key[0] for key in keys], dtype="U32"),
        library_id=np.asarray([key[1] for key in keys], dtype="U64"),
        barcode=np.asarray([key[2] for key in keys], dtype="U64"),
        target_names=np.asarray(bundle["target_names"], dtype="U40"),
        predictions_depth_only_ridge=output["depth_only_ridge"],
        predictions_color_only_ridge=output["color_only_ridge"],
    )
    return keys, output


def verify_reload() -> None:
    stage1b = load_stage1b()
    keys, predictions = predict_from_saved(stage1b)
    with np.load(IN_PROCESS_PATH, allow_pickle=False) as reference:
        reference_keys = list(
            zip(
                reference["participant_id"].astype(str),
                reference["library_id"].astype(str),
                reference["barcode"].astype(str),
            )
        )
        if reference_keys != keys:
            raise AssertionError("Fresh-process key sequence differs from in-process output")
        details = {}
        for model_name in BASELINE_MODELS:
            reference_values = reference[f"predictions_{model_name}"]
            max_difference = float(
                np.max(np.abs(predictions[model_name] - reference_values))
            )
            details[model_name] = {
                "max_absolute_difference": max_difference,
                "bitwise_identical": bool(
                    np.array_equal(predictions[model_name], reference_values)
                ),
            }
    report = {
        "fresh_process": True,
        "original_participants": 28,
        "original_libraries": 29,
        "original_spots": len(keys),
        "finite_target_fit_rows": 25_092,
        "predictions_recomputed_for_all_original_spots": True,
        "models": details,
        "performance_evaluation_performed": False,
    }
    VERIFICATION_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not all(item["bitwise_identical"] for item in details.values()):
        raise AssertionError(f"Fresh-process prediction mismatch: {details}")


def write_feature_definitions(source_hashes: dict[str, str], fit_timestamp: str) -> None:
    payload = {
        "fit_timestamp": fit_timestamp,
        "target_variant": TARGET_VARIANT,
        "fit_cohort": {
            "participants": 28,
            "libraries": 29,
            "spots": 25_104,
            "finite_target_fit_rows": 25_092,
            "excluded_no_neighbor_rows": 12,
            "key": ["participant_id", "library_id", "barcode"],
        },
        "models": {
            "depth_only_ridge": {
                "input": "log1p(library_size_umi), from the per-spot total UMI field",
                "feature_names": MODEL_INPUTS["depth_only_ridge"][1],
                "estimator": "sklearn.linear_model.Ridge",
                "alpha": 1.0,
                "alpha_selection": "fixed; no selection",
                "participant_weighting": "1 / finite training rows per participant, normalized to mean 1",
                "scaling": "weighted mean and population standard deviation; scales below 1e-12 or non-finite replaced by 1",
                "seed": None,
            },
            "color_only_ridge": {
                "input": "Stage 1 color_statistics(rgb) features on each RGB spot tile",
                "feature_function": str(STAGE1_SCRIPT) + ":color_statistics",
                "feature_names": MODEL_INPUTS["color_only_ridge"][1],
                "pixel_input": "PIL RGB conversion to uint8; raw RGB values and cv2.COLOR_RGB2HSV output; statistics over axes (0, 1)",
                "statistics": "per-channel mean and population standard deviation; no additional normalization",
                "estimator": "sklearn.linear_model.Ridge",
                "alpha": 1.0,
                "alpha_selection": "fixed; no selection",
                "participant_weighting": "1 / finite training rows per participant, normalized to mean 1",
                "scaling": "weighted mean and population standard deviation; scales below 1e-12 or non-finite replaced by 1",
                "seed": None,
            },
        },
        "target_names": [
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
        ],
        "target_scaling": "same weighted scaling as frozen MLP; verified within 1e-12",
        "randomness": "Ridge fitting and preprocessing are deterministic; no RNG seed is used",
        "source_sha256": source_hashes,
        "performance_evaluation_performed": False,
        "extra_participant_data_opened_or_used": False,
    }
    FEATURES_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_report(
    fit_timestamp: str,
    fit_rows: int,
    source_hashes: dict[str, str],
    verification: dict[str, Any],
) -> None:
    report = [
        "# Stage 1d-prep-2 — frozen comparison baselines",
        "",
        f"**Fit timestamp:** {fit_timestamp}",
        "**Status:** comparison baselines frozen; Stage 1d evaluation not started.",
        "**Stage 1 Gate A:** remains FAIL. Stage 1b remains exploratory, post-hoc.",
        "",
        "## What was frozen",
        "",
        "- Fitted depth-only Ridge (`alpha=1`) and colour-only Ridge (`alpha=1`) exactly as the Stage 1b fixed-baseline implementation, using `depth_residualized_neighbor_mean` targets.",
        "- Training used only the original 28 participants, 29 libraries, and 25,092 finite-target rows out of 25,104 keyed spots. Twelve rows with no available neighbor were omitted without imputation.",
        "- Both multi-output baselines retain the 12 Stage 1b targets in the registered order. The primary confirmation target is `myofibroblast_pro-fibrotic`.",
        "- Target scaling was checked against the frozen MLP target scaler; maximum difference was at most 1e-12.",
        "- Colour features are computed by `color_statistics(rgb)` in `run_stage1.py`; feature names, pixel value ranges, and parameters are recorded in `baseline_feature_definitions.json`.",
        "- No model performance was computed or reported. No data for the 12 extra participants was opened, downloaded, or used.",
        "",
        "## Fresh-process reload verification",
        "",
        f"- Reloaded predictions cover all {verification['original_spots']:,} original spot keys in the same order.",
        f"- Depth-only Ridge: bitwise identical = {verification['models']['depth_only_ridge']['bitwise_identical']}; maximum absolute difference = {verification['models']['depth_only_ridge']['max_absolute_difference']:.17g}.",
        f"- Colour-only Ridge: bitwise identical = {verification['models']['color_only_ridge']['bitwise_identical']}; maximum absolute difference = {verification['models']['color_only_ridge']['max_absolute_difference']:.17g}.",
        "- This is a serialization/reproducibility check, not a performance evaluation.",
        "",
        "## Source hashes",
        "",
    ]
    report.extend(f"- `{path}` — `{digest}`" for path, digest in source_hashes.items())
    report.extend(
        [
            "",
            "The complete artifact and source-reference SHA-256 inventory is in `MODEL_MANIFEST.csv`. The manifest excludes itself; its hash is recorded in the append-only Stage 1d lab notebook.",
            "",
            "## Deviations and remaining limits",
            "",
            "- No deviations from the frozen baseline definitions were found.",
            "- No confirmation-cohort files or outcomes were used. Stage 1d evaluation remains unrun and awaits explicit instruction.",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(report), encoding="utf-8")


def write_manifest(source_hashes: dict[str, str]) -> str:
    rows: list[dict[str, Any]] = []
    for path in sorted(OUT.iterdir()):
        if not path.is_file() or path == MANIFEST_PATH:
            continue
        rows.append(
            {
                "record_type": "artifact",
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "description": path.name,
            }
        )
    for path in (Path(path_text) for path_text in source_hashes):
        if not path.is_file():
            raise FileNotFoundError(f"Manifest source is missing: {path}")
        rows.append(
            {
                "record_type": "source_reference",
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "description": "Original-cohort source or frozen target definition",
            }
        )
    pd.DataFrame(rows).to_csv(MANIFEST_PATH, index=False)
    return sha256_file(MANIFEST_PATH)


def append_notebook(manifest_hash: str) -> None:
    if not NOTEBOOK_PATH.is_file():
        raise FileNotFoundError(f"Append-only lab notebook is missing: {NOTEBOOK_PATH}")
    if NOTEBOOK_PATH.stat().st_mode & 0o222 == 0:
        raise PermissionError(f"Lab notebook is not writable: {NOTEBOOK_PATH}")
    manifest = pd.read_csv(MANIFEST_PATH)
    lines = [
        "",
        "",
        "## 2026-11-13 — Stage 1d-prep-2 comparison baselines",
        "",
        "- Registered `stage1d_freeze_baselines\\PREREG_ADDENDUM_2.md` before fitting. Frozen definitions: Stage 1b depth-only and colour-only Ridge, both alpha=1, on the original 28 participants only.",
        "- Fit both models on the same 25,092 finite `depth_residualized_neighbor_mean` rows as the frozen MLP; no Stage 1d metrics were computed and no extra-participant data was accessed.",
        "- Fresh-process reload predictions were bitwise identical for both baselines; see the prep-2 report and `reload_verification.json`.",
        "",
        "### Stage 1d-prep-2 artifact SHA-256",
        "",
        "| Path | SHA-256 |",
        "|---|---|",
    ]
    for row in manifest.itertuples(index=False):
        if row.record_type == "artifact":
            lines.append(f"| `{row.path}` | `{row.sha256}` |")
    lines.extend(
        [
            f"| `MODEL_MANIFEST.csv` | `{manifest_hash}` |",
            "",
            "The manifest excludes itself and this append-only notebook to avoid recursive checksums.",
            "",
        ]
    )
    with NOTEBOOK_PATH.open("a", encoding="utf-8", newline="") as stream:
        stream.write("\n".join(lines))


def verify_manifest() -> None:
    manifest = pd.read_csv(MANIFEST_PATH, dtype={"path": str, "sha256": str})
    for row in manifest.itertuples(index=False):
        path = Path(row.path)
        if not path.is_file() or path.stat().st_size != int(row.size_bytes):
            raise AssertionError(f"Manifest path/size mismatch: {path}")
        if sha256_file(path) != row.sha256:
            raise AssertionError(f"Manifest SHA-256 mismatch: {path}")


def fit_once() -> None:
    addendum = ADDENDUM_PATH.read_text(encoding="utf-8")
    if "**Registered:** 2026-11-13T10:39:43+05:30" not in addendum:
        raise AssertionError("Timestamped addendum is missing or changed")
    fit_timestamp = now_text()
    source_hashes = assert_fixed_sources()
    stage1b = load_stage1b()
    data, transformed, finite_rows, target_scaled = prepare_data(stage1b)
    fit_results = fit_models(stage1b, data, transformed, finite_rows, target_scaled)
    save_target_residualization_parameters()
    write_feature_definitions(source_hashes, fit_timestamp)

    command = [sys.executable, str(Path(__file__).resolve()), "--verify-reload"]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "Fresh-process reload verification failed.\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    verification = json.loads(VERIFICATION_PATH.read_text(encoding="utf-8"))
    if not all(item["bitwise_identical"] for item in verification["models"].values()):
        raise AssertionError("Fresh-process predictions differ from in-process predictions")
    write_report(fit_timestamp, fit_results["fit_rows"], source_hashes, verification)
    manifest_hash = write_manifest(source_hashes)
    append_notebook(manifest_hash)
    verify_manifest()
    for path in OUT.iterdir():
        if path.is_file():
            path.chmod(path.stat().st_mode & ~0o222)
    verify_manifest()
    print(
        json.dumps(
            {
                "fit_timestamp": fit_timestamp,
                "participants": 28,
                "libraries": 29,
                "spots": 25_104,
                "fit_rows": fit_results["fit_rows"],
                "verification": verification["models"],
                "manifest_sha256": manifest_hash,
                "all_output_files_read_only": True,
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-reload", action="store_true")
    args = parser.parse_args()
    if args.verify_reload:
        verify_reload()
    else:
        fit_once()


if __name__ == "__main__":
    main()
