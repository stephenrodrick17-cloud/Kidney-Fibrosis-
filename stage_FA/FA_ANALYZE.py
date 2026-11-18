from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
import platform
import random
import sys
import time
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True

import numpy as np
import scipy
from scipy.io import mmread
from scipy.stats import spearmanr

ROOT = Path(r"D:\patent")
OUT = ROOT / "stage_FA"
ALIGNMENT = ROOT / "stage_G2" / "GENE2_ALIGNMENT_AUDIT.csv"
STAGE1_TARGETS = ROOT / "stage1_expression" / "targets_by_spot.csv"
GENE_SCREEN = ROOT / "qc_collagen" / "gene_detection_cohort_summary.csv"
SCORE_FILE = OUT / "FA_SPOT_FIBROSIS_SCORES.csv"
COLOUR_FILE = OUT / "FA_SPOT_COLOUR.csv"
SLIDE_FILE = OUT / "FA_SLIDE_FIBROSIS_FRACTIONS_FINAL.csv"
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
MASKS = ("unet", "colour")
ANALYSIS_LABEL = "EXPLORATORY, NOT CONFIRMATORY"
MASK_LABEL = "UNVALIDATED MASKS"
ASSET_STATUS = "RESEARCH-ONLY"
BOOTSTRAPS = 10_000
SIGN_FLIPS = 10_000
LABEL_SHUFFLES = 10_000
SEED = 20261117
MAX_RUNTIME_SECONDS = 90 * 60
MAX_OUTPUT_BYTES = 8 * 1024**3


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def directory_size(path: Path) -> int:
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def write_csv(name: str, rows: list[dict[str, object]]) -> Path:
    path = OUT / name
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {path}")
    if not rows:
        raise ValueError(f"Refusing to write an empty table: {name}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def expected_label(rows: list[dict[str, str]], column: str, label: str) -> None:
    if not rows or any(row.get(column) != label for row in rows):
        raise ValueError(f"Input labels are missing or inconsistent in column {column}.")


def load_stage1_expression() -> dict[tuple[str, str, str], dict[str, object]]:
    result: dict[tuple[str, str, str], dict[str, object]] = {}
    with STAGE1_TARGETS.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (row["participant_id"], row["library_id"], row["barcode"])
            if key in result:
                raise ValueError(f"Duplicate Stage 1 expression key: {key}")
            library_size = int(float(row["library_size_umi"]))
            if library_size <= 0:
                raise ValueError(f"Invalid Stage 1 library size for {key}")
            raw = {gene: int(float(row[f"raw_{gene}"])) for gene in GENES}
            result[key] = {"library_size_umi": library_size, "raw_counts": raw}
    return result


def matrix_triplet(archive: zipfile.ZipFile) -> tuple[str, str, str]:
    candidates: dict[str, dict[str, str]] = {}
    for member in archive.namelist():
        normalized = PurePosixPath(member.replace("\\", "/"))
        if normalized.is_absolute() or ".." in normalized.parts:
            raise ValueError(f"Unsafe matrix archive path: {member}")
        leaf = normalized.name.lower()
        role = None
        if leaf.endswith("barcodes.tsv.gz"):
            role = "barcodes"
        elif leaf.endswith("features.tsv.gz"):
            role = "features"
        elif leaf.endswith("matrix.mtx.gz"):
            role = "matrix"
        if role:
            candidates.setdefault(str(normalized.parent), {})[role] = member
    complete = [
        group
        for group in candidates.values()
        if set(group) == {"barcodes", "features", "matrix"}
    ]
    if len(complete) != 1:
        raise ValueError(f"Expected one Matrix Market triplet; found {len(complete)}.")
    group = complete[0]
    return group["barcodes"], group["features"], group["matrix"]


def load_stage1d_expression(
    path: Path, participant: str, library: str
) -> dict[tuple[str, str, str], dict[str, object]]:
    if not path.is_file():
        raise FileNotFoundError(f"Local Stage 1d expression archive not found: {path}")
    with zipfile.ZipFile(path) as archive:
        barcode_member, feature_member, matrix_member = matrix_triplet(archive)
        barcodes = gzip.decompress(archive.read(barcode_member)).decode("utf-8").splitlines()
        features = [
            line.split("\t")
            for line in gzip.decompress(archive.read(feature_member))
            .decode("utf-8")
            .splitlines()
        ]
        matrix = mmread(
            io.BytesIO(gzip.decompress(archive.read(matrix_member)))
        ).tocsr()
    if matrix.shape != (len(features), len(barcodes)):
        raise ValueError(f"Stage 1d matrix dimensions do not match {path.name}.")
    if len(barcodes) != len(set(barcodes)):
        raise ValueError(f"Duplicate expression barcode in {path.name}.")
    feature_rows: dict[str, list[int]] = defaultdict(list)
    for index, feature in enumerate(features):
        if len(feature) > 1:
            feature_rows[feature[1].strip().upper()].append(index)
    missing = [gene for gene in GENES if not feature_rows.get(gene)]
    if missing:
        raise ValueError(f"{path.name} is missing target genes: {missing}")
    gene_counts = {
        gene: np.asarray(matrix[feature_rows[gene], :].sum(axis=0)).ravel()
        for gene in GENES
    }
    library_sizes = np.asarray(matrix.sum(axis=0)).ravel()
    result: dict[tuple[str, str, str], dict[str, object]] = {}
    for index, barcode in enumerate(barcodes):
        key = (participant, library, barcode)
        if key in result:
            raise ValueError(f"Duplicate Stage 1d expression key: {key}")
        total = int(library_sizes[index])
        if total <= 0:
            raise ValueError(f"Invalid Stage 1d library size for {key}")
        result[key] = {
            "library_size_umi": total,
            "raw_counts": {gene: int(gene_counts[gene][index]) for gene in GENES},
        }
    return result


def load_expression(
    alignment: list[dict[str, str]],
) -> tuple[dict[tuple[str, str, str], dict[str, object]], list[dict[str, object]], list[Path]]:
    stage1 = load_stage1_expression()
    expected_stage1 = {row["participant_id"] for row in alignment if row["source_set"] == "Stage 1"}
    observed_stage1 = {key[0] for key in stage1}
    if expected_stage1 != observed_stage1:
        raise ValueError("Stage 1 target table participants differ from the audited cohort.")
    stage1_libraries = {key[:2] for key in stage1}
    expected_stage1_libraries = {
        (row["participant_id"], row["library_id"])
        for row in alignment
        if row["source_set"] == "Stage 1"
    }
    if stage1_libraries != expected_stage1_libraries:
        raise ValueError("Stage 1 target table libraries differ from the audited cohort.")
    if len(stage1) != 25_104:
        raise ValueError(f"Expected 25,104 Stage 1 target keys, found {len(stage1)}.")

    combined = dict(stage1)
    matrix_paths: list[Path] = []
    for row in alignment:
        if row["source_set"] != "Stage 1d":
            continue
        expression_name = row["expression_record"].split("::", 1)[0]
        expression_path = ROOT / "data_confirm" / Path(expression_name).name
        matrix_paths.append(expression_path)
        loaded = load_stage1d_expression(
            expression_path, row["participant_id"], row["library_id"]
        )
        overlap = set(combined).intersection(loaded)
        if overlap:
            raise ValueError(f"Stage 1d expression keys overlap other libraries: {next(iter(overlap))}")
        combined.update(loaded)

    alignment_rows: list[dict[str, object]] = []
    return combined, alignment_rows, matrix_paths


def holm_adjust(p_values: list[float]) -> list[float]:
    adjusted = [math.nan] * len(p_values)
    finite = [(index, float(value)) for index, value in enumerate(p_values) if math.isfinite(value)]
    ordered = sorted(finite, key=lambda item: item[1])
    running = 0.0
    total = len(ordered)
    for rank, (index, value) in enumerate(ordered):
        running = max(running, (total - rank) * value)
        adjusted[index] = min(1.0, running)
    return adjusted


def make_groups(
    spot_rows: list[dict[str, object]], mask: str
) -> tuple[dict[tuple[str, str, str], str], list[dict[str, object]]]:
    score_column = f"{mask}_fibrosis_fraction"
    libraries: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in spot_rows:
        libraries[(str(row["participant_id"]), str(row["library_id"]))].append(row)
    groups: dict[tuple[str, str, str], str] = {}
    summaries = []
    for (participant, library), rows in sorted(libraries.items()):
        ranked = sorted(
            rows,
            key=lambda row: (float(row[score_column]), str(row["barcode"])),
        )
        tertile_n = len(ranked) // 3
        excluded_reason = ""
        if tertile_n < 20:
            excluded_reason = "fewer than 20 spots in a tertile"
            for row in ranked:
                groups[(participant, library, str(row["barcode"]))] = "excluded"
            low_n = high_n = 0
        else:
            for index, row in enumerate(ranked):
                if index < tertile_n:
                    group = "low"
                elif index >= len(ranked) - tertile_n:
                    group = "high"
                else:
                    group = "middle"
                groups[(participant, library, str(row["barcode"]))] = group
            low_n = high_n = tertile_n
        summaries.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "mask": mask,
                "participant_id": participant,
                "library_id": library,
                "eligible_spots": len(ranked),
                "low_spots": low_n,
                "middle_spots": len(ranked) - low_n - high_n,
                "high_spots": high_n,
                "library_excluded": bool(excluded_reason),
                "exclusion_reason": excluded_reason,
            }
        )
    return groups, summaries


