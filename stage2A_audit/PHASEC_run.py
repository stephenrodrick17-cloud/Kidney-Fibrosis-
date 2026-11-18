from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import random
import sys
import time
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageEnhance
from torch.utils.data import DataLoader
from torchvision.models.segmentation import deeplabv3_resnet50

import run_renfast_baseline as phase_a


ROOT = Path(__file__).resolve().parent
ARCHIVE = Path(r"D:\patent\m2t49zf6xr-1.zip")
PHASE_A_DIR = ROOT / "renfast_baseline_run"
SPLIT_FILE = ROOT / "PHASEA_final_split_manifest.csv"
CHECKPOINT_A = PHASE_A_DIR / "checkpoint_best.pt"
PREFLIGHT_FILE = ROOT / "PHASEC_PREFLIGHT.json"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MAX_EPOCHS = 100
PATIENCE = 12
TRAIN_SEEDS = (20261122, 20261123)
DEEPLAB_SEED = 20261116
BOOTSTRAP_SEED = 20261125
BOOTSTRAP_REPLICATES = 10_000
THRESHOLD_GRID = (0.30, 0.40, 0.50, 0.60, 0.70)
METRICS = ("dice", "iou", "precision", "recall")
RESAMPLE_LIMIT_SECONDS = 7_100


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}")
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}")
    if fieldnames is None:
        fieldnames = list(dict.fromkeys(key for row in rows for key in row)) if rows else []
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_split() -> dict[str, Any]:
    records: dict[str, list[dict[str, str]]] = {
        "training": [],
        "validation": [],
        "test": [],
    }
    assignment_map = {
        "training": "training",
        "validation": "validation",
        "official_test": "test",
    }
    with SPLIT_FILE.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            normalized_assignment = assignment_map.get(row["assignment"])
            if normalized_assignment is not None:
                records[normalized_assignment].append(row)
    expected = {"training": (105, 6), "validation": (18, 1), "test": (50, 10)}
    family_sets: dict[str, set[str]] = {}
    for split, expected_counts in expected.items():
        families = {row["family_id"] for row in records[split]}
        family_sets[split] = families
        if (len(records[split]), len(families)) != expected_counts:
            raise ValueError(f"{split} split count mismatch: {len(records[split])}, {len(families)}")
    if (
        family_sets["training"] & family_sets["validation"]
        or family_sets["training"] & family_sets["test"]
        or family_sets["validation"] & family_sets["test"]
    ):
        raise ValueError("Filename family appears in multiple active splits")
    if not ARCHIVE.is_file() or file_sha256(ARCHIVE) != json.loads(
        (PHASE_A_DIR / "audit_summary.json").read_text(encoding="utf-8")
    )["archive_sha256"]:
        raise ValueError("RENFAST archive is missing or differs from the Phase A archive")
    return {
        **records,
        "families": {key: sorted(value) for key, value in family_sets.items()},
    }


def read_pair(archive: zipfile.ZipFile, record: dict[str, str]) -> tuple[np.ndarray, np.ndarray]:
    image_bytes = archive.read(record["image_member"])
    mask_bytes = archive.read(record["mask_member"])
    if sha256(image_bytes) != record["image_sha256"]:
        raise ValueError(f"Image hash mismatch: {record['image_member']}")
    if sha256(mask_bytes) != record["mask_sha256"]:
        raise ValueError(f"Mask hash mismatch: {record['mask_member']}")
    with Image.open(io.BytesIO(image_bytes)) as image:
        image.load()
        rgb = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
    with Image.open(io.BytesIO(mask_bytes)) as mask:
        mask.load()
        target = np.asarray(mask.convert("L"), dtype=np.uint8).copy() == 255
    if rgb.shape[:2] != target.shape:
        raise ValueError(f"Input/mask dimensions differ for {record['stem']}")
    if rgb.shape[:2] != (512, 512):
        raise ValueError(f"Expected 512x512 Phase A tiles, found {rgb.shape[:2]}")
    return rgb, target


def set_seeds(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def make_deeplab() -> torch.nn.Module:
    model = deeplabv3_resnet50(
        weights=None,
        weights_backbone=None,
        num_classes=1,
        aux_loss=False,
    )
    return model


def set_training_mode(model: torch.nn.Module, kind: str) -> None:
    model.train()
    if kind == "deeplab":
        pooling_branch = model.classifier[0].convs[4]
        if not any(isinstance(module, torch.nn.BatchNorm2d) for module in pooling_branch.modules()):
            raise RuntimeError("Expected the torchvision DeepLab ASPP pooling BatchNorm branch")
        pooling_branch.eval()


def model_logits(model: torch.nn.Module, image: np.ndarray) -> torch.Tensor:
    height, width = image.shape[:2]
    tensor = torch.from_numpy(np.array(image, copy=True)).permute(2, 0, 1).float().div_(255.0)
    pad_height = (-height) % 16
    pad_width = (-width) % 16
    tensor = F.pad(tensor, (0, pad_width, 0, pad_height))[None].to(DEVICE)
    output = model(tensor)
    if isinstance(output, dict):
        output = output["out"]
    return output[0, 0, :height, :width]


def pixel_metrics(prediction: np.ndarray, target: np.ndarray) -> dict[str, float | None]:
    pred = np.asarray(prediction, dtype=bool)
    truth = np.asarray(target, dtype=bool)
    tp = int(np.logical_and(pred, truth).sum())
    fp = int(np.logical_and(pred, ~truth).sum())
    fn = int(np.logical_and(~pred, truth).sum())
    pred_count = tp + fp
    truth_count = tp + fn
    denom_dice = 2 * tp + fp + fn
    denom_iou = tp + fp + fn
    return {
        "dice": 1.0 if denom_dice == 0 else (2 * tp / denom_dice),
        "iou": 1.0 if denom_iou == 0 else (tp / denom_iou),
        "precision": None if pred_count == 0 else (tp / pred_count),
        "recall": None if truth_count == 0 else (tp / truth_count),
    }


def family_macro(rows: list[dict[str, Any]], metric: str) -> float | None:
    by_family: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        value = row.get(metric)
        if value is not None:
            by_family[row["family_id"]].append(float(value))
    family_values = [float(np.mean(values)) for values in by_family.values() if values]
    return None if not family_values else float(np.mean(family_values))


def bootstrap_metric(
    rows: list[dict[str, Any]],
    metric: str,
    seed: int,
    differences: dict[str, float] | None = None,
) -> list[float] | None:
    by_family: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        value = row.get(metric)
        if differences is not None:
            value = differences.get(row["stem"])
        if value is not None:
            by_family[row["family_id"]].append(float(value))
    families = sorted(by_family)
    if len(families) < 2:
        return None
    values = np.asarray([np.mean(by_family[family]) for family in families], dtype=np.float64)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(families), size=(BOOTSTRAP_REPLICATES, len(families)))
    estimates = values[draws].mean(axis=1)
    return [float(np.percentile(estimates, 2.5)), float(np.percentile(estimates, 97.5))]


