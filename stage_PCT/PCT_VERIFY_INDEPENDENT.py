from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(r"D:\patent\stage_PCT")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


with (ROOT / "PCT_PER_IMAGE.csv").open("r", encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle))

verification: dict[str, object] = {
    "method": "Independent arithmetic recomputation from PCT_PER_IMAGE.csv",
    "n_images": len(rows),
    "numbers": {},
}

for predictor, signed_key, predicted_key in (
    ("U-Net", "unet_signed_error", "unet_pct_tissue"),
    ("Colour rule", "colour_signed_error", "colour_pct_tissue"),
):
    errors = np.asarray([float(row[signed_key]) for row in rows], dtype=np.float64)
    expert = np.asarray([float(row["expert_pct_tissue"]) for row in rows], dtype=np.float64)
    predicted = np.asarray([float(row[predicted_key]) for row in rows], dtype=np.float64)
    mean_bias = float(np.sum(errors) / len(errors))
    mae = float(np.sum(np.abs(errors)) / len(errors))
    rmse = float(math.sqrt(np.sum(errors * errors) / len(errors)))
    expert_whole_key = "expert_pct_whole"
    whole_predicted_key = (
        "unet_pct_whole" if predictor == "U-Net" else "colour_pct_whole"
    )
    whole_expert = np.asarray(
        [float(row[expert_whole_key]) for row in rows], dtype=np.float64
    )
    whole_predicted = np.asarray(
        [float(row[whole_predicted_key]) for row in rows], dtype=np.float64
    )
    whole_errors = whole_predicted - whole_expert
    verification["numbers"][predictor] = {
        "mean_bias_recomputed": mean_bias,
        "mean_absolute_error_recomputed": mae,
        "root_mean_square_error_recomputed": rmse,
        "whole_image_sensitivity_bias": float(
            np.sum(whole_errors) / len(whole_errors)
        ),
        "whole_image_sensitivity_mae": float(
            np.sum(np.abs(whole_errors)) / len(whole_errors)
        ),
    }

summary = json.loads((ROOT / "PCT_SUMMARY.json").read_text(encoding="utf-8"))
for predictor, key in (("U-Net", "u_net"), ("Colour rule", "colour_rule")):
    recomputed = verification["numbers"][predictor]
    original = summary[key]
    checks = {
        "mean_bias": abs(
            recomputed["mean_bias_recomputed"] - float(original["mean_bias"])
        ),
        "mean_absolute_error": abs(
            recomputed["mean_absolute_error_recomputed"]
            - float(original["mean_absolute_error"])
        ),
        "root_mean_square_error": abs(
            recomputed["root_mean_square_error_recomputed"]
            - float(original["root_mean_square_error"])
        ),
    }
    recomputed["maximum_absolute_difference"] = float(max(checks.values()))
    recomputed["passes_tolerance_1e-12"] = bool(
        recomputed["maximum_absolute_difference"] <= 1e-12
    )

with (ROOT / "PCT_INDEPENDENT_VERIFICATION.json").open("w", encoding="utf-8") as handle:
    json.dump(verification, handle, indent=2)
    handle.write("\n")

verification_path = ROOT / "PCT_VERIFICATION.json"
verification_document = json.loads(verification_path.read_text(encoding="utf-8"))
verification_document["independent_three_number_recheck"] = verification
verification_document["independent_command"] = r"python -B D:\patent\stage_PCT\PCT_VERIFY_INDEPENDENT.py"
verification_document["independent_passed"] = all(
    result["passes_tolerance_1e-12"] for result in verification["numbers"].values()
)
verification_document["independent_recheck_tolerance"] = 1e-12
verification_path.write_text(
    json.dumps(verification_document, indent=2) + "\n",
    encoding="utf-8",
)

hash_rows = []
for path in sorted(ROOT.iterdir()):
    if path.is_file() and path.name.startswith("PCT_") and path.name != "PCT_FILE_HASHES.csv":
        hash_rows.append((str(path), sha256_file(path)))
with (ROOT / "PCT_FILE_HASHES.csv").open("w", encoding="utf-8", newline="") as handle:
    writer = csv.writer(handle)
    writer.writerow(["path", "sha256"])
    writer.writerows(hash_rows)

print(json.dumps(verification, indent=2))
