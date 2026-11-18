from __future__ import annotations

import csv
import hashlib
import json
import platform
from pathlib import Path

import numpy as np

ROOT = Path(r"D:\patent\stage_PLAUS")
CHECKPOINT = Path(r"D:\patent\stage2A_audit\renfast_baseline_run\checkpoint_best.pt")
EXPECTED_CHECKPOINT = "674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


observed_checkpoint = sha256_file(CHECKPOINT)
if observed_checkpoint != EXPECTED_CHECKPOINT:
    raise RuntimeError("Frozen checkpoint SHA-256 mismatch.")

with (ROOT / "PLAUS_NEGATIVE_CONTROL_EFFECTS.csv").open(
    "r", encoding="utf-8-sig", newline=""
) as handle:
    controls = list(csv.DictReader(handle))
control_values = np.asarray(
    [float(row["mean_effect"]) for row in controls],
    dtype=np.float64,
)

with (ROOT / "PLAUS_EXPECTED_DIRECTION.csv").open(
    "r", encoding="utf-8-sig", newline=""
) as handle:
    panel = list(csv.DictReader(handle))
agreements = np.asarray(
    [row["expected_sign_agrees"].lower() == "true" for row in panel],
    dtype=np.float64,
)

summary = json.loads((ROOT / "PLAUS_RESULTS.json").read_text(encoding="utf-8"))
per_effect_table = Path(r"D:\patent\stage_FA\FA_PER_PARTICIPANT_EFFECTS_FINAL.csv")
with per_effect_table.open("r", encoding="utf-8-sig", newline="") as handle:
    participant_rows = [
        row for row in csv.DictReader(handle)
        if row["mask"] == "unet" and row["target"] == "collagen_module"
        and row["fit_status"] == "PASS"
    ]
participant_effects = np.asarray(
    [float(row["participant_effect_high_minus_low"]) for row in participant_rows],
    dtype=np.float64,
)

three_headline = {
    "collagen_module_mean_effect": float(participant_effects.mean()),
    "negative_control_95th_percentile": float(np.percentile(control_values, 95)),
    "expected_direction_sign_agreement_fraction": float(agreements.mean()),
}
differences = {
    "collagen_module_mean_effect": abs(
        three_headline["collagen_module_mean_effect"]
        - summary["collagen_module"]["mean_effect"]
    ),
    "negative_control_95th_percentile": abs(
        three_headline["negative_control_95th_percentile"]
        - summary["negative_controls"]["95th_percentile"]
    ),
    "expected_direction_sign_agreement_fraction": abs(
        three_headline["expected_direction_sign_agreement_fraction"]
        - summary["expected_direction"]["sign_agreement_fraction"]
    ),
}
tolerance = 1e-12
verification = {
    "method": "Independent recomputation from saved PLAUS tables and Stage FA participant effects",
    "three_headline_numbers": three_headline,
    "absolute_difference_from_result": differences,
    "maximum_absolute_difference": float(max(differences.values())),
    "tolerance": tolerance,
    "passed": bool(max(differences.values()) <= tolerance),
    "checkpoint_sha256": observed_checkpoint,
    "seed": 20261118,
    "bootstrap_resamples": 10000,
    "command": r"python -B D:\patent\stage_PLAUS\PLAUS_RUN_CHECKS.py",
    "independent_command": r"python -B D:\patent\stage_PLAUS\PLAUS_VERIFY_INDEPENDENT.py",
    "environment": {
        "python": platform.python_version(),
        "numpy": np.__version__,
    },
}
(ROOT / "PLAUS_VERIFICATION.json").write_text(
    json.dumps(verification, indent=2) + "\n",
    encoding="utf-8",
)

hash_rows = []
for path in sorted(ROOT.iterdir()):
    if path.is_file() and path.name.startswith("PLAUS_") and path.name != "PLAUS_FILE_HASHES.csv":
        hash_rows.append((str(path), sha256_file(path)))
with (ROOT / "PLAUS_FILE_HASHES.csv").open("w", encoding="utf-8", newline="") as handle:
    writer = csv.writer(handle)
    writer.writerow(["path", "sha256"])
    writer.writerows(hash_rows)

print(json.dumps(verification, indent=2))