def make_base_design(
    rows: list[dict[str, object]],
    include_count: bool = True,
    include_colour: bool = False,
) -> np.ndarray:
    columns = [
        np.ones(len(rows), dtype=np.float64),
        np.asarray([float(row["tissue_depth_um"]) for row in rows]),
    ]
    if include_count:
        columns.append(np.asarray([float(row["log_library_size"]) for row in rows]))
    columns.append(np.asarray([float(row["tissue_fraction"]) for row in rows]))
    if include_colour:
        for name in ("mean_hue", "mean_saturation", "mean_value"):
            columns.append(np.asarray([float(row[name]) for row in rows]))
    libraries = sorted({str(row["library_id"]) for row in rows})
    for library in libraries[1:]:
        columns.append(
            np.asarray([float(str(row["library_id"]) == library) for row in rows])
        )
    design = np.column_stack(columns)
    keep = [0] + [
        index
        for index in range(1, design.shape[1])
        if float(np.ptp(design[:, index])) > 0.0
    ]
    return design[:, keep]


def fit_high_low(
    rows: list[dict[str, object]],
    target: str,
    include_count: bool = True,
    group_codes: np.ndarray | None = None,
    global_indices: np.ndarray | None = None,
) -> dict[str, object]:
    if group_codes is None:
        selected = [
            row for row in rows if row.get("group") in ("low", "high")
        ]
        if not selected:
            return {"valid": False, "reason": "no high/low spots"}
        y = np.asarray([float(row[target]) for row in selected], dtype=np.float64)
        high = np.asarray([row["group"] == "high" for row in selected], dtype=np.float64)
        base = make_base_design(selected, include_count=include_count)
    else:
        if global_indices is None:
            raise ValueError("Global indices are required for shuffled group assignments.")
        local_codes = group_codes[global_indices]
        selected_mask = local_codes > 0
        y = np.asarray([float(rows[index][target]) for index in np.flatnonzero(selected_mask)])
        high = (local_codes[selected_mask] == 2).astype(np.float64)
        base_all = make_base_design(rows, include_count=include_count)
        base = base_all[selected_mask]
    if len(y) <= base.shape[1]:
        return {"valid": False, "reason": "too few spots for the registered regression"}
    design = np.column_stack((base, high))
    coefficient, _, rank, _ = np.linalg.lstsq(design, y, rcond=None)
    if rank != design.shape[1]:
        return {"valid": False, "reason": "rank-deficient within-participant regression"}
    fitted = design @ coefficient
    tss = float(np.sum((y - y.mean()) ** 2))
    r_squared = 0.0 if tss == 0 else 1.0 - float(np.sum((y - fitted) ** 2)) / tss
    return {
        "valid": True,
        "effect": float(coefficient[-1]),
        "r_squared": r_squared,
        "n_spots": int(len(y)),
        "n_low": int(np.sum(high == 0)),
        "n_high": int(np.sum(high == 1)),
        "reason": "",
    }


def fit_control_r2(rows: list[dict[str, object]], target: str, colour: bool) -> float | None:
    selected = [row for row in rows if row.get("group") in ("low", "high")]
    if not selected:
        return None
    y = np.asarray([float(row[target]) for row in selected], dtype=np.float64)
    design = make_base_design(selected, include_count=True, include_colour=colour)
    if len(y) <= design.shape[1]:
        return None
    coefficient, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
    fitted = design @ coefficient
    tss = float(np.sum((y - y.mean()) ** 2))
    return 0.0 if tss == 0 else 1.0 - float(np.sum((y - fitted) ** 2)) / tss


def bootstrap_mean(values: np.ndarray, seed: int) -> tuple[float, float]:
    if len(values) == 0:
        return math.nan, math.nan
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(values), size=(BOOTSTRAPS, len(values)))
    means = values[indices].mean(axis=1)
    low, high = np.quantile(means, [0.025, 0.975])
    return float(low), float(high)


def signflip_p(values: np.ndarray, seed: int) -> float:
    observed = abs(float(np.mean(values)))
    if len(values) == 0:
        return math.nan
    rng = np.random.default_rng(seed)
    signs = rng.choice(np.asarray([-1.0, 1.0]), size=(SIGN_FLIPS, len(values)))
    shuffled = np.abs((signs @ values) / len(values))
    return float((1 + np.sum(shuffled >= observed)) / (SIGN_FLIPS + 1))


