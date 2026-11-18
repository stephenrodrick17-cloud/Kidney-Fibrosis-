from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from collections import defaultdict
from pathlib import Path

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
from scipy.stats import binomtest

ROOT = Path(r"D:\patent\stage_PLAUS")
DATA = Path(r"D:\patent\data")
FA = Path(r"D:\patent\stage_FA")
SPOT_TABLE = FA / "FA_SPOT_ANALYSIS_FINAL.csv"
PER_EFFECT = FA / "FA_PER_PARTICIPANT_EFFECTS_FINAL.csv"
CHECKPOINT = Path(r"D:\patent\stage2A_audit\renfast_baseline_run\checkpoint_best.pt")
EXPECTED_CHECKPOINT = "674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb"
SEED = 20261118
BOOTSTRAPS = 10_000

CONTROLS = (
    "ACTB", "GAPDH", "RPL13A", "RPLP0", "RPS18", "RPS27A",
    "UBA52", "TUBB", "HPRT1", "PPIA", "B2M", "TBP", "PGK1",
    "LDHA", "SDHA", "GUSB", "HMBS", "RPL19", "RPL27", "EEF1A1",
)
LOW_GENES = ("SLC34A1", "LRP2", "UMOD", "SLC12A1")
HIGH_GENES = (
    "COL4A1", "COL5A1", "COL6A1", "FAP", "POSTN", "PDGFRB",
    "VIM", "PTPRC", "C1QA", "C1QB", "C1QC", "CD68",
)
MODULE = ("COL1A1", "COL1A2", "COL3A1")
TARGETS = ("COL1A1", "COL1A2", "COL3A1", "FN1", "TGFB1", "CCN2", "ACTA2", "MMP2", "TIMP1")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_checkpoint() -> str:
    if not CHECKPOINT.is_file():
        raise RuntimeError("Frozen checkpoint missing.")
    observed = sha256_file(CHECKPOINT)
    if observed != EXPECTED_CHECKPOINT:
        raise RuntimeError("Frozen checkpoint SHA-256 mismatch.")
    return observed


def fit_effect(rows: list[dict[str, object]], target: str) -> dict[str, object]:
    selected = [row for row in rows if str(row.get("group", "")) in ("low", "high")]
    y = np.asarray([float(row[target]) for row in selected], dtype=np.float64)
    if len(y) == 0 or np.any(~np.isfinite(y)):
        return {"valid": False, "reason": "target unavailable"}
    high = np.asarray([1.0 if row["group"] == "high" else 0.0 for row in selected])
    if len(np.unique(high)) != 2:
        return {"valid": False, "reason": "both groups required"}
    columns = [np.ones(len(selected))]
    log_library = np.asarray([float(row["log_library_size"]) for row in selected])
    tissue_fraction = np.asarray([float(row["tissue_fraction"]) for row in selected])
    depth = np.asarray([float(row.get("tissue_depth_um", np.nan)) for row in selected])
    if np.all(np.isfinite(depth)):
        columns.append(depth)
    columns.extend((log_library, tissue_fraction))
    design = np.column_stack(columns)
    keep = [0] + [
        index for index in range(1, design.shape[1])
        if np.ptp(design[:, index]) > 0
    ]
    design = design[:, keep]
    design = np.column_stack((design, high))
    if len(y) <= design.shape[1]:
        return {"valid": False, "reason": "too few spots"}
    coeff, _, rank, _ = np.linalg.lstsq(design, y, rcond=None)
    if rank != design.shape[1]:
        return {"valid": False, "reason": "rank deficient"}
    return {"valid": True, "effect": float(coeff[-1])}


def participant_effects(rows: list[dict[str, object]], target: str) -> dict[str, float]:
    by_participant: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_participant[str(row["participant_id"])].append(row)
    effects = {}
    for participant, selected in by_participant.items():
        fit = fit_effect(selected, target)
        if fit["valid"]:
            effects[participant] = float(fit["effect"])
    return effects


