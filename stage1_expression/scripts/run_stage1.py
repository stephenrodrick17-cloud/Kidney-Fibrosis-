from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import shutil
import sys
import time
import warnings
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import cv2
import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr
from sklearn.linear_model import LinearRegression, Ridge, SGDRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.preprocessing import StandardScaler

ROOT = Path(r"D:\patent")
OUT = ROOT / "stage1_expression"
DATA = ROOT / "data"
PLAN = ROOT / "plan_a_plan_b"
QC = ROOT / "qc_collagen"
HELPER_PATH = ROOT / "analyze_cohort_plan_a_b.py"
TARGET_GENES = [
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
MODULES = {
    "ECM_collagen": ["COL1A1", "COL1A2", "COL3A1", "FN1"],
    "myofibroblast_pro-fibrotic": ["ACTA2", "TGFB1", "CCN2", "SERPINE1"],
    "matrix_remodelling": ["MMP2", "TIMP1"],
}
TARGETS = TARGET_GENES + list(MODULES)
MODEL_NAMES = [
    "patient_mean",
    "depth_only",
    "color_only",
    "elasticnet_spot",
    "mlp_spot",
    "elasticnet_context",
    "mlp_context",
]
TARGET_VARIANTS = ["raw", "residualized"]
EXPECTED_PARTICIPANTS = 28
EXPECTED_LIBRARIES = 29
EXPECTED_SPOTS = 25104
FOLD_SEED = 20261112
BOOTSTRAP_SEED = 20261113
PERMUTATION_SEED = 20261114
MODEL_SEED = 20261115
N_BOOTSTRAP = 10000
N_PERMUTATIONS = 1000
MIN_DETECTED_SPOTS = 10
MIN_DISTINCT_TARGET_VALUES = 3
BLOCK_WIDTH = 10
MAX_STEP_BYTES = 1_000_000_000

sys.path.insert(0, str(ROOT))
import analyze_cohort_plan_a_b as helper


def now_text() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def ensure_output_dir() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "scripts").mkdir(parents=True, exist_ok=True)
    (OUT / "plots").mkdir(parents=True, exist_ok=True)


def ensure_write_budget(estimated_bytes: int, step: str) -> None:
    if estimated_bytes < 0 or estimated_bytes >= MAX_STEP_BYTES:
        raise RuntimeError(f"{step} estimated write is not below the 1 GB limit: {estimated_bytes}")
    free = shutil.disk_usage(ROOT).free
    reserve = 512 * 1024 * 1024
    if free < estimated_bytes + reserve:
        raise RuntimeError(
            f"Stopping before {step}: estimated {estimated_bytes} bytes plus "
            f"{reserve} bytes reserve exceeds free space {free}"
        )


def write_csv_checked(frame: pd.DataFrame, path: Path) -> None:
    estimate = max(int(frame.memory_usage(index=True, deep=True).sum() * 2.5), 1024)
    ensure_write_budget(estimate, f"write {path.name}")
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    if path.stat().st_size >= MAX_STEP_BYTES:
        raise RuntimeError(f"Output exceeded the 1 GB limit: {path}")


def write_npz_checked(path: Path, **arrays: np.ndarray) -> None:
    estimated = sum(np.asarray(value).nbytes for value in arrays.values()) + 64 * 1024 * 1024
    ensure_write_budget(estimated, f"write {path.name}")
    np.savez_compressed(path, **arrays)
    if path.stat().st_size >= MAX_STEP_BYTES:
        raise RuntimeError(f"Output exceeded the 1 GB limit: {path}")


def canonical_source(value: object) -> str:
    return str(value).replace("/", "\\").casefold()


def library_identifier(source: object) -> str:
    digest = hashlib.sha256(canonical_source(source).encode("utf-8")).hexdigest()
    return f"lib_{digest[:16]}"


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    gene = pd.read_csv(QC / "gene_expression_by_spot.csv", dtype={"participant_id": str, "sample_id": str, "barcode": str})
    module = pd.read_csv(QC / "module_scores_by_spot.csv", dtype={"participant_id": str, "sample_id": str, "barcode": str})
    metadata = pd.read_csv(QC / "sample_metadata_audit.csv", dtype=str, keep_default_na=False)
    tiles = pd.read_csv(PLAN / "plan_b_tile_manifest.csv", dtype={"participant_id": str, "sample_id": str, "barcode": str})
    return gene, module, metadata, tiles


def collect_spatial_position_maps(metadata: pd.DataFrame) -> dict[tuple[str, str], dict[str, object]]:
    source_by_key = {
        (row.participant_id, row.sample_id): row.expression_source
        for row in metadata.itertuples(index=False)
    }
    if len(source_by_key) != len(metadata):
        raise ValueError("Sample metadata has duplicate participant/sample labels")

    mappings: dict[tuple[str, str], dict[str, object]] = {}
    for participant in sorted(metadata["participant_id"].unique()):
        participant_dir = DATA / participant
        expression_sources = helper.load_expression_sources(participant_dir)
        source_by_path = {
            canonical_source(source["path"].relative_to(ROOT)): source
            for source in expression_sources
        }
        spatial_samples = helper.find_spatial_samples(participant_dir)
        for sample_id, expression_source in (
            (sample_id, source_by_key[(participant, sample_id)])
            for pid, sample_id in source_by_key
            if pid == participant
        ):
            canonical = canonical_source(expression_source)
            if canonical not in source_by_path:
                raise ValueError(
                    f"{participant}/{sample_id}: metadata expression source is not readable "
                    f"through the verified helper: {expression_source}"
                )
            source = source_by_path[canonical]
            matched_samples = []
            for spatial in spatial_samples:
                positions = helper.read_positions(spatial["positions_path"])
                in_tissue = positions.loc[positions["in_tissue"].astype(int) == 1].copy()
                if in_tissue.empty:
                    continue
                spatial_barcodes = set(in_tissue["barcode"].astype(str))
                overlap = spatial_barcodes.intersection(set(source["barcodes"]))
                if overlap == spatial_barcodes:
                    matched_samples.append((spatial, in_tissue))
            if len(matched_samples) != 1:
                raise ValueError(
                    f"{participant}/{sample_id}: expected exactly one fully paired "
                    f"spatial-position file for {expression_source}, found {len(matched_samples)}"
                )
            spatial, positions = matched_samples[0]
            scale = json.loads(spatial["scale_path"].read_text(encoding="utf-8"))
            position_path = spatial["positions_path"].relative_to(ROOT)
            image_path = spatial["image_path"].relative_to(ROOT)
            if not {"array_row", "array_col"}.issubset(positions.columns):
                raise ValueError(f"{position_path}: array coordinates are unavailable for block null")
            for row in positions.itertuples(index=False):
                if int(row.in_tissue) != 1:
                    continue
                key = (participant, canonical, str(row.barcode))
                if key in mappings:
                    raise ValueError(f"Duplicate in-tissue position key: {key}")
                mappings[key] = {
                    "array_row": int(row.array_row),
                    "array_col": int(row.array_col),
                    "positions_path": str(position_path),
                    "image_path": str(image_path),
                    "tissue_hires_scalef": float(scale["tissue_hires_scalef"]),
                    "spot_diameter_hires_px": float(scale.get("spot_diameter_fullres", 0))
                    * float(scale["tissue_hires_scalef"]),
                }
    return mappings


def assign_folds(participant_counts: dict[str, int]) -> dict[str, int]:
    rng = np.random.default_rng(FOLD_SEED)
    participants = list(participant_counts)
    shuffled = list(np.asarray(participants, dtype=object)[rng.permutation(len(participants))])
    order = {participant: idx for idx, participant in enumerate(shuffled)}
    fold_priority = list(rng.permutation(7))
    assigned: dict[str, int] = {}
    loads = [0] * 7
    for participant in sorted(participants, key=lambda p: (-participant_counts[p], order[p])):
        fold = min(fold_priority, key=lambda candidate: (loads[candidate], fold_priority.index(candidate)))
        assigned[participant] = int(fold)
        loads[fold] += participant_counts[participant]
    return assigned


