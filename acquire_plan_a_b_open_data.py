import csv
import hashlib
import re
import shutil
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(r"D:\patent")
DATA = ROOT / "data"
REPOSITORY_CSV = ROOT / "atlas_repository_filelist-20261105.csv"
CHECKLIST_CSV = ROOT / "tier_a_download_checklist.csv"
MANIFEST_CSV = ROOT / "data_manifest.csv"
BASE_URL = "https://atlas.kpmp.org/api/v1/file/download"
MAX_FILE_BYTES = 5_000_000_000
MAX_BATCH_BYTES = 20_000_000_000
FREE_SPACE_RESERVE_BYTES = 2_000_000_000
CHUNK_SIZE = 1024 * 1024


def participant_ids(value):
    return [part.strip() for part in re.split(r"[,;]", value or "") if part.strip()]


def parse_size(value):
    match = re.fullmatch(r"\s*([\d.]+)\s*(B|KB|MB|GB|TB)\s*", value or "", re.I)
    if not match:
        raise ValueError(f"Unrecognized repository size: {value!r}")
    multipliers = {
        "B": 1,
        "KB": 1_000,
        "MB": 1_000_000,
        "GB": 1_000_000_000,
        "TB": 1_000_000_000_000,
    }
    return int(float(match.group(1)) * multipliers[match.group(2).upper()])


def eligible_records():
    with REPOSITORY_CSV.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    with CHECKLIST_CSV.open(encoding="utf-8-sig", newline="") as stream:
        participants = [row["participant_id"] for row in csv.DictReader(stream)]

    selected = []
    for participant in participants:
        rows_for_participant = [
            row
            for row in rows
            if row.get("Access", "").strip().lower() == "open"
            and participant in participant_ids(row.get("Participant ID", ""))
        ]
        for row in rows_for_participant:
            strategy = row.get("Experimental Strategy", "").strip()
            workflow = row.get("Workflow Type / Panel", "").strip()
            if (
                strategy == "Spatial Transcriptomics Visium"
                and workflow in {"Expression Matrix", "Spatial Imaging Data"}
            ) or ("Whole Slide" in strategy and workflow == "TRI stain") or (
                "Segmentation" in strategy
            ):
                selected.append((participant, row))
    return participants, selected


def destination(participant, row):
    strategy = row.get("Experimental Strategy", "").strip()
    workflow = row.get("Workflow Type / Panel", "").strip()
    if strategy == "Spatial Transcriptomics Visium":
        folder = "visium"
        reason = "Plan A/B: Visium expression and spot/image inputs"
    elif "Segmentation" in strategy:
        folder = "masks"
        reason = "Plan A/B: available open segmentation features"
    else:
        folder = "wsi"
        reason = "Plan A: open trichrome WSI"
    return DATA / participant / folder / row["File Name"], reason


def already_present(participant, row, target):
    if target.exists() and target.stat().st_size > 0:
        return target
    folder = target.parent
    strategy = row.get("Experimental Strategy", "").strip()
    workflow = row.get("Workflow Type / Panel", "").strip()
    if not folder.exists():
        return None

    if strategy == "Spatial Transcriptomics Visium" and workflow == "Expression Matrix":
        return next(
            (path for path in folder.glob("*expression_matrix*.zip") if path.stat().st_size),
            None,
        )
    if strategy == "Spatial Transcriptomics Visium" and workflow == "Spatial Imaging Data":
        spatial_dir = DATA / participant / "visium" / "outs" / "spatial"
        if (
            (spatial_dir / "tissue_positions.csv").exists()
            and (spatial_dir / "scalefactors_json.json").exists()
        ):
            return spatial_dir / "tissue_positions.csv"
        visium_id = re.search(r"V\d{2}[A-Z]\d{2}-\d+_XY\d{2}_\d{2}-\d+", row["File Name"])
        if visium_id:
            return next(
                (
                    path
                    for path in folder.glob("*")
                    if path.is_file()
                    and visium_id.group(0) in path.name
                    and path.stat().st_size
                ),
                None,
            )
        return next(
            (path for path in folder.glob("*spatial*.tar.gz") if path.stat().st_size),
            None,
        )
    slide_id = re.search(r"S-\d{4}-\d{6}", row["File Name"])
    if slide_id:
        if "Segmentation" in strategy:
            return next(
                (
                    path
                    for path in (DATA / participant / "masks").glob("*Seg_Masks_Features.zip")
                    if slide_id.group(0) in path.name and path.stat().st_size
                ),
                None,
            )
        search_dirs = [folder]
        for search_dir in search_dirs:
            if search_dir.exists():
                match = next(
                    (
                        path
                        for path in search_dir.rglob("*")
                        if path.is_file()
                        and not path.name.lower().endswith(".part")
                        and slide_id.group(0) in path.name
                        and path.stat().st_size
                    ),
                    None,
                )
                if match:
                    return match
    return None


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def append_manifest(url, filename, size, checksum, participant, reason):
    exists = MANIFEST_CSV.exists()
    with MANIFEST_CSV.open("a", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "URL",
                "date",
                "file_name",
                "size",
                "checksum",
                "participant_id",
                "reason",
            ],
        )
        if not exists or MANIFEST_CSV.stat().st_size == 0:
            writer.writeheader()
        writer.writerow(
            {
                "URL": url,
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "file_name": filename,
                "size": size,
                "checksum": checksum,
                "participant_id": participant,
                "reason": reason,
            }
        )