def participant_bootstrap(effects: dict[str, float], seed: int) -> tuple[float, float, float]:
    names = sorted(effects)
    values = np.asarray([effects[name] for name in names], dtype=np.float64)
    mean = float(values.mean())
    rng = np.random.default_rng(seed)
    estimates = []
    for _ in range(BOOTSTRAPS):
        sampled = rng.choice(len(names), size=len(names), replace=True)
        estimates.append(float(values[sampled].mean()))
    low, high = np.quantile(np.asarray(estimates), [0.025, 0.975])
    return mean, float(low), float(high)


with SPOT_TABLE.open("r", encoding="utf-8-sig", newline="") as handle:
    spot_rows = list(csv.DictReader(handle))

checkpoint_hash = verify_checkpoint()

target_participant_effects = {
    target: participant_effects(
        [
            {
                **row,
                "group": row["unet_group"],
                "target_value": float(row[target]),
            }
            for row in spot_rows
            if target in row
        ],
        "target_value",
    )
    for target in ("collagen_module",) + TARGETS
}

# The spot table already stores standardized target values and group assignments.
participant_effect_values: dict[str, dict[str, float]] = defaultdict(dict)
for row in spot_rows:
    participant_effect_values[str(row["participant_id"])]

for row in spot_rows:
    participant = str(row["participant_id"])
    participant_effect_values[participant]["collagen_module"] = float(row["collagen_module"])

collagen_effects = {}
for participant in sorted(set(row["participant_id"] for row in spot_rows)):
    selected = [row for row in spot_rows if row["participant_id"] == participant]
    prepared = [
        {
            "participant_id": participant,
            "group": row["unet_group"],
            "collagen_module": float(row["collagen_module"]),
            "log_library_size": float(row["log_library_size"]),
            "tissue_fraction": float(row["tissue_fraction"]),
            "tissue_depth_um": float(row["tissue_depth_um"]),
        }
        for row in selected
    ]
    fit = fit_effect(prepared, "collagen_module")
    if fit["valid"]:
        collagen_effects[participant] = float(fit["effect"])

# Use the final Stage FA unet/collagen participant effects as the primary
# preregistered effect source. This avoids a dependent re-fit from spot rows.
per_effect_table = FA / "FA_PER_PARTICIPANT_EFFECTS_FINAL.csv"
saved_collagen_effects = {}
with per_effect_table.open("r", encoding="utf-8-sig", newline="") as handle:
    for row in csv.DictReader(handle):
        if (
            row["mask"] == "unet"
            and row["target"] == "collagen_module"
            and row["fit_status"] == "PASS"
        ):
            saved_collagen_effects[row["participant_id"]] = float(
                row["participant_effect_high_minus_low"]
            )
if saved_collagen_effects:
    collagen_effects = saved_collagen_effects

collagen_mean, collagen_ci_low, collagen_ci_high = participant_bootstrap(
    collagen_effects, SEED
)

control_effects: dict[str, float] = {}
panel_effects: dict[str, float] = {}
control_participants = set()

def find_full_matrix_for_library(participant: str, library: str) -> tuple[str, Path] | None:
    participant_dir = DATA / participant
    if not participant_dir.is_dir():
        return None
    candidates = []
    for h5 in participant_dir.rglob("filtered_feature_bc_matrix.h5"):
        candidates.append(h5)
    if not candidates:
        return None
    spot_barcodes = {
        row["barcode"]
        for row in spot_rows
        if row["participant_id"] == participant and row["library_id"] == library
    }
    best = None
    best_overlap = -1
    for h5 in candidates:
        try:
            with h5py.File(h5, "r") as handle:
                barcodes = [
                    value.decode("utf-8") if isinstance(value, bytes) else str(value)
                    for value in handle["matrix"]["barcodes"][:]
                ]
            overlap = len(set(barcodes) & spot_barcodes)
        except Exception:
            continue
        if overlap > best_overlap:
            best_overlap = overlap
            best = h5
    if best is None or best_overlap == 0:
        return None
    return library, best


