from __future__ import annotations

import csv
import hashlib
import json
import platform
from collections import defaultdict
from pathlib import Path

import numpy as np
import scipy

ROOT = Path(r"D:\patent\stage_PXY")
PCT_TABLE = Path(r"D:\patent\stage_PCT\PCT_PER_IMAGE.csv")
SEED = 20261118
BOOTSTRAPS = 10_000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


with PCT_TABLE.open("r", encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle))

family_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
for row in rows:
    family_rows[row["family_id"]].append(row)
families = sorted(family_rows)

absolute_differences = np.asarray(
    [
        float(row["unet_absolute_error"]) - float(row["colour_absolute_error"])
        for row in rows
    ],
    dtype=np.float64,
)
unet_signed = np.asarray(
    [float(row["unet_signed_error"]) for row in rows], dtype=np.float64
)
colour_signed = np.asarray(
    [float(row["colour_signed_error"]) for row in rows], dtype=np.float64
)
squared_differences = np.asarray(
    [
        float(row["unet_signed_error"]) ** 2
        - float(row["colour_signed_error"]) ** 2
        for row in rows
    ],
    dtype=np.float64,
)


def bootstrap_mean(values_by_family: dict[str, np.ndarray]) -> tuple[float, float]:
    rng = np.random.default_rng(SEED)
    estimates = []
    names = sorted(values_by_family)
    for _ in range(BOOTSTRAPS):
        sampled = rng.choice(names, size=len(names), replace=True)
        pool = np.concatenate([values_by_family[name] for name in sampled])
        estimates.append(float(pool.mean()))
    low, high = np.quantile(np.asarray(estimates), [0.025, 0.975])
    return float(low), float(high)


absolute_by_family = {
    family: np.asarray(
        [
            float(row["unet_absolute_error"]) - float(row["colour_absolute_error"])
            for row in family_rows[family]
        ]
    )
    for family in families
}
squared_by_family = {
    family: np.asarray(
        [
            float(row["unet_signed_error"]) ** 2
            - float(row["colour_signed_error"]) ** 2
            for row in family_rows[family]
        ]
    )
    for family in families
}

absolute_ci = bootstrap_mean(absolute_by_family)
squared_ci = bootstrap_mean(squared_by_family)
mean_absolute_difference = float(absolute_differences.mean())
mean_squared_difference = float(squared_differences.mean())
u_net_better = int(
    sum(
        float(row["unet_absolute_error"]) < float(row["colour_absolute_error"])
        for row in rows
    )
)
u_net_tied = int(
    sum(
        float(row["unet_absolute_error"]) == float(row["colour_absolute_error"])
        for row in rows
    )
)
u_net_worse = len(rows) - u_net_better - u_net_tied
significantly_lower = absolute_ci[1] < 0

family_output = []
for family in families:
    selected = family_rows[family]
    expert = np.asarray([float(row["expert_pct_tissue"]) for row in selected])
    unet = np.asarray([float(row["unet_pct_tissue"]) for row in selected])
    colour = np.asarray([float(row["colour_pct_tissue"]) for row in selected])
    u_errors = unet - expert
    c_errors = colour - expert
    family_output.append({
        "family_id": family,
        "n_images": len(selected),
        "u_net_signed_bias_mean": float(u_errors.mean()),
        "colour_signed_bias_mean": float(c_errors.mean()),
        "u_net_mean_absolute_error": float(np.abs(u_errors).mean()),
        "colour_mean_absolute_error": float(np.abs(c_errors).mean()),
        "paired_absolute_error_difference_u_minus_colour": float(
            np.mean(np.abs(u_errors) - np.abs(c_errors))
        ),
        "u_net_better_image_count": int(
            sum(np.abs(u_errors) < np.abs(c_errors))
        ),
    })

family_path = ROOT / "PXY_PER_FAMILY_PAIRED.csv"
with family_path.open("x", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(family_output[0]))
    writer.writeheader()
    writer.writerows(family_output)

summary = {
    "timestamp_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    "input": str(PCT_TABLE),
    "input_sha256": sha256_file(PCT_TABLE),
    "n_images": len(rows),
    "n_families": len(families),
    "denominator": "tissue pixels; RGB mean < 245",
    "bootstrap_unit": "filename family",
    "bootstrap_seed": SEED,
    "bootstrap_resamples": BOOTSTRAPS,
    "mean_absolute_error_difference_u_net_minus_colour": mean_absolute_difference,
    "absolute_error_difference_95_ci_low": absolute_ci[0],
    "absolute_error_difference_95_ci_high": absolute_ci[1],
    "u_net_better_image_count": u_net_better,
    "u_net_tied_image_count": u_net_tied,
    "u_net_worse_image_count": u_net_worse,
    "mean_paired_squared_error_difference_u_net_minus_colour": mean_squared_difference,
    "squared_error_difference_95_ci_low": squared_ci[0],
    "squared_error_difference_95_ci_high": squared_ci[1],
    "u_net_percentage_error_significantly_lower": significantly_lower,
    "significance_rule": "CI upper bound below 0",
    "outside_proxy_status": "NOT RUN: neither outside repository was eligible",
    "outside_proxy_models": ["SarderLab/Multi-Compartment-Segmentation", "vkola-lab/ajpa2021"],
}
(ROOT / "PXY_PAIRED_COMPARISON.json").write_text(
    json.dumps(summary, indent=2) + "\n", encoding="utf-8"
)

print(json.dumps(summary, indent=2))