def download(url, target, expected_bytes):
    partial = target.with_name(target.name + ".part")
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=180) as response:
        status = response.getcode()
        append = offset > 0 and status == 206
        if offset > 0 and not append:
            offset = 0
        mode = "ab" if append else "wb"
        with partial.open(mode) as stream:
            while True:
                chunk = response.read(CHUNK_SIZE)
                if chunk:
                    stream.write(chunk)
                else:
                    break
    actual = partial.stat().st_size
    tolerance = max(2_000_000, int(expected_bytes * 0.02))
    if abs(actual - expected_bytes) > tolerance:
        raise ValueError(
            f"Downloaded size {actual} differs from repository estimate "
            f"{expected_bytes} by more than tolerance {tolerance}"
        )
    partial.replace(target)
    return actual


def safe_extract_zip(archive_path, destination_dir):
    destination_dir.mkdir(parents=True, exist_ok=True)
    root = destination_dir.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise ValueError(f"ZIP CRC check failed for {bad_member}")
        for member in archive.infolist():
            resolved = (destination_dir / member.filename).resolve()
            if root not in resolved.parents and resolved != root:
                raise ValueError(f"Unsafe ZIP member path: {member.filename}")
        archive.extractall(destination_dir)


def safe_extract_tar(archive_path, destination_dir):
    destination_dir.mkdir(parents=True, exist_ok=True)
    root = destination_dir.resolve()
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            resolved = (destination_dir / member.name).resolve()
            if root not in resolved.parents and resolved != root:
                raise ValueError(f"Unsafe TAR member path: {member.name}")
            if member.issym() or member.islnk():
                raise ValueError(f"Refusing archive link member: {member.name}")
        archive.extractall(destination_dir, members=members)


def extract_if_archive(participant, target):
    suffix = target.name.lower()
    if suffix.endswith(".zip"):
        if target.parent.name == "masks":
            existing_extract = next(
                (
                    path
                    for path in target.parent.iterdir()
                    if path.is_dir() and any(path.glob("README*"))
                ),
                None,
            )
            if existing_extract:
                print(f"  segmentation contents already extracted: {existing_extract}")
                return
        extract_dir = target.parent / f"{target.stem}_extracted"
        if not extract_dir.exists() or not any(extract_dir.iterdir()):
            safe_extract_zip(target, extract_dir)
            print(f"  extracted ZIP -> {extract_dir}")
    elif suffix.endswith((".tar.gz", ".tgz")):
        extract_dir = target.parent / "outs"
        if not (extract_dir / "spatial" / "tissue_positions.csv").exists():
            safe_extract_tar(target, target.parent)
            print(f"  extracted spatial TAR -> {target.parent}")


def main():
    participants, selected = eligible_records()
    estimated_by_participant = {participant: 0 for participant in participants}
    for participant, row in selected:
        expected = parse_size(row.get("Size", ""))
        if expected > MAX_FILE_BYTES:
            raise RuntimeError(
                f"Approval required before downloading >5 GB file: "
                f"{participant} {row['File Name']} ({row['Size']})"
            )
        estimated_by_participant[participant] += expected
    batch_estimate = sum(estimated_by_participant.values())
    if batch_estimate > MAX_BATCH_BYTES:
        raise RuntimeError(
            f"Approval required before downloading batch above 20 GB: "
            f"{batch_estimate / 1e9:.2f} GB"
        )
    free = shutil.disk_usage(ROOT.anchor).free
    if free < batch_estimate + FREE_SPACE_RESERVE_BYTES:
        raise RuntimeError(
            f"Insufficient D: space: {free / 1e9:.2f} GB free for "
            f"{batch_estimate / 1e9:.2f} GB planned plus reserve"
        )

    print(
        f"Open-only planned set: {len(selected)} files, "
        f"{batch_estimate / 1e9:.2f} GB estimated across {len(participants)} participants; "
        f"{free / 1e9:.2f} GB free."
    )
    failures = []
    for participant in participants:
        records = [(p, r) for p, r in selected if p == participant]
        if not records:
            continue
        print(f"\n=== {participant} ({estimated_by_participant[participant] / 1e9:.3f} GB) ===")
        for _, row in records:
            target, reason = destination(participant, row)
            target.parent.mkdir(parents=True, exist_ok=True)
            present = already_present(participant, row, target)
            if present:
                if present.suffix.lower() == ".zip" or present.name.lower().endswith(
                    (".tar.gz", ".tgz")
                ):
                    extract_if_archive(participant, present)
                print(f"  verified locally; skip download: {present.name}")
                continue
            package_id = row["Internal Package ID"].strip()
            url = f"{BASE_URL}/{package_id}/{quote(row['File Name'], safe='')}"
            expected = parse_size(row["Size"])
            try:
                actual = download(url, target, expected)
                checksum = sha256_file(target)
                extract_if_archive(participant, target)
                append_manifest(
                    url,
                    target.name,
                    actual,
                    checksum,
                    participant,
                    reason,
                )
                print(f"  downloaded {target.name}: {actual} bytes SHA256={checksum}")
            except (
                urllib.error.URLError,
                OSError,
                ValueError,
                zipfile.BadZipFile,
                tarfile.TarError,
            ) as error:
                failures.append(
                    {
                        "participant": participant,
                        "file": row["File Name"],
                        "url": url,
                        "error": str(error),
                    }
                )
                append_manifest(
                    url,
                    target.name,
                    target.stat().st_size if target.exists() else 0,
                    "",
                    participant,
                    f"{reason}; FAILED: {error}",
                )
                print(f"  FAILED: {row['File Name']}: {error}")
                time.sleep(1)

    print("\n=== Acquisition summary ===")
    if failures:
        print(f"{len(failures)} file(s) failed; see data_manifest.csv and retry after review.")
        for item in failures:
            print(f"{item['participant']} {item['file']}: {item['error']}")
    else:
        print("No download or extraction failures.")
    print(f"Manifest: {MANIFEST_CSV}")


if __name__ == "__main__":
    main()