for participant in sorted(set(row["participant_id"] for row in spot_rows)):
    libraries = sorted({
        row["library_id"]
        for row in spot_rows
        if row["participant_id"] == participant
    })
    matched = []
    for library in libraries:
        found = find_full_matrix_for_library(participant, library)
        if found:
            matched.append(found)
    if not matched:
        continue
    control_participants.add(participant)
    per_library_effects: dict[str, list[float]] = defaultdict(list)
    for library, h5 in matched:
        spot_library = [
            row for row in spot_rows
            if row["participant_id"] == participant and row["library_id"] == library
        ]
        if not spot_library:
            continue
        barcode_to_spot = {row["barcode"]: row for row in spot_library}
        with h5py.File(h5, "r") as handle:
            barcodes = [
                value.decode("utf-8") if isinstance(value, bytes) else str(value)
                for value in handle["matrix"]["barcodes"][:]
            ]
            names = [
                value.decode("utf-8") if isinstance(value, bytes) else str(value)
                for value in handle["matrix"]["features"]["name"][:]
            ]
            matrix = handle["matrix"]["data"][:]
            indices = handle["matrix"]["indices"][:]
            indptr = handle["matrix"]["indptr"][:]
            shape = tuple(int(value) for value in handle["matrix"]["shape"][:])
        import scipy.sparse
        sparse = scipy.sparse.csc_matrix((matrix, indices, indptr), shape=shape).tocsr()
        name_to_rows: dict[str, list[int]] = defaultdict(list)
        for index, name in enumerate(names):
            name_to_rows[name.upper()].append(index)
        gene_names = CONTROLS + LOW_GENES + HIGH_GENES
        gene_vectors: dict[str, np.ndarray] = {}
        for gene in gene_names:
            rows_for_gene = name_to_rows.get(gene, [])
            if not rows_for_gene:
                continue
            gene_vectors[gene] = np.asarray(
                sparse[rows_for_gene, :].sum(axis=0)
            ).ravel().astype(np.float64)
        gene_expression_rows = [
            index for index, feature_type in enumerate(
                [
                    value.decode("utf-8") if isinstance(value, bytes) else str(value)
                    for value in handle["matrix"]["features"]["feature_type"][:]
                ]
            )
            if feature_type.lower() == "gene expression"
        ] if False else list(range(sparse.shape[0]))
        library_sizes = np.asarray(sparse.sum(axis=0)).ravel().astype(np.float64)
        for gene, raw in gene_vectors.items():
            if len(raw) != len(barcodes):
                continue
            log_values = np.log1p(10_000 * raw / np.maximum(library_sizes, 1))
            standardized = (log_values - log_values.mean()) / (
                log_values.std(ddof=0) if log_values.std(ddof=0) > 0 else 1
            )
            for barcode, value in zip(barcodes, standardized):
                if barcode not in barcode_to_spot:
                    continue
                barcode_to_spot[barcode][f"gene_{gene}"] = float(value)
        for gene in gene_names:
            prepared = []
            for row in spot_library:
                key = f"gene_{gene}"
                if key not in row:
                    continue
                prepared.append({
                    "group": row["unet_group"],
                    "log_library_size": float(row["log_library_size"]),
                    "tissue_fraction": float(row["tissue_fraction"]),
                    "tissue_depth_um": float(row["tissue_depth_um"]),
                    "effect_target": float(row[key]),
                })
            fit = fit_effect(prepared, "effect_target")
            if fit["valid"]:
                per_library_effects[gene].append(float(fit["effect"]))
    for gene, effects in per_library_effects.items():
        if not effects:
            continue
        mean_effect = float(np.mean(effects))
        if gene in CONTROLS:
            control_effects.setdefault(gene, {})
        if gene in LOW_GENES or gene in HIGH_GENES:
            panel_effects.setdefault(gene, {})