def summarize_effects(
    values: list[float], seed: int
) -> tuple[float, float, float, float, float]:
    array = np.asarray(values, dtype=np.float64)
    if len(array) == 0:
        return math.nan, math.nan, math.nan, math.nan, math.nan
    low, high = bootstrap_mean(array, seed)
    fraction_positive = float(np.mean(array > 0))
    p_value = signflip_p(array, seed + 1)
    return float(array.mean()), low, high, fraction_positive, p_value


def color_groups(slides: list[dict[str, str]]) -> tuple[dict[tuple[str, str], str], list[dict[str, object]]]:
    ordered = sorted(
        slides,
        key=lambda row: (float(row["median_tissue_hue"]), row["library_id"]),
    )
    groups: dict[tuple[str, str], str] = {}
    for index, row in enumerate(ordered):
        quartile = min(4, (index * 4) // len(ordered) + 1)
        groups[(row["participant_id"], row["library_id"])] = f"Q{quartile}"
    return groups, ordered


def panel_residual(values: np.ndarray, covariates: np.ndarray) -> np.ndarray:
    design = np.column_stack((np.ones(len(values)), covariates))
    beta, _, _, _ = np.linalg.lstsq(design, values, rcond=None)
    return values - design @ beta


def panel_correlation(
    fibrosis: np.ndarray, expression: np.ndarray, covariates: np.ndarray
) -> float:
    residual = panel_residual(expression, covariates)
    result = spearmanr(fibrosis, residual)
    return float(result.statistic) if math.isfinite(float(result.statistic)) else math.nan


def bootstrap_panel_ci(
    fibrosis: np.ndarray,
    expression: np.ndarray,
    covariates: np.ndarray,
    seed: int,
    deadline: float,
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    estimates = []
    for replicate in range(BOOTSTRAPS):
        if replicate % 100 == 0 and time.monotonic() >= deadline:
            raise TimeoutError("Stopped before the preregistered 90-minute analysis limit.")
        indices = rng.integers(0, len(fibrosis), size=len(fibrosis))
        value = panel_correlation(
            fibrosis[indices], expression[indices], covariates[indices]
        )
        if math.isfinite(value):
            estimates.append(value)
    if not estimates:
        return math.nan, math.nan
    return tuple(float(value) for value in np.quantile(estimates, [0.025, 0.975]))


def shuffled_primary_test(
    spots: list[dict[str, object]],
    mask: str,
    groups: dict[tuple[str, str, str], str],
    observed: float,
    seed: int,
    deadline: float,
) -> float:
    score_column = f"{mask}_fibrosis_fraction"
    rows = [
        row
        for row in spots
        if groups[
            (str(row["participant_id"]), str(row["library_id"]), str(row["barcode"]))
        ] != "excluded"
    ]
    libraries: dict[tuple[str, str], list[int]] = defaultdict(list)
    participants: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        key = (str(row["participant_id"]), str(row["library_id"]), str(row["barcode"]))
        libraries[key[:2]].append(index)
        participants[key[0]].append(index)
    library_sizes = {
        library: len(indices) // 3
        for library, indices in libraries.items()
    }
    included_libraries = {
        library: indices
        for library, indices in libraries.items()
        if library_sizes[library] >= 20
    }
    model_data = {}
    for participant, indices in participants.items():
        participant_rows = [rows[index] for index in indices]
        model_data[participant] = {
            "rows": participant_rows,
            "indices": np.asarray(indices, dtype=np.int64),
            "base": make_base_design(participant_rows, include_count=True),
            "target": np.asarray(
                [float(row["collagen_module"]) for row in participant_rows],
                dtype=np.float64,
            ),
        }
    rng = np.random.default_rng(seed)
    null_means = np.empty(LABEL_SHUFFLES, dtype=np.float64)
    for replicate in range(LABEL_SHUFFLES):
        if replicate % 100 == 0 and time.monotonic() >= deadline:
            raise TimeoutError("Stopped before the preregistered 90-minute analysis limit.")
        codes = np.zeros(len(rows), dtype=np.int8)
        shuffled_scores = np.empty(len(rows), dtype=np.float64)
        for indices in participants.values():
            index_array = np.asarray(indices, dtype=np.int64)
            original_scores = np.asarray(
                [float(rows[index][score_column]) for index in indices],
                dtype=np.float64,
            )
            shuffled_scores[index_array] = rng.permutation(original_scores)
        for library, indices in included_libraries.items():
            ranked = sorted(
                indices,
                key=lambda index: (
                    float(shuffled_scores[index]),
                    str(rows[index]["barcode"]),
                ),
            )
            group_size = library_sizes[library]
            codes[ranked[:group_size]] = 1
            codes[ranked[-group_size:]] = 2
        effects = []
        for data in model_data.values():
            local_codes = codes[data["indices"]]
            selected = local_codes > 0
            if not selected.any():
                continue
            design = np.column_stack(
                (data["base"][selected], (local_codes[selected] == 2).astype(np.float64))
            )
            target = data["target"][selected]
            coefficient, _, rank, _ = np.linalg.lstsq(design, target, rcond=None)
            if rank == design.shape[1]:
                effects.append(float(coefficient[-1]))
        null_means[replicate] = float(np.mean(effects)) if effects else math.nan
    valid = null_means[np.isfinite(null_means)]
    if len(valid) == 0:
        return math.nan
    return float((1 + np.sum(np.abs(valid) >= abs(observed))) / (len(valid) + 1))


def main() -> None:
    started = time.monotonic()
    deadline = started + MAX_RUNTIME_SECONDS
    started_utc = datetime.now(timezone.utc)
    if directory_size(OUT) >= MAX_OUTPUT_BYTES:
        raise RuntimeError("Stage FA output folder already meets the registered size limit.")
    planned_outputs = (
        "FA_SPOT_ANALYSIS_FINAL.csv",
        "FA_LIBRARY_GROUPS_FINAL.csv",
        "FA_EXPRESSION_ALIGNMENT_FINAL.csv",
        "FA_GENE_AVAILABILITY_FINAL.csv",
        "FA_PER_PARTICIPANT_EFFECTS_FINAL.csv",
        "FA_PRIMARY_ENDPOINT_FINAL.csv",
        "FA_SECONDARY_HOLM_FINAL.csv",
        "FA_CELL_DENSITY_SENSITIVITY_FINAL.csv",
        "FA_CONTROL_MODELS_FINAL.csv",
        "FA_LABEL_SHUFFLE_FINAL.csv",
        "FA_PANEL_SUMMARY_FINAL.csv",
        "FA_PANEL_PARTICIPANT_DATA_FINAL.csv",
        "FA_COLOR_GROUP_SUMMARY_FINAL.csv",
        "FA_COLOR_CONFOUND_CHECK_FINAL.csv",
        "FA_SEVERITY_CALIBRATION_FINAL.csv",
        "FA_ANALYSIS_DECISIONS_FINAL.csv",
        "FA_ANALYSIS_HASHES_FINAL.csv",
        "FA_ANALYSIS_METADATA_FINAL.json",
    )
    existing_outputs = [OUT / name for name in planned_outputs if (OUT / name).exists()]
    if existing_outputs:
        raise FileExistsError(f"Refusing to overwrite existing output: {existing_outputs[0]}")
    if not all(path.is_file() for path in (ALIGNMENT, STAGE1_TARGETS, GENE_SCREEN, SCORE_FILE, COLOUR_FILE, SLIDE_FILE)):
        raise FileNotFoundError("A required local expression, mask, colour, or audit file is missing.")

    alignment = read_csv(ALIGNMENT)
    scores = read_csv(SCORE_FILE)
    colours = read_csv(COLOUR_FILE)
    slides = read_csv(SLIDE_FILE)
    expected_label(scores, "analysis_label", ANALYSIS_LABEL)
    expected_label(scores, "mask_status", MASK_LABEL)
    expected_label(colours, "analysis_label", ANALYSIS_LABEL)
    expected_label(slides, "analysis_label", ANALYSIS_LABEL)
    if len(alignment) != 41 or len({row["participant_id"] for row in alignment}) != 40:
        raise ValueError("The audited participant/library counts changed.")
    alignment_libraries = {
        (row["participant_id"], row["library_id"]) for row in alignment
    }
    if len(alignment_libraries) != len(alignment) or any(
        row.get("status") != "PASS" for row in alignment
    ):
        raise ValueError("The audited spot-to-image mapping has duplicate libraries or a non-PASS row.")

    screen = {row["gene"]: row for row in read_csv(GENE_SCREEN)}
    for gene in GENES:
        if gene not in screen or screen[gene]["usable_for_prediction_rule"].lower() != "true":
            raise ValueError(f"The earlier detection screen does not confirm the registered gene: {gene}")

    expression, _, matrix_paths = load_expression(alignment)
    included_scores = [
        row for row in scores if row["included"].lower() == "true"
    ]
    expected_keys = {
        (row["participant_id"], row["library_id"], row["barcode"])
        for row in included_scores
    }
    expression_keys = set(expression)
    alignment_rows = []
    for row in alignment:
        participant = row["participant_id"]
        library = row["library_id"]
        expected_library = {
            key for key in expected_keys if key[:2] == (participant, library)
        }
        actual_library = {
            key for key in expression_keys if key[:2] == (participant, library)
        }
        missing = expected_library - actual_library
        extra = actual_library - expected_library
        alignment_rows.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "participant_id": participant,
                "library_id": library,
                "source_set": row["source_set"],
                "mapping_status_from_existing_audit": row["status"],
                "mask_score_spots": len(expected_library),
                "expression_spots": len(actual_library),
                "missing_expression_keys": len(missing),
                "extra_expression_keys": len(extra),
                "status": "PASS" if not missing and not extra else "FAIL",
                "reason": "",
            }
        )
    if expected_keys != expression_keys:
        alignment_path = write_csv("FA_EXPRESSION_ALIGNMENT.csv", alignment_rows)
        raise ValueError(
            f"Expression and saved mask spot keys do not match exactly; see {alignment_path}."
        )
    if len(expression_keys) != 34_735:
        raise ValueError(f"Expected 34,735 matched full spot keys, found {len(expression_keys)}.")

    score_by_key = {
        (row["participant_id"], row["library_id"], row["barcode"]): row
        for row in included_scores
    }
    colour_by_key = {
        (row["participant_id"], row["library_id"], row["barcode"]): row
        for row in colours
    }
    if len(score_by_key) != len(included_scores) or len(colour_by_key) != len(colours):
        raise ValueError("Duplicate full spot keys in mask-score or colour-feature inputs.")
    if set(colour_by_key) != expected_keys:
        raise ValueError("Spot colour-feature keys differ from the saved mask-score keys.")
    slide_by_library = {
        (row["participant_id"], row["library_id"]): row for row in slides
    }
    if len(slide_by_library) != len(slides) or len(slide_by_library) != len(alignment):
        raise ValueError("Slide-fraction table has duplicate or missing participant/library keys.")
    participant_source = {
        (row["participant_id"], row["library_id"]): row["source_set"]
        for row in alignment
    }

    data_rows: list[dict[str, object]] = []
    gene_available_rows = []
    for gene in GENES:
        stage1d_rows = [
            row
            for key, row in expression.items()
            if participant_source[key[:2]] == "Stage 1d"
        ]
        nonzero_spots = sum(int(row["raw_counts"][gene]) > 0 for row in stage1d_rows)
        gene_available_rows.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "gene": gene,
                "stage1_detection_screen": screen[gene]["usable_for_prediction_rule"],
                "stage1_participants_ge10pct": screen[gene]["participants_ge10pct"],
                "stage1d_participants": len({key[0] for key in expression if participant_source[key[:2]] == "Stage 1d"}),
                "stage1d_libraries_with_gene_feature": len(
                    {
                        key[:2]
                        for key, row in expression.items()
                        if participant_source[key[:2]] == "Stage 1d"
                        and int(row["raw_counts"][gene]) >= 0
                    }
                ),
                "stage1d_spots_with_nonzero_counts": nonzero_spots,
                "stage1d_spots_with_expression_rows": len(stage1d_rows),
            }
        )

    for key in sorted(expected_keys):
        raw = expression[key]["raw_counts"]
        library_size = int(expression[key]["library_size_umi"])
        if library_size <= 0:
            raise ValueError(f"Zero library size for matched expression key {key}")
        score = score_by_key[key]
        colour = colour_by_key[key]
        slide = slide_by_library[key[:2]]
        row: dict[str, object] = {
            "analysis_label": ANALYSIS_LABEL,
            "mask_status": MASK_LABEL,
            "asset_status": ASSET_STATUS,
            "participant_id": key[0],
            "library_id": key[1],
            "barcode": key[2],
            "source_set": participant_source[key[:2]],
            "library_size_umi": library_size,
            "log_library_size": math.log1p(library_size),
            "tissue_fraction": float(score["tissue_fraction"]),
            "tissue_depth_um": float(score["tissue_depth_um"]),
            "unet_fibrosis_fraction": float(score["unet_fibrosis_fraction"]),
            "colour_fibrosis_fraction": float(score["colour_fibrosis_fraction"]),
            "mean_hue": float(colour["mean_hue"]),
            "mean_saturation": float(colour["mean_saturation"]),
            "mean_value": float(colour["mean_value"]),
            "unet_slide_fibrosis_percent": float(slide["unet_fibrosis_percent_tissue"]),
            "colour_slide_fibrosis_percent": float(slide["colour_fibrosis_percent_tissue"]),
        }
        for gene in GENES:
            count = int(raw[gene])
            row[f"raw_{gene}"] = count
            row[gene] = math.log1p(10_000.0 * count / library_size)
        data_rows.append(row)

    for gene in GENES:
        values = np.asarray([float(row[gene]) for row in data_rows])
        deviation = float(values.std(ddof=0))
        if not math.isfinite(deviation) or deviation == 0:
            raise ValueError(f"Cannot z-score constant or invalid target: {gene}")
        mean = float(values.mean())
        for row in data_rows:
            row[f"z_{gene}"] = (float(row[gene]) - mean) / deviation
    for row in data_rows:
        row["collagen_module"] = float(
            np.mean([row[f"z_{gene}"] for gene in MODULE_GENES])
        )

    color_group_by_library, ordered_color_slides = color_groups(slides)
    for row in data_rows:
        key = (str(row["participant_id"]), str(row["library_id"]), str(row["barcode"]))
        row["unet_group"] = ""
        row["colour_group"] = ""
        row["color_quartile"] = color_group_by_library[key[:2]]

    group_maps: dict[str, dict[tuple[str, str, str], str]] = {}
    group_summaries: list[dict[str, object]] = []
    for mask in MASKS:
        group_map, summaries = make_groups(included_scores, mask)
        group_maps[mask] = group_map
        group_summaries.extend(summaries)
        group_column = f"{mask}_group"
        for row in data_rows:
            key = (str(row["participant_id"]), str(row["library_id"]), str(row["barcode"]))
            row[group_column] = group_map[key]
    spot_analysis_path = OUT / "FA_SPOT_ANALYSIS.csv"
    group_path = OUT / "FA_LIBRARY_GROUPS.csv"
    alignment_path = OUT / "FA_EXPRESSION_ALIGNMENT.csv"
    availability_path = OUT / "FA_GENE_AVAILABILITY.csv"

    participant_ids = sorted({str(row["participant_id"]) for row in data_rows})
    index_by_key = {
        (str(row["participant_id"]), str(row["library_id"]), str(row["barcode"])): index
        for index, row in enumerate(data_rows)
    }
    participants: dict[str, list[int]] = defaultdict(list)
    libraries: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, row in enumerate(data_rows):
        participants[str(row["participant_id"])].append(index)
        libraries[(str(row["participant_id"]), str(row["library_id"]))].append(index)

    effects_rows: list[dict[str, object]] = []
    primary_rows: list[dict[str, object]] = []
    secondary_rows: list[dict[str, object]] = []
    density_rows: list[dict[str, object]] = []
    control_rows: list[dict[str, object]] = []
    effect_values: dict[tuple[str, str], list[float]] = {}
    effect_records: dict[tuple[str, str], list[dict[str, object]]] = {}
    primary_seeds: dict[str, int] = {}

    for mask_index, mask in enumerate(MASKS):
        mask_groups = group_maps[mask]
        for target_index, target in enumerate(TARGETS):
            fitted_rows = []
            for participant in participant_ids:
                rows = [data_rows[index] for index in participants[participant]]
                for row in rows:
                    key = (str(row["participant_id"]), str(row["library_id"]), str(row["barcode"]))
                    row["group"] = mask_groups[key]
                fit = fit_high_low(rows, target, include_count=True)
                if fit["valid"]:
                    fitted_rows.append(
                        {
                            "analysis_label": ANALYSIS_LABEL,
                            "mask_status": MASK_LABEL,
                            "asset_status": ASSET_STATUS,
                            "mask": mask,
                            "target": target,
                            "participant_id": participant,
                            "n_spots": fit["n_spots"],
                            "n_low": fit["n_low"],
                            "n_high": fit["n_high"],
                            "participant_effect_high_minus_low": fit["effect"],
                            "model_r_squared": fit["r_squared"],
                            "positive_effect": fit["effect"] > 0,
                            "count_adjustment": "included",
                            "fit_status": "PASS",
                            "exclusion_reason": "",
                        }
                    )
                else:
                    fitted_rows.append(
                        {
                            "analysis_label": ANALYSIS_LABEL,
                            "mask_status": MASK_LABEL,
                            "asset_status": ASSET_STATUS,
                            "mask": mask,
                            "target": target,
                            "participant_id": participant,
                            "n_spots": 0,
                            "n_low": 0,
                            "n_high": 0,
                            "participant_effect_high_minus_low": math.nan,
                            "model_r_squared": math.nan,
                            "positive_effect": "",
                            "count_adjustment": "included",
                            "fit_status": "EXCLUDED",
                            "exclusion_reason": fit["reason"],
                        }
                    )
            effect_records[(mask, target)] = fitted_rows
            valid_effects = [
                float(row["participant_effect_high_minus_low"])
                for row in fitted_rows
                if row["fit_status"] == "PASS"
            ]
            effect_values[(mask, target)] = valid_effects
            effects_rows.extend(fitted_rows)
            seed = SEED + mask_index * 100 + target_index * 10
            mean, low, high, positive_fraction, p_value = summarize_effects(
                valid_effects, seed
            )
            n_participants = len(valid_effects)
            n_spots = sum(
                int(row["n_spots"])
                for row in fitted_rows
                if row["fit_status"] == "PASS"
            )
            if target == "collagen_module":
                met = low > 0 and positive_fraction >= 0.70
                role = "PRIMARY" if mask == "unet" else "ROBUSTNESS REPEAT ONLY"
                primary_rows.append(
                    {
                        "analysis_label": ANALYSIS_LABEL,
                        "mask_status": MASK_LABEL,
                        "asset_status": ASSET_STATUS,
                        "mask": mask,
                        "endpoint_role": role,
                        "target": target,
                        "participants": n_participants,
                        "spots_in_high_low_groups": n_spots,
                        "mean_high_minus_low_effect": mean,
                        "participant_bootstrap_ci95_low": low,
                        "participant_bootstrap_ci95_high": high,
                        "bootstrap_resamples": BOOTSTRAPS,
                        "bootstrap_seed": seed,
                        "positive_participant_fraction": positive_fraction,
                        "positive_participant_count": sum(
                            float(value) > 0 for value in valid_effects
                        ),
                        "signflip_p_two_sided": p_value,
                        "signflip_resamples": SIGN_FLIPS,
                        "registered_rule_status": (
                            "met" if met else "not met"
                        ) if mask == "unet" else "robustness only; not a co-primary",
                        "analysis_outcome": (
                            "met" if met else "not met"
                        ) if mask == "unet" else "robustness-only estimate",
                    }
                )
                primary_seeds[mask] = seed
            else:
                secondary_rows.append(
                    {
                        "analysis_label": ANALYSIS_LABEL,
                        "mask_status": MASK_LABEL,
                        "asset_status": ASSET_STATUS,
                        "mask": mask,
                        "gene": target,
                        "participants": n_participants,
                        "spots_in_high_low_groups": n_spots,
                        "mean_high_minus_low_effect": mean,
                        "participant_bootstrap_ci95_low": low,
                        "participant_bootstrap_ci95_high": high,
                        "bootstrap_resamples": BOOTSTRAPS,
                        "bootstrap_seed": seed,
                        "positive_participant_fraction": positive_fraction,
                        "signflip_p_two_sided": p_value,
                        "holm_adjusted_p": math.nan,
                        "holm_family": f"9 secondary genes within {mask} mask",
                        "can_rescue_primary": False,
                    }
                )

    for mask in MASKS:
        candidates = [
            row for row in secondary_rows if row["mask"] == mask
        ]
        adjusted = holm_adjust([float(row["signflip_p_two_sided"]) for row in candidates])
        for row, value in zip(candidates, adjusted):
            row["holm_adjusted_p"] = value
    for target in GENES:
        target_rows = [row for row in secondary_rows if row["gene"] == target]
        unet_row = next(row for row in target_rows if row["mask"] == "unet")
        colour_row = next(row for row in target_rows if row["mask"] == "colour")
        unet_effect = float(unet_row["mean_high_minus_low_effect"])
        colour_effect = float(colour_row["mean_high_minus_low_effect"])
        agreement = (
            (unet_effect > 0 and colour_effect > 0)
            or (unet_effect < 0 and colour_effect < 0)
        )
        for row in target_rows:
            row["mask_direction_agreement"] = agreement

    for mask_index, mask in enumerate(MASKS):
        rows_for_mask = [
            row for row in data_rows
            if group_maps[mask][
                (str(row["participant_id"]), str(row["library_id"]), str(row["barcode"]))
            ] in ("low", "high")
        ]
        for participant in participant_ids:
            rows = [
                row for row in rows_for_mask
                if str(row["participant_id"]) == participant
            ]
            if not rows:
                continue
            for row in rows:
                key = (str(row["participant_id"]), str(row["library_id"]), str(row["barcode"]))
                row["group"] = group_maps[mask][key]
            for color_only, model_name in ((False, "depth_only"), (True, "colour_only")):
                r2 = fit_control_r2(rows, "collagen_module", colour=color_only)
                control_rows.append(
                    {
                        "analysis_label": ANALYSIS_LABEL,
                        "mask_status": MASK_LABEL,
                        "asset_status": ASSET_STATUS,
                        "mask": mask,
                        "model": model_name,
                        "participant_id": participant,
                        "target": "collagen_module",
                        "n_spots": len(rows),
                        "r_squared": r2,
                        "high_low_indicator_included": False,
                        "colour_features_included": color_only,
                    }
                )
            fit_rows = effect_records[(mask, "collagen_module")]
            fit = next((row for row in fit_rows if row["participant_id"] == participant), None)
            control_rows.append(
                {
                    "analysis_label": ANALYSIS_LABEL,
                    "mask_status": MASK_LABEL,
                    "asset_status": ASSET_STATUS,
                    "mask": mask,
                    "model": "full_primary",
                    "participant_id": participant,
                    "target": "collagen_module",
                    "n_spots": int(fit["n_spots"]) if fit else 0,
                    "r_squared": fit["model_r_squared"] if fit else math.nan,
                    "high_low_indicator_included": True,
                    "colour_features_included": False,
                }
            )

    for mask_index, mask in enumerate(MASKS):
        density_effect_rows = []
        for participant in participant_ids:
            rows = [data_rows[index] for index in participants[participant]]
            for row in rows:
                key = (str(row["participant_id"]), str(row["library_id"]), str(row["barcode"]))
                row["group"] = group_maps[mask][key]
            fit = fit_high_low(rows, "collagen_module", include_count=False)
            if fit["valid"]:
                density_effect_rows.append(
                    {
                        "participant_id": participant,
                        "effect": float(fit["effect"]),
                        "n_spots": int(fit["n_spots"]),
                    }
                )
        values = np.asarray([row["effect"] for row in density_effect_rows], dtype=np.float64)
        mean, low, high, positive_fraction, p_value = summarize_effects(
            values, SEED + 500 + mask_index * 10
        )
        density_rows.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "mask": mask,
                "target": "collagen_module",
                "count_adjustment": "excluded",
                "participants": len(values),
                "spots_in_high_low_groups": sum(row["n_spots"] for row in density_effect_rows),
                "mean_high_minus_low_effect": mean,
                "participant_bootstrap_ci95_low": low,
                "participant_bootstrap_ci95_high": high,
                "bootstrap_resamples": BOOTSTRAPS,
                "bootstrap_seed": SEED + 500 + mask_index * 10,
                "positive_participant_fraction": positive_fraction,
                "signflip_p_two_sided": p_value,
                "participant_effects_json": json.dumps(density_effect_rows, separators=(",", ":")),
            }
        )

    label_shuffle_rows = []
    for mask_index, mask in enumerate(MASKS):
        observed_values = np.asarray(effect_values[(mask, "collagen_module")])
        observed = float(observed_values.mean()) if len(observed_values) else math.nan
        shuffle_p = shuffled_primary_test(
            data_rows,
            mask,
            group_maps[mask],
            observed,
            SEED + 700 + mask_index,
            deadline,
        )
        label_shuffle_rows.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "mask": mask,
                "target": "collagen_module",
                "observed_mean_effect": observed,
                "shuffle_p_two_sided": shuffle_p,
                "shuffle_resamples": LABEL_SHUFFLES,
                "shuffle_seed": SEED + 700 + mask_index,
                "permutation_unit": "fibrosis scores permuted within participant; tertiles rebuilt per library",
            }
        )

    primary_unet = next(row for row in primary_rows if row["mask"] == "unet")
    primary_colour = next(row for row in primary_rows if row["mask"] == "colour")
    unet_mean = float(primary_unet["mean_high_minus_low_effect"])
    colour_mean = float(primary_colour["mean_high_minus_low_effect"])
    direction_agreement = (
        (unet_mean > 0 and colour_mean > 0)
        or (unet_mean < 0 and colour_mean < 0)
    )
    for row in primary_rows:
        row["mask_direction_agreement"] = direction_agreement
        row["unet_primary_mean_effect"] = unet_mean
        row["colour_robustness_mean_effect"] = colour_mean

    participant_panel: dict[str, dict[str, object]] = {}
    for participant in participant_ids:
        participant_rows = [data_rows[index] for index in participants[participant]]
        libraries_for_participant = sorted({str(row["library_id"]) for row in participant_rows})
        panel = {
            "participant_id": participant,
            "mean_log_library_size": float(np.mean([row["log_library_size"] for row in participant_rows])),
            "mean_tissue_fraction": float(np.mean([row["tissue_fraction"] for row in participant_rows])),
        }
        for mask in MASKS:
            per_library = [
                float(slide_by_library[(participant, library)][f"{mask}_fibrosis_percent_tissue"])
                for library in libraries_for_participant
            ]
            panel[f"{mask}_mean_fibrosis_percent"] = float(np.mean(per_library))
        for gene in GENES:
            raw_total = sum(int(row[f"raw_{gene}"]) for row in participant_rows)
            library_total = sum(int(row["library_size_umi"]) for row in participant_rows)
            panel[f"pseudobulk_{gene}"] = math.log1p(10_000.0 * raw_total / library_total)
        participant_panel[participant] = panel

    for mask in MASKS:
        pseudo_values = {
            gene: np.asarray([float(participant_panel[p][f"pseudobulk_{gene}"]) for p in participant_ids])
            for gene in GENES
        }
        for gene in GENES:
            values = pseudo_values[gene]
            deviation = float(values.std(ddof=0))
            if deviation == 0:
                raise ValueError(f"Cannot z-score constant pseudobulk gene: {gene}")
            for index, participant in enumerate(participant_ids):
                participant_panel[participant][f"pseudobulk_z_{gene}"] = (
                    float(values[index]) - float(values.mean())
                ) / deviation
        module_values = np.asarray(
            [
                np.mean(
                    [participant_panel[p][f"pseudobulk_z_{gene}"] for gene in MODULE_GENES]
                )
                for p in participant_ids
            ],
            dtype=np.float64,
        )
        for index, participant in enumerate(participant_ids):
            participant_panel[participant]["pseudobulk_collagen_module"] = float(module_values[index])

    panel_rows: list[dict[str, object]] = []
    panel_participant_rows: list[dict[str, object]] = []
    panel_p_values: dict[str, list[tuple[int, float]]] = {mask: [] for mask in MASKS}
    for participant in participant_ids:
        panel = participant_panel[participant]
        for mask in MASKS:
            panel_participant_rows.append(
                {
                    "analysis_label": ANALYSIS_LABEL,
                    "mask_status": MASK_LABEL,
                    "asset_status": ASSET_STATUS,
                    "participant_id": participant,
                    "mask": mask,
                    "mean_fibrosis_percent_tissue": panel[f"{mask}_mean_fibrosis_percent"],
                    "mean_log_library_size": panel["mean_log_library_size"],
                    "mean_tissue_fraction": panel["mean_tissue_fraction"],
                    **{
                        f"pseudobulk_{gene}": panel[f"pseudobulk_{gene}"]
                        for gene in GENES
                    },
                    "pseudobulk_collagen_module": panel["pseudobulk_collagen_module"],
                }
            )

    for mask_index, mask in enumerate(MASKS):
        fibrosis = np.asarray(
            [float(participant_panel[p][f"{mask}_mean_fibrosis_percent"]) for p in participant_ids]
        )
        covariates = np.asarray(
            [
                [
                    float(participant_panel[p]["mean_log_library_size"]),
                    float(participant_panel[p]["mean_tissue_fraction"]),
                ]
                for p in participant_ids
            ],
            dtype=np.float64,
        )
        targets = {
            "collagen_module": np.asarray(
                [float(participant_panel[p]["pseudobulk_collagen_module"]) for p in participant_ids]
            ),
            **{
                gene: np.asarray(
                    [float(participant_panel[p][f"pseudobulk_{gene}"]) for p in participant_ids]
                )
                for gene in GENES
            },
        }
        for target_index, (target, values) in enumerate(targets.items()):
            residual = panel_residual(values, covariates)
            result = spearmanr(fibrosis, residual)
            rho = float(result.statistic)
            p_value = float(result.pvalue)
            ci_low, ci_high = bootstrap_panel_ci(
                fibrosis,
                values,
                covariates,
                SEED + 900 + mask_index * 100 + target_index,
                deadline,
            )
            panel_rows.append(
                {
                    "analysis_label": ANALYSIS_LABEL,
                    "mask_status": MASK_LABEL,
                    "asset_status": ASSET_STATUS,
                    "mask": mask,
                    "target": target,
                    "participants": len(participant_ids),
                    "spearman_rho_depth_adjusted": rho,
                    "spearman_rho_squared": rho * rho,
                    "participant_bootstrap_ci95_low": ci_low,
                    "participant_bootstrap_ci95_high": ci_high,
                    "bootstrap_resamples": BOOTSTRAPS,
                    "bootstrap_seed": SEED + 900 + mask_index * 100 + target_index,
                    "asymptotic_spearman_p": p_value,
                    "holm_adjusted_p": math.nan,
                    "holm_family": f"10 pseudobulk panel targets within {mask} mask",
                    "pseudobulk_depth_adjustment": "OLS on mean log spot counts and mean tissue fraction",
                }
            )
            panel_p_values[mask].append((len(panel_rows) - 1, p_value))
    for mask in MASKS:
        indices = [index for index, _ in panel_p_values[mask]]
        adjusted = holm_adjust([value for _, value in panel_p_values[mask]])
        for index, value in zip(indices, adjusted):
            panel_rows[index]["holm_adjusted_p"] = value
    for target in ("collagen_module",) + GENES:
        target_rows = [row for row in panel_rows if row["target"] == target]
        unet_row = next(row for row in target_rows if row["mask"] == "unet")
        colour_row = next(row for row in target_rows if row["mask"] == "colour")
        unet_rho = float(unet_row["spearman_rho_depth_adjusted"])
        colour_rho = float(colour_row["spearman_rho_depth_adjusted"])
        agreement = (
            (unet_rho > 0 and colour_rho > 0)
            or (unet_rho < 0 and colour_rho < 0)
        )
        for row in target_rows:
            row["mask_direction_agreement"] = agreement

    color_group_rows: list[dict[str, object]] = []
    color_confound_rows: list[dict[str, object]] = []
    for mask in MASKS:
        library_values = []
        for slide in slides:
            library_values.append(
                (
                    color_group_by_library[(slide["participant_id"], slide["library_id"])],
                    float(slide[f"{mask}_fibrosis_percent_tissue"]),
                    slide["participant_id"],
                    slide["library_id"],
                )
            )
        overall = float(np.mean([item[1] for item in library_values]))
        total_ss = float(sum((item[1] - overall) ** 2 for item in library_values))
        between_ss = 0.0
        for quartile in ("Q1", "Q2", "Q3", "Q4"):
            group = [item for item in library_values if item[0] == quartile]
            mean_value = float(np.mean([item[1] for item in group])) if group else math.nan
            if group:
                between_ss += len(group) * (mean_value - overall) ** 2
            color_group_rows.append(
                {
                    "analysis_label": ANALYSIS_LABEL,
                    "mask_status": MASK_LABEL,
                    "asset_status": ASSET_STATUS,
                    "mask": mask,
                    "image_colour_quartile": quartile,
                    "libraries": len(group),
                    "participants": len({item[2] for item in group}),
                    "mean_fibrosis_percent_tissue": mean_value,
                    "sd_fibrosis_percent_tissue": float(np.std([item[1] for item in group], ddof=1))
                    if len(group) > 1 else math.nan,
                    "group_definition": "equal-frequency quartile of library median tissue hue; ties by library ID",
                    "verified_stain_label": False,
                }
            )
        eta_squared = between_ss / total_ss if total_ss > 0 else math.nan
        gene_rows = [
            row for row in panel_rows
            if row["mask"] == mask and row["target"] in GENES
        ]
        max_gene = max(gene_rows, key=lambda row: float(row["spearman_rho_squared"]))
        max_gene_r2 = float(max_gene["spearman_rho_squared"])
        color_confound_rows.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "mask": mask,
                "library_level_color_group_eta_squared": eta_squared,
                "largest_gene_participant_spearman_rho_squared": max_gene_r2,
                "gene_with_largest_squared_signal": max_gene["target"],
                "colour_group_explains_more_than_any_gene_signal": (
                    eta_squared > max_gene_r2 if math.isfinite(eta_squared) else ""
                ),
                "interpretation": "image-colour proxy only; stain groups are not verified",
            }
        )

    severity_rows = [
        {
            "analysis_label": ANALYSIS_LABEL,
            "mask_status": MASK_LABEL,
            "asset_status": ASSET_STATUS,
            "pathology_or_clinical_variable": variable,
            "participants_with_confirmed_local_value": 0,
            "result": "NOT TESTABLE",
            "reason": "No value was identified in the allowed local records; Stage 1d metadata coverage is incomplete.",
        }
        for variable in (
            "IFTA percentage or grade",
            "interstitial fibrosis score",
            "tubular atrophy",
            "eGFR",
            "serum creatinine",
            "diagnosis",
            "age",
            "sex",
        )
    ]

    if not direction_agreement:
        direction_note = "The U-Net and colour-mask mean effects do not agree in direction."
    else:
        direction_note = "The U-Net and colour-mask mean effects agree in direction."
    main_rows = [
        {
            "analysis_label": ANALYSIS_LABEL,
            "mask_status": MASK_LABEL,
            "asset_status": ASSET_STATUS,
            "item": "mask direction agreement",
            "value": direction_agreement,
            "plain_language_note": direction_note,
        }
    ]

    input_paths = [
        ALIGNMENT,
        STAGE1_TARGETS,
        GENE_SCREEN,
        SCORE_FILE,
        COLOUR_FILE,
        SLIDE_FILE,
        OUT / "FA_IMAGE_RUN_METADATA.json",
        OUT / "FA_COLOUR_RUN_METADATA.json",
        OUT / "FA_SLIDE_FIBROSIS_FRACTIONS.csv",
        OUT / "FA_HUE_CORRECTION_HASHES.csv",
        OUT / "FA_IMAGE_HASHES.csv",
        OUT / "FA_COLOUR_HASHES.csv",
        OUT / "FA_DATA_AUDIT.md",
        OUT / "FA_MASK_GATE.md",
        OUT / "FA_PREREG.md",
        OUT / "FA_DEVIATIONS.md",
        OUT / "FA_ALIGNMENT_REVIEW.csv",
        OUT / "FA_RUN_IMAGES.py",
        OUT / "FA_EXTRACT_COLOUR.py",
        OUT / "FA_ANALYZE.py",
        ROOT / "stage_G2" / "GENE2_DATA_AUDIT.md",
        ROOT / "stage2A_audit" / "PHASEB_REPORT.md",
        ROOT / "stage2A_audit" / "PHASEA_PERMISSION_RECORD.md",
        ROOT / "stage2A_audit" / "PHASEA_LICENCE_REGISTER.md",
        ROOT / "qc_collagen" / "review" / "reference_label_availability_summary.csv",
        ROOT / "qc_collagen" / "review" / "metadata_label_field_audit.csv",
        ROOT / "qc_collagen" / "sample_metadata_audit.csv",
    ] + matrix_paths
    mask_paths = [
        OUT / f"FA_MASK_{row['participant_id']}_{row['library_id']}.npz"
        for row in alignment
    ]
    missing_provenance = [
        path for path in input_paths + mask_paths if not path.is_file()
    ]
    if missing_provenance:
        raise FileNotFoundError(
            f"Required provenance file was not found: {missing_provenance[0]}"
        )
    if time.monotonic() >= deadline:
        raise TimeoutError("Stopped before the preregistered 90-minute analysis limit.")
    output_paths = [
        write_csv("FA_SPOT_ANALYSIS_FINAL.csv", data_rows),
        write_csv("FA_LIBRARY_GROUPS_FINAL.csv", group_summaries),
        write_csv("FA_EXPRESSION_ALIGNMENT_FINAL.csv", alignment_rows),
        write_csv("FA_GENE_AVAILABILITY_FINAL.csv", gene_available_rows),
        write_csv("FA_PER_PARTICIPANT_EFFECTS_FINAL.csv", effects_rows),
        write_csv("FA_PRIMARY_ENDPOINT_FINAL.csv", primary_rows),
        write_csv("FA_SECONDARY_HOLM_FINAL.csv", secondary_rows),
        write_csv("FA_CELL_DENSITY_SENSITIVITY_FINAL.csv", density_rows),
        write_csv("FA_CONTROL_MODELS_FINAL.csv", control_rows),
        write_csv("FA_LABEL_SHUFFLE_FINAL.csv", label_shuffle_rows),
        write_csv("FA_PANEL_SUMMARY_FINAL.csv", panel_rows),
        write_csv("FA_PANEL_PARTICIPANT_DATA_FINAL.csv", panel_participant_rows),
        write_csv("FA_COLOR_GROUP_SUMMARY_FINAL.csv", color_group_rows),
        write_csv("FA_COLOR_CONFOUND_CHECK_FINAL.csv", color_confound_rows),
        write_csv("FA_SEVERITY_CALIBRATION_FINAL.csv", severity_rows),
        write_csv("FA_ANALYSIS_DECISIONS_FINAL.csv", main_rows),
    ]
    if directory_size(OUT) >= MAX_OUTPUT_BYTES:
        raise RuntimeError("Stopped before the Stage FA analysis outputs exceed 8 GB.")

    hash_rows = []
    for path in input_paths:
        hash_rows.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "record_type": "input",
                "source_path": str(path),
                "sha256": sha256_file(path),
            }
        )
    for output in mask_paths:
        hash_rows.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "record_type": "input",
                "source_path": str(output),
                "sha256": sha256_file(output),
            }
        )
    for path in output_paths:
        hash_rows.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "record_type": "output",
                "source_path": str(path),
                "sha256": sha256_file(path),
            }
        )
    hashes_path = write_csv("FA_ANALYSIS_HASHES_FINAL.csv", hash_rows)
    metadata = {
        "analysis_label": ANALYSIS_LABEL,
        "mask_status": MASK_LABEL,
        "asset_status": ASSET_STATUS,
        "participants": len(participant_ids),
        "libraries": len(alignment),
        "matched_spots": len(data_rows),
        "stage1_participants": len({row["participant_id"] for row in alignment if row["source_set"] == "Stage 1"}),
        "stage1d_participants": len({row["participant_id"] for row in alignment if row["source_set"] == "Stage 1d"}),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "seeds": {
            "bootstrap_and_sign_flip": SEED,
            "label_shuffle_unet": SEED + 700,
            "label_shuffle_colour": SEED + 701,
        },
        "bootstraps": BOOTSTRAPS,
        "sign_flips": SIGN_FLIPS,
        "label_shuffles": LABEL_SHUFFLES,
        "command": "python -B D:\\patent\\stage_FA\\FA_ANALYZE.py",
        "started_at_utc": started_utc.isoformat(),
        "runtime_seconds": round(time.monotonic() - started, 3),
        "outputs_bytes": directory_size(OUT),
        "expression_files_read": [str(STAGE1_TARGETS)] + [str(path) for path in matrix_paths],
        "formal_primary_mask": "unet",
        "robustness_mask": "colour",
        "output_hash_manifest": str(hashes_path),
    }
    metadata_path = OUT / "FA_ANALYSIS_METADATA_FINAL.json"
    if metadata_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {metadata_path}")
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
