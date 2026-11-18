"""Audit, train, and evaluate the preregistered RENFAST fibrosis baseline."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import random
import re
import sys
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import PIL
import torch
from PIL import Image
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader, Dataset


SEED = 20261116
BOOTSTRAP_SEED = 20261117
THRESHOLD = 0.5
MAX_EPOCHS = 100
PATIENCE = 12


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def filename_key(member: str, extension: str) -> tuple[str, int]:
    basename = member.rsplit("/", 1)[-1]
    match = re.fullmatch(
        rf"(.+){re.escape(extension)}(?: (\d+))?",
        basename,
        flags=re.IGNORECASE,
    )
    if match is None:
        raise ValueError(f"Unexpected archive member name: {member}")
    return match.group(1), int(match.group(2) or 0)


def family_id(stem: str) -> str:
    match = re.match(r"^(\d+)(?:_|$)", stem)
    if match is None:
        raise ValueError(f"Cannot derive filename-family ID from {stem!r}")
    return match.group(1)


def index_members(
    archive: zipfile.ZipFile, split: str, folder: str, extension: str
) -> dict[tuple[str, int], str]:
    prefix = f"{split}/{folder}/"
    indexed: dict[tuple[str, int], str] = {}
    for member in archive.namelist():
        if not member.startswith(prefix) or member.endswith("/"):
            continue
        key = filename_key(member, extension)
        if key in indexed:
            raise ValueError(f"Duplicate normalized archive key: {member}")
        indexed[key] = member
    return indexed


def pair_split(archive: zipfile.ZipFile, split: str) -> list[dict[str, Any]]:
    images = index_members(archive, split, "IMAGES", ".png")
    masks = index_members(archive, split, "MANUAL_FIBROSIS", ".tif")
    if set(images) != set(masks):
        image_only = sorted(set(images) - set(masks))[:5]
        mask_only = sorted(set(masks) - set(images))[:5]
        raise ValueError(
            f"Image/mask pairing mismatch in {split}: "
            f"image-only={image_only}, mask-only={mask_only}"
        )

    records: list[dict[str, Any]] = []
    for key in sorted(images):
        image_member = images[key]
        mask_member = masks[key]
        image_bytes = archive.read(image_member)
        mask_bytes = archive.read(mask_member)
        stem, copy_index = key
        records.append(
            {
                "source_split": split,
                "stem": stem,
                "copy_index": copy_index,
                "family_id": family_id(stem),
                "image_member": image_member,
                "mask_member": mask_member,
                "image_sha256": sha256_bytes(image_bytes),
                "mask_sha256": sha256_bytes(mask_bytes),
            }
        )
    return records


def inspect_training_pixels(
    archive: zipfile.ZipFile, records: list[dict[str, Any]]
) -> None:
    for record in records:
        with Image.open(io.BytesIO(archive.read(record["image_member"]))) as image:
            image.load()
            image_size = image.size
            image_mode = image.mode
        with Image.open(io.BytesIO(archive.read(record["mask_member"]))) as mask:
            mask.load()
            mask_array = np.asarray(mask.convert("L"))
            mask_size = mask.size
            mask_values = np.unique(mask_array)

        if image_mode != "RGB":
            raise ValueError(
                f"Expected RGB image, got {image_mode}: {record['image_member']}"
            )
        if image_size != mask_size:
            raise ValueError(
                f"Image/mask geometry mismatch for {record['stem']}: "
                f"{image_size} vs {mask_size}"
            )
        if not np.array_equal(mask_values, np.array([0, 255], dtype=mask_values.dtype)):
            raise ValueError(
                f"Expected binary mask values 0 and 255, got "
                f"{mask_values.tolist()}: {record['mask_member']}"
            )
        record["width"] = image_size[0]
        record["height"] = image_size[1]
        record["mask_values"] = "0;255"
        record["foreground_fraction"] = float(np.mean(mask_array == 255))


def unique_pairs(
    records: list[dict[str, Any]], *, fail_on_duplicates: bool = False
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    seen: dict[tuple[str, str, str], dict[str, Any]] = {}
    unique: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    for record in records:
        identity = (
            record["stem"],
            record["image_sha256"],
            record["mask_sha256"],
        )
        if identity in seen:
            record["duplicate_of"] = seen[identity]["image_member"]
            duplicates.append(record)
            if fail_on_duplicates:
                raise ValueError(
                    f"Exact duplicate pair within test split: {record['stem']}"
                )
            continue
        record["duplicate_of"] = ""
        seen[identity] = record
        unique.append(record)
    return unique, duplicates


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_audit(archive_path: Path, output_dir: Path) -> dict[str, Any]:
    if not archive_path.is_file():
        raise FileNotFoundError(f"RENFAST archive not found: {archive_path}")
    with zipfile.ZipFile(archive_path) as archive:
        train_raw = pair_split(archive, "FIBROSIS_TRAIN")
        test_raw = pair_split(archive, "FIBROSIS_TEST")
        train_unique, train_duplicates = unique_pairs(train_raw)
        test_unique, test_duplicates = unique_pairs(test_raw, fail_on_duplicates=True)

        train_image_hashes = {r["image_sha256"] for r in train_unique}
        train_mask_hashes = {r["mask_sha256"] for r in train_unique}
        test_image_hashes = {r["image_sha256"] for r in test_unique}
        test_mask_hashes = {r["mask_sha256"] for r in test_unique}
        if train_image_hashes & test_image_hashes:
            raise ValueError("Exact image content crosses official train/test split")
        if train_mask_hashes & test_mask_hashes:
            raise ValueError("Exact mask content crosses official train/test split")

        inspect_training_pixels(archive, train_unique)

    test_families = {r["family_id"] for r in test_unique}
    train_families = {r["family_id"] for r in train_unique}
    overlap_families = train_families & test_families
    eligible = [r for r in train_unique if r["family_id"] not in test_families]
    eligible_families = sorted({r["family_id"] for r in eligible})
    if len(eligible_families) < 2:
        raise ValueError("Fewer than two train-only filename families remain")

    ordered_families = sorted(
        eligible_families,
        key=lambda group: sha256_bytes(f"{SEED}|{group}".encode("utf-8")),
    )
    validation_count = max(1, round(0.20 * len(ordered_families)))
    validation_families = set(ordered_families[:validation_count])
    training_families = set(ordered_families[validation_count:])
    if not training_families or not validation_families:
        raise ValueError("Group split produced an empty training or validation set")

    assignments: dict[tuple[str, str, str], str] = {}
    for record in train_unique:
        if record["family_id"] in test_families:
            assignment = "excluded_shared_with_test_family"
        elif record["family_id"] in validation_families:
            assignment = "validation"
        else:
            assignment = "training"
        record["assignment"] = assignment
        assignments[(record["stem"], record["image_sha256"], record["mask_sha256"])] = assignment

    for duplicate in train_duplicates:
        duplicate["assignment"] = "duplicate_copy"
    for record in test_unique:
        record["assignment"] = "official_test"

    rows: list[dict[str, Any]] = []
    for record in train_raw + test_raw:
        assignment = record.get("assignment")
        if assignment is None and record["source_split"] == "FIBROSIS_TRAIN":
            identity = (
                record["stem"],
                record["image_sha256"],
                record["mask_sha256"],
            )
            assignment = assignments[identity]
        rows.append(
            {
                "source_split": record["source_split"],
                "stem": record["stem"],
                "copy_index": record["copy_index"],
                "family_id": record["family_id"],
                "image_member": record["image_member"],
                "mask_member": record["mask_member"],
                "image_sha256": record["image_sha256"],
                "mask_sha256": record["mask_sha256"],
                "width": record.get("width", ""),
                "height": record.get("height", ""),
                "mask_values": record.get("mask_values", ""),
                "foreground_fraction": record.get("foreground_fraction", ""),
                "assignment": assignment,
                "duplicate_of": record.get("duplicate_of", ""),
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "renfast_pair_manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    training_records = [r for r in train_unique if r["assignment"] == "training"]
    validation_records = [r for r in train_unique if r["assignment"] == "validation"]
    excluded_records = [
        r for r in train_unique if r["assignment"] == "excluded_shared_with_test_family"
    ]
    summary = {
        "archive": str(archive_path),
        "archive_sha256": sha256_file(archive_path),
        "python": sys.version.split()[0],
        "pillow": PIL.__version__,
        "numpy": np.__version__,
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "official_train_raw_pairs": len(train_raw),
        "official_train_exact_duplicate_pairs": len(train_duplicates),
        "official_train_unique_pairs": len(train_unique),
        "official_train_filename_families": sorted(train_families),
        "official_test_pairs": len(test_unique),
        "official_test_filename_families": sorted(test_families),
        "test_duplicate_pairs": len(test_duplicates),
        "train_test_shared_filename_families": sorted(overlap_families),
        "train_test_shared_exact_image_hashes": 0,
        "train_test_shared_exact_mask_hashes": 0,
        "train_pairs_excluded_for_test_family_overlap": len(excluded_records),
        "eligible_train_only_pairs": len(eligible),
        "eligible_train_only_families": ordered_families,
        "training_families": sorted(training_families),
        "training_pairs": len(training_records),
        "validation_families": sorted(validation_families),
        "validation_pairs": len(validation_records),
        "test_pixels_decoded": False,
        "test_content_hashed_for_integrity_only": True,
        "train_masks_with_required_values": len(train_unique),
        "foreground_fraction_min": min(r["foreground_fraction"] for r in train_unique),
        "foreground_fraction_median": float(
            np.median([r["foreground_fraction"] for r in train_unique])
        ),
        "foreground_fraction_max": max(r["foreground_fraction"] for r in train_unique),
        "manifest": manifest_path.name,
    }
    write_json(output_dir / "audit_summary.json", summary)
    print(json.dumps(summary, indent=2))
    return {
        "summary": summary,
        "training": training_records,
        "validation": validation_records,
        "excluded": excluded_records,
        "test": test_unique,
        "manifest": manifest_path,
    }


class DoubleConv(nn.Module):
    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
        )

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.layers(value)


class UNet(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.encoder1 = DoubleConv(3, 32)
        self.encoder2 = DoubleConv(32, 64)
        self.encoder3 = DoubleConv(64, 128)
        self.encoder4 = DoubleConv(128, 256)
        self.bottleneck = DoubleConv(256, 512)
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)
        self.up4 = nn.ConvTranspose2d(512, 256, kernel_size=2, stride=2)
        self.decoder4 = DoubleConv(512, 256)
        self.up3 = nn.ConvTranspose2d(256, 128, kernel_size=2, stride=2)
        self.decoder3 = DoubleConv(256, 128)
        self.up2 = nn.ConvTranspose2d(128, 64, kernel_size=2, stride=2)
        self.decoder2 = DoubleConv(128, 64)
        self.up1 = nn.ConvTranspose2d(64, 32, kernel_size=2, stride=2)
        self.decoder1 = DoubleConv(64, 32)
        self.output = nn.Conv2d(32, 1, kernel_size=1)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        e1 = self.encoder1(value)
        e2 = self.encoder2(self.pool(e1))
        e3 = self.encoder3(self.pool(e2))
        e4 = self.encoder4(self.pool(e3))
        center = self.bottleneck(self.pool(e4))
        d4 = self.decoder4(torch.cat((self.up4(center), e4), dim=1))
        d3 = self.decoder3(torch.cat((self.up3(d4), e3), dim=1))
        d2 = self.decoder2(torch.cat((self.up2(d3), e2), dim=1))
        d1 = self.decoder1(torch.cat((self.up1(d2), e1), dim=1))
        return self.output(d1)


class TileDataset(Dataset[tuple[torch.Tensor, torch.Tensor]]):
    def __init__(
        self,
        archive_path: Path,
        records: list[dict[str, Any]],
        augment: bool,
        seed: int,
    ) -> None:
        self.images: list[torch.Tensor] = []
        self.masks: list[torch.Tensor] = []
        self.augment = augment
        self.random = random.Random(seed)
        with zipfile.ZipFile(archive_path) as archive:
            for record in records:
                image_data = archive.read(record["image_member"])
                mask_data = archive.read(record["mask_member"])
                with Image.open(io.BytesIO(image_data)) as image:
                    image_array = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
                with Image.open(io.BytesIO(mask_data)) as mask:
                    mask_array = np.asarray(mask.convert("L"), dtype=np.uint8).copy()
                image_tensor = torch.from_numpy(image_array).permute(2, 0, 1)
                mask_tensor = torch.from_numpy((mask_array == 255).astype(np.float32))[None]
                height, width = mask_tensor.shape[-2:]
                pad_height = (-height) % 16
                pad_width = (-width) % 16
                if pad_height or pad_width:
                    image_tensor = F.pad(image_tensor, (0, pad_width, 0, pad_height))
                    mask_tensor = F.pad(mask_tensor, (0, pad_width, 0, pad_height))
                self.images.append(image_tensor)
                self.masks.append(mask_tensor)

    def __len__(self) -> int:
        return len(self.images)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        image = self.images[index].float().div_(255.0)
        mask = self.masks[index]
        if self.augment:
            if self.random.random() < 0.5:
                image = torch.flip(image, dims=(2,))
                mask = torch.flip(mask, dims=(2,))
            if self.random.random() < 0.5:
                image = torch.flip(image, dims=(1,))
                mask = torch.flip(mask, dims=(1,))
            rotations = self.random.randrange(4)
            if rotations:
                image = torch.rot90(image, rotations, dims=(1, 2))
                mask = torch.rot90(mask, rotations, dims=(1, 2))
        return image, mask


def soft_dice_loss(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    probability = torch.sigmoid(logits)
    numerator = 2.0 * torch.sum(probability * target) + 1e-6
    denominator = torch.sum(probability) + torch.sum(target) + 1e-6
    return 1.0 - numerator / denominator


def tensor_dice(logits: torch.Tensor, target: torch.Tensor) -> float:
    prediction = torch.sigmoid(logits) >= THRESHOLD
    truth = target >= 0.5
    intersection = torch.logical_and(prediction, truth).sum().item()
    denominator = prediction.sum().item() + truth.sum().item()
    return 1.0 if denominator == 0 else (2.0 * intersection / denominator)


def set_seeds() -> None:
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEED)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def run_smoke_test(device: torch.device) -> None:
    model = UNet().to(device)
    image = torch.zeros((1, 3, 512, 512), device=device)
    target = torch.zeros((1, 1, 512, 512), device=device)
    logits = model(image)
    loss = F.binary_cross_entropy_with_logits(logits, target) + soft_dice_loss(logits, target)
    loss.backward()
    print(
        json.dumps(
            {
                "device": str(device),
                "input_shape": [1, 3, 512, 512],
                "output_shape": list(logits.shape),
                "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
                "loss_finite": bool(torch.isfinite(loss).item()),
                "cuda_peak_memory_bytes": (
                    torch.cuda.max_memory_allocated(device) if device.type == "cuda" else None
                ),
            },
            indent=2,
        )
    )


def train_model(
    archive_path: Path,
    output_dir: Path,
    audit: dict[str, Any],
    device: torch.device,
) -> None:
    set_seeds()
    training_data = TileDataset(archive_path, audit["training"], True, SEED)
    validation_data = TileDataset(archive_path, audit["validation"], False, SEED)
    train_generator = torch.Generator().manual_seed(SEED)
    train_loader = DataLoader(
        training_data, batch_size=1, shuffle=True, num_workers=0, generator=train_generator
    )
    validation_loader = DataLoader(
        validation_data, batch_size=1, shuffle=False, num_workers=0
    )
    model = UNet().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    best_dice = -math.inf
    best_epoch = 0
    epochs_without_improvement = 0
    history: list[dict[str, Any]] = []
    checkpoint_path = output_dir / "checkpoint_best.pt"
    started = time.time()

    for epoch in range(1, MAX_EPOCHS + 1):
        model.train()
        train_losses: list[float] = []
        for images, masks in train_loader:
            images = images.to(device)
            masks = masks.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = 0.5 * F.binary_cross_entropy_with_logits(logits, masks)
            loss = loss + 0.5 * soft_dice_loss(logits, masks)
            loss.backward()
            optimizer.step()
            train_losses.append(float(loss.detach().item()))

        model.eval()
        validation_dice: list[float] = []
        with torch.no_grad():
            for images, masks in validation_loader:
                logits = model(images.to(device))
                validation_dice.append(tensor_dice(logits.cpu(), masks))
        mean_validation_dice = float(np.mean(validation_dice))
        mean_train_loss = float(np.mean(train_losses))
        history.append(
            {
                "epoch": epoch,
                "train_loss": mean_train_loss,
                "validation_dice_at_0_5": mean_validation_dice,
            }
        )
        print(
            f"epoch={epoch:03d} train_loss={mean_train_loss:.6f} "
            f"validation_dice={mean_validation_dice:.6f}"
        )

        if mean_validation_dice > best_dice:
            best_dice = mean_validation_dice
            best_epoch = epoch
            epochs_without_improvement = 0
            temporary = checkpoint_path.with_suffix(".tmp")
            torch.save(
                {
                    "model_state": model.state_dict(),
                    "best_epoch": best_epoch,
                    "validation_dice": best_dice,
                    "threshold": THRESHOLD,
                    "seed": SEED,
                    "train_families": audit["summary"]["training_families"],
                    "validation_families": audit["summary"]["validation_families"],
                },
                temporary,
            )
            temporary.replace(checkpoint_path)
        else:
            epochs_without_improvement += 1

        with (output_dir / "train_history.csv").open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(file, fieldnames=list(history[0]))
            writer.writeheader()
            writer.writerows(history)
        if epochs_without_improvement >= PATIENCE:
            break

    checkpoint_sha256 = sha256_bytes(checkpoint_path.read_bytes())
    run_metadata = {
        "status": "completed",
        "device": str(device),
        "seed": SEED,
        "epochs_completed": len(history),
        "best_epoch": best_epoch,
        "best_validation_dice_at_0_5": best_dice,
        "threshold": THRESHOLD,
        "checkpoint": checkpoint_path.name,
        "checkpoint_sha256": checkpoint_sha256,
        "elapsed_seconds": round(time.time() - started, 2),
        "train_pairs": len(training_data),
        "validation_pairs": len(validation_data),
        "train_families": audit["summary"]["training_families"],
        "validation_families": audit["summary"]["validation_families"],
        "test_pixels_decoded": False,
    }
    write_json(output_dir / "run_metadata.json", run_metadata)
    print(json.dumps(run_metadata, indent=2))


def pixel_metrics(
    prediction: np.ndarray, target: np.ndarray
) -> dict[str, float | None]:
    prediction = prediction.astype(bool)
    target = target.astype(bool)
    tp = int(np.logical_and(prediction, target).sum())
    fp = int(np.logical_and(prediction, ~target).sum())
    fn = int(np.logical_and(~prediction, target).sum())
    tn = int(np.logical_and(~prediction, ~target).sum())
    dice_denominator = 2 * tp + fp + fn
    iou_denominator = tp + fp + fn
    pixel_count = tp + fp + fn + tn
    return {
        "dice": 1.0 if dice_denominator == 0 else 2 * tp / dice_denominator,
        "iou": 1.0 if iou_denominator == 0 else tp / iou_denominator,
        "sensitivity": None if tp + fn == 0 else tp / (tp + fn),
        "specificity": None if tn + fp == 0 else tn / (tn + fp),
        "pixel_accuracy": None if pixel_count == 0 else (tp + tn) / pixel_count,
    }


def bootstrap_ci(
    records: list[dict[str, Any]], metric: str, seed: int
) -> list[float] | None:
    by_group: dict[str, list[float]] = defaultdict(list)
    for record in records:
        value = record[metric]
        if value is not None:
            by_group[record["family_id"]].append(float(value))
    groups = sorted(by_group)
    if len(groups) < 2:
        return None

    rng = np.random.default_rng(seed)
    estimates = np.empty(10_000, dtype=np.float64)
    for index in range(len(estimates)):
        sampled_groups = rng.choice(groups, size=len(groups), replace=True)
        sampled_values = [
            value
            for group in sampled_groups
            for value in by_group[str(group)]
        ]
        estimates[index] = float(np.mean(sampled_values))
    return [float(np.percentile(estimates, 2.5)), float(np.percentile(estimates, 97.5))]


def evaluate_once(
    archive_path: Path,
    output_dir: Path,
    audit: dict[str, Any],
    device: torch.device,
) -> None:
    checkpoint_path = output_dir / "checkpoint_best.pt"
    metrics_path = output_dir / "test_metrics.json"
    started_path = output_dir / "test_evaluation_started.json"
    if not checkpoint_path.is_file():
        raise FileNotFoundError("Cannot evaluate: frozen best checkpoint is missing")
    if metrics_path.exists() or started_path.exists():
        raise FileExistsError(
            "Test evaluation has already started or completed; refusing a second test run"
        )

    checkpoint_hash = sha256_bytes(checkpoint_path.read_bytes())
    run_metadata_path = output_dir / "run_metadata.json"
    if not run_metadata_path.is_file():
        raise FileNotFoundError("Cannot evaluate before training metadata is complete")
    run_metadata = json.loads(run_metadata_path.read_text(encoding="utf-8"))
    if run_metadata.get("status") != "completed":
        raise ValueError("Cannot evaluate: training run is not marked completed")
    if run_metadata.get("checkpoint_sha256") != checkpoint_hash:
        raise ValueError("Checkpoint hash differs from the frozen training record")
    write_json(
        started_path,
        {
            "status": "started",
            "checkpoint_sha256": checkpoint_hash,
            "threshold": THRESHOLD,
            "test_pair_count": len(audit["test"]),
            "started_unix_time": time.time(),
        },
    )

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    if checkpoint.get("threshold") != THRESHOLD:
        raise ValueError("Checkpoint threshold differs from the preregistered threshold")
    model = UNet().to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    results: list[dict[str, Any]] = []
    with zipfile.ZipFile(archive_path) as archive, torch.no_grad():
        for record in audit["test"]:
            image_bytes = archive.read(record["image_member"])
            mask_bytes = archive.read(record["mask_member"])
            if sha256_bytes(image_bytes) != record["image_sha256"]:
                raise ValueError(f"Test image changed after audit: {record['image_member']}")
            if sha256_bytes(mask_bytes) != record["mask_sha256"]:
                raise ValueError(f"Test mask changed after audit: {record['mask_member']}")
            with Image.open(io.BytesIO(image_bytes)) as image:
                image.load()
                image_array = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
            with Image.open(io.BytesIO(mask_bytes)) as mask:
                mask.load()
                mask_array = np.asarray(mask.convert("L"), dtype=np.uint8).copy()
            if image_array.shape[:2] != mask_array.shape:
                raise ValueError(f"Test image/mask geometry mismatch: {record['stem']}")
            mask_values = np.unique(mask_array)
            if not np.array_equal(mask_values, np.array([0, 255], dtype=mask_values.dtype)):
                raise ValueError(
                    f"Expected binary test mask values 0 and 255, got "
                    f"{mask_values.tolist()}: {record['mask_member']}"
                )

            height, width = mask_array.shape
            pad_height = (-height) % 16
            pad_width = (-width) % 16
            input_tensor = torch.from_numpy(image_array).permute(2, 0, 1).float().div_(255.0)
            input_tensor = F.pad(input_tensor, (0, pad_width, 0, pad_height))[None].to(device)
            probability = torch.sigmoid(model(input_tensor))[0, 0, :height, :width]
            prediction = (probability >= THRESHOLD).cpu().numpy()
            target = mask_array == 255
            result = {
                "stem": record["stem"],
                "family_id": record["family_id"],
                "image_member": record["image_member"],
                "mask_member": record["mask_member"],
                **pixel_metrics(prediction, target),
            }
            results.append(result)
            print(
                f"test={record['stem']} dice={result['dice']:.6f} "
                f"iou={result['iou']:.6f} sensitivity={result['sensitivity']} "
                f"specificity={result['specificity']}"
            )

    metric_names = ("dice", "iou", "sensitivity", "specificity")
    macro = {}
    for metric in metric_names:
        values = [r[metric] for r in results if r[metric] is not None]
        macro[metric] = None if not values else float(np.mean(values))
    confidence_intervals = {
        metric: bootstrap_ci(results, metric, BOOTSTRAP_SEED)
        for metric in metric_names
    }
    summary = {
        "status": "completed",
        "checkpoint_sha256": checkpoint_hash,
        "threshold": THRESHOLD,
        "test_images": len(results),
        "test_filename_families": sorted({r["family_id"] for r in results}),
        "family_ids_are_verified_patient_ids": False,
        "macro_per_image_metrics": macro,
        "group_bootstrap_95_percent_confidence_intervals": confidence_intervals,
        "bootstrap_resamples": 10_000,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "empty_mask_handling": (
            "Dice/IoU are 1 only when prediction and target are both empty; "
            "sensitivity is null when target has no positive pixels; "
            "specificity is null when target has no negative pixels."
        ),
        "per_image_metrics": results,
    }
    write_json(metrics_path, summary)
    with (output_dir / "test_metrics_per_image.csv").open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    started_path.unlink()
    print(json.dumps({k: v for k, v in summary.items() if k != "per_image_metrics"}, indent=2))


def evaluate_all_samples(
    archive_path: Path,
    output_dir: Path,
    audit: dict[str, Any],
    device: torch.device,
) -> None:
    metrics_path = output_dir / "all_sample_metrics.json"
    csv_path = output_dir / "all_sample_metrics_per_image.csv"
    if metrics_path.exists() or csv_path.exists():
        raise FileExistsError(
            "All-sample evaluation outputs already exist; refusing to overwrite them"
        )

    checkpoint_path = output_dir / "checkpoint_best.pt"
    run_metadata_path = output_dir / "run_metadata.json"
    if not checkpoint_path.is_file() or not run_metadata_path.is_file():
        raise FileNotFoundError("A completed RENFAST training checkpoint is required")
    checkpoint_hash = sha256_file(checkpoint_path)
    run_metadata = json.loads(run_metadata_path.read_text(encoding="utf-8"))
    if run_metadata.get("status") != "completed":
        raise ValueError("The training run is not marked completed")
    if run_metadata.get("checkpoint_sha256") != checkpoint_hash:
        raise ValueError("Checkpoint hash differs from the frozen training record")

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    if checkpoint.get("threshold") != THRESHOLD:
        raise ValueError("Checkpoint threshold differs from the preregistered threshold")
    model = UNet().to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    records = audit["training"] + audit["validation"] + audit["excluded"] + audit["test"]
    split_assignments = {
        "training": "training",
        "validation": "validation",
        "excluded": "excluded_shared_with_test_family",
        "official_test": "official_test",
    }
    results: list[dict[str, Any]] = []
    with zipfile.ZipFile(archive_path) as archive, torch.no_grad():
        for split_name, split_records in (
            ("training", audit["training"]),
            ("validation", audit["validation"]),
            ("excluded", audit["excluded"]),
            ("official_test", audit["test"]),
        ):
            for record in split_records:
                image_bytes = archive.read(record["image_member"])
                mask_bytes = archive.read(record["mask_member"])
                if sha256_bytes(image_bytes) != record["image_sha256"]:
                    raise ValueError(f"Image changed after audit: {record['image_member']}")
                if sha256_bytes(mask_bytes) != record["mask_sha256"]:
                    raise ValueError(f"Mask changed after audit: {record['mask_member']}")
                with Image.open(io.BytesIO(image_bytes)) as image:
                    image_array = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
                with Image.open(io.BytesIO(mask_bytes)) as mask:
                    mask_array = np.asarray(mask.convert("L"), dtype=np.uint8).copy()
                if image_array.shape[:2] != mask_array.shape:
                    raise ValueError(f"Image/mask geometry mismatch: {record['stem']}")
                values = np.unique(mask_array)
                if not np.array_equal(values, np.array([0, 255], dtype=values.dtype)):
                    raise ValueError(f"Non-binary fibrosis mask: {record['mask_member']}")

                height, width = mask_array.shape
                pad_height = (-height) % 16
                pad_width = (-width) % 16
                input_tensor = (
                    torch.from_numpy(image_array).permute(2, 0, 1).float().div_(255.0)
                )
                input_tensor = F.pad(input_tensor, (0, pad_width, 0, pad_height))
                probability = torch.sigmoid(model(input_tensor[None].to(device)))[
                    0, 0, :height, :width
                ]
                prediction = (probability >= THRESHOLD).cpu().numpy()
                scores = pixel_metrics(prediction, mask_array == 255)
                results.append(
                    {
                        "evaluation_split": split_name,
                        "assignment": split_assignments[split_name],
                        "stem": record["stem"],
                        "family_id": record["family_id"],
                        "image_member": record["image_member"],
                        **scores,
                    }
                )
                print(
                    f"split={split_name} image={record['stem']} "
                    f"dice={scores['dice']:.6f} "
                    f"pixel_accuracy={scores['pixel_accuracy']:.6f}"
                )

    metric_names = (
        "dice",
        "iou",
        "sensitivity",
        "specificity",
        "pixel_accuracy",
    )
    by_split: dict[str, dict[str, Any]] = {}
    for split_name in ("training", "validation", "excluded", "official_test"):
        split_results = [r for r in results if r["evaluation_split"] == split_name]
        by_split[split_name] = {
            "images": len(split_results),
            "filename_families": sorted({r["family_id"] for r in split_results}),
            "macro_per_image_metrics": {
                metric: (
                    None
                    if not (values := [
                        float(r[metric])
                        for r in split_results
                        if r[metric] is not None
                    ])
                    else float(np.mean(values))
                )
                for metric in metric_names
            },
        }

    test_results = [r for r in results if r["evaluation_split"] == "official_test"]
    test_intervals = {
        metric: bootstrap_ci(test_results, metric, BOOTSTRAP_SEED)
        for metric in metric_names
    }
    result = {
        "status": "completed",
        "checkpoint_sha256": checkpoint_hash,
        "threshold": THRESHOLD,
        "unique_images_evaluated": len(results),
        "duplicate_training_entries_not_recounted": audit["summary"][
            "official_train_exact_duplicate_pairs"
        ],
        "overall_macro_per_image_metrics": {
            metric: (
                None
                if not (values := [
                    float(record[metric])
                    for record in results
                    if record[metric] is not None
                ])
                else float(np.mean(values))
            )
            for metric in metric_names
        },
        "split_results": by_split,
        "official_test_group_bootstrap_95_percent_confidence_intervals": test_intervals,
        "bootstrap_resamples": 10_000,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "pixel_accuracy_definition": "(true positive pixels + true negative pixels) / all pixels",
        "limitations": [
            "Training-set scores are in-sample and should not be read as generalization accuracy.",
            "Filename-family IDs have not been verified as patient or biopsy identifiers.",
            "The official test is an internal RENFAST benchmark, not external clinical validation.",
            "Scores measure agreement with the supplied binary masks, not diagnostic accuracy.",
        ],
        "per_image_metrics": results,
    }
    write_json(metrics_path, result)
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    print(json.dumps({k: v for k, v in result.items() if k != "per_image_metrics"}, indent=2))


def predict_patch(
    image_path: Path,
    prediction_path: Path,
    output_dir: Path,
    device: torch.device,
) -> None:
    checkpoint_path = output_dir / "checkpoint_best.pt"
    run_metadata_path = output_dir / "run_metadata.json"
    if not image_path.is_file():
        raise FileNotFoundError(f"Input patch not found: {image_path}")
    if not checkpoint_path.is_file() or not run_metadata_path.is_file():
        raise FileNotFoundError("A completed RENFAST training checkpoint is required")
    if prediction_path.exists() or prediction_path.with_suffix(".json").exists():
        raise FileExistsError("Prediction output already exists; choose a new output path")

    run_metadata = json.loads(run_metadata_path.read_text(encoding="utf-8"))
    checkpoint_hash = sha256_file(checkpoint_path)
    if run_metadata.get("status") != "completed":
        raise ValueError("The training run is not marked completed")
    if run_metadata.get("checkpoint_sha256") != checkpoint_hash:
        raise ValueError("Checkpoint hash differs from the frozen training record")

    image_bytes = image_path.read_bytes()
    with Image.open(io.BytesIO(image_bytes)) as image:
        image.load()
        image_array = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
    if image_array.shape[:2] != (512, 512):
        raise ValueError(
            "This baseline accepts one 512x512 patch at a time; it does not "
            "resize whole-slide images."
        )

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    if checkpoint.get("threshold") != THRESHOLD:
        raise ValueError("Checkpoint threshold differs from the preregistered threshold")
    model = UNet().to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    input_tensor = (
        torch.from_numpy(image_array).permute(2, 0, 1).float().div_(255.0)[None].to(device)
    )
    with torch.no_grad():
        probability = torch.sigmoid(model(input_tensor))[0, 0].cpu().numpy()
    prediction = (probability >= THRESHOLD).astype(np.uint8) * 255

    prediction_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(prediction).save(prediction_path)
    metadata = {
        "status": "research_only_segmentation",
        "input_sha256": sha256_bytes(image_bytes),
        "checkpoint_sha256": checkpoint_hash,
        "threshold": THRESHOLD,
        "input_dimensions": [512, 512],
        "predicted_positive_pixel_fraction": float(np.mean(prediction == 255)),
        "prediction_mask": prediction_path.name,
        "warning": (
            "Not a diagnosis or fibrosis score. Intended only for 512x512 "
            "Masson's trichrome patches similar to RENFAST; expert review and "
            "external validation are required."
        ),
    }
    write_json(prediction_path.with_suffix(".json"), metadata)
    print(json.dumps(metadata, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("audit", "smoke", "train", "evaluate", "evaluate-all", "predict"),
        required=True,
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=Path(r"D:\patent\m2t49zf6xr-1.zip"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(r"D:\patent\stage2A_audit\renfast_baseline_run"),
    )
    parser.add_argument("--image", type=Path)
    parser.add_argument("--prediction", type=Path)
    args = parser.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if args.mode == "smoke":
        set_seeds()
        run_smoke_test(device)
        return

    if args.mode == "predict":
        if args.image is None or args.prediction is None:
            parser.error("--mode predict requires --image and --prediction")
        predict_patch(args.image, args.prediction, args.output_dir, device)
        return

    audit = build_audit(args.archive, args.output_dir)
    if args.mode == "train":
        train_model(args.archive, args.output_dir, audit, device)
    elif args.mode == "evaluate":
        evaluate_once(args.archive, args.output_dir, audit, device)
    elif args.mode == "evaluate-all":
        evaluate_all_samples(args.archive, args.output_dir, audit, device)


if __name__ == "__main__":
    main()