# Recompute control/panel effects across participant-library sets.
control_effect_participant: dict[str, list[float]] = defaultdict(list)
panel_effect_participant: dict[str, list[float]] = defaultdict(list)

for participant in sorted(control_participants):
    libraries = sorted({
        row["library_id"] for row in spot_rows if row["participant_id"] == participant
    })
    for library in libraries:
        found = find_full_matrix_for_library(participant, library)
        if not found:
            continue
        _, h5 = found
        spot_library = [
            row for row in spot_rows
            if row["participant_id"] == participant and row["library_id"] == library
        ]
        barcode_to_spot = {row["barcode"]: row for row in spot_library}
        with h5py.File(h5, "r") as handle:
            barcodes = [
                value.decode("utf-8") if isinstance(value, bytes) else str(value)
                for value in handle["matrix"]["barcodes"][:]
            ]
            names = [
                value.decode("utf-8") if isinstance(value, bytes) else str(value)
                for value in handle["matrix"]["features"]["name"][:]
            ]
            matrix = handle["matrix"]["data"][:]
            indices = handle["matrix"]["indices"][:]
            indptr = handle["matrix"]["indptr"][:]
            shape = tuple(int(value) for value in handle["matrix"]["shape"][:])
        sparse = scipy.sparse.csc_matrix((matrix, indices, indptr), shape=shape).tocsr()
        name_to_rows = defaultdict(list)
        for index, name in enumerate(names):
            name_to_rows[name.upper()].append(index)
        library_sizes = np.asarray(sparse.sum(axis=0)).ravel().astype(np.float64)
        for gene in CONTROLS + LOW_GENES + HIGH_GENES:
            gene_rows = name_to_rows.get(gene, [])
            if not gene_rows:
                continue
            raw = np.asarray(sparse[gene_rows, :].sum(axis=0)).ravel().astype(np.float64)
            log_values = np.log1p(10_000 * raw / np.maximum(library_sizes, 1))
            sd = log_values.std(ddof=0)
            standardized = (log_values - log_values.mean()) / (sd if sd > 0 else 1)
            prepared = []
            for barcode, value in zip(barcodes, standardized):
                row = barcode_to_spot.get(barcode)
                if row is None:
                    continue
                prepared.append({
                    "group": row["unet_group"],
                    "log_library_size": float(row["log_library_size"]),
                    "tissue_fraction": float(row["tissue_fraction"]),
                    "tissue_depth_um": float(row["tissue_depth_um"]),
                    "effect_target": float(value),
                })
            fit = fit_effect(prepared, "effect_target")
            if fit["valid"]:
                if gene in CONTROLS:
                    control_effect_participant[gene].append(float(fit["effect"]))
                else:
                    panel_effect_participant[gene].append(float(fit["effect"]))

control_summary = {}
for gene in CONTROLS:
    values = control_effect_participant.get(gene, [])
    if not values:
        control_summary[gene] = {"n_participant_libraries": 0, "mean_effect": None}
    else:
        control_summary[gene] = {
            "n_participant_libraries": len(values),
            "mean_effect": float(np.mean(values)),
        }

available_control_effects = [
    item["mean_effect"] for item in control_summary.values()
    if item["mean_effect"] is not None
]
control_p95 = float(np.percentile(available_control_effects, 95)) if available_control_effects else float("nan")
collagen_below_or_above = (
    sum(value < collagen_mean for value in available_control_effects)
    if available_control_effects
    else 0
)
collagen_rank = (
    float(collagen_below_or_above + 1) / len(available_control_effects)
    if available_control_effects
    else float("nan")
)

