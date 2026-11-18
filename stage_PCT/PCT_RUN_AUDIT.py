from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import platform
import sys
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
import torch
from PIL import Image
from scipy.stats import pearsonr, spearmanr

ROOT = Path(r"D:\patent\stage_PCT")
PHASEA_DIR = Path(r"D:\patent\stage2A_audit")
ARCHIVE = Path(r"D:\patent\m2t49zf6xr-1.zip")
SPLIT = PHASEA_DIR / "PHASEA_final_split_manifest.csv"
METRICS = PHASEA_DIR / "PHASEA_final_per_image_metrics.csv"
MODEL_SOURCE = PHASEA_DIR / "run_renfast_baseline.py"
CHECKPOINT = PHASEA_DIR / "renfast_baseline_run" / "checkpoint_best.pt"
EXPECTED_HASH = "674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb"
SEED = 20261118
BOOTSTRAPS = 10_000
COLOUR_THRESHOLD = 2
TISSUE_THRESHOLD = 245.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def import_phasea() -> tuple[type, object]:
    spec = importlib.util.spec_from_file_location("pct_phasea_model", MODEL_SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load Phase A model source.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if getattr(module, "THRESHOLD", None) != 0.5:
        raise RuntimeError("Phase A threshold is not 0.5.")
    return module.UNet, module


def pct(mask: np.ndarray, denominator: np.ndarray) -> float:
    denominator_count = int(denominator.sum())
    if denominator_count == 0:
        raise RuntimeError("The denominator has zero pixels.")
    return 100.0 * float(np.logical_and(mask, denominator).sum()) / denominator_count


def pearson(a: np.ndarray, b: np.ndarray) -> float:
    if np.ptp(a) == 0 or np.ptp(b) == 0:
        return float("nan")
    return float(pearsonr(a, b).statistic)


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    if np.ptp(a) == 0 or np.ptp(b) == 0:
        return float("nan")
    return float(spearmanr(a, b).statistic)


def lin_ccc(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if len(a) < 2:
        return float("nan")
    a_mean, b_mean = a.mean(), b.mean()
    a_var = np.sum((a - a_mean) ** 2) / len(a)
    b_var = np.sum((b - b_mean) ** 2) / len(b)
    covariance = np.sum((a - a_mean) * (b - b_mean)) / len(a)
    denominator = a_var + b_var + (a_mean - b_mean) ** 2
    return float("nan") if denominator == 0 else float(2 * covariance / denominator)


def rmse(errors: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.asarray(errors, dtype=np.float64) ** 2)))


