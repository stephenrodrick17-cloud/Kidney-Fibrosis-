from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy
from scipy.stats import spearmanr

ROOT = Path(r"D:\patent")
OUT = ROOT / "stage_FA"
ANALYSIS_LABEL = "EXPLORATORY, NOT CONFIRMATORY"
MASK_LABEL = "UNVALIDATED MASKS"
ASSET_STATUS = "RESEARCH-ONLY"
SEED = 20261117
BOOTSTRAPS = 10_000
TOLERANCE = 1e-10
CHECKPOINT_SHA256 = "674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def add_check(
    checks: list[dict[str, object]],
    name: str,
    passed: bool,
    observed: object,
    expected: object,
    note: str,
) -> None:
    checks.append(
        {
            "analysis_label": ANALYSIS_LABEL,
            "mask_status": MASK_LABEL,
            "asset_status": ASSET_STATUS,
            "check": name,
            "status": "PASS" if passed else "FAIL",
            "observed": json.dumps(observed, sort_keys=True),
            "expected": json.dumps(expected, sort_keys=True),
            "note": note,
        }
    )


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {path}")
    if not rows:
        raise ValueError(f"Refusing to write an empty verification file: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def participant_fit(rows: list[dict[str, str]], mask: str) -> float:
    selected = [
        row
        for row in rows
        if row[f"{mask}_group"] in ("low", "high")
    ]
    if not selected:
        raise ValueError("Participant has no low/high rows.")
    columns = [
        np.ones(len(selected), dtype=np.float64),
        np.asarray([float(row["tissue_depth_um"]) for row in selected]),
        np.asarray([float(row["log_library_size"]) for row in selected]),
        np.asarray([float(row["tissue_fraction"]) for row in selected]),
    ]
    libraries = sorted({row["library_id"] for row in selected})
    for library in libraries[1:]:
        columns.append(
            np.asarray([float(row["library_id"] == library) for row in selected])
        )
    design_base = np.column_stack(columns)
    keep = [0] + [
        index
        for index in range(1, design_base.shape[1])
        if float(np.ptp(design_base[:, index])) > 0.0
    ]
    design_base = design_base[:, keep]
    high = np.asarray(
        [float(row[f"{mask}_group"] == "high") for row in selected],
        dtype=np.float64,
    )
    design = np.column_stack((design_base, high))
    target = np.asarray([float(row["collagen_module"]) for row in selected])
    coefficient, _, rank, _ = np.linalg.lstsq(design, target, rcond=None)
    if rank != design.shape[1]:
        raise ValueError("Independent participant regression is rank deficient.")
    return float(coefficient[-1])


def main() -> None:
    started = time.monotonic()
    started_at = datetime.now(timezone.utc)
    final = "_FINAL"
    spot_path = OUT / f"FA_SPOT_ANALYSIS{final}.csv"
    effect_path = OUT / f"FA_PER_PARTICIPANT_EFFECTS{final}.csv"
    primary_path = OUT / f"FA_PRIMARY_ENDPOINT{final}.csv"
    panel_path = OUT / f"FA_PANEL_SUMMARY{final}.csv"
    panel_people_path = OUT / f"FA_PANEL_PARTICIPANT_DATA{final}.csv"
    alignment_path = OUT / f"FA_EXPRESSION_ALIGNMENT{final}.csv"
    groups_path = OUT / f"FA_LIBRARY_GROUPS{final}.csv"
    slide_path = OUT / "FA_SLIDE_FIBROSIS_FRACTIONS_FINAL.csv"
    image_hash_path = OUT / "FA_IMAGE_HASHES.csv"
    analysis_hash_path = OUT / "FA_ANALYSIS_HASHES_FINAL.csv"
    verification_path = OUT / "FA_VERIFICATION_FINAL.csv"
    verification_hash_path = OUT / "FA_VERIFICATION_HASHES_FINAL.csv"
    metadata_path = OUT / "FA_VERIFICATION_METADATA_FINAL.json"
    planned = (verification_path, verification_hash_path, metadata_path)
    if any(path.exists() for path in planned):
        raise FileExistsError("A verification output already exists; refusing to overwrite.")

    checks: list[dict[str, object]] = []
    spots = read_csv(spot_path)
    effects = read_csv(effect_path)
    primary = read_csv(primary_path)
    panel = read_csv(panel_path)
    panel_people = read_csv(panel_people_path)
    alignment = read_csv(alignment_path)
    group_rows = read_csv(groups_path)
    slides = read_csv(slide_path)
    analysis_hashes = read_csv(analysis_hash_path)
    image_hashes = read_csv(image_hash_path)

    for name, rows in (
        ("spot predictions", spots),
        ("participant effects", effects),
        ("primary summary", primary),
        ("panel summary", panel),
        ("panel participant data", panel_people),
        ("expression alignment", alignment),
        ("library groups", group_rows),
    ):
        labels_ok = bool(rows) and all(
            row.get("analysis_label") == ANALYSIS_LABEL
            and row.get("mask_status") == MASK_LABEL
            for row in rows
        )
        add_check(
            checks,
            f"{name} labels",
            labels_ok,
            len(rows),
            f"all rows labelled {ANALYSIS_LABEL} / {MASK_LABEL}",
            "Every final analysis table must carry both required labels.",
        )

    spot_keys = [
        (row["participant_id"], row["library_id"], row["barcode"])
        for row in spots
    ]
    key_unique = len(spot_keys) == len(set(spot_keys))
    participant_ids = {row["participant_id"] for row in spots}
    library_to_participant: dict[str, set[str]] = {}
    for row in spots:
        library_to_participant.setdefault(row["library_id"], set()).add(
            row["participant_id"]
        )
    library_mapping_ok = all(len(values) == 1 for values in library_to_participant.values())
    add_check(
        checks,
        "full spot-key uniqueness",
        key_unique,
        len(spot_keys),
        f"{len(set(spot_keys))} unique participant/library/barcode keys",
        "The full key includes participant, library, and barcode.",
    )
    add_check(
        checks,
        "participant and library mapping",
        len(participant_ids) == 40
        and len(library_to_participant) == 41
        and library_mapping_ok,
        {
            "participants": len(participant_ids),
            "libraries": len(library_to_participant),
            "libraries_with_multiple_participants": sum(
                len(values) != 1 for values in library_to_participant.values()
            ),
        },
        {"participants": 40, "libraries": 41, "cross-participant_libraries": 0},
        "A library is assigned to one participant; 28-12265 retains both libraries.",
    )

    groups_by_mask: dict[str, list[str]] = {}
    for mask in ("unet", "colour"):
        groups_by_mask[mask] = [row[f"{mask}_group"] for row in spots]
        group_counts = {
            label: groups_by_mask[mask].count(label)
            for label in ("low", "middle", "high", "excluded")
        }
        add_check(
            checks,
            f"{mask} spot role exclusivity",
            sum(group_counts.values()) == len(spots)
            and group_counts["excluded"] == 0,
            group_counts,
            f"exactly one low/middle/high role per spot; {len(spots)} assigned",
            "There are no train/test folds in this association analysis. Each spot has one tertile role per mask.",
        )
    group_keys = {
        (row["participant_id"], row["library_id"]): row for row in group_rows
    }
    add_check(
        checks,
        "per-library group eligibility",
        len(group_rows) == 82
        and all(row["library_excluded"].lower() == "false" for row in group_rows),
        {
            "mask_library_rows": len(group_rows),
            "excluded_libraries": sum(
                row["library_excluded"].lower() != "false" for row in group_rows
            ),
        },
        {"mask_library_rows": 82, "excluded_libraries": 0},
        "Both masks have 41 eligible libraries; each library is a separate mask row.",
    )
    add_check(
        checks,
        "expression-image alignment",
        len(alignment) == 41
        and all(row["status"] == "PASS" for row in alignment)
        and all(
            int(row["missing_expression_keys"]) == 0
            and int(row["extra_expression_keys"]) == 0
            for row in alignment
        ),
        {
            "libraries": len(alignment),
            "pass": sum(row["status"] == "PASS" for row in alignment),
            "missing_keys": sum(int(row["missing_expression_keys"]) for row in alignment),
            "extra_keys": sum(int(row["extra_expression_keys"]) for row in alignment),
        },
        {"libraries": 41, "pass": 41, "missing_keys": 0, "extra_keys": 0},
        "Rechecked using the participant+library+barcode key.",
    )

    unet_effect_rows = [
        row
        for row in effects
        if row["mask"] == "unet"
        and row["target"] == "collagen_module"
        and row["fit_status"] == "PASS"
    ]
    saved_effects = {
        row["participant_id"]: float(row["participant_effect_high_minus_low"])
        for row in unet_effect_rows
    }
    spot_effects: dict[str, float] = {}
    by_participant: dict[str, list[dict[str, str]]] = {}
    for row in spots:
        by_participant.setdefault(row["participant_id"], []).append(row)
    for participant, rows in by_participant.items():
        spot_effects[participant] = participant_fit(rows, "unet")
    effect_keys_ok = set(saved_effects) == set(spot_effects) == participant_ids
    max_effect_diff = max(
        abs(saved_effects[participant] - spot_effects[participant])
        for participant in spot_effects
    )
    add_check(
        checks,
        "independent participant regression",
        effect_keys_ok and max_effect_diff <= TOLERANCE,
        {
            "participants_recomputed": len(spot_effects),
            "maximum_absolute_effect_difference": max_effect_diff,
        },
        {"participants_recomputed": 40, "maximum_absolute_effect_difference": f"<= {TOLERANCE}"},
        "Recomputed high-minus-low collagen-module coefficients directly from saved spot predictions.",
    )

    values = np.asarray(
        [spot_effects[participant] for participant in sorted(spot_effects)],
        dtype=np.float64,
    )
    mean_effect = float(values.mean())
    rng = np.random.default_rng(SEED)
    bootstrap_indices = rng.integers(0, len(values), size=(BOOTSTRAPS, len(values)))
    bootstrap_means = values[bootstrap_indices].mean(axis=1)
    ci_low, ci_high = (
        float(value)
        for value in np.quantile(bootstrap_means, [0.025, 0.975])
    )
    saved_primary = next(row for row in primary if row["mask"] == "unet")
    saved_mean = float(saved_primary["mean_high_minus_low_effect"])
    saved_low = float(saved_primary["participant_bootstrap_ci95_low"])
    saved_high = float(saved_primary["participant_bootstrap_ci95_high"])
    add_check(
        checks,
        "headline primary mean",
        abs(mean_effect - saved_mean) <= TOLERANCE,
        mean_effect,
        saved_mean,
        "Mean of the 40 independently recomputed participant effects.",
    )
    add_check(
        checks,
        "headline primary bootstrap lower bound",
        abs(ci_low - saved_low) <= TOLERANCE,
        ci_low,
        saved_low,
        "Recomputed with 10,000 participant resamples and seed 20261117.",
    )
    add_check(
        checks,
        "headline primary bootstrap upper bound",
        abs(ci_high - saved_high) <= TOLERANCE,
        ci_high,
        saved_high,
        "Recomputed with 10,000 participant resamples and seed 20261117.",
    )

    unet_panel = next(
        row
        for row in panel
        if row["mask"] == "unet" and row["target"] == "collagen_module"
    )
    panel_rows = [
        row for row in panel_people if row["mask"] == "unet"
    ]
    panel_people_ids = [row["participant_id"] for row in panel_rows]
    fibrosis = np.asarray(
        [float(row["mean_fibrosis_percent_tissue"]) for row in panel_rows],
        dtype=np.float64,
    )
    panel_values = np.asarray(
        [float(row["pseudobulk_collagen_module"]) for row in panel_rows],
        dtype=np.float64,
    )
    covariates = np.asarray(
        [
            [
                float(row["mean_log_library_size"]),
                float(row["mean_tissue_fraction"]),
            ]
            for row in panel_rows
        ],
        dtype=np.float64,
    )
    design = np.column_stack((np.ones(len(panel_values)), covariates))
    beta, _, _, _ = np.linalg.lstsq(design, panel_values, rcond=None)
    residual = panel_values - design @ beta
    panel_rho = float(spearmanr(fibrosis, residual).statistic)
    panel_saved_rho = float(unet_panel["spearman_rho_depth_adjusted"])
    add_check(
        checks,
        "independent panel collagen rho",
        len(set(panel_people_ids)) == 40
        and abs(panel_rho - panel_saved_rho) <= TOLERANCE,
        {"participants": len(set(panel_people_ids)), "rho": panel_rho},
        {"participants": 40, "rho": panel_saved_rho},
        "Recomputed the depth-adjusted participant Spearman correlation from saved pseudobulk rows.",
    )

    ordered_slides = sorted(
        slides,
        key=lambda row: (float(row["median_tissue_hue"]), row["library_id"]),
    )
    color_group_by_library = {
        (row["participant_id"], row["library_id"]): f"Q{min(4, (index * 4) // len(ordered_slides) + 1)}"
        for index, row in enumerate(ordered_slides)
    }
    eta_squared_values = {}
    for mask in ("unet", "colour"):
        values_by_quartile: dict[str, list[float]] = {
            f"Q{index}": [] for index in range(1, 5)
        }
        all_values = []
        for row in ordered_slides:
            quartile = color_group_by_library[(row["participant_id"], row["library_id"])]
            value = float(row[f"{mask}_fibrosis_percent_tissue"])
            values_by_quartile[quartile].append(value)
            all_values.append(value)
        grand_mean = float(np.mean(all_values))
        total_ss = float(sum((value - grand_mean) ** 2 for value in all_values))
        between_ss = sum(
            len(group) * (float(np.mean(group)) - grand_mean) ** 2
            for group in values_by_quartile.values()
            if group
        )
        eta_squared_values[mask] = between_ss / total_ss if total_ss > 0 else math.nan
    saved_confound = read_csv(OUT / "FA_COLOR_CONFOUND_CHECK_FINAL.csv")
    for mask in ("unet", "colour"):
        row = next(item for item in saved_confound if item["mask"] == mask)
        eta = eta_squared_values[mask]
        add_check(
            checks,
            f"{mask} image-colour eta-squared",
            abs(eta - float(row["library_level_color_group_eta_squared"])) <= TOLERANCE,
            eta,
            float(row["library_level_color_group_eta_squared"]),
            "Recomputed from library tissue-normalized fractions and the final median-hue quartiles.",
        )

    manifest_checks = []
    for row in analysis_hashes:
        path = Path(row["source_path"])
        exists = path.is_file()
        actual = sha256_file(path) if exists else ""
        manifest_checks.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "record_type": "analysis manifest verification",
                "source_path": str(path),
                "expected_sha256": row["sha256"],
                "actual_sha256": actual,
                "status": "PASS" if exists and actual == row["sha256"] else "FAIL",
            }
        )
    manifest_ok = bool(manifest_checks) and all(
        row["status"] == "PASS" for row in manifest_checks
    )
    add_check(
        checks,
        "analysis input/output hashes",
        manifest_ok,
        {
            "checked": len(manifest_checks),
            "passed": sum(row["status"] == "PASS" for row in manifest_checks),
        },
        {"all": "PASS"},
        "Rehashed every file listed in the final analysis manifest.",
    )

    checkpoint_rows = [
        row
        for row in image_hashes
        if row["record_type"] == "input"
        and row["sha256"] == CHECKPOINT_SHA256
    ]
    checkpoint_ok = len(checkpoint_rows) == 1
    checkpoint_actual = ""
    if checkpoint_ok:
        checkpoint_path = Path(checkpoint_rows[0]["source_path"])
        checkpoint_actual = sha256_file(checkpoint_path) if checkpoint_path.is_file() else ""
        checkpoint_ok = checkpoint_actual == CHECKPOINT_SHA256
    add_check(
        checks,
        "frozen RENFAST checkpoint hash",
        checkpoint_ok,
        checkpoint_actual,
        CHECKPOINT_SHA256,
        "Checkpoint was loaded read-only for the image-only mask run.",
    )

    all_pass = all(row["status"] == "PASS" for row in checks)
    write_csv(verification_path, checks)
    metadata = {
        "analysis_label": ANALYSIS_LABEL,
        "mask_status": MASK_LABEL,
        "asset_status": ASSET_STATUS,
        "verification_status": "PASS" if all_pass else "FAIL",
        "checks": len(checks),
        "checks_passed": sum(row["status"] == "PASS" for row in checks),
        "participants": len(participant_ids),
        "libraries": len(library_to_participant),
        "matched_spots": len(spots),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "command": "python -B D:\\patent\\stage_FA\\FA_VERIFY.py",
        "started_at_utc": started_at.isoformat(),
        "runtime_seconds": round(time.monotonic() - started, 3),
        "inputs_checked": len(manifest_checks),
        "checkpoint_sha256": checkpoint_actual,
        "fold_membership": "NOT APPLICABLE; no cross-validation folds in Stage FA",
        "bootstrap_seed": SEED,
        "bootstrap_resamples": BOOTSTRAPS,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    verification_hashes = list(manifest_checks)
    for path in (
        verification_path,
        metadata_path,
        OUT / "FA_VERIFY.py",
        OUT / "FA_ANALYSIS_METADATA_FINAL.json",
        OUT / "FA_IMAGE_RUN_METADATA.json",
        OUT / "FA_HUE_CORRECTION_METADATA.json",
    ):
        verification_hashes.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "record_type": "verification read/write",
                "source_path": str(path),
                "expected_sha256": "",
                "actual_sha256": sha256_file(path),
                "status": "PASS",
            }
        )
    write_csv(verification_hash_path, verification_hashes)
    print(json.dumps(metadata, indent=2))
    if not all_pass:
        raise RuntimeError("One or more independent verification checks failed.")


if __name__ == "__main__":
    main()