def summarize_rows(
    rows: list[dict[str, Any]],
    seed: int,
    delta_by_stem: dict[str, float] | None = None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "images": len(rows),
        "families": len({row["family_id"] for row in rows}),
    }
    for metric in METRICS:
        values = [float(row[metric]) for row in rows if row.get(metric) is not None]
        summary[f"{metric}_image_macro"] = None if not values else float(np.mean(values))
        summary[f"{metric}_family_macro"] = family_macro(rows, metric)
        summary[f"{metric}_family_bootstrap_95_ci"] = bootstrap_metric(
            rows, metric, seed
        )
        if delta_by_stem is not None:
            summary[f"{metric}_delta_family_macro"] = family_macro(
                [
                    {
                        "family_id": row["family_id"],
                        "stem": row["stem"],
                        metric: delta_by_stem.get(row["stem"]),
                    }
                    for row in rows
                ],
                metric,
            )
            summary[f"{metric}_delta_family_bootstrap_95_ci"] = bootstrap_metric(
                rows, metric, seed, delta_by_stem
            )
    return summary


def train_one(
    split: dict[str, Any],
    seed: int,
    kind: str,
) -> dict[str, Any]:
    if kind not in {"unet", "deeplab"}:
        raise ValueError(f"Unknown training kind: {kind}")
    if kind == "unet":
        stem = f"PHASEC_UNET_seed_{seed}"
        model_factory = phase_a.UNet
    else:
        stem = "PHASEC_DEEPLABV3_RESNET50_seed_20261116"
        model_factory = make_deeplab
    checkpoint_path = ROOT / f"{stem}_checkpoint.pt"
    history_path = ROOT / f"{stem}_history.csv"
    metadata_path = ROOT / f"{stem}_metadata.json"
    for path in (checkpoint_path, history_path, metadata_path):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite {path}")

    set_seeds(seed)
    train_data = phase_a.TileDataset(ARCHIVE, split["training"], True, seed)
    validation_data = phase_a.TileDataset(ARCHIVE, split["validation"], False, seed)
    generator = torch.Generator().manual_seed(seed)
    train_loader = DataLoader(
        train_data, batch_size=1, shuffle=True, num_workers=0, generator=generator
    )
    validation_loader = DataLoader(
        validation_data, batch_size=1, shuffle=False, num_workers=0
    )
    model = model_factory().to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    best_dice = -math.inf
    best_epoch = 0
    stale_epochs = 0
    history: list[dict[str, Any]] = []
    started = time.monotonic()
    chosen_threshold = 0.5

    for epoch in range(1, MAX_EPOCHS + 1):
        if time.monotonic() - started > RESAMPLE_LIMIT_SECONDS:
            raise TimeoutError(f"{stem} reached the 2-hour safety stop")
        set_training_mode(model, kind)
        losses: list[float] = []
        for images, masks in train_loader:
            if time.monotonic() - started > RESAMPLE_LIMIT_SECONDS:
                raise TimeoutError(f"{stem} reached the 2-hour safety stop")
            images, masks = images.to(DEVICE), masks.to(DEVICE)
            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            if isinstance(logits, dict):
                logits = logits["out"]
            loss = 0.5 * F.binary_cross_entropy_with_logits(logits, masks)
            loss = loss + 0.5 * phase_a.soft_dice_loss(logits, masks)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach().item()))

        model.eval()
        val_probabilities: list[np.ndarray] = []
        val_targets: list[np.ndarray] = []
        with torch.no_grad():
            for images, masks in validation_loader:
                logits = model(images.to(DEVICE))
                if isinstance(logits, dict):
                    logits = logits["out"]
                val_probabilities.append(torch.sigmoid(logits)[0, 0].cpu().numpy())
                val_targets.append((masks[0, 0].numpy() >= 0.5))
        candidate_thresholds = THRESHOLD_GRID if kind == "deeplab" else (0.5,)
        threshold_scores = []
        for threshold in candidate_thresholds:
            scores = [
                pixel_metrics(probability >= threshold, target)["dice"]
                for probability, target in zip(val_probabilities, val_targets)
            ]
            threshold_scores.append(float(np.mean(scores)))
        best_index = max(
            range(len(candidate_thresholds)),
            key=lambda index: (
                threshold_scores[index],
                -abs(candidate_thresholds[index] - 0.5),
                -candidate_thresholds[index],
            ),
        )
        epoch_dice = threshold_scores[best_index]
        epoch_threshold = candidate_thresholds[best_index]
        history.append(
            {
                "epoch": epoch,
                "train_loss": float(np.mean(losses)),
                "validation_dice": epoch_dice,
                "validation_threshold": epoch_threshold,
            }
        )
        print(
            f"{stem} epoch={epoch:03d} loss={np.mean(losses):.6f} "
            f"val_dice={epoch_dice:.6f} threshold={epoch_threshold:.2f}"
        )
        if epoch_dice > best_dice:
            best_dice = epoch_dice
            best_epoch = epoch
            chosen_threshold = epoch_threshold
            stale_epochs = 0
            temporary = checkpoint_path.with_name(checkpoint_path.name + ".tmp")
            torch.save(
                {
                    "model_state": model.state_dict(),
                    "seed": seed,
                    "best_epoch": best_epoch,
                    "validation_dice": best_dice,
                    "threshold": chosen_threshold,
                    "model_kind": kind,
                    "train_families": split["families"]["training"],
                    "validation_families": split["families"]["validation"],
                },
                temporary,
            )
            temporary.replace(checkpoint_path)
        else:
            stale_epochs += 1
        if stale_epochs >= PATIENCE:
            break
        if time.monotonic() - started > RESAMPLE_LIMIT_SECONDS:
            raise TimeoutError(f"{stem} reached the 2-hour safety stop")

    elapsed = time.monotonic() - started
    if not checkpoint_path.is_file():
        raise RuntimeError(f"No best checkpoint was produced for {stem}")
    with history_path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(history[0]))
        writer.writeheader()
        writer.writerows(history)
    metadata = {
        "status": "completed",
        "model_kind": kind,
        "seed": seed,
        "device": str(DEVICE),
        "epochs_completed": len(history),
        "best_epoch": best_epoch,
        "best_validation_dice": best_dice,
        "selected_threshold": chosen_threshold,
        "threshold_grid": list(THRESHOLD_GRID) if kind == "deeplab" else [0.5],
        "checkpoint": checkpoint_path.name,
        "checkpoint_sha256": file_sha256(checkpoint_path),
        "elapsed_seconds": round(elapsed, 2),
        "train_pairs": len(train_data),
        "validation_pairs": len(validation_data),
        "train_families": split["families"]["training"],
        "validation_families": split["families"]["validation"],
        "training_recipe": "Phase A AdamW lr=1e-3 weight_decay=1e-4, batch=1, BCE/Dice weighted 0.5 each, Phase A flips/rotations",
        "patience": PATIENCE,
        "max_epochs": MAX_EPOCHS,
    }
    write_json(metadata_path, metadata)
    return {"model": model_factory, "checkpoint": checkpoint_path, "metadata": metadata}


