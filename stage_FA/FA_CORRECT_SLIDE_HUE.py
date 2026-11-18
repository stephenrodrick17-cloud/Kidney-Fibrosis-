from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np
from PIL import Image

import FA_RUN_IMAGES as image_runner

ROOT = Path(r"D:\patent")
OUT = ROOT / "stage_FA"
ALIGNMENT = ROOT / "stage_G2" / "GENE2_ALIGNMENT_AUDIT.csv"
OLD_SLIDE_FILE = OUT / "FA_SLIDE_FIBROSIS_FRACTIONS.csv"
ANALYSIS_LABEL = "EXPLORATORY, NOT CONFIRMATORY"
MASK_LABEL = "UNVALIDATED MASKS"
ASSET_STATUS = "RESEARCH-ONLY"
MAX_RUNTIME_SECONDS = 95 * 60
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


def main() -> None:
    started = time.monotonic()
    started_utc = datetime.now(timezone.utc)
    deadline = started + MAX_RUNTIME_SECONDS
    alignment = read_csv(ALIGNMENT)
    old_rows = read_csv(OLD_SLIDE_FILE)
    slide_by_key = {
        (row["participant_id"], row["library_id"]): row for row in old_rows
    }
    if len(alignment) != 41 or len(slide_by_key) != 41:
        raise ValueError("The image-only table does not contain all 41 libraries.")
    if directory_size(OUT) >= MAX_OUTPUT_BYTES:
        raise RuntimeError("Stage FA output folder already meets the registered size limit.")
    hash_rows = []
    archive_cache: dict[Path, str] = {}

    def record_hash(path: Path, member: str | None, content: bytes, kind: str) -> None:
        if member is not None and path not in archive_cache:
            archive_cache[path] = sha256_file(path)
            hash_rows.append(
                {
                    "analysis_label": ANALYSIS_LABEL,
                    "mask_status": MASK_LABEL,
                    "asset_status": ASSET_STATUS,
                    "record_type": "input",
                    "source_kind": "source archive file",
                    "source_path": str(path),
                    "archive_member": "",
                    "sha256": archive_cache[path],
                }
            )
        hash_rows.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "record_type": "input",
                "source_kind": kind,
                "source_path": str(path),
                "archive_member": member or "",
                "sha256": image_runner.sha256_bytes(content),
            }
        )

    final_rows = []
    for index, row in enumerate(alignment, start=1):
        if time.monotonic() >= deadline:
            raise TimeoutError("Stopped before the preregistered process limit.")
        image_ref = image_runner.resolve_row_reference(row["image_record"], row)
        scale_ref = image_runner.sibling_reference(image_ref, "scalefactors_json.json")
        image_bytes, image_path, image_member = image_runner.read_reference(image_ref)
        scale_bytes, scale_path, scale_member = image_runner.read_reference(scale_ref)
        record_hash(image_path, image_member, image_bytes, "slide image")
        record_hash(scale_path, scale_member, scale_bytes, "scale factors")
        with Image.open(io.BytesIO(image_bytes)) as source_image:
            hires = np.asarray(source_image.convert("RGB"), dtype=np.uint8).copy()
        scale = json.loads(scale_bytes.decode("utf-8"))
        spot_diameter = float(scale["spot_diameter_fullres"])
        hires_scale = float(scale["tissue_hires_scalef"])
        source_mpp = image_runner.NOMINAL_SPOT_UM / (spot_diameter * hires_scale)
        factor = source_mpp / image_runner.TARGET_MPP
        old_height, old_width = hires.shape[:2]
        width = max(1, int(round(old_width * factor)))
        height = max(1, int(round(old_height * factor)))
        resized = np.asarray(
            Image.fromarray(hires, mode="RGB").resize(
                (width, height), resample=Image.Resampling.LANCZOS
            ),
            dtype=np.uint8,
        )
        tissue = resized.mean(axis=2) < 245.0
        if not tissue.any():
            raise ValueError(f"No tissue pixels under the registered rule: {row['participant_id']}/{row['library_id']}")
        hue = np.asarray(Image.fromarray(resized, mode="RGB").convert("HSV"))[:, :, 0]
        key = (row["participant_id"], row["library_id"])
        result = dict(slide_by_key[key])
        result["median_tissue_hue"] = float(np.median(hue[tissue]))
        result["hue_method"] = "median 8-bit HSV hue among pixels with mean RGB < 245"
        result["analysis_label"] = ANALYSIS_LABEL
        result["mask_status"] = MASK_LABEL
        result["asset_status"] = ASSET_STATUS
        final_rows.append(result)
        print(f"Corrected slide hue {index}/{len(alignment)}: {key[0]}/{key[1]}")

    final_path = OUT / "FA_SLIDE_FIBROSIS_FRACTIONS_FINAL.csv"
    if final_path.exists():
        raise FileExistsError(f"Refusing to overwrite {final_path}")
    with final_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(final_rows[0]))
        writer.writeheader()
        writer.writerows(final_rows)

    provenance = [
        ALIGNMENT,
        OLD_SLIDE_FILE,
        OUT / "FA_PREREG.md",
        OUT / "FA_DEVIATIONS.md",
        OUT / "FA_CORRECT_SLIDE_HUE.py",
        OUT / "FA_RUN_IMAGES.py",
    ]
    for path in provenance:
        hash_rows.append(
            {
                "analysis_label": ANALYSIS_LABEL,
                "mask_status": MASK_LABEL,
                "asset_status": ASSET_STATUS,
                "record_type": "input",
                "source_kind": "image, score, or protocol",
                "source_path": str(path),
                "archive_member": "",
                "sha256": sha256_file(path),
            }
        )
    hash_rows.append(
        {
            "analysis_label": ANALYSIS_LABEL,
            "mask_status": MASK_LABEL,
            "asset_status": ASSET_STATUS,
            "record_type": "output",
            "source_kind": "corrected image-only slide table",
            "source_path": str(final_path),
            "archive_member": "",
            "sha256": sha256_file(final_path),
        }
    )
    hash_path = OUT / "FA_HUE_CORRECTION_HASHES.csv"
    if hash_path.exists():
        raise FileExistsError(f"Refusing to overwrite {hash_path}")
    with hash_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(hash_rows[0]))
        writer.writeheader()
        writer.writerows(hash_rows)
    metadata = {
        "analysis_label": ANALYSIS_LABEL,
        "mask_status": MASK_LABEL,
        "asset_status": ASSET_STATUS,
        "libraries": len(final_rows),
        "hue_definition": "median 8-bit HSV hue among tissue pixels",
        "command": "python -B D:\\patent\\stage_FA\\FA_CORRECT_SLIDE_HUE.py",
        "started_at_utc": started_utc.isoformat(),
        "runtime_seconds": round(time.monotonic() - started, 3),
        "outputs_bytes": directory_size(OUT),
        "expression_files_read": False,
    }
    metadata_path = OUT / "FA_HUE_CORRECTION_METADATA.json"
    if metadata_path.exists():
        raise FileExistsError(f"Refusing to overwrite {metadata_path}")
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
