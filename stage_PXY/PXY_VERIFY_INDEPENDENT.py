from __future__ import annotations

import csv
import hashlib
import json
import platform
from pathlib import Path

import numpy as np

ROOT = Path(r"D:\patent\stage_PXY")
PCT_TABLE = Path(r"D:\patent\stage_PCT\PCT_PER_IMAGE.csv")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


with PCT_TABLE.open("r", encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle))

summary = json.loads((ROOT / "PXY_PAIRED_COMPARISON.json").read_text(encoding="utf-8"))

absolute_difference = np.asarray([
    float(row["unet_absolute_error"]) - float(row["colour_absolute_error"])
    for row in rows
], dtype=np.float64)
squared_difference = np.asarray([
    float(row["unet_signed_error"]) ** 2
    - float(row["colour_signed_error"]) ** 2
    for row in rows
], dtype=np.float64)
u_net_better = int(np.sum(absolute_difference < 0))

recomputed = {
    "mean_absolute_error_difference": float(np.mean(absolute_difference)),
    "u_net_better_image_count": u_net_better,
    "mean_paired_squared_error_difference": float(np.mean(squared_difference)),
}

checks = {
    "mean_absolute_error_difference": abs(
        recomputed["mean_absolute_error_difference"]
        - summary["mean_absolute_error_difference_u_net_minus_colour"]
    ),
    "u_net_better_image_count": abs(
        recomputed["u_net_better_image_count"]
        - summary["u_net_better_image_count"]
    ),
    "mean_paired_squared_error_difference": abs(
        recomputed["mean_paired_squared_error_difference"]
        - summary["mean_paired_squared_error_difference_u_net_minus_colour"]
    ),
}
tolerance = 1e-12
passed = all(value <= tolerance for value in checks.values())

verification = {
    "independent_method": "Arithmetic recomputation from PCT_PER_IMAGE.csv",
    "n_images": len(rows),
    "three_headline_numbers": recomputed,
    "maximum_absolute_difference": float(max(checks.values())),
    "per_number_absolute_difference": checks,
    "tolerance": tolerance,
    "passed": passed,
    "checkpoint_sha256": "674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb",
    "pct_input_sha256": sha256_file(PCT_TABLE),
    "seed": 20261118,
    "bootstrap_resamples": 10000,
    "command": r"python -B D:\patent\stage_PXY\PXY_PAIRED_COMPARISON.py",
    "independent_command": r"python -B D:\patent\stage_PXY\PXY_VERIFY_INDEPENDENT.py",
    "environment": {
        "python": platform.python_version(),
        "numpy": np.__version__,
    },
}
(ROOT / "PXY_VERIFICATION.json").write_text(
    json.dumps(verification, indent=2) + "\n",
    encoding="utf-8",
)

hash_rows = []
for path in sorted(ROOT.iterdir()):
    if path.is_file() and path.name.startswith("PXY_") and path.name != "PXY_FILE_HASHES.csv":
        hash_rows.append((str(path), sha256_file(path)))
with (ROOT / "PXY_FILE_HASHES.csv").open("w", encoding="utf-8", newline="") as handle:
    writer = csv.writer(handle)
    writer.writerow(["path", "sha256"])
    writer.writerows(hash_rows)

print(json.dumps(verification, indent=2))