panel_summary = {}
for gene in LOW_GENES + HIGH_GENES:
    values = panel_effect_participant.get(gene, [])
    mean_effect = float(np.mean(values)) if values else None
    expected = "lower" if gene in LOW_GENES else "higher"
    observed = (
        "lower" if mean_effect is not None and mean_effect < 0
        else "higher" if mean_effect is not None and mean_effect > 0
        else "no clear direction"
    )
    panel_summary[gene] = {
        "n_participant_libraries": len(values),
        "mean_effect": mean_effect,
        "expected_direction": expected,
        "observed_direction": observed,
        "expected_sign_agrees": (
            (expected == "lower" and observed == "lower")
            or (expected == "higher" and observed == "higher")
        ) if mean_effect is not None else "NOT AVAILABLE",
    }

available_agreements = [
    bool(item["expected_sign_agrees"])
    for item in panel_summary.values()
    if item["expected_sign_agrees"] != "NOT AVAILABLE"
]
sign_agreement_fraction = (
    float(np.mean(available_agreements)) if available_agreements else float("nan")
)
binomial = (
    binomtest(
        sum(available_agreements),
        len(available_agreements),
        p=0.5,
        alternative="greater",
    )
    if available_agreements
    else None
)

# Image-colour quartiles using participant mean hue.
participant_hue = {}
for participant in sorted(set(row["participant_id"] for row in spot_rows)):
    selected = [row for row in spot_rows if row["participant_id"] == participant]
    hue_values = [float(row["mean_hue"]) for row in selected]
    participant_hue[participant] = float(np.mean(hue_values))
ordered = sorted(participant_hue)
hue_values = np.asarray([participant_hue[name] for name in ordered])
boundaries = np.quantile(hue_values, [0.25, 0.5, 0.75])
quartile_rank = np.searchsorted(boundaries, hue_values, side="right")
quartile_rank = np.clip(quartile_rank, 0, 3).astype(int)
quartile_participants = defaultdict(list)
for name, quartile in zip(ordered, quartile_rank):
    quartile_participants[int(quartile)].append(name)

quartile_summary = []
for quartile in range(4):
    names = quartile_participants[quartile]
    values = [collagen_effects[name] for name in names if name in collagen_effects]
    mean = float(np.mean(values)) if values else None
    ci = participant_bootstrap({name: collagen_effects[name] for name in names if name in collagen_effects}, SEED + quartile) if len(values) >= 2 else (None, None, None)
    quartile_summary.append({
        "quartile": quartile + 1,
        "n_participants": len(names),
        "too_small_to_judge": len(names) < 5,
        "mean_collagen_effect": mean,
        "ci95_low": ci[1],
        "ci95_high": ci[2],
        "direction": "higher" if mean is not None and mean > 0 else "lower" if mean is not None and mean < 0 else "NOT AVAILABLE",
    })

# Leave-one-participant-out.
loo_effects = {}
for removed in sorted(collagen_effects):
    remaining = {name: value for name, value in collagen_effects.items() if name != removed}
    loo_effects[removed] = participant_bootstrap(remaining, SEED)[0]
loo_min = float(min(loo_effects.values()))
loo_max = float(max(loo_effects.values()))
loo_keeps_direction = (loo_min > 0) if collagen_mean > 0 else (loo_max < 0)

# Library-size exclusion.
library_sizes = np.asarray([float(row["library_size_umi"]) for row in spot_rows])
library_threshold = float(np.percentile(library_sizes, 25))
low_library_excluded = [
    row for row in spot_rows if float(row["library_size_umi"]) >= library_threshold
]
low_library_effects = participant_effects(
    [
        {
            "participant_id": row["participant_id"],
            "group": row["unet_group"],
            "target_value": float(row["collagen_module"]),
            "log_library_size": float(row["log_library_size"]),
            "tissue_fraction": float(row["tissue_fraction"]),
            "tissue_depth_um": float(row["tissue_depth_um"]),
        }
        for row in low_library_excluded
    ],
    "target_value",
)
library_exclusion_mean = participant_bootstrap(low_library_effects, SEED)[0]