def summary(expert: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    errors = predicted - expert
    return {
        "mean_bias": float(errors.mean()),
        "mean_absolute_error": float(np.mean(np.abs(errors))),
        "root_mean_square_error": rmse(errors),
        "pearson": pearson(expert, predicted),
        "spearman": spearman(expert, predicted),
        "lin_concordance": lin_ccc(expert, predicted),
        "bland_altman_bias": float(errors.mean()),
        "bland_altman_sd": float(errors.std(ddof=1)),
        "bland_altman_loa_low": float(errors.mean() - 1.96 * errors.std(ddof=1)),
        "bland_altman_loa_high": float(errors.mean() + 1.96 * errors.std(ddof=1)),
    }


def slope(expert: np.ndarray, predicted: np.ndarray) -> float:
    errors = predicted - expert
    x_mean = expert.mean()
    denominator = float(np.sum((expert - x_mean) ** 2))
    if denominator == 0:
        return float("nan")
    return float(np.sum((expert - x_mean) * (errors - errors.mean())) / denominator)


def bootstrap_metric(
    families: list[str],
    family_rows: dict[str, list[dict[str, object]]],
    value_function,
) -> tuple[float, float]:
    rng = np.random.default_rng(SEED)
    estimates = []
    for _ in range(BOOTSTRAPS):
        sampled_names = rng.choice(families, size=len(families), replace=True)
        rows = [row for name in sampled_names for row in family_rows[str(name)]]
        estimate = value_function(rows)
        if np.isfinite(estimate):
            estimates.append(float(estimate))
    if not estimates:
        return float("nan"), float("nan")
    low, high = np.quantile(np.asarray(estimates), [0.025, 0.975])
    return float(low), float(high)


def bootstrap_summary(
    expert_key: str,
    predicted_key: str,
    families: list[str],
    family_rows: dict[str, list[dict[str, object]]],
) -> dict[str, tuple[float, float]]:
    def for_rows(rows: list[dict[str, object]], statistic: str) -> float:
        expert = np.asarray([float(row[expert_key]) for row in rows])
        predicted = np.asarray([float(row[predicted_key]) for row in rows])
        values = summary(expert, predicted)
        if statistic == "slope":
            return slope(expert, predicted)
        return values[statistic]

    names = (
        "mean_bias",
        "mean_absolute_error",
        "root_mean_square_error",
        "pearson",
        "spearman",
        "lin_concordance",
        "bland_altman_bias",
        "bland_altman_loa_low",
        "bland_altman_loa_high",
        "slope",
    )
    return {
        name: bootstrap_metric(
            families,
            family_rows,
            lambda rows, name=name: (
                for_rows(rows, name) if name != "slope" else slope(
                    np.asarray([float(row[expert_key]) for row in rows]),
                    np.asarray([float(row[predicted_key]) for row in rows]),
                )
            ),
        )
        for name in names
    }


def band_name(value: float) -> str:
    if value < 5:
        return "0-5"
    if value < 15:
        return "5-15"
    if value < 30:
        return "15-30"
    return "over 30"


def write_scatter(rows: list[dict[str, object]], stem: str) -> None:
    expert = np.asarray([float(row["expert_pct_tissue"]) for row in rows])
    for key, title in (
        ("unet_pct_tissue", "U-Net"),
        ("colour_pct_tissue", "Colour rule"),
    ):
        predicted = np.asarray([float(row[key]) for row in rows])
        fig, ax = plt.subplots(figsize=(7, 7))
        ax.scatter(expert, predicted, s=28, alpha=0.75)
        limit = max(100.0, float(max(expert.max(), predicted.max())) * 1.05)
        ax.plot([0, limit], [0, limit], "k--", linewidth=1.5, label="Identity")
        ax.set_xlim(0, limit)
        ax.set_ylim(0, limit)
        ax.set_xlabel("Expert fibrosis percentage")
        ax.set_ylabel(f"{title} fibrosis percentage")
        ax.set_title(f"{title}: area percentage")
        ax.legend()
        ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(ROOT / f"PCT_SCATTER_{stem}_{key.split('_')[0].upper()}.png", dpi=180)
        plt.close(fig)


def write_bland_altman(rows: list[dict[str, object]], stem: str) -> None:
    expert = np.asarray([float(row["expert_pct_tissue"]) for row in rows])
    for key, title in (
        ("unet_pct_tissue", "U-Net"),
        ("colour_pct_tissue", "Colour rule"),
    ):
        predicted = np.asarray([float(row[key]) for row in rows])
        average = (expert + predicted) / 2
        difference = predicted - expert
        bias = difference.mean()
        sd = difference.std(ddof=1)
        low, high = bias - 1.96 * sd, bias + 1.96 * sd
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.scatter(average, difference, s=28, alpha=0.75)
        ax.axhline(bias, color="tab:red", linewidth=1.5, label=f"Bias {bias:.3f}")
        ax.axhline(low, color="tab:blue", linestyle="--", linewidth=1.2,
                   label=f"LOA low {low:.3f}")
        ax.axhline(high, color="tab:blue", linestyle="--", linewidth=1.2,
                   label=f"LOA high {high:.3f}")
        ax.set_xlabel("Mean of expert and predicted percentage")
        ax.set_ylabel("Predicted minus expert percentage")
        ax.set_title(f"{title}: Bland-Altman plot")
        ax.legend()
        ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(ROOT / f"PCT_BLAND_ALTMAN_{stem}_{key.split('_')[0].upper()}.png", dpi=180)
        plt.close(fig)


def main() -> int:
    observed_hash = sha256_file(CHECKPOINT)
    if observed_hash != EXPECTED_HASH:
        raise RuntimeError("Frozen checkpoint SHA-256 mismatch.")

    unet_class, _ = import_phasea()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(CHECKPOINT, map_location=device, weights_only=True)
    if checkpoint.get("threshold") != 0.5:
        raise RuntimeError("Checkpoint threshold is not 0.5.")
    model = unet_class().to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    split_rows = []
    with SPLIT.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["assignment"] == "official_test":
                split_rows.append(row)
    if len(split_rows) != 50:
        raise RuntimeError(f"Expected 50 official test images; found {len(split_rows)}.")

    metric_rows = {}
    with METRICS.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            metric_rows[row["stem"]] = row

    rows: list[dict[str, object]] = []
    with zipfile.ZipFile(ARCHIVE) as archive, torch.inference_mode():
        for record in split_rows:
            stem = record["stem"]
            image_bytes = archive.read(record["image_member"])
            mask_bytes = archive.read(record["mask_member"])
            with Image.open(io.BytesIO(image_bytes)) as image:
                rgb = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
            with Image.open(io.BytesIO(mask_bytes)) as mask:
                expert = np.asarray(mask.convert("L"), dtype=np.uint8) == 255

            height, width = rgb.shape[:2]
            pad_height = (-height) % 16
            pad_width = (-width) % 16
            tensor = torch.from_numpy(rgb).permute(2, 0, 1).float().div_(255.0)
            tensor = torch.nn.functional.pad(tensor, (0, pad_width, 0, pad_height))[None].to(device)
            probability = torch.sigmoid(model(tensor))[0, 0, :height, :width]
            unet = (probability >= 0.5).cpu().numpy()
            colour = (rgb[:, :, 2].astype(np.int16) - rgb[:, :, 0].astype(np.int16)) >= COLOUR_THRESHOLD
            tissue = rgb.mean(axis=2) < TISSUE_THRESHOLD
            whole = np.ones_like(tissue, dtype=bool)

            expert_tissue = pct(expert, tissue)
            unet_tissue = pct(unet, tissue)
            colour_tissue = pct(colour, tissue)
            expert_whole = pct(expert, whole)
            unet_whole = pct(unet, whole)
            colour_whole = pct(colour, whole)

            intersection = int(np.logical_and(unet, expert).sum())
            unet_dice = 1.0 if 2 * intersection == 0 and unet.sum() + expert.sum() == 0 else (
                2.0 * intersection / (int(unet.sum()) + int(expert.sum()))
            )
            saved = metric_rows[stem]
            if not np.isclose(unet_dice, float(saved["unet_dice"]), rtol=0.0, atol=1e-12):
                raise RuntimeError(
                    f"Regenerated Dice mismatch for {stem}: {unet_dice} vs {saved['unet_dice']}"
                )

            rows.append({
                "stem": stem,
                "family_id": record["family_id"],
                "expert_pct_tissue": expert_tissue,
                "unet_pct_tissue": unet_tissue,
                "colour_pct_tissue": colour_tissue,
                "unet_signed_error": unet_tissue - expert_tissue,
                "unet_absolute_error": abs(unet_tissue - expert_tissue),
                "colour_signed_error": colour_tissue - expert_tissue,
                "colour_absolute_error": abs(colour_tissue - expert_tissue),
                "expert_pct_whole": expert_whole,
                "unet_pct_whole": unet_whole,
                "colour_pct_whole": colour_whole,
                "unet_dice_recomputed": unet_dice,
                "saved_unet_dice": float(saved["unet_dice"]),
            })

    per_image_path = ROOT / "PCT_PER_IMAGE.csv"
    fieldnames = list(rows[0])
    with per_image_path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    family_rows: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        family_rows[str(row["family_id"])].append(row)
    families = sorted(family_rows)

    def table_summary(predicted_key: str, signed_key: str, absolute_key: str) -> dict[str, object]:
        expert = np.asarray([float(row["expert_pct_tissue"]) for row in rows])
        predicted = np.asarray([float(row[predicted_key]) for row in rows])
        values = summary(expert, predicted)
        ci = bootstrap_summary(
            "expert_pct_tissue", predicted_key, families, family_rows
        )
        values["error_slope"] = slope(expert, predicted)
        values["error_slope_ci_low"] = ci["slope"][0]
        values["error_slope_ci_high"] = ci["slope"][1]
        values["bootstrap_ci"] = ci
        return values

    unet_summary = table_summary("unet_pct_tissue", "unet_signed_error", "unet_absolute_error")
    colour_summary = table_summary("colour_pct_tissue", "colour_signed_error", "colour_absolute_error")

    band_rows = []
    for predictor_key in ("unet_pct_tissue", "colour_pct_tissue"):
        for name in ("0-5", "5-15", "15-30", "over 30"):
            selected = [row for row in rows if band_name(float(row["expert_pct_tissue"])) == name]
            expert = np.asarray([float(row["expert_pct_tissue"]) for row in selected])
            predicted = np.asarray([float(row[predictor_key]) for row in selected])
            if selected:
                values = summary(expert, predicted)
                band_rows.append({
                    "predictor": "U-Net" if predictor_key.startswith("unet") else "Colour rule",
                    "band": name,
                    "n": len(selected),
                    "small_band_note": "too small to judge" if len(selected) < 5 else "",
                    **values,
                })

    band_path = ROOT / "PCT_BANDS.csv"
    with band_path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(band_rows[0]))
        writer.writeheader()
        writer.writerows(band_rows)

    family_rows_out = []
    for family in families:
        selected = family_rows[family]
        expert = np.asarray([float(row["expert_pct_tissue"]) for row in selected])
        unet = np.asarray([float(row["unet_pct_tissue"]) for row in selected])
        colour = np.asarray([float(row["colour_pct_tissue"]) for row in selected])
        family_rows_out.append({
            "family_id": family,
            "n": len(selected),
            "expert_mean_pct": float(expert.mean()),
            "unet_mean_pct": float(unet.mean()),
            "unet_mean_bias": float(np.mean(unet - expert)),
            "unet_mean_absolute_error": float(np.mean(np.abs(unet - expert))),
            "unet_rmse": rmse(unet - expert),
            "colour_mean_pct": float(colour.mean()),
            "colour_mean_bias": float(np.mean(colour - expert)),
            "colour_mean_absolute_error": float(np.mean(np.abs(colour - expert))),
            "colour_rmse": rmse(colour - expert),
        })
    family_path = ROOT / "PCT_PER_FAMILY.csv"
    with family_path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(family_rows_out[0]))
        writer.writeheader()
        writer.writerows(family_rows_out)

    worst_unet = sorted(rows, key=lambda row: -float(row["unet_absolute_error"]))[:3]
    worst_colour = sorted(rows, key=lambda row: -float(row["colour_absolute_error"]))[:3]
    worst_path = ROOT / "PCT_WORST_IMAGES.csv"
    with worst_path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "predictor", "rank", "stem", "family_id", "expert_pct_tissue",
            "predicted_pct_tissue", "signed_error", "absolute_error",
        ])
        writer.writeheader()
        for predictor, selected in (("U-Net", worst_unet), ("Colour rule", worst_colour)):
            key = "unet" if predictor == "U-Net" else "colour"
            for rank, row in enumerate(selected, 1):
                writer.writerow({
                    "predictor": predictor,
                    "rank": rank,
                    "stem": row["stem"],
                    "family_id": row["family_id"],
                    "expert_pct_tissue": row["expert_pct_tissue"],
                    "predicted_pct_tissue": row[f"{key}_pct_tissue"],
                    "signed_error": row[f"{key}_signed_error"],
                    "absolute_error": row[f"{key}_absolute_error"],
                })

    write_scatter(rows, "TISSUE")
    write_bland_altman(rows, "TISSUE")

    expert_values = np.asarray([float(row["expert_pct_tissue"]) for row in rows])
    min_index = int(np.argmin(expert_values))
    detection_row = rows[min_index]

    summary_doc = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_sha256": observed_hash,
        "n_images": len(rows),
        "n_families": len(families),
        "family_resampling": "filename family",
        "bootstrap_seed": SEED,
        "bootstrap_resamples": BOOTSTRAPS,
        "tissue_rule": "RGB channel mean < 245",
        "colour_rule": "B - R >= 2",
        "u_net": unet_summary,
        "colour_rule": colour_summary,
        "smallest_expert_pct_tissue": float(expert_values[min_index]),
        "smallest_expert_image": {
            "stem": detection_row["stem"],
            "family_id": detection_row["family_id"],
            "expert_pct_tissue": detection_row["expert_pct_tissue"],
            "unet_pct_tissue": detection_row["unet_pct_tissue"],
            "colour_pct_tissue": detection_row["colour_pct_tissue"],
        },
        "three_worst_u_net": [
            {
                "stem": row["stem"],
                "family_id": row["family_id"],
                "expert_pct_tissue": row["expert_pct_tissue"],
                "predicted_pct_tissue": row["unet_pct_tissue"],
                "signed_error": row["unet_signed_error"],
                "absolute_error": row["unet_absolute_error"],
            }
            for row in worst_unet
        ],
        "three_worst_colour": [
            {
                "stem": row["stem"],
                "family_id": row["family_id"],
                "expert_pct_tissue": row["expert_pct_tissue"],
                "predicted_pct_tissue": row["colour_pct_tissue"],
                "signed_error": row["colour_signed_error"],
                "absolute_error": row["colour_absolute_error"],
            }
            for row in worst_colour
        ],
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "torch": torch.__version__,
            "matplotlib": matplotlib.__version__,
            "pillow": __import__("PIL").__version__,
        },
    }
    (ROOT / "PCT_SUMMARY.json").write_text(
        json.dumps(summary_doc, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    verification = {
        "checkpoint_hash": observed_hash,
        "n_images": len(rows),
        "n_families": len(families),
        "independent_rechecks": [
            {
                "stem": rows[0]["stem"],
                "expert_pct_tissue": rows[0]["expert_pct_tissue"],
                "u_net_pct_tissue": rows[0]["unet_pct_tissue"],
                "colour_pct_tissue": rows[0]["colour_pct_tissue"],
            },
            {
                "stem": rows[-1]["stem"],
                "expert_pct_tissue": rows[-1]["expert_pct_tissue"],
                "u_net_pct_tissue": rows[-1]["unet_pct_tissue"],
                "colour_pct_tissue": rows[-1]["colour_pct_tissue"],
            },
            {
                "stem": detection_row["stem"],
                "expert_pct_tissue": detection_row["expert_pct_tissue"],
                "u_net_pct_tissue": detection_row["unet_pct_tissue"],
                "colour_pct_tissue": detection_row["colour_pct_tissue"],
            },
        ],
        "command": r'python -B D:\patent\stage_PCT\PCT_RUN_AUDIT.py',
        "seed": SEED,
        "bootstrap_resamples": BOOTSTRAPS,
        "environment": summary_doc["environment"],
    }
    (ROOT / "PCT_VERIFICATION.json").write_text(
        json.dumps(verification, indent=2) + "\n",
        encoding="utf-8",
    )

    report_lines = [
        "# PCT area-percentage accuracy report",
        "",
        f"This audit used 50 RENFAST official test images in {len(families)} filename families.",
        "",
        "## Plain-language answer",
        "",
        f"On this test set, U-Net mean area error was {unet_summary['mean_bias']:.3f} percentage points "
        "(predicted minus expert). Mean absolute error was "
        f"{unet_summary['mean_absolute_error']:.3f} percentage points.",
        f"Colour-rule mean area error was {colour_summary['mean_bias']:.3f} percentage points, "
        f"and mean absolute error was {colour_summary['mean_absolute_error']:.3f} percentage points.",
        "",
        "## What this result means",
        "",
        "This is an audit of area percentage inside tissue: positive mask pixels divided by tissue pixels. "
        "It does not measure collagen mass and does not establish clinical interstitial fibrosis.",
        "",
        "Trust is limited to RENFAST trichrome test images. The 10 filename families are not verified "
        "patients or slides, and expert masks are not an independent clinical reference.",
        "",
        "## Detection floor",
        "",
        f"The smallest expert tissue percentage was {detection_row['expert_pct_tissue']:.6f}% in "
        f"{detection_row['stem']}. U-Net reported {detection_row['unet_pct_tissue']:.6f}% and "
        f"the colour rule reported {detection_row['colour_pct_tissue']:.6f}%. "
        "No true limit of detection was tested.",
        "",
        "## Bias structure",
        "",
        f"U-Net signed-error slope on expert percentage: {unet_summary['error_slope']:.6f} "
        f"(family-bootstrap 95% CI {unet_summary['error_slope_ci_low']:.6f} to "
        f"{unet_summary['error_slope_ci_high']:.6f}).",
        f"Colour-rule signed-error slope: {colour_summary['error_slope']:.6f} "
        f"(family-bootstrap 95% CI {colour_summary['error_slope_ci_low']:.6f} to "
        f"{colour_summary['error_slope_ci_high']:.6f}).",
        "These are bias-structure checks. A linear correction would be post-hoc and was not applied.",
        "",
        "## Where it is trustworthy and not trustworthy",
        "",
        "The tables and plots describe this 50-image RENFAST test set under its exact preprocessing and "
        "tissue denominator. Confidence intervals resample filename families, but only 10 families were available.",
        "Do not generalize to other stains, scanners, tissues, patients or clinical diagnosis. Small bands "
        "with fewer than five images are marked too small to judge.",
        "",
        "No clinical accuracy, novelty or patentability claim is made.",
    ]
    (ROOT / "PCT_REPORT.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    hash_rows = []
    for path in sorted(ROOT.iterdir()):
        if path.is_file() and path.name.startswith("PCT_") and path.name != "PCT_FILE_HASHES.csv":
            hash_rows.append((str(path), sha256_file(path)))
    with (ROOT / "PCT_FILE_HASHES.csv").open("x", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["path", "sha256"])
        writer.writerows(hash_rows)
    print(json.dumps({
        "n_images": len(rows),
        "n_families": len(families),
        "u_net": unet_summary,
        "colour": colour_summary,
        "smallest_expert_pct_tissue": float(expert_values[min_index]),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
