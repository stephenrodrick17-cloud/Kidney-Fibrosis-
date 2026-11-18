"""Analyze returned blinded masks; --self-test uses synthetic arrays only."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

ROOT = Path(r"D:\patent\stage2A_audit")
KEY_PATH = ROOT / "PHASEB2_KEY_DO_NOT_SHARE.csv"
PREDICTION_DIR = ROOT / "PHASEB_region_images"
BOOTSTRAP_SEED = 20261120
BOOTSTRAP_REPLICATES = 10_000
MASK_SIZE = (512, 512)
METRIC_NAMES = ("dice", "iou", "precision", "recall")


def binary_metrics(prediction: np.ndarray, reference: np.ndarray) -> dict[str, float | None]:
    prediction = prediction.astype(bool)
    reference = reference.astype(bool)
    true_positive = int(np.logical_and(prediction, reference).sum())
    false_positive = int(np.logical_and(prediction, ~reference).sum())
    false_negative = int(np.logical_and(~prediction, reference).sum())
    dice_denominator = 2 * true_positive + false_positive + false_negative
    iou_denominator = true_positive + false_positive + false_negative
    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative
    return {
        "dice": (
            1.0
            if dice_denominator == 0
            else 2 * true_positive / dice_denominator
        ),
        "iou": (
            1.0 if iou_denominator == 0 else true_positive / iou_denominator
        ),
        "precision": (
            None
            if precision_denominator == 0
            else true_positive / precision_denominator
        ),
        "recall": (
            None if recall_denominator == 0 else true_positive / recall_denominator
        ),
    }


def mean_present(values: list[float | None]) -> float | None:
    present = [float(value) for value in values if value is not None]
    return None if not present else float(np.mean(present))


def participant_bootstrap_ci(
    participant_differences: list[float],
    seed: int = BOOTSTRAP_SEED,
    replicates: int = BOOTSTRAP_REPLICATES,
) -> list[float] | None:
    values = np.asarray(participant_differences, dtype=np.float64)
    if values.size < 2:
        return None
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, values.size, size=(replicates, values.size))
    estimates = values[indices].mean(axis=1)
    return [
        float(np.quantile(estimates, 0.025)),
        float(np.quantile(estimates, 0.975)),
    ]


def read_binary_png(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        if image.size != MASK_SIZE:
            raise ValueError(f"Expected 512x512 mask: {path}")
        if image.mode == "L":
            pixels = np.asarray(image, dtype=np.uint8)
        elif image.mode == "RGB":
            rgb = np.asarray(image, dtype=np.uint8)
            if not (
                np.array_equal(rgb[:, :, 0], rgb[:, :, 1])
                and np.array_equal(rgb[:, :, 0], rgb[:, :, 2])
            ):
                raise ValueError(f"RGB mask channels are not identical: {path}")
            pixels = rgb[:, :, 0]
        else:
            raise ValueError(f"Mask must be L or grayscale RGB: {path}")
    if not np.isin(np.unique(pixels), (0, 255)).all():
        raise ValueError(f"Mask must contain only 0 and 255: {path}")
    return pixels == 255


def read_key(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))
    required = {"opaque_id", "region_id", "participant_id"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("The private key is empty or missing required columns.")
    if len(rows) != 20:
        raise ValueError(f"Expected 20 key rows, found {len(rows)}.")
    if len({row["opaque_id"] for row in rows}) != 20:
        raise ValueError("Opaque IDs in the private key are not unique.")
    if len({row["region_id"] for row in rows}) != 20:
        raise ValueError("Region IDs in the private key are not unique.")
    return {row["opaque_id"]: row for row in rows}


def read_status(path: Path, key: dict[str, dict[str, str]]) -> tuple[str, dict[str, dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))
    required = {
        "opaque_id",
        "mask_filename",
        "annotator_id",
        "gradable_yes_no",
        "comments",
    }
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"Invalid annotation status form: {path}")
    if {row["opaque_id"] for row in rows} != set(key):
        raise ValueError(f"Status form does not contain every opaque ID: {path}")
    if len(rows) != len(key):
        raise ValueError(f"Status form has duplicate or extra rows: {path}")
    annotator_ids = {row["annotator_id"].strip() for row in rows}
    if len(annotator_ids) != 1 or not next(iter(annotator_ids)):
        raise ValueError(f"Status form must have one nonblank annotator ID: {path}")
    annotator_id = next(iter(annotator_ids))
    if path.parent.name != annotator_id:
        raise ValueError(
            f"Annotator folder {path.parent.name!r} must match ID {annotator_id!r}."
        )
    return annotator_id, {row["opaque_id"]: row for row in rows}


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(
            {
                key: "NA" if value is None else value
                for key, value in row.items()
            }
            for row in rows
        )


def analyze(
    annotations_dir: Path, output_dir: Path, key_path: Path = KEY_PATH
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite analysis outputs: {output_dir}")
    if not annotations_dir.is_dir():
        raise FileNotFoundError(f"Returned annotations folder not found: {annotations_dir}")
    key = read_key(key_path)
    annotator_dirs = sorted(path for path in annotations_dir.iterdir() if path.is_dir())
    if not annotator_dirs:
        raise ValueError("No annotator folders were found.")

    annotations: dict[str, dict[str, np.ndarray]] = {}
    metadata_by_opaque: dict[str, dict[str, str]] = {}
    quality_rows: list[dict[str, Any]] = []
    annotator_ids: list[str] = []
    for annotator_dir in annotator_dirs:
        status_path = annotator_dir / "PHASEB2_ANNOTATION_STATUS.csv"
        if not status_path.is_file():
            raise FileNotFoundError(f"Annotation status form is missing: {status_path}")
        annotator_id, status = read_status(status_path, key)
        if annotator_id in annotator_ids:
            raise ValueError(f"Duplicate annotator ID: {annotator_id}")
        annotator_ids.append(annotator_id)
        annotations[annotator_id] = {}
        for opaque_id, key_row in key.items():
            status_row = status[opaque_id]
            expected_filename = f"PHASEB2_{opaque_id}.png"
            mask_filename = status_row["mask_filename"].strip()
            gradable = status_row["gradable_yes_no"].strip().lower()
            if mask_filename != expected_filename:
                quality_rows.append(
                    {
                        "annotator_id": annotator_id,
                        "opaque_id": opaque_id,
                        "region_id": key_row["region_id"],
                        "status": "invalid_mask_filename",
                        "details": mask_filename,
                    }
                )
                continue
            if gradable not in ("yes", "no"):
                quality_rows.append(
                    {
                        "annotator_id": annotator_id,
                        "opaque_id": opaque_id,
                        "region_id": key_row["region_id"],
                        "status": "invalid_gradable_value",
                        "details": gradable,
                    }
                )
                continue
            mask_path = annotator_dir / expected_filename
            if gradable == "no":
                quality_rows.append(
                    {
                        "annotator_id": annotator_id,
                        "opaque_id": opaque_id,
                        "region_id": key_row["region_id"],
                        "status": "ungradable",
                        "details": status_row["comments"],
                    }
                )
                continue
            if not mask_path.is_file():
                quality_rows.append(
                    {
                        "annotator_id": annotator_id,
                        "opaque_id": opaque_id,
                        "region_id": key_row["region_id"],
                        "status": "missing_mask",
                        "details": "",
                    }
                )
                continue
            try:
                mask = read_binary_png(mask_path)
            except (OSError, ValueError) as error:
                quality_rows.append(
                    {
                        "annotator_id": annotator_id,
                        "opaque_id": opaque_id,
                        "region_id": key_row["region_id"],
                        "status": "invalid_mask",
                        "details": str(error),
                    }
                )
                continue
            annotations[annotator_id][opaque_id] = mask
            metadata_by_opaque[opaque_id] = key_row
            quality_rows.append(
                {
                    "annotator_id": annotator_id,
                    "opaque_id": opaque_id,
                    "region_id": key_row["region_id"],
                    "status": "analyzable",
                    "details": "",
                }
            )

    region_metric_rows: list[dict[str, Any]] = []
    participant_metric_rows: list[dict[str, Any]] = []
    annotator_summary: list[dict[str, Any]] = []
    region_metrics: dict[str, dict[str, dict[str, dict[str, float | None]]]] = {}
    participant_differences: dict[str, dict[str, float]] = {}

    for annotator_id in sorted(annotations):
        region_metrics[annotator_id] = {}
        participant_region_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for opaque_id, annotation in annotations[annotator_id].items():
            key_row = metadata_by_opaque[opaque_id]
            region_id = key_row["region_id"]
            prediction_paths = {
                "unet": PREDICTION_DIR / f"{region_id}_unet_mask.png",
                "colour_threshold": PREDICTION_DIR / f"{region_id}_colour_mask.png",
            }
            region_metrics[annotator_id][opaque_id] = {}
            for model_name, prediction_path in prediction_paths.items():
                prediction = read_binary_png(prediction_path)
                values = binary_metrics(prediction, annotation)
                region_metrics[annotator_id][opaque_id][model_name] = values
                region_metric_rows.append(
                    {
                        "annotator_id": annotator_id,
                        "opaque_id": opaque_id,
                        "region_id": region_id,
                        "participant_id": key_row["participant_id"],
                        "model": model_name,
                        **values,
                        "annotation_positive_pixels": int(annotation.sum()),
                        "prediction_positive_pixels": int(prediction.sum()),
                    }
                )
            participant_region_records[key_row["participant_id"]].append(
                {
                    "opaque_id": opaque_id,
                    "unet": region_metrics[annotator_id][opaque_id]["unet"],
                    "colour_threshold": region_metrics[annotator_id][opaque_id][
                        "colour_threshold"
                    ],
                }
            )

        participant_differences[annotator_id] = {}
        for participant_id, records in sorted(participant_region_records.items()):
            model_means: dict[str, dict[str, float | None]] = {}
            for model_name in ("unet", "colour_threshold"):
                model_means[model_name] = {
                    metric: mean_present(
                        [record[model_name][metric] for record in records]
                    )
                    for metric in METRIC_NAMES
                }
            dice_differences = [
                float(record["unet"]["dice"])
                - float(record["colour_threshold"]["dice"])
                for record in records
            ]
            participant_difference = float(np.mean(dice_differences))
            participant_differences[annotator_id][participant_id] = (
                participant_difference
            )
            participant_metric_rows.append(
                {
                    "annotator_id": annotator_id,
                    "participant_id": participant_id,
                    "n_regions": len(records),
                    **{f"unet_{key}": value for key, value in model_means["unet"].items()},
                    **{
                        f"colour_threshold_{key}": value
                        for key, value in model_means["colour_threshold"].items()
                    },
                    "mean_region_dice_difference_unet_minus_colour": participant_difference,
                }
            )
        participant_values = [
            value
            for _, value in sorted(participant_differences[annotator_id].items())
        ]
        ci = participant_bootstrap_ci(participant_values)
        mean_difference = (
            float(np.mean(participant_values)) if participant_values else None
        )
        if len(participant_values) < 2:
            success_status = "BLOCKED"
        elif ci is not None and ci[0] > 0.0:
            success_status = "PASS"
        else:
            success_status = "NOT_MET"
        annotator_summary.append(
            {
                "annotator_id": annotator_id,
                "analyzable_regions": len(annotations[annotator_id]),
                "analyzable_participants": len(participant_values),
                "mean_participant_dice_difference_unet_minus_colour": mean_difference,
                "participant_bootstrap_95_ci": ci,
                "registered_success_rule": success_status,
            }
        )

    interannotator_rows: list[dict[str, Any]] = []
    interparticipant: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for annotator_a, annotator_b in itertools.combinations(sorted(annotations), 2):
        common_ids = sorted(
            set(annotations[annotator_a]) & set(annotations[annotator_b])
        )
        for opaque_id in common_ids:
            key_row = metadata_by_opaque[opaque_id]
            values = binary_metrics(
                annotations[annotator_a][opaque_id],
                annotations[annotator_b][opaque_id],
            )
            row = {
                "annotator_a_prediction": annotator_a,
                "annotator_b_reference": annotator_b,
                "opaque_id": opaque_id,
                "region_id": key_row["region_id"],
                "participant_id": key_row["participant_id"],
                **values,
            }
            interannotator_rows.append({**row, "aggregation_level": "region"})
            interparticipant[(annotator_a, annotator_b)].append(row)
    for pair, records in sorted(interparticipant.items()):
        by_participant: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            by_participant[record["participant_id"]].append(record)
        for participant_id, participant_records in sorted(by_participant.items()):
            interannotator_rows.append(
                {
                    "annotator_a_prediction": pair[0],
                    "annotator_b_reference": pair[1],
                    "opaque_id": "",
                    "region_id": "",
                    "participant_id": participant_id,
                    **{
                        metric: mean_present(
                            [record[metric] for record in participant_records]
                        )
                        for metric in METRIC_NAMES
                    },
                    "aggregation_level": "participant",
                }
            )

    output_dir.mkdir(parents=True)
    write_csv(
        output_dir / "PHASEB2_REGION_METRICS.csv",
        region_metric_rows,
        [
            "annotator_id",
            "opaque_id",
            "region_id",
            "participant_id",
            "model",
            *METRIC_NAMES,
            "annotation_positive_pixels",
            "prediction_positive_pixels",
        ],
    )
    write_csv(
        output_dir / "PHASEB2_PARTICIPANT_METRICS.csv",
        participant_metric_rows,
        [
            "annotator_id",
            "participant_id",
            "n_regions",
            "unet_dice",
            "unet_iou",
            "unet_precision",
            "unet_recall",
            "colour_threshold_dice",
            "colour_threshold_iou",
            "colour_threshold_precision",
            "colour_threshold_recall",
            "mean_region_dice_difference_unet_minus_colour",
        ],
    )
    write_csv(
        output_dir / "PHASEB2_INTERANNOTATOR_METRICS.csv",
        interannotator_rows,
        [
            "aggregation_level",
            "annotator_a_prediction",
            "annotator_b_reference",
            "opaque_id",
            "region_id",
            "participant_id",
            *METRIC_NAMES,
        ],
    )
    write_csv(
        output_dir / "PHASEB2_DATA_QUALITY.csv",
        quality_rows,
        ["annotator_id", "opaque_id", "region_id", "status", "details"],
    )
    summary = {
        "status": "completed" if annotator_summary else "BLOCKED",
        "annotators": annotator_summary,
        "interannotator_pairs": len(list(itertools.combinations(annotator_ids, 2))),
        "interannotator_agreement_available": bool(interannotator_rows),
        "missing_or_ungradable_masks": sum(
            row["status"] != "analyzable" for row in quality_rows
        ),
        "resampling_unit": "participant",
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "not_a_clinical_performance_claim": True,
    }
    (output_dir / "PHASEB2_ANALYSIS_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def self_test() -> dict[str, Any]:
    truth = np.zeros((8, 8), dtype=bool)
    truth[1:4, 1:4] = True
    exact = truth.copy()
    partial = np.zeros_like(truth)
    partial[1:3, 1:3] = True
    partial[6, 6] = True
    exact_metrics = binary_metrics(exact, truth)
    partial_metrics = binary_metrics(partial, truth)
    if exact_metrics != {
        "dice": 1.0,
        "iou": 1.0,
        "precision": 1.0,
        "recall": 1.0,
    }:
        raise AssertionError(f"Perfect-overlap synthetic case failed: {exact_metrics}")
    expected_partial = {
        "dice": 8 / 14,
        "iou": 4 / 10,
        "precision": 4 / 5,
        "recall": 4 / 9,
    }
    for metric, expected in expected_partial.items():
        actual = partial_metrics[metric]
        if actual is None or not math.isclose(actual, expected, abs_tol=1e-12):
            raise AssertionError(f"Synthetic {metric} mismatch: {actual} != {expected}")
    ci = participant_bootstrap_ci([0.25, 0.75], seed=7, replicates=1000)
    if ci is None or not (0.25 <= ci[0] <= ci[1] <= 0.75):
        raise AssertionError(f"Synthetic participant bootstrap failed: {ci}")
    result = {
        "status": "synthetic_test_passed",
        "real_annotations_read": False,
        "perfect_overlap_metrics": exact_metrics,
        "partial_overlap_metrics": partial_metrics,
        "two_participant_bootstrap_ci": ci,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--annotations-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--key-path", type=Path, default=KEY_PATH)
    args = parser.parse_args()
    if args.self_test:
        if args.annotations_dir or args.output_dir:
            parser.error("--self-test cannot be combined with real-data paths.")
        self_test()
        return
    if args.annotations_dir is None or args.output_dir is None:
        parser.error(
            "Real analysis requires --annotations-dir and --output-dir; "
            "use --self-test for synthetic-only validation."
        )
    result = analyze(args.annotations_dir, args.output_dir, args.key_path)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