# Mask sensitivity cells.
sensitivity_cells = [
    {"setting": "threshold 0.3", "status": "NOT AVAILABLE", "reason": "saved probability map absent"},
    {"setting": "threshold 0.5 saved mask", "status": "available", "mean_effect": collagen_mean,
     "ci95_low": collagen_ci_low, "ci95_high": collagen_ci_high},
    {"setting": "threshold 0.7", "status": "NOT AVAILABLE", "reason": "saved probability map absent"},
]
for setting in ("erosion 2 pixels", "dilation 2 pixels"):
    sensitivity_cells.append({"setting": setting, "status": "NOT AVAILABLE", "reason": "mask morphology inputs not saved"})
for multiplier in (0.75, 1.25):
    sensitivity_cells.append({
        "setting": f"footprint {multiplier:.2f} standard",
        "status": "NOT AVAILABLE",
        "reason": "spot rescoring inputs not saved",
    })
sensitivity_cells.append({"setting": "quartile groups", "status": "NOT AVAILABLE",
                          "reason": "spot coordinates and mask rescoring not available for a full sensitivity run"})

available_grid_effects = [
    cell for cell in sensitivity_cells
    if cell["status"] == "available" and cell.get("mean_effect") is not None
]
grid_direction_fraction = (
    float(np.mean([
        (collagen_mean > 0) == (cell["mean_effect"] > 0)
        for cell in available_grid_effects
    ]))
    if available_grid_effects else float("nan")
)

stain_quartile_direction_count = sum(
    item["direction"] == ("higher" if collagen_mean > 0 else "lower")
    and not item["too_small_to_judge"]
    for item in quartile_summary
)

# Interpretation rules.
rule_1 = (
    collagen_mean is not None
    and len(available_control_effects) > 0
    and collagen_mean > control_p95
)
rule_2 = sign_agreement_fraction >= 0.75
rule_3 = grid_direction_fraction >= 0.90 and stain_quartile_direction_count >= 3
spatial_permutation_available = False
rule_4 = (
    spatial_permutation_available
    and loo_keeps_direction
    and library_exclusion_mean * collagen_mean > 0
)
failed_rules = []
if not rule_1:
    failed_rules.append("1: collagen module not above 95th percentile of negative-control effects")
if not rule_2:
    failed_rules.append("2: fewer than 75% of expected-direction genes show expected sign")
if not rule_3:
    failed_rules.append("3: sensitivity direction or at least 3 stain quartiles failed")
if not rule_4:
    failed_rules.append("4: leave-one-out, spatial permutation or library-exclusion robustness failed")
overall = "PLAUSIBLE" if not failed_rules else "CONCERN"

control_csv = ROOT / "PLAUS_NEGATIVE_CONTROL_EFFECTS.csv"
with control_csv.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=[
        "gene", "n_participant_libraries", "mean_effect"
    ])
    writer.writeheader()
    for gene in CONTROLS:
        writer.writerow({
            "gene": gene,
            **control_summary[gene],
        })

panel_csv = ROOT / "PLAUS_EXPECTED_DIRECTION.csv"
with panel_csv.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=[
        "gene", "n_participant_libraries", "mean_effect",
        "expected_direction", "observed_direction", "expected_sign_agrees",
    ])
    writer.writeheader()
    for gene in LOW_GENES + HIGH_GENES:
        writer.writerow({"gene": gene, **panel_summary[gene]})

with (ROOT / "PLAUS_MASK_SENSITIVITY.csv").open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=[
        "setting", "status", "mean_effect", "ci95_low", "ci95_high", "reason"
    ])
    writer.writeheader()
    for cell in sensitivity_cells:
        writer.writerow({
            "setting": cell["setting"],
            "status": cell["status"],
            "mean_effect": cell.get("mean_effect", "NOT AVAILABLE"),
            "ci95_low": cell.get("ci95_low", "NOT AVAILABLE"),
            "ci95_high": cell.get("ci95_high", "NOT AVAILABLE"),
            "reason": cell.get("reason", ""),
        })

with (ROOT / "PLAUS_STAIN_QUARTILES.csv").open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(quartile_summary[0]))
    writer.writeheader()
    writer.writerows(quartile_summary)

