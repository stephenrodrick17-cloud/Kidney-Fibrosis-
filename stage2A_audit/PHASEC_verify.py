from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

import run_renfast_baseline as phase_a


ROOT = Path(__file__).resolve().parent
ARCHIVE = Path(r"D:\patent\m2t49zf6xr-1.zip")
PHASE_A_CHECKPOINT = ROOT / "renfast_baseline_run" / "checkpoint_best.pt"
OUTPUT = ROOT / "PHASEC_VERIFICATION.json"
EXPECTED_ARCHIVE_SHA256 = "f796f0fa585701d66bd8f6b0ed096bb30f4376eff3359cb32ccbf1fd64d08a4e"
EXPECTED_FROZEN_SHA256 = "674b0045ab8c5857fa056dc85d691f7e1c30a86479ffe7ba0be933351b2fbcbb"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def digest_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pixels(image: np.ndarray, mask: np.ndarray) -> tuple[float, float, float]:
    tp = int(np.logical_and(image, mask).sum())
    fp = int(np.logical_and(image, ~mask).sum())
    fn = int(np.logical_and(~image, mask).sum())
    return (
        1.0 if 2 * tp + fp + fn == 0 else (2 * tp / (2 * tp + fp + fn)),
        1.0 if tp + fp + fn == 0 else (tp / (tp + fp + fn)),
        1.0 if tp + fn == 0 else (tp / (tp + fn)),
    )


def read_active_test():
    with (ROOT / "PHASEA_final_split_manifest.csv").open(
        newline="", encoding="utf-8-sig"
    ) as stream:
        return [row for row in csv.DictReader(stream) if row["assignment"] == "official_test"]


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError(f"Refusing to overwrite {OUTPUT}")
    archive_hash = digest_file(ARCHIVE)
    checkpoint_hash = digest_file(PHASE_A_CHECKPOINT)
    if archive_hash != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("RENFAST archive hash differs from the Phase A record")
    if checkpoint_hash != EXPECTED_FROZEN_SHA256:
        raise ValueError("Frozen checkpoint hash differs from the Phase A record")

    frozen_checkpoint = torch.load(PHASE_A_CHECKPOINT, map_location=DEVICE, weights_only=True)
    frozen = phase_a.UNet().to(DEVICE)
    frozen.load_state_dict(frozen_checkpoint["model_state"])
    frozen.eval()
    ensemble_models = [frozen]
    ensemble_hashes = []
    for seed in (20261122, 20261123):
        checkpoint_path = ROOT / f"PHASEC_UNET_seed_{seed}_checkpoint.pt"
        ensemble_hashes.append(digest_file(checkpoint_path))
        checkpoint = torch.load(checkpoint_path, map_location=DEVICE, weights_only=True)
        model = phase_a.UNet().to(DEVICE)
        model.load_state_dict(checkpoint["model_state"])
        model.eval()
        ensemble_models.append(model)

    image_dice: list[float] = []
    color_group: dict[str, list[float]] = defaultdict(list)
    brier_total = 0.0
    pixel_total = 0
    test_rows = read_active_test()
    if len(test_rows) != 50 or len({row["family_id"] for row in test_rows}) != 10:
        raise ValueError("Official test count or family count differs from Phase A")

    with zipfile.ZipFile(ARCHIVE) as archive, torch.no_grad():
        for row in test_rows:
            image_bytes = archive.read(row["image_member"])
            mask_bytes = archive.read(row["mask_member"])
            if digest(image_bytes) != row["image_sha256"] or digest(mask_bytes) != row["mask_sha256"]:
                raise ValueError(f"Saved test pair hash mismatch: {row['stem']}")
            with Image.open(io.BytesIO(image_bytes)) as source_image:
                rgb = np.asarray(source_image.convert("RGB"), dtype=np.uint8).copy()
            with Image.open(io.BytesIO(mask_bytes)) as source_mask:
                target = np.asarray(source_mask.convert("L"), dtype=np.uint8) == 255
            tensor = torch.from_numpy(rgb).permute(2, 0, 1).float().div_(255.0)
            pad_height = (-tensor.shape[-2]) % 16
            pad_width = (-tensor.shape[-1]) % 16
            tensor = F.pad(tensor, (0, pad_width, 0, pad_height))[None].to(DEVICE)
            probabilities = [
                torch.sigmoid(model(tensor))[0, 0, : target.shape[0], : target.shape[1]]
                .cpu()
                .numpy()
                for model in ensemble_models
            ]
            frozen_prediction = probabilities[0] >= 0.5
            image_dice.append(float(pixels(frozen_prediction, target)[0]))
            color_prediction = rgb[:, :, 2].astype(np.int16) - rgb[:, :, 0].astype(np.int16) >= 2
            color_group[row["family_id"]].append(float(pixels(color_prediction, target)[0]))
            ensemble_probability = np.mean(probabilities, axis=0, dtype=np.float32)
            brier_total += float(np.square(ensemble_probability - target.astype(np.float32)).sum())
            pixel_total += target.size

    frozen_image_macro_dice = float(np.mean(image_dice))
    color_family_macro_dice = float(
        np.mean([np.mean(values) for values in color_group.values()])
    )
    ensemble_brier_score = brier_total / pixel_total

    with (ROOT / "PHASEC_test_model_comparison.csv").open(
        newline="", encoding="utf-8-sig"
    ) as stream:
        comparisons = list(csv.DictReader(stream))
    frozen_saved = float(next(row for row in comparisons if row["model"] == "frozen_unet")["dice_image_macro"])
    color_saved = float(next(row for row in comparisons if row["model"] == "color_threshold")["dice_family_macro"])
    uncertainty_saved = json.loads(
        (ROOT / "PHASEC_uncertainty_summary.json").read_text(encoding="utf-8")
    )["brier_score"]
    differences = {
        "frozen_unet_image_macro_dice": abs(frozen_image_macro_dice - frozen_saved),
        "color_threshold_family_macro_dice": abs(color_family_macro_dice - color_saved),
        "ensemble_brier_score": abs(ensemble_brier_score - uncertainty_saved),
    }
    if any(value > 1e-8 for value in differences.values()):
        raise ValueError(f"Independent recomputation mismatch: {differences}")

    result = {
        "status": "verified",
        "recomputation_method": "Independent second pass from saved checkpoint(s), official test images/masks, and fixed colour rule.",
        "archive_sha256": archive_hash,
        "frozen_checkpoint_sha256": checkpoint_hash,
        "ensemble_checkpoint_sha256": ensemble_hashes,
        "test_pairs": len(test_rows),
        "test_filename_families": len(color_group),
        "filename_families_are_verified_patient_or_slide_ids": False,
        "recomputed_values": {
            "frozen_unet_image_macro_dice": frozen_image_macro_dice,
            "color_threshold_family_macro_dice": color_family_macro_dice,
            "ensemble_brier_score": ensemble_brier_score,
        },
        "absolute_difference_from_reported": differences,
        "tolerance": 1e-8,
        "pixel_count_for_brier": pixel_total,
    }
    OUTPUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
