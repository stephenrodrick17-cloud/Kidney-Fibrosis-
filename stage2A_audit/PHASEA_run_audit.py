"""Run the preregistered Phase A RENFAST audit without changing prior outputs."""

from __future__ import annotations

import csv
import io
import json
import math
import platform
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import PIL
import torch
from PIL import Image, ImageDraw
from torch.nn import functional as F

ROOT = Path(r"D:\patent\stage2A_audit")
sys.path.insert(0, str(ROOT))
import run_renfast_baseline as baseline  # noqa: E402

ARCHIVE = Path(r"D:\patent\m2t49zf6xr-1.zip")
RUN_DIR = ROOT / "renfast_baseline_run"
CHECKPOINT = RUN_DIR / "checkpoint_best.pt"
RUN_METADATA = RUN_DIR / "run_metadata.json"
AUDIT_SUMMARY = RUN_DIR / "audit_summary.json"
TEST_METRICS = RUN_DIR / "test_metrics.json"
PAIR_MANIFEST = RUN_DIR / "renfast_pair_manifest.csv"

PER_IMAGE_CSV = ROOT / "PHASEA_final_per_image_metrics.csv"
PER_GROUP_CSV = ROOT / "PHASEA_final_per_group_metrics.csv"
SPLIT_CSV = ROOT / "PHASEA_final_split_manifest.csv"
SUMMARY_JSON = ROOT / "PHASEA_final_metrics.json"
GALLERY_PNG = ROOT / "PHASEA_final_failure_gallery.png"
OUTPUTS = (PER_IMAGE_CSV, PER_GROUP_CSV, SPLIT_CSV, SUMMARY_JSON, GALLERY_PNG)

METRICS = ("dice", "iou", "precision", "recall")
MODELS = ("unet", "colour_threshold", "all_background")
THRESHOLD_VALUES = np.arange(-255, 256, dtype=np.int16)
GROUP_BOOTSTRAP_SEED = 20261117
WITHIN_GROUP_BOOTSTRAP_SEED = 20261118
BOOTSTRAP_RESAMPLES = 10_000
TARGET_DICE = 0.9153


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_manifest() -> list[dict[str, str]]:
    with PAIR_MANIFEST.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def load_pair(
    archive: zipfile.ZipFile, record: dict[str, str]
) -> tuple[np.ndarray, np.ndarray]:
    image_bytes = archive.read(record["image_member"])
    mask_bytes = archive.read(record["mask_member"])
    if baseline.sha256_bytes(image_bytes) != record["image_sha256"]:
        raise ValueError(f"Image hash mismatch: {record['image_member']}")
    if baseline.sha256_bytes(mask_bytes) != record["mask_sha256"]:
        raise ValueError(f"Mask hash mismatch: {record['mask_member']}")

    with Image.open(io.BytesIO(image_bytes)) as image:
        if image.mode != "RGB":
            raise ValueError(f"Expected RGB image: {record['image_member']}")
        image_array = np.asarray(image, dtype=np.uint8).copy()
    with Image.open(io.BytesIO(mask_bytes)) as mask:
        mask_array = np.asarray(mask.convert("L"), dtype=np.uint8).copy()
    if image_array.shape[:2] != mask_array.shape:
        raise ValueError(f"Image/mask dimensions differ: {record['stem']}")
    if not np.isin(np.unique(mask_array), (0, 255)).all():
        raise ValueError(f"Non-binary mask values: {record['mask_member']}")
    return image_array, mask_array == 255