def prepare() -> None:
    ensure_output_dir()
    gene, module, metadata, tiles = load_inputs()
    key_cols = ["participant_id", "sample_id", "barcode"]
    library_metadata = metadata[["participant_id", "sample_id", "expression_source", "tier"]].copy()
    if library_metadata.duplicated(["participant_id", "sample_id"]).any():
        raise ValueError("Sample metadata keys are not unique")
    library_metadata["library_id"] = library_metadata["expression_source"].map(library_identifier)
    if library_metadata["library_id"].duplicated().any():
        raise ValueError("Derived library_id values are not unique")

    gene = gene.merge(
        library_metadata,
        on=["participant_id", "sample_id"],
        how="left",
        validate="many_to_one",
        suffixes=("", "_metadata"),
    )
    if gene["library_id"].isna().any() or gene["expression_source"].isna().any():
        raise ValueError("Some normalized expression rows have no source-expression library mapping")
    module_cols = [
        "participant_id",
        "sample_id",
        "barcode",
        "ECM_collagen_mean_log1p_cp10k",
        "ECM_collagen_any_member_detected",
        "myofibroblast_pro-fibrotic_mean_log1p_cp10k",
        "myofibroblast_pro-fibrotic_any_member_detected",
        "matrix_remodelling_mean_log1p_cp10k",
        "matrix_remodelling_any_member_detected",
    ]
    module = module[module_cols].copy()
    gene = gene.merge(module, on=key_cols, how="left", validate="one_to_one")
    module_source = {
        "ECM_collagen": "ECM_collagen_mean_log1p_cp10k",
        "myofibroblast_pro-fibrotic": "myofibroblast_pro-fibrotic_mean_log1p_cp10k",
        "matrix_remodelling": "matrix_remodelling_mean_log1p_cp10k",
    }
    for target, source_col in module_source.items():
        gene[target] = gene[source_col]
    for module_name in MODULES:
        gene[f"{module_name}_any_detected"] = gene[f"{module_name}_any_member_detected"].astype(bool)

    gene["source_key"] = gene["expression_source"].map(canonical_source)
    tiles["source_key"] = tiles["expression_source"].map(canonical_source)
    tiles = tiles.drop(columns=["sample_id"]).drop_duplicates(
        ["participant_id", "source_key", "barcode"], keep=False
    )
    if len(tiles) != EXPECTED_SPOTS:
        raise ValueError(f"Tile key count differs from expected spots: {len(tiles)}")
    gene = gene.merge(
        tiles[
            [
                "participant_id",
                "source_key",
                "barcode",
                "tile_path",
                "center_x_hires_px",
                "center_y_hires_px",
                "spot_diameter_hires_px",
            ]
        ],
        on=["participant_id", "source_key", "barcode"],
        how="left",
        validate="one_to_one",
    )
    if gene["tile_path"].isna().any():
        raise ValueError(f"Missing tile for {int(gene['tile_path'].isna().sum())} expression rows")

    position_maps = collect_spatial_position_maps(metadata)
    gene["position_key"] = list(
        zip(gene["participant_id"], gene["source_key"], gene["barcode"].astype(str))
    )
    pos_df = pd.DataFrame(
        [
            {
                "position_key": key,
                "array_row": value["array_row"],
                "array_col": value["array_col"],
                "positions_path": value["positions_path"],
                "image_path": value["image_path"],
                "tissue_hires_scalef": value["tissue_hires_scalef"],
                "position_spot_diameter_hires_px": value["spot_diameter_hires_px"],
            }
            for key, value in position_maps.items()
        ]
    )
    gene = gene.merge(pos_df, on="position_key", how="left", validate="one_to_one")
    if gene["array_row"].isna().any() or gene["image_path"].isna().any():
        raise ValueError(f"Spatial positions missing for {int(gene['array_row'].isna().sum())} expression rows")

    for target in TARGET_GENES:
        raw_col = f"{target}_raw_count"
        norm_col = f"{target}_log1p_cp10k"
        if raw_col not in gene or norm_col not in gene:
            raise ValueError(f"QC expression table is missing target columns for {target}")
        gene[f"raw_{target}"] = pd.to_numeric(gene[raw_col], errors="raise").astype(np.int64)
        gene[target] = pd.to_numeric(gene[norm_col], errors="raise")
    for target in MODULES:
        gene[target] = pd.to_numeric(gene[target], errors="coerce")
    if gene[TARGETS].isna().any().any():
        missing = gene[TARGETS].isna().sum()
        raise ValueError(f"Target values have missing entries: {missing[missing > 0].to_dict()}")

    gene["library_id"] = gene["expression_source"].map(library_identifier)
    gene["tile_path"] = gene["tile_path"].map(lambda p: str((ROOT / p).resolve()))
    gene["image_path"] = gene["image_path"].map(lambda p: str((ROOT / p).resolve()))
    if not gene["tile_path"].map(lambda p: Path(p).is_file()).all():
        raise FileNotFoundError("At least one existing tile path is missing")

    count_by_key = gene.groupby(["participant_id", "library_id"], sort=True).size()
    if gene.duplicated(["participant_id", "library_id", "barcode"]).any():
        raise ValueError("The (participant_id, library_id, barcode) key is not unique")
    participant_counts = gene.groupby("participant_id").size().to_dict()
    fold_map = assign_folds({str(k): int(v) for k, v in participant_counts.items()})
    gene["fold"] = gene["participant_id"].map(fold_map).astype(int)

    if gene["participant_id"].nunique() != EXPECTED_PARTICIPANTS:
        raise ValueError(f"Expected {EXPECTED_PARTICIPANTS} participants, got {gene['participant_id'].nunique()}")
    if gene[["participant_id", "library_id"]].drop_duplicates().shape[0] != EXPECTED_LIBRARIES:
        raise ValueError("Library count does not reconcile to 29")
    if len(gene) != EXPECTED_SPOTS:
        raise ValueError(f"Spot count does not reconcile to {EXPECTED_SPOTS}")
    p28 = gene.loc[gene["participant_id"] == "28-12265"]
    if p28["library_id"].nunique() != 2 or p28["fold"].nunique() != 1:
        raise ValueError("Both 28-12265 libraries must remain in one fold")

    gene = gene.sort_values(["participant_id", "library_id", "barcode"]).reset_index(drop=True)
    output_cols = [
        "participant_id",
        "library_id",
        "barcode",
        "sample_id",
        "expression_source",
        "tier",
        "fold",
        "library_size_umi",
        "array_row",
        "array_col",
        "center_x_hires_px",
        "center_y_hires_px",
        "spot_diameter_hires_px",
        "tile_path",
        "image_path",
        "positions_path",
    ]
    output_cols += [f"raw_{gene_name}" for gene_name in TARGET_GENES]
    output_cols += TARGETS
    output_cols += [f"{module_name}_any_detected" for module_name in MODULES]
    for module_name in MODULES:
        detected_col = f"{module_name}_any_detected"
        if detected_col not in gene:
            raise ValueError(f"QC module detection column is missing: {detected_col}")
    write_csv_checked(gene[output_cols], OUT / "targets_by_spot.csv")

    mapping = (
        gene.groupby(
            ["participant_id", "sample_id", "library_id", "expression_source", "fold"],
            as_index=False,
            sort=True,
        )
        .agg(in_tissue_spots=("barcode", "size"))
        .sort_values(["participant_id", "library_id"])
    )
    write_csv_checked(mapping, OUT / "library_key_map.csv")
    folds = (
        gene.groupby(["participant_id", "fold"], as_index=False, sort=True)
        .agg(in_tissue_spots=("barcode", "size"))
        .sort_values("participant_id")
    )
    write_csv_checked(folds, OUT / "fold_assignments.csv")
    fold_summary = (
        folds.groupby("fold", as_index=False, sort=True)
        .agg(participants=("participant_id", "nunique"), in_tissue_spots=("in_tissue_spots", "sum"))
    )
    write_csv_checked(fold_summary, OUT / "fold_summary.csv")
    config = {
        "created_at": now_text(),
        "command": "python D:\\patent\\stage1_expression\\scripts\\run_stage1.py prepare",
        "counts": {
            "participants": int(gene["participant_id"].nunique()),
            "libraries": int(gene[["participant_id", "library_id"]].drop_duplicates().shape[0]),
            "spots": int(len(gene)),
            "spots_key_unique": bool(not gene.duplicated(["participant_id", "library_id", "barcode"]).any()),
        },
        "fold_seed": FOLD_SEED,
        "target_columns": TARGETS,
        "gene_normalization": "log1p(raw target counts / total spot UMI * 10000), sourced from qc_collagen",
        "module_method": "simple mean of member-gene log1p(CP10K), sourced from qc_collagen",
    }
    (OUT / "stage1_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(json.dumps(config["counts"], indent=2))
    print(f"fold spots: {fold_summary.to_dict(orient='records')}")


def color_statistics(rgb: np.ndarray) -> np.ndarray:
    rgb_float = rgb.astype(np.float32)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    return np.concatenate(
        [
            rgb_float.mean(axis=(0, 1)),
            rgb_float.std(axis=(0, 1)),
            hsv.mean(axis=(0, 1)),
            hsv.std(axis=(0, 1)),
        ]
    )


def crop_reflect(image: np.ndarray, x: int, y: int, size: int) -> np.ndarray:
    half = size // 2
    left, top = x - half, y - half
    pad_left = max(0, -left)
    pad_top = max(0, -top)
    pad_right = max(0, left + size - image.shape[1])
    pad_bottom = max(0, top + size - image.shape[0])
    padded = cv2.copyMakeBorder(
        image,
        pad_top,
        pad_bottom,
        pad_left,
        pad_right,
        cv2.BORDER_REFLECT_101,
    )
    x0 = left + pad_left
    y0 = top + pad_top
    return padded[y0 : y0 + size, x0 : x0 + size]


def embed() -> None:
    ensure_output_dir()
    target_path = OUT / "targets_by_spot.csv"
    if not target_path.is_file():
        raise FileNotFoundError("Run the prepare command before embed")
    frame = pd.read_csv(target_path, dtype={"participant_id": str, "library_id": str, "barcode": str})
    n = len(frame)
    expected_feature_bytes = n * 2048 * 2 * 2
    ensure_write_budget(expected_feature_bytes + 300_000_000, "extract and save spot/context embeddings")

    import torch
    from PIL import Image
    from torchvision.models import ResNet50_Weights, resnet50

    cache_dir = OUT / "model_cache"
    cache_dir.mkdir(exist_ok=True)
    torch.hub.set_dir(str(cache_dir))
    weights = ResNet50_Weights.IMAGENET1K_V2
    weight_path = cache_dir / "checkpoints" / Path(weights.url).name
    weight_was_cached = weight_path.is_file()
    model = resnet50(weights=weights, progress=True)
    model.fc = torch.nn.Identity()
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.set_num_threads(min(8, os.cpu_count() or 1))
    model.to(device)
    transform = weights.transforms()
    device_name = torch.cuda.get_device_name(0) if device.type == "cuda" else "CPU"

    spot_embeddings = np.zeros((n, 2048), dtype=np.float16)
    context_embeddings = np.full((n, 2048), np.nan, dtype=np.float16)
    color_features = np.zeros((n, 12), dtype=np.float32)
    image_path_by_library = {
        key: str(group.iloc[0]["image_path"])
        for key, group in frame.groupby("library_id", sort=False)
    }
    context_available = np.ones(n, dtype=bool)
    batch_size = 64

    with torch.inference_mode():
        for start in range(0, n, batch_size):
            stop = min(start + batch_size, n)
            tensors = []
            for row in frame.iloc[start:stop].itertuples(index=False):
                with Image.open(row.tile_path) as image:
                    rgb_image = image.convert("RGB")
                    tensors.append(transform(rgb_image))
                    color_features[start + len(tensors) - 1] = color_statistics(np.asarray(rgb_image))
            batch = torch.stack(tensors).to(device)
            spot_embeddings[start:stop] = (
                model(batch).detach().cpu().numpy().astype(np.float16)
            )

        for library_id, row_indexes in frame.groupby("library_id", sort=False).indices.items():
            idxs = np.asarray(row_indexes, dtype=np.int64)
            image_path = image_path_by_library[library_id]
            hires_bgr = cv2.imread(image_path, cv2.IMREAD_COLOR)
            if hires_bgr is None:
                context_available[idxs] = False
                continue
            hires_rgb = cv2.cvtColor(hires_bgr, cv2.COLOR_BGR2RGB)
            for start in range(0, len(idxs), batch_size):
                current = idxs[start : start + batch_size]
                tensors = []
                for idx in current:
                    x = int(round(float(frame.at[idx, "center_x_hires_px"])))
                    y = int(round(float(frame.at[idx, "center_y_hires_px"])))
                    crop = crop_reflect(hires_rgb, x, y, 448)
                    resized = cv2.resize(crop, (224, 224), interpolation=cv2.INTER_AREA)
                    tensors.append(transform(Image.fromarray(resized)))
                batch = torch.stack(tensors).to(device)
                context_embeddings[current] = (
                    model(batch).detach().cpu().numpy().astype(np.float16)
                )

    if not context_available.all():
        missing = sorted(frame.loc[~context_available, "library_id"].unique())
        print(f"context image unavailable for libraries: {missing}")
    key_arrays = {
        "participant_id": frame["participant_id"].astype(str).to_numpy(dtype="U16"),
        "library_id": frame["library_id"].astype(str).to_numpy(dtype="U24"),
        "barcode": frame["barcode"].astype(str).to_numpy(dtype="U32"),
    }
    write_npz_checked(
        OUT / "spot_embeddings.npz",
        **key_arrays,
        embeddings=spot_embeddings,
    )
    write_npz_checked(
        OUT / "context_embeddings.npz",
        **key_arrays,
        embeddings=context_embeddings,
        context_available=context_available,
    )
    color_names = [
        "rgb_mean_r", "rgb_mean_g", "rgb_mean_b",
        "rgb_std_r", "rgb_std_g", "rgb_std_b",
        "hsv_mean_h", "hsv_mean_s", "hsv_mean_v",
        "hsv_std_h", "hsv_std_s", "hsv_std_v",
    ]
    write_npz_checked(
        OUT / "color_statistics.npz",
        **key_arrays,
        features=color_features,
        feature_names=np.asarray(color_names, dtype="U16"),
    )

    sha256 = ""
    weight_bytes = 0
    if weight_path.is_file():
        weight_bytes = weight_path.stat().st_size
        digest = hashlib.sha256()
        with weight_path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        sha256 = digest.hexdigest()
    asset = pd.DataFrame(
        [
            {
                "asset": "torchvision ResNet-50 IMAGENET1K_V2",
                "url": weights.url,
                "license": "torchvision code BSD-3-Clause; weight-specific and upstream ImageNet dataset terms not independently verified",
                "cached_before_run": weight_was_cached,
                "size_bytes": weight_bytes,
                "sha256": sha256,
                "device": str(device),
                "device_name": device_name,
                "torch_version": torch.__version__,
                "torchvision_version": __import__("torchvision").__version__,
                "context_libraries_available": int(frame.loc[context_available, "library_id"].nunique()),
                "context_libraries_total": int(frame["library_id"].nunique()),
            }
        ]
    )
    write_csv_checked(asset, OUT / "model_assets_manifest.csv")
    print(
        f"saved embeddings: spots={spot_embeddings.shape}, context={context_embeddings.shape}, "
        f"context_libraries={asset.iloc[0]['context_libraries_available']}/{asset.iloc[0]['context_libraries_total']}, "
        f"device={device_name}"
    )


def participant_weights(participants: np.ndarray) -> np.ndarray:
    counts = Counter(participants.tolist())
    values = np.asarray([1.0 / counts[participant] for participant in participants], dtype=np.float64)
    return values / values.mean()


def residualize_fold(
    y: np.ndarray,
    depth: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    participants: np.ndarray,
    weights: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, list[dict[str, object]]]:
    train_residual = np.zeros((len(train_idx), y.shape[1]), dtype=np.float64)
    test_residual = np.zeros((len(test_idx), y.shape[1]), dtype=np.float64)
    records: list[dict[str, object]] = []
    for column, target in enumerate(TARGETS):
        nuisance = LinearRegression()
        nuisance.fit(depth[train_idx], y[train_idx, column], sample_weight=weights)
        train_values = y[train_idx, column] - nuisance.predict(depth[train_idx])
        test_values = y[test_idx, column] - nuisance.predict(depth[test_idx])
        for participant in np.unique(participants[train_idx]):
            local = participants[train_idx] == participant
            train_values[local] -= np.average(train_values[local], weights=weights[local])
        train_residual[:, column] = train_values
        test_residual[:, column] = test_values
        records.append(
            {
                "target": target,
                "intercept": float(nuisance.intercept_),
                "depth_coefficient": float(nuisance.coef_[0]),
                "train_spots": int(len(train_idx)),
                "train_participants": int(len(np.unique(participants[train_idx]))),
            }
        )
    return train_residual, test_residual, records


def scaled_ridge_predict(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    weights: np.ndarray,
) -> np.ndarray:
    scaler = StandardScaler()
    scaler.fit(x_train, sample_weight=weights)
    model = Ridge(alpha=1.0)
    model.fit(scaler.transform(x_train), y_train, sample_weight=weights)
    return model.predict(scaler.transform(x_test))


def enet_predict(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    weights: np.ndarray,
    seed: int,
    fit_status: list[dict[str, object]],
    fold: int,
    variant: str,
    feature_set: str,
) -> np.ndarray:
    x_scaler = StandardScaler()
    x_scaler.fit(x_train, sample_weight=weights)
    y_scaler = StandardScaler()
    y_scaler.fit(y_train, sample_weight=weights)
    model = MultiOutputRegressor(
        SGDRegressor(
            loss="squared_error",
            penalty="elasticnet",
            alpha=0.01,
            l1_ratio=0.5,
            max_iter=10,
            tol=None,
            n_iter_no_change=5,
            average=True,
            random_state=seed,
        ),
        n_jobs=1,
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model.fit(
            x_scaler.transform(x_train),
            y_scaler.transform(y_train),
            sample_weight=weights,
        )
    for warning in caught:
        fit_status.append(
            {
                "fold": fold,
                "target_variant": variant,
                "feature_set": feature_set,
                "target": "all",
                "status": "warning",
                "iterations": "",
                "warning": f"{warning.category.__name__}: {warning.message}",
            }
        )
    for target, estimator in zip(TARGETS, model.estimators_):
        fit_status.append(
            {
                "fold": fold,
                "target_variant": variant,
                "feature_set": feature_set,
                "target": target,
                "status": "fixed_iteration_budget",
                "iterations": int(estimator.n_iter_),
                "warning": "",
            }
        )
    return y_scaler.inverse_transform(model.predict(x_scaler.transform(x_test)))


def mlp_predict(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    weights: np.ndarray,
    fold: int,
    device: object,
) -> np.ndarray:
    import torch

    torch.manual_seed(int(MODEL_SEED + int(fold)))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(MODEL_SEED + int(fold)))
    torch.use_deterministic_algorithms(True)
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True

    x_scaler = StandardScaler()
    x_scaler.fit(x_train, sample_weight=weights)
    y_scaler = StandardScaler()
    y_scaler.fit(y_train, sample_weight=weights)
    train_x = torch.as_tensor(x_scaler.transform(x_train), dtype=torch.float32, device=device)
    train_y = torch.as_tensor(y_scaler.transform(y_train), dtype=torch.float32, device=device)
    train_w = torch.as_tensor(weights, dtype=torch.float32, device=device)
    test_x = torch.as_tensor(x_scaler.transform(x_test), dtype=torch.float32, device=device)

    model = torch.nn.Sequential(
        torch.nn.Linear(train_x.shape[1], 128),
        torch.nn.ReLU(),
        torch.nn.Linear(128, len(TARGETS)),
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    generator = torch.Generator(device="cpu")
    generator.manual_seed(int(MODEL_SEED + int(fold)))
    batch_size = 4096
    model.train()
    for _ in range(5):
        order = torch.randperm(len(train_x), generator=generator)
        for start in range(0, len(order), batch_size):
            idx = order[start : start + batch_size].to(device)
            optimizer.zero_grad(set_to_none=True)
            predicted = model(train_x[idx])
            per_spot_loss = torch.mean((predicted - train_y[idx]) ** 2, dim=1)
            loss = torch.mean(per_spot_loss * train_w[idx])
            loss.backward()
            optimizer.step()
    model.eval()
    with torch.inference_mode():
        scaled_predictions = model(test_x).cpu().numpy()
    return y_scaler.inverse_transform(scaled_predictions)


def fit() -> None:
    ensure_output_dir()
    target_path = OUT / "targets_by_spot.csv"
    fold_path = OUT / "fold_assignments.csv"
    required = [
        target_path,
        fold_path,
        OUT / "spot_embeddings.npz",
        OUT / "context_embeddings.npz",
        OUT / "color_statistics.npz",
    ]
    if any(not path.is_file() for path in required):
        raise FileNotFoundError("Run prepare and embed before fit")
    frame = pd.read_csv(target_path, dtype={"participant_id": str, "library_id": str, "barcode": str})
    folds = pd.read_csv(fold_path)
    if frame.duplicated(["participant_id", "library_id", "barcode"]).any():
        raise ValueError("Spot key is not unique before fitting")
    if folds.groupby("participant_id")["fold"].nunique().max() != 1:
        raise ValueError("Participant appears in more than one test fold")

    spot_archive = np.load(OUT / "spot_embeddings.npz")
    context_archive = np.load(OUT / "context_embeddings.npz")
    color_archive = np.load(OUT / "color_statistics.npz")
    spot_x = spot_archive["embeddings"].astype(np.float32)
    context_x = context_archive["embeddings"].astype(np.float32)
    context_available = context_archive["context_available"].astype(bool)
    color_x = color_archive["features"].astype(np.float32)
    n = len(frame)
    if spot_x.shape != (n, 2048) or context_x.shape != (n, 2048) or color_x.shape != (n, 12):
        raise ValueError("Feature dimensions do not align with target rows")
    keys = list(zip(frame["participant_id"], frame["library_id"], frame["barcode"]))
    archive_keys = list(
        zip(
            spot_archive["participant_id"].astype(str),
            spot_archive["library_id"].astype(str),
            spot_archive["barcode"].astype(str),
        )
    )
    if keys != archive_keys:
        raise ValueError("Embedding rows do not match the ordered unique spot-key table")
    if context_available.shape[0] != n:
        raise ValueError("Context availability mask does not align")

    participant = frame["participant_id"].astype(str).to_numpy()
    fold_vector = frame["fold"].to_numpy(dtype=int)
    depth = np.log1p(frame["library_size_umi"].to_numpy(dtype=np.float64)).reshape(-1, 1)
    y_raw = frame[TARGETS].to_numpy(dtype=np.float64)
    raw_counts = frame[[f"raw_{gene}" for gene in TARGET_GENES]].to_numpy(dtype=np.int64)
    module_detect = frame[[f"{name}_any_detected" for name in MODULES]].to_numpy(dtype=bool)
    detection = np.column_stack([raw_counts > 0, module_detect])
    if not np.isfinite(y_raw).all():
        raise ValueError("Missing or non-finite target values prevent model fitting")

    pred_raw = np.full((len(MODEL_NAMES), n, len(TARGETS)), np.nan, dtype=np.float32)
    pred_resid = np.full_like(pred_raw, np.nan)
    observed_resid = np.full_like(y_raw, np.nan, dtype=np.float32)
    nuisance_rows: list[dict[str, object]] = []
    enet_fit_status: list[dict[str, object]] = []
    fold_ids = sorted(np.unique(fold_vector))
    if fold_ids != list(range(7)):
        raise ValueError(f"Expected seven contiguous folds, got {fold_ids}")

    import torch

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    for fold in fold_ids:
        test_idx = np.flatnonzero(fold_vector == fold)
        train_idx = np.flatnonzero(fold_vector != fold)
        if set(participant[train_idx]).intersection(set(participant[test_idx])):
            raise ValueError(f"Participant leakage into fold {fold}")
        residual_weights = participant_weights(participant[train_idx])
        y_train_resid, y_test_resid, coeffs = residualize_fold(
            y_raw, depth, train_idx, test_idx, participant, residual_weights
        )
        observed_resid[test_idx] = y_test_resid.astype(np.float32)
        for row in coeffs:
            row["fold"] = fold
            nuisance_rows.append(row)

        for variant_index, (variant, y_train, y_test) in enumerate(
            [
                ("raw", y_raw[train_idx], y_raw[test_idx]),
                ("residualized", y_train_resid, y_test_resid),
            ]
        ):
            weights = participant_weights(participant[train_idx])
            patient_means = []
            for pid in np.unique(participant[train_idx]):
                local = participant[train_idx] == pid
                patient_means.append(np.average(y_train[local], axis=0, weights=weights[local]))
            patient_array = pred_raw if variant == "raw" else pred_resid
            patient_array[MODEL_NAMES.index("patient_mean"), test_idx] = np.mean(patient_means, axis=0)

            model_features = [
                ("depth_only", depth[train_idx], depth[test_idx]),
                ("color_only", color_x[train_idx], color_x[test_idx]),
            ]
            for model_name, x_train, x_test in model_features:
                pred = scaled_ridge_predict(x_train, y_train, x_test, weights)
                target_array = pred_raw if variant == "raw" else pred_resid
                target_array[MODEL_NAMES.index(model_name), test_idx] = pred.astype(np.float32)

            for feature_name, features, model_name in [
                ("spot", spot_x, "elasticnet_spot"),
                ("context", context_x, "elasticnet_context"),
            ]:
                model_idx = MODEL_NAMES.index(model_name)
                if feature_name == "context":
                    valid_train = context_available[train_idx]
                    valid_test = context_available[test_idx]
                    if valid_test.sum() == 0:
                        continue
                    fit_idx = train_idx[valid_train]
                    pred_idx = test_idx[valid_test]
                    x_train = features[fit_idx]
                    x_test = features[pred_idx]
                    y_fit = y_raw[fit_idx] if variant == "raw" else y_train_resid[valid_train]
                    w_fit = participant_weights(participant[fit_idx])
                else:
                    pred_idx = test_idx
                    x_train = features[train_idx]
                    x_test = features[test_idx]
                    y_fit = y_train
                    w_fit = weights
                pred = enet_predict(
                    x_train,
                    y_fit,
                    x_test,
                    w_fit,
                    MODEL_SEED + fold,
                    enet_fit_status,
                    fold,
                    variant,
                    feature_name,
                )
                target_array = pred_raw if variant == "raw" else pred_resid
                target_array[model_idx, pred_idx] = pred.astype(np.float32)

            for feature_name, features, model_name in [
                ("spot", spot_x, "mlp_spot"),
                ("context", context_x, "mlp_context"),
            ]:
                model_idx = MODEL_NAMES.index(model_name)
                if feature_name == "context":
                    valid_train = context_available[train_idx]
                    valid_test = context_available[test_idx]
                    if valid_test.sum() == 0:
                        continue
                    fit_idx = train_idx[valid_train]
                    pred_idx = test_idx[valid_test]
                    x_train = features[fit_idx]
                    x_test = features[pred_idx]
                    y_fit = y_raw[fit_idx] if variant == "raw" else y_train_resid[valid_train]
                    w_fit = participant_weights(participant[fit_idx])
                else:
                    pred_idx = test_idx
                    x_train = features[train_idx]
                    x_test = features[test_idx]
                    y_fit = y_train
                    w_fit = weights
                pred = mlp_predict(x_train, y_fit, x_test, w_fit, fold, device)
                target_array = pred_raw if variant == "raw" else pred_resid
                target_array[model_idx, pred_idx] = pred.astype(np.float32)
        print(f"completed fold {fold + 1}/7: train={len(train_idx)} test={len(test_idx)}")

    if np.isnan(pred_raw[:5]).any() or np.isnan(pred_resid[:5]).any():
        raise RuntimeError("One or more primary model predictions are missing")
    if np.isnan(observed_resid).any():
        raise RuntimeError("Residualized evaluation targets are incomplete")
    keys_arr = {
        "participant_id": frame["participant_id"].astype(str).to_numpy(dtype="U16"),
        "library_id": frame["library_id"].astype(str).to_numpy(dtype="U24"),
        "barcode": frame["barcode"].astype(str).to_numpy(dtype="U32"),
    }
    predictions = {
        **keys_arr,
        "fold": fold_vector.astype(np.int8),
        "model_names": np.asarray(MODEL_NAMES, dtype="U24"),
        "target_names": np.asarray(TARGETS, dtype="U40"),
        "raw_predictions": pred_raw,
        "residualized_predictions": pred_resid,
        "raw_targets": y_raw.astype(np.float32),
        "residualized_targets": observed_resid,
        "context_available": context_available,
    }
    write_npz_checked(OUT / "oof_predictions.npz", **predictions)
    write_csv_checked(pd.DataFrame(nuisance_rows), OUT / "residualization_coefficients.csv")
    write_csv_checked(pd.DataFrame(enet_fit_status), OUT / "elastic_net_fit_status.csv")
    fold_table = frame[
        [
            "participant_id",
            "library_id",
            "barcode",
            "fold",
        ]
    ].copy()
    write_csv_checked(fold_table, OUT / "oof_spot_key_index.csv")


def bootstrap_mean(values: np.ndarray, rng: np.random.Generator) -> tuple[float, float, float]:
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return math.nan, math.nan, math.nan
    mean = float(np.mean(values))
    if len(values) == 1:
        return mean, mean, mean
    samples = rng.choice(values, size=(N_BOOTSTRAP, len(values)), replace=True)
    lows, highs = np.quantile(samples.mean(axis=1), [0.025, 0.975])
    return mean, float(lows), float(highs)


def score_predictions() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frame = pd.read_csv(OUT / "targets_by_spot.csv", dtype={"participant_id": str, "library_id": str, "barcode": str})
    archive = np.load(OUT / "oof_predictions.npz")
    pred_raw = archive["raw_predictions"]
    pred_resid = archive["residualized_predictions"]
    observed_raw = archive["raw_targets"]
    observed_resid = archive["residualized_targets"]
    pred_sets = {"raw": pred_raw, "residualized": pred_resid}
    obs_sets = {"raw": observed_raw, "residualized": observed_resid}
    participants = frame["participant_id"].astype(str).to_numpy()
    detected_counts = {
        target: (
            frame[f"raw_{target}"].to_numpy(dtype=np.int64) > 0
            if target in TARGET_GENES
            else frame[f"{target}_any_detected"].to_numpy(dtype=bool)
        )
        for target in TARGETS
    }
    metric_rows: list[dict[str, object]] = []
    for variant in TARGET_VARIANTS:
        preds = pred_sets[variant]
        observed = obs_sets[variant]
        for model_idx, model in enumerate(MODEL_NAMES):
            for target_idx, target in enumerate(TARGETS):
                for pid in sorted(np.unique(participants)):
                    idx = np.flatnonzero(participants == pid)
                    y = observed[idx, target_idx]
                    p = preds[model_idx, idx, target_idx]
                    detect = detected_counts[target][idx]
                    n_detected = int(detect.sum())
                    reason = ""
                    rho = math.nan
                    if n_detected < MIN_DETECTED_SPOTS:
                        reason = f"fewer_than_{MIN_DETECTED_SPOTS}_detected_spots"
                    elif np.unique(y).size < MIN_DISTINCT_TARGET_VALUES:
                        reason = "fewer_than_3_distinct_target_values"
                    elif not np.isfinite(p).all():
                        reason = "prediction_missing"
                    elif np.unique(p).size < 2:
                        reason = "constant_prediction"
                    else:
                        rho = float(spearmanr(y, p).statistic)
                        if not np.isfinite(rho):
                            reason = "nonfinite_spearman"
                    valid = not reason
                    mae = float(np.mean(np.abs(y - p))) if np.isfinite(p).all() else math.nan
                    rmse = float(np.sqrt(np.mean((y - p) ** 2))) if np.isfinite(p).all() else math.nan
                    metric_rows.append(
                        {
                            "target_variant": variant,
                            "model": model,
                            "target": target,
                            "participant_id": pid,
                            "n_spots": int(len(idx)),
                            "n_detected_spots": n_detected,
                            "spearman_rho": rho if valid else math.nan,
                            "mae": mae,
                            "rmse": rmse,
                            "eligible_for_spearman": bool(valid),
                            "skip_reason": reason,
                        }
                    )
    metrics = pd.DataFrame(metric_rows)
    write_csv_checked(metrics, OUT / "participant_metrics.csv")

    rng = np.random.default_rng(BOOTSTRAP_SEED)
    summaries = []
    for (variant, model, target), group in metrics.groupby(
        ["target_variant", "model", "target"], sort=True
    ):
        valid = group.loc[group["eligible_for_spearman"], "spearman_rho"].to_numpy(dtype=np.float64)
        mean, low, high = bootstrap_mean(valid, rng)
        summaries.append(
            {
                "target_variant": variant,
                "model": model,
                "target": target,
                "n_participants": int(np.isfinite(valid).sum()),
                "mean_participant_spearman": mean,
                "ci95_low": low,
                "ci95_high": high,
                "mean_participant_mae": float(group.loc[group["mae"].notna()].groupby("participant_id")["mae"].first().mean()),
            }
        )
    summary = pd.DataFrame(summaries)
    write_csv_checked(summary, OUT / "model_summary.csv")

    comparisons: list[dict[str, object]] = []
    baselines = ["depth_only", "color_only"]
    candidates = [m for m in MODEL_NAMES if m not in {"patient_mean", *baselines}]
    for variant in TARGET_VARIANTS:
        for target in TARGETS:
            target_rows = metrics.loc[metrics["target_variant"] == variant]
            for candidate in candidates:
                for baseline in baselines:
                    left = target_rows.loc[
                        (target_rows["target"] == target)
                        & (target_rows["model"] == candidate)
                        & target_rows["eligible_for_spearman"],
                        ["participant_id", "spearman_rho"],
                    ].set_index("participant_id")
                    right = target_rows.loc[
                        (target_rows["target"] == target)
                        & (target_rows["model"] == baseline)
                        & target_rows["eligible_for_spearman"],
                        ["participant_id", "spearman_rho"],
                    ].set_index("participant_id")
                    common = left.index.intersection(right.index)
                    delta = left.loc[common, "spearman_rho"].to_numpy() - right.loc[common, "spearman_rho"].to_numpy()
                    mean, low, high = bootstrap_mean(delta, rng)
                    comparisons.append(
                        {
                            "scope": "target",
                            "target_variant": variant,
                            "target": target,
                            "model": candidate,
                            "baseline": baseline,
                            "n_participants": int(len(delta)),
                            "mean_delta_spearman": mean,
                            "ci95_low": low,
                            "ci95_high": high,
                            "participants_positive": int((delta > 0).sum()),
                            "participants_over_half": bool(len(delta) > 0 and (delta > 0).sum() > len(delta) / 2),
                        }
                    )

        macro_scores: dict[str, pd.Series] = {}
        subset = metrics.loc[(metrics["target_variant"] == variant) & metrics["eligible_for_spearman"]]
        for model in MODEL_NAMES:
            model_rows = subset.loc[subset["model"] == model]
            macro_scores[model] = model_rows.groupby("participant_id")["spearman_rho"].mean()
        for candidate in candidates:
            for baseline in baselines:
                common = macro_scores[candidate].index.intersection(macro_scores[baseline].index)
                delta = (
                    macro_scores[candidate].loc[common].to_numpy()
                    - macro_scores[baseline].loc[common].to_numpy()
                )
                mean, low, high = bootstrap_mean(delta, rng)
                comparisons.append(
                    {
                        "scope": "participant_macro",
                        "target_variant": variant,
                        "target": "macro_mean_eligible_targets",
                        "model": candidate,
                        "baseline": baseline,
                        "n_participants": int(len(delta)),
                        "mean_delta_spearman": mean,
                        "ci95_low": low,
                        "ci95_high": high,
                        "participants_positive": int((delta > 0).sum()),
                        "participants_over_half": bool(len(delta) > 0 and (delta > 0).sum() > len(delta) / 2),
                    }
                )

    comparison_frame = pd.DataFrame(comparisons)
    write_csv_checked(comparison_frame, OUT / "gate_comparisons.csv")
    wins = []
    raw_metrics = metrics.loc[metrics["target_variant"] == "raw"]
    for model in MODEL_NAMES:
        if model == "patient_mean":
            continue
        for target in TARGETS:
            model_rows = raw_metrics.loc[
                (raw_metrics["model"] == model) & (raw_metrics["target"] == target)
            ].set_index("participant_id")
            baseline_rows = raw_metrics.loc[
                (raw_metrics["model"] == "patient_mean") & (raw_metrics["target"] == target)
            ].set_index("participant_id")
            common = model_rows.index.intersection(baseline_rows.index)
            valid = common[
                model_rows.loc[common, "mae"].notna()
                & baseline_rows.loc[common, "mae"].notna()
            ]
            win = (
                model_rows.loc[valid, "mae"].to_numpy()
                < baseline_rows.loc[valid, "mae"].to_numpy()
            )
            wins.append(
                {
                    "target_variant": "raw",
                    "model": model,
                    "target": target,
                    "n_participants": int(len(valid)),
                    "participants_beating_patient_mean_by_mae": int(win.sum()),
                }
            )
    win_frame = pd.DataFrame(wins)
    write_csv_checked(win_frame, OUT / "patient_mean_wins.csv")
    return metrics, summary, comparison_frame


def block_permutation() -> pd.DataFrame:
    frame = pd.read_csv(OUT / "targets_by_spot.csv", dtype={"participant_id": str, "library_id": str, "barcode": str})
    archive = np.load(OUT / "oof_predictions.npz")
    predictions = {
        "raw": archive["raw_predictions"],
        "residualized": archive["residualized_predictions"],
    }
    observed = {
        "raw": archive["raw_targets"],
        "residualized": archive["residualized_targets"],
    }
    rows = []
    rng = np.random.default_rng(PERMUTATION_SEED)
    participants = frame["participant_id"].astype(str).to_numpy()
    libraries = frame["library_id"].astype(str).to_numpy()
    block_id = (
        frame["array_row"].to_numpy(dtype=np.int64) // BLOCK_WIDTH * 1_000_000
        + frame["array_col"].to_numpy(dtype=np.int64) // BLOCK_WIDTH
    )
    for variant in TARGET_VARIANTS:
        for model_idx, model in enumerate(MODEL_NAMES):
            for target_idx, target in enumerate(TARGETS):
                participant_records = []
                skipped = Counter()
                for pid in sorted(np.unique(participants)):
                    values_y = []
                    values_p = []
                    groups = []
                    for library_id in sorted(np.unique(libraries[participants == pid])):
                        idx = np.flatnonzero((participants == pid) & (libraries == library_id))
                        local_frame = frame.iloc[idx]
                        local_blocks = block_id[idx]
                        y = observed[variant][idx, target_idx]
                        p = predictions[variant][model_idx, idx, target_idx]
                        if not np.isfinite(p).all():
                            skipped["missing_predictions"] += 1
                            continue
                        group_values = []
                        for bid in np.unique(local_blocks):
                            bidx = local_blocks == bid
                            group_values.append(
                                (
                                    float(np.mean(y[bidx], dtype=np.float64)),
                                    float(np.mean(p[bidx], dtype=np.float64)),
                                )
                            )
                        if len(group_values) < 2:
                            skipped["library_fewer_than_2_blocks"] += 1
                            continue
                        values_y.extend(pair[0] for pair in group_values)
                        values_p.extend(pair[1] for pair in group_values)
                        groups.append(len(group_values))
                    if len(values_y) < 4:
                        skipped["participant_fewer_than_4_blocks"] += 1
                        continue
                    y_values = np.asarray(values_y, dtype=np.float64)
                    p_values = np.asarray(values_p, dtype=np.float64)
                    if np.unique(y_values).size < 2 or np.unique(p_values).size < 2:
                        skipped["constant_block_values"] += 1
                        continue
                    observed_rho = float(spearmanr(y_values, p_values).statistic)
                    if not np.isfinite(observed_rho):
                        skipped["nonfinite_block_spearman"] += 1
                        continue
                    participant_records.append((y_values, p_values, groups, observed_rho))
                if not participant_records:
                    rows.append(
                        {
                            "target_variant": variant,
                            "model": model,
                            "target": target,
                            "n_participants": 0,
                            "observed_macro_block_spearman": math.nan,
                            "null95_low": math.nan,
                            "null95_high": math.nan,
                            "empirical_p_one_sided": math.nan,
                            "skip_counts": json.dumps(dict(skipped), sort_keys=True),
                        }
                    )
                    continue
                observed_macro = float(np.mean([rec[3] for rec in participant_records]))
                null_sum = np.zeros(N_PERMUTATIONS, dtype=np.float64)
                for y_values, p_values, group_sizes, _ in participant_records:
                    pred_ranks = rankdata(p_values)
                    pred_centered = pred_ranks - pred_ranks.mean()
                    pred_norm = math.sqrt(float(np.sum(pred_centered**2)))
                    permuted_targets = np.tile(y_values, (N_PERMUTATIONS, 1))
                    start = 0
                    for group_size in group_sizes:
                        stop = start + group_size
                        order = np.argsort(rng.random((N_PERMUTATIONS, group_size)), axis=1)
                        permuted_targets[:, start:stop] = y_values[start:stop][order]
                        start = stop
                    permuted_ranks = rankdata(permuted_targets, axis=1)
                    centered = permuted_ranks - permuted_ranks.mean(axis=1, keepdims=True)
                    denom = np.sqrt(np.sum(centered**2, axis=1)) * pred_norm
                    rho = np.divide(
                        centered @ pred_centered,
                        denom,
                        out=np.full(N_PERMUTATIONS, np.nan),
                        where=denom > 0,
                    )
                    null_sum += rho
                null_macro = null_sum / len(participant_records)
                low, high = np.quantile(null_macro, [0.025, 0.975])
                p_value = (1 + int(np.sum(null_macro >= observed_macro))) / (1 + N_PERMUTATIONS)
                rows.append(
                    {
                        "target_variant": variant,
                        "model": model,
                        "target": target,
                        "n_participants": len(participant_records),
                        "observed_macro_block_spearman": observed_macro,
                        "null95_low": float(low),
                        "null95_high": float(high),
                        "empirical_p_one_sided": float(p_value),
                        "skip_counts": json.dumps(dict(skipped), sort_keys=True),
                    }
                )
    result = pd.DataFrame(rows)
    write_csv_checked(result, OUT / "spatial_block_permutation.csv")
    return result


def verify_outputs() -> pd.DataFrame:
    target = pd.read_csv(OUT / "targets_by_spot.csv", dtype={"participant_id": str, "library_id": str, "barcode": str})
    pred_archive = np.load(OUT / "oof_predictions.npz")
    metrics = pd.read_csv(OUT / "participant_metrics.csv")
    participants = pred_archive["participant_id"].astype(str)
    library_ids = pred_archive["library_id"].astype(str)
    barcodes = pred_archive["barcode"].astype(str)
    keys = list(zip(participants, library_ids, barcodes))
    target_keys = list(zip(target["participant_id"], target["library_id"], target["barcode"]))
    if keys != target_keys or len(set(keys)) != len(keys):
        raise AssertionError("Prediction key order/uniqueness does not reconcile with targets")
    fold_values = pred_archive["fold"].astype(int)
    if len(set(fold_values.tolist())) != 7:
        raise AssertionError("Expected predictions from exactly seven test folds")
    participant_folds: dict[str, set[int]] = defaultdict(set)
    key_folds: dict[tuple[str, str, str], set[int]] = defaultdict(set)
    for key, fold in zip(keys, fold_values):
        participant_folds[key[0]].add(int(fold))
        key_folds[key].add(int(fold))
    if any(len(value) != 1 for value in participant_folds.values()):
        raise AssertionError("A participant appears in multiple test folds")
    if any(len(value) != 1 for value in key_folds.values()):
        raise AssertionError("A spot key appears in multiple test folds")
    if len(participant_folds) != EXPECTED_PARTICIPANTS:
        raise AssertionError("Participant count mismatch")
    if len(set((key[0], key[1]) for key in keys)) != EXPECTED_LIBRARIES:
        raise AssertionError("Library count mismatch")
    if len(keys) != EXPECTED_SPOTS:
        raise AssertionError("Spot count mismatch")
    if target.loc[target["participant_id"] == "28-12265", "fold"].nunique() != 1:
        raise AssertionError("28-12265 libraries were split across folds")

    report_rows = []
    choices = [
        ("color_only", "COL1A1"),
        ("elasticnet_spot", "COL1A1"),
        ("mlp_spot", "ECM_collagen"),
    ]
    for model, target_name in choices:
        row = metrics.loc[
            (metrics["target_variant"] == "raw")
            & (metrics["model"] == model)
            & (metrics["target"] == target_name)
            & metrics["eligible_for_spearman"].astype(bool)
        ].head(1)
        if row.empty:
            row = metrics.loc[
                (metrics["target_variant"] == "raw")
                & (metrics["model"] == model)
                & metrics["eligible_for_spearman"].astype(bool)
            ].head(1)
        if row.empty:
            report_rows.append(
                {
                    "model": model,
                    "target": target_name,
                    "participant_id": "",
                    "reported_spearman": math.nan,
                    "recomputed_spearman": math.nan,
                    "absolute_difference": math.nan,
                    "verified": False,
                }
            )
            continue
        metric = row.iloc[0]
        pid = str(metric["participant_id"])
        actual_target = str(metric["target"])
        model_idx = MODEL_NAMES.index(model)
        target_idx = TARGETS.index(actual_target)
        idx = np.flatnonzero(participants == pid)
        y = pred_archive["raw_targets"][idx, target_idx]
        p = pred_archive["raw_predictions"][model_idx, idx, target_idx]
        recomputed = float(spearmanr(y, p).statistic)
        difference = abs(float(metric["spearman_rho"]) - recomputed)
        report_rows.append(
            {
                "model": model,
                "target": actual_target,
                "participant_id": pid,
                "reported_spearman": float(metric["spearman_rho"]),
                "recomputed_spearman": recomputed,
                "absolute_difference": difference,
                "verified": bool(difference < 1e-10),
            }
        )
    verification = pd.DataFrame(report_rows)
    if len(verification) != 3 or not verification["verified"].all():
        raise AssertionError("Three-metric independent recomputation did not pass")
    write_csv_checked(verification, OUT / "metric_recompute_verification.csv")
    check_rows = [
        {"check": "participants", "expected": EXPECTED_PARTICIPANTS, "observed": len(participant_folds), "passed": True},
        {"check": "libraries", "expected": EXPECTED_LIBRARIES, "observed": len(set((key[0], key[1]) for key in keys)), "passed": True},
        {"check": "spots", "expected": EXPECTED_SPOTS, "observed": len(keys), "passed": True},
        {"check": "unique_full_spot_keys", "expected": EXPECTED_SPOTS, "observed": len(set(keys)), "passed": True},
        {"check": "participant_single_test_fold", "expected": EXPECTED_PARTICIPANTS, "observed": sum(len(x) == 1 for x in participant_folds.values()), "passed": True},
        {"check": "28-12265_two_libraries_one_fold", "expected": 1, "observed": int(target.loc[target["participant_id"] == "28-12265", "fold"].nunique()), "passed": True},
    ]
    write_csv_checked(pd.DataFrame(check_rows), OUT / "verification_checks.csv")
    return verification


def run_report() -> None:
    metrics, summary, comparisons = score_predictions()
    block = block_permutation()
    verification = verify_outputs()
    frame = pd.read_csv(OUT / "targets_by_spot.csv")
    assets = pd.read_csv(OUT / "model_assets_manifest.csv")
    raw_macro = comparisons.loc[
        (comparisons["scope"] == "participant_macro")
        & (comparisons["target_variant"] == "raw")
    ]
    gate_pass = False
    gate_reasons = []
    for candidate in ["elasticnet_spot", "mlp_spot", "elasticnet_context", "mlp_context"]:
        rows = raw_macro.loc[raw_macro["model"] == candidate]
        by_baseline = {row["baseline"]: row for _, row in rows.iterrows()}
        qualifies = True
        for baseline in ["depth_only", "color_only"]:
            row = by_baseline.get(baseline)
            condition = bool(
                row is not None
                and row["n_participants"] > 0
                and row["ci95_low"] > 0
                and row["participants_over_half"]
            )
            qualifies = qualifies and condition
            gate_reasons.append(
                f"{candidate} vs {baseline}: n={int(row['n_participants']) if row is not None else 0}, "
                f"mean_delta={row['mean_delta_spearman'] if row is not None else math.nan:.4f}, "
                f"95% CI=[{row['ci95_low'] if row is not None else math.nan:.4f},"
                f" {row['ci95_high'] if row is not None else math.nan:.4f}], "
                f"positive_participants={int(row['participants_positive']) if row is not None else 0}"
            )
        if qualifies:
            gate_pass = True
    gate_status = "PASS" if gate_pass else "FAIL"
    participant_summary = (
        frame.groupby("participant_id", as_index=False)
        .agg(spots=("barcode", "size"), libraries=("library_id", "nunique"))
    )
    library_summary = frame.groupby("library_id", as_index=False).agg(
        participant_id=("participant_id", "first"),
        source=("expression_source", "first"),
        spots=("barcode", "size"),
    )
    skipped = metrics.loc[
        metrics["skip_reason"].isin(
            ["fewer_than_10_detected_spots", "fewer_than_3_distinct_target_values"]
        ),
        [
            "target_variant",
            "target",
            "participant_id",
            "n_spots",
            "n_detected_spots",
            "skip_reason",
        ],
    ].drop_duplicates()
    write_csv_checked(skipped, OUT / "skipped_participant_targets.csv")

    try:
        import torch
        import torchvision

        package_versions = {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": __import__("scipy").__version__,
            "scikit_learn": __import__("sklearn").__version__,
            "opencv": cv2.__version__,
            "pillow": __import__("PIL").__version__,
            "torch": torch.__version__,
            "torchvision": torchvision.__version__,
        }
    except ImportError as exc:
        raise RuntimeError(f"Required Stage 1 package disappeared after the run: {exc}") from exc

    summary_report = [
        "# Stage 1 — Expression-only baselines",
        "",
        f"**Run timestamp:** {now_text()}  ",
        f"**Gate A:** **{gate_status}**  ",
        f"**Scope:** expression-only image baselines. No registration, collagen feature use, batch correction, or fine-tuning.",
        "",
        "## Preregistered protocol and cohort",
        "",
        "The model sequence, preprocessing, folds, metrics, comparisons, gate, and spatial-block null were timestamped in [PREREG.md](./PREREG.md) before fitting. The immutable spot key is `(participant_id, library_id, barcode)`; library IDs are SHA-256-derived from the source expression-matrix path.",
        "",
        f"- Reconciled: **{frame['participant_id'].nunique()} participants, {frame[['participant_id', 'library_id']].drop_duplicates().shape[0]} libraries, {len(frame):,} spots**.",
        f"- Key uniqueness: {frame[['participant_id', 'library_id', 'barcode']].drop_duplicates().shape[0]:,}/{len(frame):,}.",
        f"- 28-12265: {frame.loc[frame['participant_id'] == '28-12265', 'library_id'].nunique()} libraries in {frame.loc[frame['participant_id'] == '28-12265', 'fold'].nunique()} fold.",
        "- Seven participant-grouped folds are balanced by in-tissue spot count; see `fold_assignments.csv` and `fold_summary.csv`.",
        f"- Eligible targets: {', '.join(TARGETS)}. Normalization is the same `log1p(counts / total spot UMI × 10,000)` as `qc_collagen`; modules use the documented simple mean of member-gene log-normalized values.",
        "",
        "## Encoder, license, and image features",
        "",
        f"- Frozen encoder: torchvision ResNet-50 `IMAGENET1K_V2`; features are the 2,048-dimensional global-average-pooling output. The torchvision code license is BSD-3-Clause; weight-specific and upstream ImageNet dataset terms were not independently verified. No gated pathology encoder was used.",
        f"- Device: {assets.iloc[0]['device_name']}; official weights URL: {assets.iloc[0]['url']}; weight file SHA-256: `{assets.iloc[0]['sha256']}` ({int(assets.iloc[0]['size_bytes']):,} bytes).",
        f"- Spot embeddings were extracted from existing 224×224 tiles; wider-context embeddings use 448×448 Visium hires crops resized to 224×224. Context available for {int(assets.iloc[0]['context_libraries_available'])}/{int(assets.iloc[0]['context_libraries_total'])} libraries.",
        "- Tiles were read in place. No PNG tile folder was regenerated, and no participant data were uploaded.",
        "",
        "## Model results",
        "",
        "Per-target mean participant Spearman and participant-bootstrap 95% CIs are in `model_summary.csv`; participant-level estimates and skips are in `participant_metrics.csv` and `skipped_participant_targets.csv`. The primary results are the raw normalized targets; fold-residualized results are secondary. The constant patient-mean reference has undefined within-participant Spearman by construction, so its predictive-model wins are counted by MAE in `patient_mean_wins.csv`.",
    ]
    summary_report += [
        "",
        "### Per-target raw normalized performance",
        "",
        "| Target | n participants | Depth-only rho [95% CI] | Colour rho [95% CI] | Elastic Net spot rho [95% CI] | MLP spot rho [95% CI] | Elastic Net context rho [95% CI] | MLP context rho [95% CI] |",
        "| --- | ---: | --- | --- | --- | --- | --- | --- |",
    ]

    raw_summary = summary.loc[summary["target_variant"] == "raw"].set_index(["target", "model"])

    def metric_cell(target_name: str, model_name: str) -> str:
        row = raw_summary.loc[(target_name, model_name)]
        if not np.isfinite(row["mean_participant_spearman"]):
            return "NA"
        return (
            f"{row['mean_participant_spearman']:.3f} "
            f"[{row['ci95_low']:.3f}, {row['ci95_high']:.3f}]"
        )

    display_models = [
        "depth_only",
        "color_only",
        "elasticnet_spot",
        "mlp_spot",
        "elasticnet_context",
        "mlp_context",
    ]
    for target_name in TARGETS:
        eligible_n = int(raw_summary.loc[(target_name, "depth_only"), "n_participants"])
        summary_report.append(
            f"| {target_name} | {eligible_n} | "
            + " | ".join(metric_cell(target_name, model) for model in display_models)
            + " |"
        )
    win_summary = pd.read_csv(OUT / "patient_mean_wins.csv").groupby("model")[
        "participants_beating_patient_mean_by_mae"
    ].agg(["sum", "count"])
    win_total = int(win_summary["count"].max() * EXPECTED_PARTICIPANTS)
    summary_report += [
        "",
        "### Participants beating the patient-mean reference by MAE",
        "",
        f"Counts below are participant-target wins out of {win_total} possible per model (28 participants × 12 targets); target-level counts are in `patient_mean_wins.csv`.",
        "",
        "| Model | Participant-target wins |",
        "| --- | ---: |",
    ]
    for model_name, row in win_summary.iterrows():
        summary_report.append(f"| {model_name} | {int(row['sum'])} |")

    detection_skips = metrics.loc[
        (metrics["target_variant"] == "raw")
        & (metrics["model"] == "depth_only")
        & metrics["skip_reason"].isin(
            ["fewer_than_10_detected_spots", "fewer_than_3_distinct_target_values"]
        )
    ]
    summary_report += [
        "",
        "### Participants excluded from per-target Spearman",
        "",
    ]
    for target_name in TARGETS:
        rows = detection_skips.loc[detection_skips["target"] == target_name]
        if rows.empty:
            summary_report.append(f"- **{target_name}:** none.")
        else:
            details = ", ".join(
                f"{row.participant_id} ({row.skip_reason}; {int(row.n_detected_spots)} detected)"
                for row in rows.itertuples(index=False)
            )
            summary_report.append(f"- **{target_name}:** {details}.")

    summary_report += [
        "",
        "### Gate A macro comparisons (raw targets)",
        "",
        "| Model | Baseline | n participants | Mean Δ Spearman | 95% participant-bootstrap CI | Positive participants |",
        "| --- | --- | ---: | ---: | --- | ---: |",
    ]
    for _, row in raw_macro.iterrows():
        summary_report.append(
            f"| {row['model']} | {row['baseline']} | {int(row['n_participants'])} | "
            f"{row['mean_delta_spearman']:.4f} | [{row['ci95_low']:.4f}, {row['ci95_high']:.4f}] | "
            f"{int(row['participants_positive'])} |"
        )
    summary_report += [
        "",
        f"**Gate decision:** {gate_status}. {('At least one preregistered embedding model met both baseline comparisons.' if gate_pass else 'No preregistered embedding model met both baseline comparisons with a CI above zero and positive deltas in more than half of eligible participants.')}",
        "",
        "The exact candidate/baseline conditions were:",
        *[f"- {line}" for line in gate_reasons],
        "",
        "### Spatial-block permutation null",
        "",
        "The null aggregates targets and fixed out-of-fold predictions to 10×10 array-coordinate blocks and permutes block target means within library (1,000 permutations; no spot-wise shuffling). Full per-model/per-target results and skip counts are in `spatial_block_permutation.csv`.",
        f"- {int((block['empirical_p_one_sided'] < 0.05).sum())}/{int(block['empirical_p_one_sided'].notna().sum())} available model/target/variant tests had marginal one-sided empirical p < 0.05 (uncorrected; exploratory). Block-level support is not a substitute for participant-level gate comparisons.",
        "",
        "## Compute deviations and interpretation",
        "",
        "- The coordinate-descent Elastic Net run was stopped before any fold output; the solver was changed before seeing scores to SGD with the same squared-error Elastic Net penalty, alpha and L1/L2 mix, then capped at 10 epochs. The fixed iteration count is recorded in `elastic_net_fit_status.csv`.",
        "- Two MLP runs were stopped before predictions/metrics were available. The final model uses five epochs and batch size 4,096 (128-unit architecture and AdamW settings unchanged). These learned models are limited-optimization feasibility baselines, not tuned or converged candidates.",
        "- These compute deviations were recorded in `PREREG.md` before inspecting model results. The participant folds, target definitions, metric, bootstrap, comparisons and gate were unchanged.",
        "",
        "## Verification",
        "",
        f"- Independently recomputed three participant-level Spearman metrics; maximum absolute difference: {verification['absolute_difference'].max():.3g}. Details: `metric_recompute_verification.csv`.",
        "- Confirmed no spot key is repeated and no participant appears in more than one test fold; both 28-12265 libraries share one fold.",
        "- Counts reconcile to the existing Plan A/Plan B cohort: 28 participants, 29 libraries, 25,104 spots.",
        "",
        "## Risks, gaps, and what was not done",
        "",
        "- ResNet-50 is ImageNet-pretrained, not pathology-pretrained; ImageNet dataset usage terms were not independently verified. No claims are made about histology-specific representation quality.",
        "- Per-participant Spearman is descriptive on this cohort; participants and spots are few for generalization, and many spot-level values are sparse. Skipped participant-targets are listed rather than imputed.",
        "- Patient-mean Spearman is undefined for a constant prediction; its comparison is supplementary MAE only.",
        "- Stage 1 does not test clinical fibrosis labels, collagen/compartment features, registration, batch correction, fine-tuning, or external-cohort performance.",
        f"- Gate A result is **{gate_status}**; do not proceed to a later stage without explicit instruction.",
        "",
        "## Software versions and commands",
        "",
        "```text",
        json.dumps(package_versions, sort_keys=True),
        "```",
        "",
        "- Preparation: `python D:\\patent\\stage1_expression\\scripts\\run_stage1.py prepare`",
        "- Embeddings: `python D:\\patent\\stage1_expression\\scripts\\run_stage1.py embed`",
        "- Fitting: `python D:\\patent\\stage1_expression\\scripts\\run_stage1.py fit`",
        "- Metrics/report: `python D:\\patent\\stage1_expression\\scripts\\run_stage1.py report`",
        "",
        "## Output inventory",
        "",
        *[f"- `{path.name}`" for path in sorted(OUT.iterdir()) if path.is_file() and path.name != "STAGE1_REPORT.md"],
        "- `plots/target_spearman_summary.png`",
    ]
    report_path = OUT / "STAGE1_REPORT.md"
    estimate = sum(len(line) + 1 for line in summary_report) * 2
    ensure_write_budget(estimate, "write STAGE1_REPORT.md")
    report_path.write_text("\n".join(summary_report) + "\n", encoding="utf-8")
    print(f"Gate A {gate_status}; report: {report_path}")


def make_plots() -> None:
    import matplotlib.pyplot as plt

    summary = pd.read_csv(OUT / "model_summary.csv")
    raw = summary.loc[summary["target_variant"] == "raw"]
    fig, axes = plt.subplots(3, 4, figsize=(18, 12), constrained_layout=True)
    for ax, target in zip(axes.flat, TARGETS):
        group = raw.loc[(raw["target"] == target) & raw["mean_participant_spearman"].notna()]
        x = np.arange(len(group))
        means = group["mean_participant_spearman"].to_numpy()
        low = means - group["ci95_low"].to_numpy()
        high = group["ci95_high"].to_numpy() - means
        ax.errorbar(x, means, yerr=np.vstack([low, high]), fmt="o", capsize=3)
        ax.axhline(0, color="gray", linewidth=0.8)
        ax.set_xticks(x, group["model"], rotation=60, ha="right", fontsize=7)
        ax.set_title(f"{target} (n={int(group['n_participants'].max()) if not group.empty else 0})")
        ax.set_ylabel("Mean participant Spearman (95% bootstrap CI)")
    fig.suptitle("Out-of-fold expression baselines — raw normalized targets")
    path = OUT / "plots" / "target_spearman_summary.png"
    ensure_write_budget(20_000_000, "write result plot")
    fig.savefig(path, dpi=160)
    plt.close(fig)
    if path.stat().st_size >= MAX_STEP_BYTES:
        raise RuntimeError(f"Plot exceeded the 1 GB limit: {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "embed", "fit", "report", "all"])
    args = parser.parse_args()
    ensure_output_dir()
    if args.command == "prepare":
        prepare()
    elif args.command == "embed":
        embed()
    elif args.command == "fit":
        fit()
    elif args.command == "report":
        run_report()
        make_plots()
    else:
        prepare()
        embed()
        fit()
        run_report()
        make_plots()


if __name__ == "__main__":
    main()