summary = {
    "label": "EXPLORATORY, NOT CONFIRMATORY. UNVALIDATED MASKS.",
    "checkpoint_sha256": checkpoint_hash,
    "n_participants_in_primary": len(collagen_effects),
    "n_full_matrix_participants": len(control_participants),
    "collagen_module": {
        "mean_effect": collagen_mean,
        "ci95_low": collagen_ci_low,
        "ci95_high": collagen_ci_high,
    },
    "negative_controls": {
        "n_available": len(available_control_effects),
        "95th_percentile": control_p95,
        "collagen_rank_fraction": collagen_rank,
        "collagen_above_95th_percentile": rule_1,
    },
    "expected_direction": {
        "n_available": len(available_agreements),
        "sign_agreement_fraction": sign_agreement_fraction,
        "binomial_test_alternative_greater_than_half_p": (
            float(binomial.pvalue) if binomial is not None else None
        ),
    },
    "mask_sensitivity": {
        "available_direction_fraction": grid_direction_fraction,
        "n_available_cells": len(available_grid_effects),
    },
    "stain_quartiles": quartile_summary,
    "leave_one_out": {
        "range_low": loo_min,
        "range_high": loo_max,
        "keeps_direction": loo_keeps_direction,
    },
    "library_exclusion": {
        "25th_percentile_library_size": library_threshold,
        "mean_collagen_effect": library_exclusion_mean,
    },
    "spatial_permutation": {
        "status": "NOT AVAILABLE",
        "reason": "saved spot table lacks array-coordinate blocks for the 40-participant combined run",
    },
    "tissue_edge_exclusion": {
        "status": "NOT AVAILABLE",
        "reason": "saved spot table lacks a complete tissue-edge distance field",
    },
    "interpretation": {
        "overall": overall,
        "failed_rules": failed_rules,
        "rule_status": {
            "1_negative_control": rule_1,
            "2_expected_direction": rule_2,
            "3_sensitivity_and_stain": rule_3,
            "4_robustness": rule_4,
        },
    },
    "environment": {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "h5py": h5py.__version__,
        "matplotlib": matplotlib.__version__,
    },
}
(ROOT / "PLAUS_RESULTS.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

genes = list(control_summary)
effects = [
    control_summary[gene]["mean_effect"]
    if control_summary[gene]["mean_effect"] is not None
    else 0
    for gene in genes
]
fig, ax = plt.subplots(figsize=(9, 5))
ax.boxplot([effects], tick_labels=["Negative controls"])
ax.axhline(collagen_mean, color="tab:red", linestyle="--", label=f"Collagen module {collagen_mean:.3f}")
ax.set_ylabel("Participant-library mean effect")
ax.set_title("Negative-control effect distribution")
ax.legend()
fig.tight_layout()
fig.savefig(ROOT / "PLAUS_NEGATIVE_CONTROL_EFFECTS.png", dpi=180)
plt.close(fig)

panel_genes = list(LOW_GENES + HIGH_GENES)
panel_values = [
    panel_summary[gene]["mean_effect"]
    if panel_summary[gene]["mean_effect"] is not None
    else 0.0
    for gene in panel_genes
]
fig, ax = plt.subplots(figsize=(10, 6))
colors = ["tab:blue" if gene in LOW_GENES else "tab:red" for gene in panel_genes]
ax.barh(range(len(panel_genes)), panel_values, color=colors)
ax.axvline(0, color="black", linewidth=1)
ax.set_yticks(range(len(panel_genes)), panel_genes)
ax.invert_yaxis()
ax.set_xlabel("Participant-library mean effect")
ax.set_title("Expected-direction gene panel")
fig.tight_layout()
fig.savefig(ROOT / "PLAUS_EXPECTED_DIRECTION_EFFECTS.png", dpi=180)
plt.close(fig)

print(json.dumps(summary, indent=2))