def preflight(split: dict[str, Any]) -> dict[str, Any]:
    if PREFLIGHT_FILE.exists():
        raise FileExistsError(f"Refusing to overwrite {PREFLIGHT_FILE}")
    phase_a_meta = json.loads((PHASE_A_DIR / "run_metadata.json").read_text(encoding="utf-8"))
    if phase_a_meta["checkpoint_sha256"] != file_sha256(CHECKPOINT_A):
        raise ValueError("Frozen Phase A checkpoint hash mismatch")

    training = phase_a.TileDataset(ARCHIVE, split["training"][:1], False, 20261122)
    image, target = training[0]
    image = image[None].to(DEVICE)
    target = target[None].to(DEVICE)

    def measure(kind: str) -> float:
        set_seeds(20261116)
        model = (phase_a.UNet() if kind == "unet" else make_deeplab()).to(DEVICE)
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        durations = []
        for _ in range(5):
            set_training_mode(model, kind)
            start = time.perf_counter()
            optimizer.zero_grad(set_to_none=True)
            result = model(image)
            if isinstance(result, dict):
                result = result["out"]
            loss = 0.5 * F.binary_cross_entropy_with_logits(result, target)
            loss = loss + 0.5 * phase_a.soft_dice_loss(result, target)
            loss.backward()
            if DEVICE.type == "cuda":
                torch.cuda.synchronize()
            durations.append(time.perf_counter() - start)
        del model, optimizer
        if DEVICE.type == "cuda":
            torch.cuda.empty_cache()
        return float(np.mean(durations[1:]))

    unet_step = measure("unet")
    deeplab_step = measure("deeplab")
    phase_a_seconds_per_epoch = phase_a_meta["elapsed_seconds"] / phase_a_meta["epochs_completed"]
    measured_unet_estimate = 100 * phase_a_seconds_per_epoch
    # Scale the recorded Phase A whole-epoch runtime by the measured model-step ratio.
    deeplab_estimate = measured_unet_estimate * (deeplab_step / unet_step)
    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "device": str(DEVICE),
        "gpu": torch.cuda.get_device_name(DEVICE) if DEVICE.type == "cuda" else None,
        "phase_a_elapsed_seconds": phase_a_meta["elapsed_seconds"],
        "phase_a_epochs": phase_a_meta["epochs_completed"],
        "phase_a_seconds_per_epoch": phase_a_seconds_per_epoch,
        "max_epochs": MAX_EPOCHS,
        "unet_preflight_step_seconds": unet_step,
        "deeplab_preflight_step_seconds": deeplab_step,
        "unet_projected_seconds": measured_unet_estimate,
        "deeplab_projected_seconds": deeplab_estimate,
        "preflight_updates_saved_weights": False,
        "runtime_budget_seconds": 7200,
        "all_runs_within_budget": max(measured_unet_estimate, deeplab_estimate) < 7200,
        "checkpoint_sha256": file_sha256(CHECKPOINT_A),
    }
    write_json(PREFLIGHT_FILE, result)
    return result


