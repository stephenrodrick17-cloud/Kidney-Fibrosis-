"""Download only the 24 catalogued open expression/spatial files for Stage 1d."""

from __future__ import annotations

import csv
import hashlib
import shutil
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(r"D:\patent")
OUT = ROOT / "stage1d_confirm"
DATA_DIR = ROOT / "data_confirm"
ASSETS_CSV = ROOT / "stage1c_confirm" / "open_visium_extra_assets.csv"
CATALOG_CSV = ROOT / "atlas_repository_filelist-20261105.csv"
PLAN_PATH = OUT / "download_plan.csv"
MANIFEST_PATH = OUT / "data_manifest.csv"
ENDPOINT = "https://atlas.kpmp.org/api/v1/file/download"
PARTICIPANTS = {
    "164-10",
    "164-22",
    "27-10123",
    "27-10166",
    "27-10229",
    "29-10277",
    "29-10282",
    "30-11081",
    "34-11042",
    "34-11048",
    "933-10271",
    "933-11258",
}
ALLOWED_ROLES = {"open_expression_matrix", "spatial_bundle"}
MAX_FILE_BYTES = 1_000_000_000
MIN_FREE_AFTER_BYTES = 2_000_000_000


def now_text() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def build_plan() -> list[dict[str, Any]]:
    assets = [
        row
        for row in read_csv(ASSETS_CSV)
        if row["participant_id"] in PARTICIPANTS
        and row["asset_type"] in ALLOWED_ROLES
    ]
    catalog = {row["File Name"]: row for row in read_csv(CATALOG_CSV)}
    if len(assets) != 24 or {row["participant_id"] for row in assets} != PARTICIPANTS:
        raise AssertionError("Expected exactly two selected open assets for each of 12 participants")
    plan: list[dict[str, Any]] = []
    for asset in assets:
        record = catalog.get(asset["file_name"])
        if (
            record is None
            or record["Access"] != "open"
            or record["Participant ID"] != asset["participant_id"]
            or record["Internal Package ID"] == ""
        ):
            raise AssertionError(f"Catalog access or package ID validation failed: {asset['file_name']}")
        if asset["asset_type"] == "open_expression_matrix" and not asset["file_name"].endswith(".zip"):
            raise AssertionError(f"Unexpected expression matrix format: {asset['file_name']}")
        if asset["asset_type"] == "spatial_bundle" and not asset["file_name"].endswith((".zip", ".tar.gz")):
            raise AssertionError(f"Unexpected spatial bundle format: {asset['file_name']}")
        estimate = int(asset["estimated_bytes_from_rounded_catalog_size"])
        if estimate <= 0 or estimate > MAX_FILE_BYTES:
            raise RuntimeError(f"Catalog size is over the 1 GB limit: {asset['file_name']} ({estimate})")
        package_id = record["Internal Package ID"]
        plan.append(
            {
                "participant_id": asset["participant_id"],
                "asset_type": asset["asset_type"],
                "file_name": asset["file_name"],
                "catalog_size": asset["catalog_size"],
                "estimated_bytes": estimate,
                "access": record["Access"],
                "doi": record["DOIs"],
                "package_id": package_id,
                "url": f"{ENDPOINT}/{package_id}/{asset['file_name']}",
            }
        )
    counts: dict[str, int] = {}
    for row in plan:
        counts[row["participant_id"]] = counts.get(row["participant_id"], 0) + 1
    if any(counts.get(pid) != 2 for pid in PARTICIPANTS):
        raise AssertionError("Selected assets do not reconcile to 12 participants x 2 files")
    if len({row["file_name"] for row in plan}) != 24:
        raise AssertionError("Selected filenames are not unique")
    return plan


def write_plan(plan: list[dict[str, Any]]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with PLAN_PATH.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(plan[0]))
        writer.writeheader()
        writer.writerows(plan)