def validate_split(
    manifest: list[dict[str, str]], audit: dict[str, Any], run: dict[str, Any]
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    assignments = {
        "training": [row for row in manifest if row["assignment"] == "training"],
        "validation": [row for row in manifest if row["assignment"] == "validation"],
        "official_test": [
            row for row in manifest if row["assignment"] == "official_test"
        ],
        "excluded_shared_with_test_family": [
            row
            for row in manifest
            if row["assignment"] == "excluded_shared_with_test_family"
        ],
    }
    counts = {name: len(rows) for name, rows in assignments.items()}
    expected = {
        "training": 105,
        "validation": 18,
        "official_test": 50,
        "excluded_shared_with_test_family": 127,
    }
    if counts != expected:
        raise ValueError(f"Unexpected unique-pair split counts: {counts}")
    if len([row for row in manifest if row["assignment"] == "duplicate_copy"]) != 250:
        raise ValueError("Expected 250 byte-identical duplicate training entries.")

    family_sets = {
        name: {row["family_id"] for row in rows}
        for name, rows in assignments.items()
        if name != "excluded_shared_with_test_family"
    }
    names = list(family_sets)
    for index, name in enumerate(names):
        for other in names[index + 1 :]:
            overlap = family_sets[name] & family_sets[other]
            if overlap:
                raise ValueError(f"Filename families cross splits: {name}/{other}: {overlap}")

    if len(family_sets["training"]) != 6 or len(family_sets["validation"]) != 1:
        raise ValueError(f"Unexpected training/validation families: {family_sets}")
    if len(family_sets["official_test"]) != 10:
        raise ValueError(f"Unexpected official test families: {family_sets}")
    if run["train_pairs"] != 105 or run["validation_pairs"] != 18:
        raise ValueError("Run metadata split counts differ from the pair manifest.")
    if sorted(run["train_families"]) != sorted(family_sets["training"]):
        raise ValueError("Training filename-family IDs differ from run metadata.")
    if sorted(run["validation_families"]) != sorted(family_sets["validation"]):
        raise ValueError("Validation filename-family IDs differ from run metadata.")
    if audit["official_test_pairs"] != 50:
        raise ValueError("Audit summary test count differs from the pair manifest.")
    if audit["train_pairs_excluded_for_test_family_overlap"] != 127:
        raise ValueError("Excluded-pair count differs from the audit summary.")

    split_rows = [
        row
        for name in (
            "training",
            "validation",
            "excluded_shared_with_test_family",
            "official_test",
        )
        for row in assignments[name]
    ]
    return (
        assignments["training"],
        assignments["validation"],
        assignments["official_test"],
        split_rows,
    )


def binary_metrics(prediction: np.ndarray, target: np.ndarray) -> dict[str, float | None]:
    prediction = prediction.astype(bool)
    target = target.astype(bool)
    tp = int(np.logical_and(prediction, target).sum())
    fp = int(np.logical_and(prediction, ~target).sum())
    fn = int(np.logical_and(~prediction, target).sum())
    dice_denominator = 2 * tp + fp + fn
    iou_denominator = tp + fp + fn
    precision_denominator = tp + fp
    recall_denominator = tp + fn
    return {
        "dice": 1.0 if dice_denominator == 0 else 2 * tp / dice_denominator,
        "iou": 1.0 if iou_denominator == 0 else tp / iou_denominator,
        "precision": (
            None if precision_denominator == 0 else tp / precision_denominator
        ),
        "recall": None if recall_denominator == 0 else tp / recall_denominator,
    }


def tune_colour_threshold(
    archive: zipfile.ZipFile, training: list[dict[str, str]]
) -> tuple[int, float, dict[str, float]]:
    group_score_sums: dict[str, np.ndarray] = {}
    group_image_counts: dict[str, int] = defaultdict(int)
    for record in training:
        image, target = load_pair(archive, record)
        score_index = (
            image[:, :, 2].astype(np.int16)
            - image[:, :, 0].astype(np.int16)
            + 255
        )
        positive_histogram = np.bincount(
            score_index[target].ravel(), minlength=len(THRESHOLD_VALUES)
        )
        negative_histogram = np.bincount(
            score_index[~target].ravel(), minlength=len(THRESHOLD_VALUES)
        )
        tp = np.cumsum(positive_histogram[::-1], dtype=np.int64)[::-1]
        fp = np.cumsum(negative_histogram[::-1], dtype=np.int64)[::-1]
        positives = int(target.sum())
        fn = positives - tp
        dice = np.divide(
            2.0 * tp,
            2.0 * tp + fp + fn,
            out=np.ones_like(tp, dtype=np.float64),
            where=(2 * tp + fp + fn) != 0,
        )
        family = record["family_id"]
        if family not in group_score_sums:
            group_score_sums[family] = np.zeros_like(dice)
        group_score_sums[family] += dice
        group_image_counts[family] += 1

    family_scores = {
        family: group_score_sums[family] / group_image_counts[family]
        for family in group_score_sums
    }
    equal_family_scores = np.mean(np.stack(list(family_scores.values())), axis=0)
    maximum = float(equal_family_scores.max())
    best_indices = np.flatnonzero(
        np.isclose(equal_family_scores, maximum, rtol=0.0, atol=1e-15)
    )
    selected_index = int(best_indices[-1])
    selected_threshold = int(THRESHOLD_VALUES[selected_index])
    selected_family_scores = {
        family: float(scores[selected_index]) for family, scores in family_scores.items()
    }
    return (
        selected_threshold,
        float(equal_family_scores[selected_index]),
        selected_family_scores,
    )


def run_unet(
    image: np.ndarray, model: torch.nn.Module, device: torch.device
) -> np.ndarray:
    height, width = image.shape[:2]
    pad_height = (-height) % 16
    pad_width = (-width) % 16
    tensor = (
        torch.from_numpy(image)
        .permute(2, 0, 1)
        .float()
        .div_(255.0)
    )
    tensor = F.pad(tensor, (0, pad_width, 0, pad_height))[None].to(device)
    probability = torch.sigmoid(model(tensor))[0, 0, :height, :width]
    return (probability >= baseline.THRESHOLD).cpu().numpy()


def macro(values: list[float | None]) -> float | None:
    present = [float(value) for value in values if value is not None]
    return None if not present else float(np.mean(present))


def per_family(
    records: list[dict[str, Any]], key: str
) -> dict[str, list[float | None]]:
    grouped: dict[str, list[float | None]] = defaultdict(list)
    for record in records:
        grouped[record["family_id"]].append(record[key])
    return dict(grouped)


def percentile_ci(values: np.ndarray) -> list[float] | None:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return None
    return [
        float(np.percentile(finite, 2.5)),
        float(np.percentile(finite, 97.5)),
    ]


def family_bootstrap_ci(
    records: list[dict[str, Any]], value_fn: Any, seed: int
) -> list[float] | None:
    group_values = value_fn(records)
    groups = sorted(group_values)
    if len(groups) < 2:
        return None
    rng = np.random.default_rng(seed)
    estimates = np.empty(BOOTSTRAP_RESAMPLES, dtype=np.float64)
    for index in range(BOOTSTRAP_RESAMPLES):
        sampled = rng.choice(groups, size=len(groups), replace=True)
        values = [group_values[str(group)] for group in sampled]
        estimates[index] = float(np.mean(values))
    return percentile_ci(estimates)


def stratified_image_bootstrap_ci(
    records: list[dict[str, Any]], value_fn: Any, seed: int
) -> list[float] | None:
    grouped = value_fn(records)
    groups = sorted(grouped)
    if len(groups) < 2:
        return None
    rng = np.random.default_rng(seed)
    estimates = np.empty(BOOTSTRAP_RESAMPLES, dtype=np.float64)
    for index in range(BOOTSTRAP_RESAMPLES):
        group_means: list[float] = []
        for group in groups:
            array = np.asarray(grouped[group], dtype=np.float64)
            array = array[np.isfinite(array)]
            if array.size:
                sample_indices = rng.integers(0, array.size, size=array.size)
                group_means.append(float(np.mean(array[sample_indices])))
        estimates[index] = float(np.mean(group_means)) if group_means else np.nan
    return percentile_ci(estimates)


def model_metric_groups(
    records: list[dict[str, Any]], model_name: str, metric: str
) -> dict[str, list[float | None]]:
    key = f"{model_name}_{metric}"
    return per_family(records, key)


def group_values(
    records: list[dict[str, Any]], model_name: str, metric: str
) -> dict[str, float]:
    grouped = model_metric_groups(records, model_name, metric)
    result: dict[str, float] = {}
    for family, values in grouped.items():
        value = macro(values)
        if value is not None:
            result[family] = value
    return result


def paired_difference_groups(
    records: list[dict[str, Any]], metric: str
) -> dict[str, list[float]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for record in records:
        unet = record[f"unet_{metric}"]
        colour = record[f"colour_threshold_{metric}"]
        if unet is not None and colour is not None:
            grouped[record["family_id"]].append(float(unet) - float(colour))
    return dict(grouped)


def make_gallery(
    gallery_rows: list[dict[str, Any]], image_data: dict[str, dict[str, Any]]
) -> None:
    thumbnail = 256
    header = 30
    panel_width = thumbnail + 12
    row_height = thumbnail + header + 12
    canvas = Image.new("RGB", (panel_width * 4, row_height * len(gallery_rows)), "white")
    draw = ImageDraw.Draw(canvas)
    panel_titles = ("Input", "Manual mask", "U-Net: TP/FN/FP", "Colour: TP/FN/FP")

    for row_index, record in enumerate(gallery_rows):
        data = image_data[record["stem"]]
        y = row_index * row_height
        draw.text((4, y + 3), f"{record['stem']} (Dice {record['unet_dice']:.4f})", fill="black")
        for panel_index, title in enumerate(panel_titles):
            x = panel_index * panel_width + 4
            draw.text((x, y + header), title, fill="black")
            panel_y = y + header + 18
            if panel_index == 0:
                panel = Image.fromarray(data["image"])
            elif panel_index == 1:
                grey = np.where(data["target"], 255, 0).astype(np.uint8)
                panel = Image.fromarray(grey).convert("RGB")
            else:
                prediction = (
                    data["unet_prediction"]
                    if panel_index == 2
                    else data["colour_prediction"]
                )
                target = data["target"]
                tp = target & prediction
                fn = target & ~prediction
                fp = ~target & prediction
                overlay = data["image"].astype(np.float32).copy()
                overlay[tp] = 0.55 * overlay[tp] + 0.45 * np.array([255, 255, 0])
                overlay[fn] = 0.55 * overlay[fn] + 0.45 * np.array([0, 0, 255])
                overlay[fp] = 0.55 * overlay[fp] + 0.45 * np.array([255, 0, 0])
                panel = Image.fromarray(np.clip(overlay, 0, 255).astype(np.uint8))
            panel = panel.resize((thumbnail, thumbnail), Image.Resampling.LANCZOS)
            canvas.paste(panel, (x, panel_y))
    canvas.save(GALLERY_PNG)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write an empty CSV: {path.name}")
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    existing = [str(path) for path in OUTPUTS if path.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite Phase A outputs: {existing}")
    required = (ARCHIVE, CHECKPOINT, RUN_METADATA, AUDIT_SUMMARY, TEST_METRICS, PAIR_MANIFEST)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Required frozen evaluation files are missing: {missing}")

    archive_hash = baseline.sha256_file(ARCHIVE)
    checkpoint_hash = baseline.sha256_file(CHECKPOINT)
    run = read_json(RUN_METADATA)
    audit = read_json(AUDIT_SUMMARY)
    saved_test = read_json(TEST_METRICS)
    if run.get("checkpoint_sha256") != checkpoint_hash:
        raise ValueError("Checkpoint hash differs from frozen run metadata.")
    if saved_test.get("checkpoint_sha256") != checkpoint_hash:
        raise ValueError("Checkpoint hash differs from saved test metrics.")
    if audit.get("archive_sha256") != archive_hash:
        raise ValueError("RENFAST archive hash differs from the audit record.")
    if saved_test.get("status") != "completed":
        raise ValueError("Saved test evaluation is not complete.")

    manifest = read_manifest()
    training, validation, test_records, split_rows = validate_split(
        manifest, audit, run
    )
    with zipfile.ZipFile(ARCHIVE) as archive:
        selected_threshold, train_macro_dice, train_group_scores = (
            tune_colour_threshold(archive, training)
        )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(CHECKPOINT, map_location=device, weights_only=True)
    if checkpoint.get("threshold") != baseline.THRESHOLD:
        raise ValueError("Checkpoint threshold differs from frozen 0.5 threshold.")
    model = baseline.UNet().to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    output_rows: list[dict[str, Any]] = []
    image_data: dict[str, dict[str, Any]] = {}
    with zipfile.ZipFile(ARCHIVE) as archive, torch.no_grad():
        for record in sorted(test_records, key=lambda row: row["stem"]):
            image, target = load_pair(archive, record)
            unet_prediction = run_unet(image, model, device)
            colour_prediction = (
                image[:, :, 2].astype(np.int16)
                - image[:, :, 0].astype(np.int16)
                >= selected_threshold
            )
            all_background = np.zeros(target.shape, dtype=bool)
            predictions = {
                "unet": unet_prediction,
                "colour_threshold": colour_prediction,
                "all_background": all_background,
            }
            row: dict[str, Any] = {
                "stem": record["stem"],
                "family_id": record["family_id"],
                "image_member": record["image_member"],
                "mask_member": record["mask_member"],
            }
            for model_name, prediction in predictions.items():
                values = binary_metrics(prediction, target)
                for metric in METRICS:
                    row[f"{model_name}_{metric}"] = values[metric]

            saved_by_pair = {
                (item["image_member"], item["mask_member"]): item
                for item in saved_test["per_image_metrics"]
            }
            key = (record["image_member"], record["mask_member"])
            if key not in saved_by_pair:
                raise ValueError(f"Test pair missing from saved results: {key}")
            old = saved_by_pair[key]
            for current_key, saved_key in (
                ("unet_dice", "dice"),
                ("unet_iou", "iou"),
                ("unet_recall", "sensitivity"),
            ):
                if not math.isclose(
                    float(row[current_key]),
                    float(old[saved_key]),
                    rel_tol=0.0,
                    abs_tol=1e-12,
                ):
                    raise ValueError(
                        f"Recomputed {current_key} differs from saved value "
                        f"for {record['stem']}: {row[current_key]} vs {old[saved_key]}"
                    )
            output_rows.append(row)
            image_data[record["stem"]] = {
                "image": image,
                "target": target,
                "unet_prediction": unet_prediction,
                "colour_prediction": colour_prediction,
            }

    if len(output_rows) != 50:
        raise ValueError(f"Expected 50 test images, found {len(output_rows)}.")
    if len(saved_test["per_image_metrics"]) != 50:
        raise ValueError("Saved per-image test result count is not 50.")
    saved_test_pairs = {
        (item["image_member"], item["mask_member"])
        for item in saved_test["per_image_metrics"]
    }
    current_test_pairs = {
        (row["image_member"], row["mask_member"]) for row in output_rows
    }
    if saved_test_pairs != current_test_pairs:
        raise ValueError("Current and saved test-pair manifests differ.")

    group_rows: list[dict[str, Any]] = []
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in output_rows:
        groups[row["family_id"]].append(row)
    for family in sorted(groups):
        group_row: dict[str, Any] = {
            "family_id": family,
            "n_images": len(groups[family]),
        }
        for model_name in MODELS:
            for metric in METRICS:
                group_row[f"{model_name}_{metric}"] = macro(
                    [row[f"{model_name}_{metric}"] for row in groups[family]]
                )
        group_row["unet_minus_colour_threshold_dice"] = (
            group_row["unet_dice"] - group_row["colour_threshold_dice"]
        )
        group_rows.append(group_row)
    if len(group_rows) != 10:
        raise ValueError(f"Expected 10 test filename families, found {len(group_rows)}.")

    metric_estimates: dict[str, Any] = {}
    for model_name in MODELS:
        metric_estimates[model_name] = {}
        for metric in METRICS:
            key = f"{model_name}_{metric}"
            group_fn = lambda records, k=key: {
                family: value
                for family, values in per_family(records, k).items()
                if (value := macro(values)) is not None
            }
            image_ci = stratified_image_bootstrap_ci(
                output_rows,
                lambda records, k=key: per_family(records, k),
                WITHIN_GROUP_BOOTSTRAP_SEED,
            )
            family_ci = family_bootstrap_ci(
                output_rows, group_fn, GROUP_BOOTSTRAP_SEED
            )
            metric_estimates[model_name][metric] = {
                "image_macro_mean": macro([row[key] for row in output_rows]),
                "equal_family_macro_mean": macro(
                    [row[f"{model_name}_{metric}"] for row in group_rows]
                ),
                "family_bootstrap_95_ci": family_ci,
                "within_family_image_bootstrap_95_ci": image_ci,
            }

    paired_dice = paired_difference_groups(output_rows, "dice")
    paired_group_fn = {
        family: macro(values) for family, values in paired_dice.items()
    }
    paired_group_ci = family_bootstrap_ci(
        output_rows,
        lambda _records: {
            family: float(value)
            for family, value in paired_group_fn.items()
            if value is not None
        },
        GROUP_BOOTSTRAP_SEED,
    )
    paired_image_ci = stratified_image_bootstrap_ci(
        output_rows,
        lambda _records: paired_dice,
        WITHIN_GROUP_BOOTSTRAP_SEED,
    )
    unet_dice = float(metric_estimates["unet"]["dice"]["equal_family_macro_mean"])
    colour_dice = float(
        metric_estimates["colour_threshold"]["dice"]["equal_family_macro_mean"]
    )
    mean_difference = unet_dice - colour_dice
    primary_ci_lower = None if paired_group_ci is None else paired_group_ci[0]
    passed = primary_ci_lower is not None and primary_ci_lower > 0.0

    group_test_values = {
        model_name: {
            metric: [
                row[f"{model_name}_{metric}"] for row in group_rows
            ]
            for metric in METRICS
        }
        for model_name in MODELS
    }
    image_distributions = {
        model_name: {
            metric: {
                "minimum": (
                    None
                    if not [
                        row[f"{model_name}_{metric}"]
                        for row in output_rows
                        if row[f"{model_name}_{metric}"] is not None
                    ]
                    else float(
                        np.min(
                            [
                                row[f"{model_name}_{metric}"]
                                for row in output_rows
                                if row[f"{model_name}_{metric}"] is not None
                            ]
                        )
                    )
                ),
                "median": (
                    None
                    if not [
                        row[f"{model_name}_{metric}"]
                        for row in output_rows
                        if row[f"{model_name}_{metric}"] is not None
                    ]
                    else float(
                        np.median(
                            [
                                row[f"{model_name}_{metric}"]
                                for row in output_rows
                                if row[f"{model_name}_{metric}"] is not None
                            ]
                        )
                    )
                ),
                "maximum": (
                    None
                    if not [
                        row[f"{model_name}_{metric}"]
                        for row in output_rows
                        if row[f"{model_name}_{metric}"] is not None
                    ]
                    else float(
                        np.max(
                            [
                                row[f"{model_name}_{metric}"]
                                for row in output_rows
                                if row[f"{model_name}_{metric}"] is not None
                            ]
                        )
                    )
                ),
            }
            for metric in METRICS
        }
        for model_name in MODELS
    }

    saved_dice = float(saved_test["macro_per_image_metrics"]["dice"])
    recomputed_dice = macro([row["unet_dice"] for row in output_rows])
    if recomputed_dice is None or not math.isclose(
        recomputed_dice, saved_dice, rel_tol=0.0, abs_tol=1e-12
    ):
        raise ValueError(
            f"Full-precision macro Dice differs from saved result: "
            f"{recomputed_dice} vs {saved_dice}"
        )
    if round(recomputed_dice, 4) != TARGET_DICE:
        raise ValueError(f"Rounded Dice does not reproduce {TARGET_DICE}.")

    low_dice = sorted(output_rows, key=lambda row: (row["unet_dice"], row["stem"]))[:12]
    make_gallery(low_dice, image_data)
    write_csv(PER_IMAGE_CSV, output_rows)
    write_csv(PER_GROUP_CSV, group_rows)
    write_csv(
        SPLIT_CSV,
        [
            {
                "source_split": row["source_split"],
                "stem": row["stem"],
                "family_id": row["family_id"],
                "image_member": row["image_member"],
                "mask_member": row["mask_member"],
                "assignment": row["assignment"],
                "image_sha256": row["image_sha256"],
                "mask_sha256": row["mask_sha256"],
            }
            for row in split_rows
        ],
    )

    summary = {
        "status": "completed",
        "scope": "Phase A only; no new model training; Phase B not started",
        "timestamp": "2026-11-16",
        "data_grouping_unit": (
            "Filename families, not verified patient or slide IDs."
        ),
        "split_counts": {
            "training_pairs": len(training),
            "training_families": sorted({row["family_id"] for row in training}),
            "validation_pairs": len(validation),
            "validation_families": sorted(
                {row["family_id"] for row in validation}
            ),
            "test_pairs": len(test_records),
            "test_families": sorted({row["family_id"] for row in test_records}),
            "excluded_unique_training_pairs": 127,
            "duplicate_training_entries_not_used": 250,
            "families_overlap_between_active_splits": False,
        },
        "hashes": {
            "archive_sha256": archive_hash,
            "checkpoint_sha256": checkpoint_hash,
        },
        "reproduced_unet_dice": {
            "saved_full_precision": saved_dice,
            "recomputed_full_precision": recomputed_dice,
            "difference_from_saved_full_precision": recomputed_dice - saved_dice,
            "difference_from_reported_rounded_0_9153": recomputed_dice - TARGET_DICE,
            "rounded_to_four_decimals": round(recomputed_dice, 4),
            "per_image_dice_iou_recall_match_saved_within_1e_12": True,
        },
        "colour_threshold": {
            "rule": "Predict fibrosis where uint8 B minus R is greater than or equal to t.",
            "selected_t": selected_threshold,
            "candidate_values": {"minimum": -255, "maximum": 255, "step": 1},
            "selection_metric": "equal-family-weighted mean per-image Dice on 105 training pairs",
            "training_equal_family_mean_dice": train_macro_dice,
            "training_family_mean_dice_at_selected_t": train_group_scores,
            "test_data_used_for_tuning": False,
        },
        "test_estimates": metric_estimates,
        "test_group_level_metrics": group_test_values,
        "test_image_distributions": image_distributions,
        "paired_unet_minus_colour_threshold_dice": {
            "equal_family_macro_difference": mean_difference,
            "primary_test_family_bootstrap_95_ci": paired_group_ci,
            "secondary_within_family_image_bootstrap_95_ci": paired_image_ci,
            "primary_lower_bound_above_zero": passed,
        },
        "success_rule": {
            "criterion": "U-Net equal-family macro Dice exceeds the colour-threshold baseline with paired test-family bootstrap 95% CI lower bound > 0.",
            "outcome": "PASS" if passed else "FAIL",
        },
        "bootstrap": {
            "primary": "10,000 paired resamples of the 10 test filename families, equal weight per family.",
            "primary_seed": GROUP_BOOTSTRAP_SEED,
            "secondary": "10,000 stratified resamples of images within each of the 10 fixed test filename families, then equal weight per family.",
            "secondary_seed": WITHIN_GROUP_BOOTSTRAP_SEED,
            "test_family_count_limits_precision": True,
        },
        "metric_conventions": {
            "positive_class": "Manual fibrosis mask.",
            "recall": "TP / (TP + FN), same quantity as sensitivity.",
            "precision": "TP / (TP + FP); NA if no pixels are predicted positive.",
            "dice_iou": "1 only if both prediction and target are empty; otherwise standard binary formulas.",
        },
        "failure_gallery": {
            "lowest_unet_dice_test_images": [
                {
                    "stem": row["stem"],
                    "family_id": row["family_id"],
                    "unet_dice": row["unet_dice"],
                }
                for row in low_dice
            ],
            "file": GALLERY_PNG.name,
        },
        "software": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pillow": PIL.__version__,
            "torch": torch.__version__,
            "device": str(device),
            "cuda_available": torch.cuda.is_available(),
        },
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