def rotate_od(rgb: np.ndarray, angle_degrees: float) -> np.ndarray:
    axis = np.ones(3, dtype=np.float64) / math.sqrt(3.0)
    angle = math.radians(angle_degrees)
    skew = np.array(
        [[0.0, -axis[2], axis[1]], [axis[2], 0.0, -axis[0]], [-axis[1], axis[0], 0.0]],
        dtype=np.float64,
    )
    rotation = (
        np.eye(3) * math.cos(angle)
        + (1 - math.cos(angle)) * np.outer(axis, axis)
        + math.sin(angle) * skew
    )
    optical_density = -np.log((rgb.astype(np.float32) + 1.0) / 256.0)
    shifted = np.maximum(optical_density @ rotation.T, 0.0)
    transformed = 256.0 * np.exp(-shifted) - 1.0
    return np.clip(np.rint(transformed), 0, 255).astype(np.uint8)


def perturb(rgb: np.ndarray, kind: str, multiplier_or_degrees: float) -> np.ndarray:
    if kind == "hue":
        hsv = np.asarray(Image.fromarray(rgb).convert("HSV"), dtype=np.uint8).copy()
        offset = int(round(multiplier_or_degrees * 256.0 / 360.0))
        hsv[:, :, 0] = ((hsv[:, :, 0].astype(np.int16) + offset) % 256).astype(np.uint8)
        return np.asarray(Image.fromarray(hsv, mode="HSV").convert("RGB"), dtype=np.uint8)
    image = Image.fromarray(rgb)
    if kind == "saturation":
        return np.asarray(ImageEnhance.Color(image).enhance(multiplier_or_degrees), dtype=np.uint8)
    if kind == "brightness":
        return np.asarray(ImageEnhance.Brightness(image).enhance(multiplier_or_degrees), dtype=np.uint8)
    if kind == "contrast":
        return np.asarray(ImageEnhance.Contrast(image).enhance(multiplier_or_degrees), dtype=np.uint8)
    if kind == "od":
        return rotate_od(rgb, multiplier_or_degrees)
    raise ValueError(f"Unknown perturbation {kind}")


def color_prediction(rgb: np.ndarray) -> np.ndarray:
    return rgb[:, :, 2].astype(np.int16) - rgb[:, :, 0].astype(np.int16) >= 2


def inference_probability(model: torch.nn.Module, rgb: np.ndarray) -> np.ndarray:
    return torch.sigmoid(model_logits(model, rgb)).detach().cpu().numpy()


def test_inputs(split: dict[str, Any]) -> list[tuple[dict[str, str], np.ndarray, np.ndarray]]:
    result = []
    with zipfile.ZipFile(ARCHIVE) as archive:
        for record in split["test"]:
            rgb, target = read_pair(archive, record)
            result.append((record, rgb, target))
    return result


def bootstrap_correlation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    per_family: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for row in rows:
        per_family[row["family_id"]].append(
            (float(row["mean_entropy"]), 1.0 - float(row["ensemble_dice"]))
        )
    families = sorted(per_family)
    family_values = [
        (
            float(np.mean([item[0] for item in per_family[family]])),
            float(np.mean([item[1] for item in per_family[family]])),
        )
        for family in families
    ]

    def spearman(values: list[tuple[float, float]]) -> float | None:
        if len(values) < 3:
            return None

        def rank(values_: list[float]) -> np.ndarray:
            order = np.argsort(values_, kind="mergesort")
            ranks = np.empty(len(values_), dtype=np.float64)
            start = 0
            while start < len(order):
                end = start + 1
                while end < len(order) and values_[order[end]] == values_[order[start]]:
                    end += 1
                ranks[order[start:end]] = (start + end - 1) / 2.0 + 1.0
                start = end
            return ranks

        x = rank([item[0] for item in values])
        y = rank([item[1] for item in values])
        if np.std(x) == 0 or np.std(y) == 0:
            return None
        return float(np.corrcoef(x, y)[0, 1])

    estimate = spearman(family_values)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = rng.integers(0, len(families), size=(BOOTSTRAP_REPLICATES, len(families)))
    boot: list[float] = []
    for draw in draws:
        value = spearman([family_values[index] for index in draw])
        if value is not None and math.isfinite(value):
            boot.append(value)
    interval = (
        [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]
        if boot
        else None
    )
    return {
        "family_spearman": estimate,
        "family_bootstrap_95_ci": interval,
        "valid_bootstrap_replicates": len(boot),
        "families": len(families),
    }


def svg_reliability(rows: list[dict[str, Any]], path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}")
    width, height, margin = 640, 520, 60
    plot_width, plot_height = width - 2 * margin, height - 2 * margin
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{margin}" stroke="#777" stroke-dasharray="6,5"/>',
        f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="black"/>',
        f'<line x1="{margin}" y1="{height-margin}" x2="{margin}" y2="{margin}" stroke="black"/>',
        f'<text x="{width/2}" y="{height-12}" text-anchor="middle" font-family="sans-serif">Mean predicted probability</text>',
        f'<text x="16" y="{height/2}" transform="rotate(-90 16 {height/2})" text-anchor="middle" font-family="sans-serif">Observed positive fraction</text>',
        f'<text x="{width/2}" y="24" text-anchor="middle" font-family="sans-serif" font-size="16">Ensemble reliability (test pixels)</text>',
    ]
    for row in rows:
        if row["pixel_count"] == 0:
            continue
        x = margin + float(row["mean_probability"]) * plot_width
        y = height - margin - float(row["observed_positive_fraction"]) * plot_height
        radius = min(12.0, 3.0 + math.log10(float(row["pixel_count"]) + 1))
        elements.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" fill="#2463a6" fill-opacity="0.75"/>')
    elements.append("</svg>")
    path.write_text("\n".join(elements), encoding="utf-8")