def download() -> None:
    plan = build_plan()
    write_plan(plan)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    plan_by_name = {row["file_name"]: row for row in plan}
    completed: list[dict[str, Any]] = []
    if MANIFEST_PATH.exists():
        for row in read_csv(MANIFEST_PATH):
            item = plan_by_name.get(row["file_name"])
            if (
                item is None
                or row["participant_id"] != item["participant_id"]
                or row["asset_type"] != item["asset_type"]
                or row["url"] != item["url"]
            ):
                raise AssertionError(f"Existing manifest row is not in the authorized plan: {row}")
            target = DATA_DIR / row["file_name"]
            if (
                not target.is_file()
                or target.stat().st_size != int(row["size_bytes"])
                or hashlib.sha256(target.read_bytes()).hexdigest() != row["sha256"]
            ):
                raise IOError(f"Existing downloaded file failed manifest verification: {target}")
            completed.append(row)
    completed_names = {row["file_name"] for row in completed}
    if len(completed_names) != len(completed):
        raise AssertionError("Download manifest contains duplicate filenames")
    for path in DATA_DIR.iterdir():
        if path.name.endswith(".part"):
            continue
        if path.name not in completed_names:
            raise FileExistsError(f"Refusing to overwrite unverified data: {path}")
    if any(path.name.endswith(".part") for path in DATA_DIR.iterdir()):
        raise FileExistsError(f"Remove or inspect the incomplete partial file(s) in {DATA_DIR} before retrying")
    free = shutil.disk_usage(ROOT.drive + "\\").free
    remaining = [row for row in plan if row["file_name"] not in completed_names]
    estimate_total = sum(row["estimated_bytes"] for row in remaining)
    if free - estimate_total < MIN_FREE_AFTER_BYTES:
        raise RuntimeError(
            f"Insufficient space: {free} free, estimated {estimate_total} download bytes, "
            f"required post-download reserve {MIN_FREE_AFTER_BYTES}"
        )
    if max(row["estimated_bytes"] for row in plan) > MAX_FILE_BYTES:
        raise RuntimeError("At least one catalogued file exceeds 1 GB; stopping before download")
    remaining_estimate = estimate_total
    for item in remaining:
        if item["estimated_bytes"] > MAX_FILE_BYTES:
            raise RuntimeError(f"File exceeds 1 GB; stopping: {item['file_name']}")
        free = shutil.disk_usage(ROOT.drive + "\\").free
        if free - remaining_estimate < MIN_FREE_AFTER_BYTES:
            raise RuntimeError("Disk reserve would fall below 2 GB; stopping before next file")
        target = DATA_DIR / item["file_name"]
        partial = DATA_DIR / (item["file_name"] + ".part")
        if target.exists() or partial.exists():
            raise FileExistsError(f"Refusing to overwrite an existing download: {target}")
        last_error: Exception | None = None
        for attempt in range(1, 4):
            digest = hashlib.sha256()
            bytes_written = 0
            request = urllib.request.Request(
                item["url"],
                headers={"User-Agent": "Stage1d-confirmation/1.0"},
            )
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    status = getattr(response, "status", None)
                    disposition = response.headers.get("Content-Disposition", "")
                    if status != 200 or item["file_name"] not in disposition:
                        raise RuntimeError(
                            f"Unexpected download response for {item['file_name']}: "
                            f"status={status}, disposition={disposition!r}"
                        )
                    content_length = response.headers.get("Content-Length")
                    reader = getattr(response, "read1", response.read)
                    with partial.open("xb") as output:
                        while True:
                            chunk = reader(1024 * 1024)
                            if not chunk:
                                break
                            bytes_written += len(chunk)
                            if bytes_written > MAX_FILE_BYTES:
                                raise RuntimeError(
                                    f"Actual download exceeded 1 GB; stopping: {item['file_name']}"
                                )
                            output.write(chunk)
                            digest.update(chunk)
                    if content_length and bytes_written != int(content_length):
                        raise IOError(
                            f"Content-Length mismatch for {item['file_name']}: "
                            f"{bytes_written} != {content_length}"
                        )
                if bytes_written <= 0:
                    raise IOError(f"Empty download: {item['file_name']}")
                partial.replace(target)
                last_error = None
                break
            except Exception as error:
                last_error = error
                if partial.exists():
                    partial.unlink()
                if attempt < 3:
                    time.sleep(attempt * 3)
        if last_error is not None:
            raise RuntimeError(
                f"Download failed after three attempts: {item['file_name']}"
            ) from last_error
        completed.append(
            {
                "url": item["url"],
                "downloaded_at": now_text(),
                "file_name": item["file_name"],
                "participant_id": item["participant_id"],
                "asset_type": item["asset_type"],
                "size_bytes": bytes_written,
                "sha256": digest.hexdigest(),
                "reason": "Open expression matrix or spatial bundle required for Stage 1d confirmation",
                "step_needed": "Stage 1d steps 2-3",
                "access": item["access"],
                "catalog_size": item["catalog_size"],
                "doi": item["doi"],
            }
        )
        remaining_estimate -= item["estimated_bytes"]
        with MANIFEST_PATH.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(completed[0]))
            writer.writeheader()
            writer.writerows(completed)
        print(
            f"{len(completed):02d}/24 {item['participant_id']} {item['file_name']} "
            f"{bytes_written} bytes sha256={digest.hexdigest()}"
        )
    if len(completed) != 24:
        raise AssertionError(f"Downloaded {len(completed)} files, expected 24")
    post_free = shutil.disk_usage(ROOT.drive + "\\").free
    if post_free < MIN_FREE_AFTER_BYTES:
        raise RuntimeError(f"Post-download disk reserve is below 2 GB: {post_free}")
    print(
        {
            "downloaded_files": len(completed),
            "download_bytes": sum(int(row["size_bytes"]) for row in completed),
            "free_bytes_after": post_free,
        }
    )


if __name__ == "__main__":
    download()