def test_and_write(split: dict[str, Any], trained: dict[str, Any]) -> dict[str, Any]:
    expected = [
        "PHASEC_robustness_per_image.csv",
        "PHASEC_robustness_summary.csv",
        "PHASEC_test_model_comparison.csv",
        "PHASEC_ensemble_uncertainty_per_image.csv",
        "PHASEC_reliability_bins.csv",
        "PHASEC_reliability_plot.svg",
        "PHASEC_ood_feature_stats.json",
        "PHASEC_ood_test_flags.csv",
        "PHASEC_uncertainty_summary.json",
    ]
    for name in expected:
        if (ROOT / name).exists():
            raise FileExistsError(f"Refusing to overwrite {ROOT / name}")

    # All training and validation decisions are complete before test pixels are read.
    phase_a_checkpoint = torch.load(CHECKPOINT_A, map_location=DEVICE, weights_only=True)
    frozen_unet = phase_a.UNet().to(DEVICE)
    frozen_unet.load_state_dict(phase_a_checkpoint["model_state"])
    frozen_unet.eval()
    unet_models = [frozen_unet]
    for seed in TRAIN_SEEDS:
        checkpoint = torch.load(trained[f"unet_{seed}"]["checkpoint"], map_location=DEVICE, weights_only=True)
        model = phase_a.UNet().to(DEVICE)
        model.load_state_dict(checkpoint["model_state"])
        model.eval()
        unet_models.append(model)
    deeplab = None
    deeplab_threshold = None
    if "deeplab" in trained:
        deeplab_checkpoint = torch.load(
            trained["deeplab"]["checkpoint"], map_location=DEVICE, weights_only=True
        )
        deeplab = make_deeplab().to(DEVICE)
        deeplab.load_state_dict(deeplab_checkpoint["model_state"])
        deeplab.eval()
        deeplab_threshold = float(deeplab_checkpoint["threshold"])

    training_features = []
    with zipfile.ZipFile(ARCHIVE) as archive:
        for record in split["training"]:
            rgb, _ = read_pair(archive, record)
            channels = np.moveaxis(rgb.astype(np.float64), 2, 0)
            training_features.append(
                [float(channels[channel].mean()) for channel in range(3)]
                + [float(channels[channel].std()) for channel in range(3)]
            )
    feature_array = np.asarray(training_features, dtype=np.float64)
    feature_mean = feature_array.mean(axis=0)
    feature_sd = np.maximum(feature_array.std(axis=0, ddof=0), 1e-6)
    feature_names = ("R_mean", "G_mean", "B_mean", "R_sd", "G_sd", "B_sd")
    write_json(
        ROOT / "PHASEC_ood_feature_stats.json",
        {
            "fit_split": "Phase A training only",
            "feature_names": list(feature_names),
            "mean": feature_mean.tolist(),
            "sd": feature_sd.tolist(),
            "sd_floor": 1e-6,
            "flag_rule": "flag if any absolute standardized feature deviation > 3.0",
        },
    )

    data = test_inputs(split)
    clean_rows: dict[str, list[dict[str, Any]]] = {
        "frozen_unet": [],
        "color_threshold": [],
        "ensemble": [],
        "deeplab": [],
    }
    uncertainty_rows: list[dict[str, Any]] = []
    ood_rows: list[dict[str, Any]] = []
    reliability_counts = np.zeros(10, dtype=np.int64)
    reliability_probability = np.zeros(10, dtype=np.float64)
    reliability_positive = np.zeros(10, dtype=np.float64)
    brier_sum = 0.0
    pixel_total = 0
    pixel_entropy_sum = 0.0
    pixel_variance_sum = 0.0
    pixel_entropy_values: list[np.ndarray] = []
    pixel_variance_values: list[np.ndarray] = []

    for record, rgb, target in data:
        with torch.no_grad():
            member_probabilities = [inference_probability(model, rgb) for model in unet_models]
            deeplab_probability = (
                inference_probability(deeplab, rgb) if deeplab is not None else None
            )
        ensemble_probability = np.mean(member_probabilities, axis=0)
        ensemble_prediction = ensemble_probability >= 0.5
        frozen_prediction = member_probabilities[0] >= 0.5
        baseline_prediction = color_prediction(rgb)
        record_base = {"stem": record["stem"], "family_id": record["family_id"]}
        clean_rows["frozen_unet"].append({**record_base, **pixel_metrics(frozen_prediction, target)})
        clean_rows["color_threshold"].append({**record_base, **pixel_metrics(baseline_prediction, target)})
        clean_rows["ensemble"].append({**record_base, **pixel_metrics(ensemble_prediction, target)})
        if deeplab_probability is not None and deeplab_threshold is not None:
            clean_rows["deeplab"].append(
                {
                    **record_base,
                    **pixel_metrics(deeplab_probability >= deeplab_threshold, target),
                }
            )

        entropy = -(
            ensemble_probability * np.log(np.clip(ensemble_probability, 1e-7, 1.0))
            + (1.0 - ensemble_probability)
            * np.log(np.clip(1.0 - ensemble_probability, 1e-7, 1.0))
        )
        variance = np.var(np.stack(member_probabilities, axis=0), axis=0)
        pixel_entropy_values.append(entropy.astype(np.float32).ravel())
        pixel_variance_values.append(variance.astype(np.float32).ravel())
        pixel_entropy_sum += float(entropy.sum())
        pixel_variance_sum += float(variance.sum())
        pixels = ensemble_probability.size
        pixel_total += pixels
        brier_sum += float(np.square(ensemble_probability - target.astype(np.float32)).sum())
        bin_index = np.minimum((ensemble_probability * 10).astype(np.int64), 9)
        for index in range(10):
            selected = bin_index == index
            count = int(selected.sum())
            reliability_counts[index] += count
            if count:
                reliability_probability[index] += float(ensemble_probability[selected].sum())
                reliability_positive[index] += float(target[selected].sum())
        p_entropy = np.percentile(entropy, [50, 95])
        p_variance = np.percentile(variance, [50, 95])
        uncertainty_rows.append(
            {
                **record_base,
                "ensemble_dice": clean_rows["ensemble"][-1]["dice"],
                "mean_entropy": float(entropy.mean()),
                "median_pixel_entropy": float(p_entropy[0]),
                "p95_pixel_entropy": float(p_entropy[1]),
                "mean_probability_variance": float(variance.mean()),
                "median_pixel_variance": float(p_variance[0]),
                "p95_pixel_variance": float(p_variance[1]),
                "mean_ensemble_probability": float(ensemble_probability.mean()),
            }
        )

        channels = np.moveaxis(rgb.astype(np.float64), 2, 0)
        features = np.asarray(
            [float(channels[channel].mean()) for channel in range(3)]
            + [float(channels[channel].std()) for channel in range(3)],
            dtype=np.float64,
        )
        standardized = np.abs((features - feature_mean) / feature_sd)
        flagged = bool(np.any(standardized > 3.0))
        ood_rows.append(
            {
                **record_base,
                "ood_flag": flagged,
                "max_abs_standardized_feature": float(standardized.max()),
                "ensemble_dice": clean_rows["ensemble"][-1]["dice"],
                **{f"feature_{name}": float(value) for name, value in zip(feature_names, features)},
            }
        )

    # Robustness experiments: no transformed inputs or test outputs are used for tuning.
    robustness_per_image: list[dict[str, Any]] = []
    robustness_sets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for model_name, model in (("frozen_unet", frozen_unet), ("color_threshold", None)):
        for record, rgb, target in data:
            clean_prediction = (
                inference_probability(model, rgb) >= 0.5
                if model is not None
                else color_prediction(rgb)
            )
            row = {
                "model": model_name,
                "condition": "clean",
                "condition_type": "clean",
                "level": "0",
                "direction": "none",
                "stem": record["stem"],
                "family_id": record["family_id"],
                **pixel_metrics(clean_prediction, target),
            }
            robustness_per_image.append(row)
            robustness_sets[(model_name, "clean")] = robustness_sets.get((model_name, "clean"), []) + [row]

    paired_specs: list[tuple[str, str, tuple[float, float, float]]] = []
    for kind, levels in (
        ("hue", (5.0, 10.0, 20.0)),
        ("saturation", (0.2, 0.4, 0.6)),
        ("brightness", (0.1, 0.25, 0.5)),
        ("contrast", (0.1, 0.25, 0.5)),
        ("od", (5.0, 10.0, 15.0)),
    ):
        for level_index, level in enumerate(levels, start=1):
            paired_specs.append((kind, str(level_index), (level, 0.0, 0.0)))

    def condition_images(kind: str, level_index: int, level: float, rgb: np.ndarray) -> list[tuple[str, np.ndarray]]:
        if kind == "hue" or kind == "od":
            return [
                (str(direction), perturb(rgb, kind, direction * level))
                for direction in (-1, 1)
            ]
        if kind in {"saturation", "brightness", "contrast"}:
            multiplier_pairs = {
                "saturation": ((0.8, 1.2), (0.6, 1.4), (0.4, 1.6)),
                "brightness": ((0.9, 1.1), (0.75, 1.25), (0.5, 1.5)),
                "contrast": ((0.9, 1.1), (0.75, 1.25), (0.5, 1.5)),
            }
            return [
                (f"mult_{value:.2f}", perturb(rgb, kind, value))
                for value in multiplier_pairs[kind][level_index - 1]
            ]
        raise ValueError(kind)

    for kind, level_index_text, _ in paired_specs:
        level_index = int(level_index_text)
        if kind in {"hue", "od"}:
            level = ({"hue": (5.0, 10.0, 20.0), "od": (5.0, 10.0, 15.0)})[kind][level_index - 1]
        else:
            level = 0.0
        by_direction: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
        for record, rgb, target in data:
            for direction, transformed in condition_images(kind, level_index, level, rgb):
                for model_name, model in (("frozen_unet", frozen_unet), ("color_threshold", None)):
                    prediction = (
                        inference_probability(model, transformed) >= 0.5
                        if model is not None
                        else color_prediction(transformed)
                    )
                    metric_values = pixel_metrics(prediction, target)
                    condition = f"{kind}_level_{level_index}"
                    directional_row = {
                        "model": model_name,
                        "condition": condition,
                        "condition_type": kind,
                        "level": level_index,
                        "direction": direction,
                        "stem": record["stem"],
                        "family_id": record["family_id"],
                        **metric_values,
                    }
                    robustness_per_image.append(directional_row)
                    by_direction[model_name][direction].append(directional_row)
        for model_name, direction_rows in by_direction.items():
            directions = list(direction_rows.values())
            for pair_index, first in enumerate(directions):
                for second in directions[pair_index + 1 :]:
                    lookup_second = {row["stem"]: row for row in second}
                    for first_row in first:
                        second_row = lookup_second[first_row["stem"]]
                        mean_row = {
                            "model": model_name,
                            "condition": f"{kind}_level_{level_index}_mean",
                            "condition_type": kind,
                            "level": level_index,
                            "direction": "mean",
                            "stem": first_row["stem"],
                            "family_id": first_row["family_id"],
                        }
                        for metric in METRICS:
                            values = [
                                first_row[metric],
                                second_row[metric],
                            ]
                            valid = [float(value) for value in values if value is not None]
                            mean_row[metric] = None if not valid else float(np.mean(valid))
                        robustness_per_image.append(mean_row)

    # Resolution sensitivity.
    for scale in (0.5, 0.75, 1.25, 1.5):
        for record, rgb, target in data:
            resized_size = (int(round(rgb.shape[1] * scale)), int(round(rgb.shape[0] * scale)))
            resized = np.asarray(
                Image.fromarray(rgb).resize(resized_size, Image.Resampling.LANCZOS),
                dtype=np.uint8,
            )
            # The target grid remains the original 512x512 mask; model outputs are mapped back.
            with torch.no_grad():
                probability = inference_probability(frozen_unet, resized)
            pred_scaled = (probability >= 0.5).astype(np.uint8) * 255
            prediction = np.asarray(
                Image.fromarray(pred_scaled).resize((512, 512), Image.Resampling.NEAREST),
                dtype=np.uint8,
            ) > 0
            baseline_scaled = color_prediction(resized).astype(np.uint8) * 255
            baseline = np.asarray(
                Image.fromarray(baseline_scaled).resize((512, 512), Image.Resampling.NEAREST),
                dtype=np.uint8,
            ) > 0
            for model_name, pred in (("frozen_unet", prediction), ("color_threshold", baseline)):
                robustness_per_image.append(
                    {
                        "model": model_name,
                        "condition": f"resolution_{scale:.2f}x",
                        "condition_type": "resolution",
                        "level": scale,
                        "direction": "none",
                        "stem": record["stem"],
                        "family_id": record["family_id"],
                        **pixel_metrics(pred, target),
                    }
                )

    # Tile-size sensitivity compares corresponding center crops only.
    for tile_size in (256, 384, 512):
        start = (512 - tile_size) // 2
        end = start + tile_size
        for record, rgb, target in data:
            crop = rgb[start:end, start:end]
            target_crop = target[start:end, start:end]
            with torch.no_grad():
                prediction = inference_probability(frozen_unet, crop) >= 0.5
            baseline = color_prediction(crop)
            for model_name, pred in (("frozen_unet", prediction), ("color_threshold", baseline)):
                robustness_per_image.append(
                    {
                        "model": model_name,
                        "condition": f"tile_{tile_size}",
                        "condition_type": "tile_size",
                        "level": tile_size,
                        "direction": "none",
                        "stem": record["stem"],
                        "family_id": record["family_id"],
                        **pixel_metrics(pred, target_crop),
                    }
                )

    # Clean rows in the aggregate table use the same test observations.
    summary_rows = []
    grouped_conditions: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in robustness_per_image:
        grouped_conditions[(row["model"], row["condition"])].append(row)
    for (model_name, condition), rows in grouped_conditions.items():
        clean = robustness_sets[(model_name, "clean")]
        clean_by_stem = {row["stem"]: row for row in clean}
        delta_rows = {
            row["stem"]: float(row["dice"] - clean_by_stem[row["stem"]]["dice"])
            for row in rows
            if row["dice"] is not None and clean_by_stem[row["stem"]]["dice"] is not None
        }
        summary = summarize_rows(rows, BOOTSTRAP_SEED, delta_rows)
        summary_rows.append(
            {
                "model": model_name,
                "condition": condition,
                "condition_type": rows[0]["condition_type"],
                "level": rows[0]["level"],
                "direction": rows[0]["direction"],
                **summary,
            }
        )
    write_csv(ROOT / "PHASEC_robustness_per_image.csv", robustness_per_image)
    write_csv(ROOT / "PHASEC_robustness_summary.csv", summary_rows)

    comparison_rows = []
    for model_name in ("frozen_unet", "color_threshold", "ensemble", "deeplab"):
        rows = clean_rows[model_name]
        if model_name == "deeplab" and not rows:
            continue
        summary = summarize_rows(rows, BOOTSTRAP_SEED)
        comparison_rows.append({"model": model_name, **summary})
    frozen_dice = {row["stem"]: float(row["dice"]) for row in clean_rows["frozen_unet"]}
    for model_name in ("ensemble",) + (("deeplab",) if clean_rows["deeplab"] else ()):
        rows = clean_rows[model_name]
        differences = {
            row["stem"]: float(row["dice"]) - frozen_dice[row["stem"]]
            for row in rows
        }
        summary = summarize_rows(rows, BOOTSTRAP_SEED, differences)
        comparison_rows.append(
            {
                "model": f"{model_name}_minus_frozen_unet",
                "dice_delta_family_macro": summary["dice_delta_family_macro"],
                "dice_delta_family_bootstrap_95_ci": summary[
                    "dice_delta_family_bootstrap_95_ci"
                ],
            }
        )
    if not clean_rows["deeplab"]:
        preflight_result = json.loads(PREFLIGHT_FILE.read_text(encoding="utf-8"))
        comparison_rows.append(
            {
                "model": "deeplab_v3_resnet50",
                "status": "BLOCKED_BEFORE_TRAINING",
                "reason": "Registered runtime preflight projected this run above the 2-hour cap.",
                "projected_seconds": preflight_result["deeplab_projected_seconds"],
            }
        )
    write_csv(ROOT / "PHASEC_test_model_comparison.csv", comparison_rows)

    write_csv(ROOT / "PHASEC_ensemble_uncertainty_per_image.csv", uncertainty_rows)
    write_csv(ROOT / "PHASEC_ood_test_flags.csv", ood_rows)
    bin_rows = []
    ece = 0.0
    for index in range(10):
        count = int(reliability_counts[index])
        mean_probability = None if count == 0 else reliability_probability[index] / count
        observed = None if count == 0 else reliability_positive[index] / count
        if mean_probability is not None and observed is not None:
            ece += count / pixel_total * abs(mean_probability - observed)
        bin_rows.append(
            {
                "bin": index,
                "lower": index / 10,
                "upper": (index + 1) / 10,
                "pixel_count": count,
                "mean_probability": mean_probability,
                "observed_positive_fraction": observed,
            }
        )
    write_csv(ROOT / "PHASEC_reliability_bins.csv", bin_rows)
    svg_reliability(bin_rows, ROOT / "PHASEC_reliability_plot.svg")

    corr = bootstrap_correlation(uncertainty_rows)
    flag_groups: dict[str, list[float]] = {"flagged": [], "not_flagged": []}
    for row in ood_rows:
        flag_groups["flagged" if row["ood_flag"] else "not_flagged"].append(
            float(row["ensemble_dice"])
        )
    entropy_all = np.concatenate(pixel_entropy_values)
    variance_all = np.concatenate(pixel_variance_values)
    uncertainty_summary = {
        "pixel_count": pixel_total,
        "mean_pixel_entropy": pixel_entropy_sum / pixel_total,
        "pixel_entropy_quantiles_50_95": np.percentile(entropy_all, [50, 95]).tolist(),
        "mean_pixel_probability_variance": pixel_variance_sum / pixel_total,
        "pixel_variance_quantiles_50_95": np.percentile(variance_all, [50, 95]).tolist(),
        "brier_score": brier_sum / pixel_total,
        "ece_10_bins": ece,
        "reliability_plot": "PHASEC_reliability_plot.svg",
        "uncertainty_dice_family_spearman": corr,
        "image_level_spearman": _image_spearman(uncertainty_rows),
        "ood_flag_count": sum(bool(row["ood_flag"]) for row in ood_rows),
        "ood_test_images": len(ood_rows),
        "ensemble_dice_by_ood_flag": {
            key: {
                "n_images": len(values),
                "mean_dice": None if not values else float(np.mean(values)),
            }
            for key, values in flag_groups.items()
        },
        "test_families_are_verified_patients": False,
        "test_family_count": len({row["family_id"] for row in uncertainty_rows}),
    }
    write_json(ROOT / "PHASEC_uncertainty_summary.json", uncertainty_summary)
    return {
        "comparison_rows": comparison_rows,
        "robustness_rows": summary_rows,
        "uncertainty_summary": uncertainty_summary,
        "test_images": len(data),
        "test_families": len({record["family_id"] for record, _, _ in data}),
    }


def _image_spearman(rows: list[dict[str, Any]]) -> float | None:
    pairs = [(float(row["mean_entropy"]), 1.0 - float(row["ensemble_dice"])) for row in rows]
    if len(pairs) < 3:
        return None

    def rank(values: list[float]) -> np.ndarray:
        order = np.argsort(values, kind="mergesort")
        ranks = np.empty(len(order), dtype=np.float64)
        start = 0
        while start < len(order):
            end = start + 1
            while end < len(order) and values[order[end]] == values[order[start]]:
                end += 1
            ranks[order[start:end]] = (start + end - 1) / 2.0 + 1.0
            start = end
        return ranks

    x = rank([pair[0] for pair in pairs])
    y = rank([pair[1] for pair in pairs])
    if np.std(x) == 0 or np.std(y) == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def write_split_copy() -> None:
    destination = ROOT / "PHASEC_SPLIT_MANIFEST.csv"
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite {destination}")
    with SPLIT_FILE.open(newline="", encoding="utf-8-sig") as source:
        rows = list(csv.DictReader(source))
    rows = [
        row
        for row in rows
        if row["assignment"] in {"training", "validation", "official_test"}
    ]
    fields = list(rows[0])
    with destination.open("x", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_all() -> None:
    split = read_split()
    preflight_result = json.loads(PREFLIGHT_FILE.read_text(encoding="utf-8"))
    if preflight_result["unet_projected_seconds"] >= 7200:
        raise RuntimeError("Preflight projects a U-Net run beyond two hours")
    blocked_runs = ROOT / "PHASEC_BLOCKED_RUNS.csv"
    write_csv(
        blocked_runs,
        [
            {
                "run": "DeepLabV3-ResNet50",
                "seed": DEEPLAB_SEED,
                "status": "BLOCKED_BEFORE_TRAINING",
                "projected_seconds": preflight_result["deeplab_projected_seconds"],
                "limit_seconds": 7200,
                "reason": "Preflight estimate exceeds the registered 2-hour cap; no run launched.",
            }
        ],
    )
    write_split_copy()
    trained: dict[str, Any] = {}
    for seed in TRAIN_SEEDS:
        trained[f"unet_{seed}"] = train_one(split, seed, "unet")
    results = test_and_write(split, trained)
    env = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "torch": version("torch"),
        "torchvision": version("torchvision"),
        "numpy": version("numpy"),
        "pillow": version("Pillow"),
        "device": str(DEVICE),
        "gpu": torch.cuda.get_device_name(DEVICE) if DEVICE.type == "cuda" else None,
        "seeds": {
            "unet_ensemble": list(TRAIN_SEEDS),
            "deeplab": "not run; projected duration exceeded 7200 seconds",
            "bootstrap": BOOTSTRAP_SEED,
        },
        "split_counts": {"training": 105, "validation": 18, "test": 50},
        "split_families": split["families"],
        "test_pixels_decoded_after_training_frozen": True,
        "results_summary": results,
    }
    write_json(ROOT / "PHASEC_ENVIRONMENT.json", env)
    print(json.dumps(results, indent=2, allow_nan=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preflight", "run"))
    args = parser.parse_args()
    split = read_split()
    if args.command == "preflight":
        print(json.dumps(preflight(split), indent=2, allow_nan=False))
    else:
        run_all()


if __name__ == "__main__":
    main()
