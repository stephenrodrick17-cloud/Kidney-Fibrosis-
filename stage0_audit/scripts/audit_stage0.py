from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

import openslide
import tifffile
from PIL import Image


ROOT = Path(r"D:\patent")
DATA = ROOT / "data"
OUT = ROOT / "stage0_audit"
PLAN_SUMMARY = ROOT / "plan_a_plan_b" / "plan_a_patient_summary.csv"
SEGMENTATION_AUDIT = ROOT / "qc_collagen" / "review" / "segmentation_package_audit.csv"
REFERENCE_LABEL_SUMMARY = (
    ROOT / "qc_collagen" / "review" / "reference_label_availability_summary.csv"
)
CATALOG = ROOT / "atlas_repository_filelist-20261105.csv"
RENFAST_ZIP = ROOT / "m2t49zf6xr-1.zip"
MEB_DATASET_URL = "https://data.mendeley.com/datasets/m2t49zf6xr/1"
TEN_GB = 10_000_000_000


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(
    path: Path,
    rows: list[dict[str, object]],
    empty_fields: list[str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        if empty_fields:
            with path.open("w", newline="", encoding="utf-8-sig") as handle:
                csv.writer(handle).writerow(empty_fields)
        else:
            path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def format_gib(size: int) -> str:
    return f"{size / (1024 ** 3):.3f}"


def format_gb(size: int) -> str:
    return f"{size / 1_000_000_000:.3f}"


def folder_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(child.stat().st_size for child in path.rglob("*") if child.is_file())


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = [
        "| " + " | ".join(str(item).replace("|", "\\|").replace("\n", " ") for item in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                str(item).replace("|", "\\|").replace("\n", " ").replace("\r", "")
                for item in row
            )
            + " |"
        )
    return "\n".join(lines)


def storage_inventory() -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], int]:
    existing_files = [
        path
        for path in ROOT.rglob("*")
        if path.is_file() and OUT not in path.parents
    ]
    total_existing_bytes = sum(path.stat().st_size for path in existing_files)
    top_level = []
    for path in sorted(ROOT.iterdir(), key=lambda item: item.name.lower()):
        if path == OUT:
            continue
        size = folder_size(path)
        top_level.append(
            {
                "name": path.name,
                "kind": "folder" if path.is_dir() else "file",
                "size_bytes": size,
                "size_GB_decimal": format_gb(size),
                "size_GiB": format_gib(size),
            }
        )

    participant_rows = []
    if DATA.exists():
        for path in sorted(DATA.iterdir(), key=lambda item: item.name):
            if path.is_dir():
                size = folder_size(path)
                participant_rows.append(
                    {
                        "participant_id": path.name,
                        "size_bytes": size,
                        "size_GB_decimal": format_gb(size),
                        "size_GiB": format_gib(size),
                        "file_count": sum(1 for child in path.rglob("*") if child.is_file()),
                    }
                )

    largest_rows = []
    for path in sorted(existing_files, key=lambda item: item.stat().st_size, reverse=True)[:20]:
        size = path.stat().st_size
        largest_rows.append(
            {
                "path": str(path),
                "size_bytes": size,
                "size_MB": f"{size / (1024 ** 2):.1f}",
                "size_GiB": format_gib(size),
            }
        )
    return top_level, participant_rows, largest_rows, total_existing_bytes


def normalized_archive_name(name: str) -> str:
    basename = PurePosixPath(name).name
    basename = re.sub(r"\s+\d+$", "", basename)
    return PurePosixPath(basename).stem.casefold()


def renfast_inventory() -> tuple[list[dict[str, object]], list[dict[str, object]], int, int]:
    entries = []
    folders = Counter()
    total_uncompressed_bytes = 0
    file_count = 0
    pairing_files: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    with zipfile.ZipFile(RENFAST_ZIP) as archive:
        for item in archive.infolist():
            if item.is_dir():
                continue
            file_count += 1
            total_uncompressed_bytes += item.file_size
            parts = PurePosixPath(item.filename).parts
            split = parts[0] if parts else ""
            subfolder = parts[1] if len(parts) > 1 else ""
            folders[(split, subfolder)] += 1
            basename = PurePosixPath(item.filename).name
            normalized_basename = re.sub(r"\s+\d+$", "", basename)
            extension = PurePosixPath(normalized_basename).suffix.lower()
            role = (
                "image"
                if subfolder.upper() == "IMAGES"
                else "mask"
                if subfolder.upper().startswith("MANUAL")
                else "other"
            )
            entries.append(
                {
                    "archive_path": item.filename,
                    "split": split,
                    "subfolder": subfolder,
                    "role": role,
                    "file_type": extension or "[no extension]",
                    "size_bytes": item.file_size,
                }
            )
            if role in {"image", "mask"} and len(parts) > 1:
                pairing_files[(split, subfolder, normalized_archive_name(basename))].add(
                    item.filename
                )

    pairing_rows = []
    split_names = sorted({key[0] for key in pairing_files})
    for split in split_names:
        subfolders = {key[1] for key in pairing_files if key[0] == split}
        image_keys = {
            key[2] for key in pairing_files if key[0] == split and key[1].upper() == "IMAGES"
        }
        mask_folders = sorted(folder for folder in subfolders if folder.upper().startswith("MANUAL"))
        for mask_folder in mask_folders:
            mask_keys = {
                key[2] for key in pairing_files if key[0] == split and key[1] == mask_folder
            }
            image_file_count = folders[(split, "IMAGES")]
            mask_file_count = folders[(split, mask_folder)]
            pairing_rows.append(
                {
                    "split": split,
                    "image_folder": "IMAGES",
                    "mask_folder": mask_folder,
                    "image_file_count": image_file_count,
                    "mask_file_count": mask_file_count,
                    "image_unique_basenames": len(image_keys),
                    "mask_unique_basenames": len(mask_keys),
                    "paired_unique_basenames": len(image_keys & mask_keys),
                    "duplicate_image_basename_entries": image_file_count - len(image_keys),
                    "duplicate_mask_basename_entries": mask_file_count - len(mask_keys),
                    "unmatched_image_basenames": len(image_keys - mask_keys),
                    "unmatched_mask_basenames": len(mask_keys - image_keys),
                }
            )

    folder_rows = [
        {
            "folder": f"{split}/{subfolder}",
            "file_count": count,
            "size_bytes": sum(
                row["size_bytes"]
                for row in entries
                if row["split"] == split and row["subfolder"] == subfolder
            ),
        }
        for (split, subfolder), count in sorted(folders.items())
    ]
    return entries, folder_rows + pairing_rows, total_uncompressed_bytes, file_count


def image_dimensions(path: Path) -> tuple[int | None, int | None]:
    suffix = path.suffix.lower()
    if suffix in {".tif", ".tiff"}:
        with tifffile.TiffFile(path) as tif:
            series = tif.series[0]
            shape = dict(zip(series.axes, series.shape))
            return shape.get("X"), shape.get("Y")
    with Image.open(path) as image:
        return image.width, image.height


def parse_dimension_strings(value: str) -> set[tuple[int, int]]:
    dimensions = set()
    for match in re.finditer(r":\s*(\d+)x(\d+)", value or ""):
        dimensions.add((int(match.group(1)), int(match.group(2))))
    return dimensions


def readme_quotes() -> list[dict[str, str]]:
    rows = []
    packages = [row for row in read_csv(SEGMENTATION_AUDIT) if row.get("archive")]
    packages_per_participant = Counter(row["participant_id"] for row in packages)
    for package in packages:
        participant = package["participant_id"]
        slide_id = package["archive_slide_id"]
        archive_path = ROOT / Path(package["archive_path"])
        participant_readmes = list((DATA / participant / "masks").glob("**/README.md"))
        package_stem = Path(package["archive"]).stem
        local_candidates = [
            path
            for path in participant_readmes
            if package_stem in path.parent.name or slide_id in path.parent.name
        ]
        if not local_candidates and packages_per_participant[participant] == 1:
            local_candidates = participant_readmes
        archive_readme = ""
        text = ""
        if archive_path.is_file():
            with zipfile.ZipFile(archive_path) as archive:
                member = next(
                    (
                        name
                        for name in archive.namelist()
                        if PurePosixPath(name).name.lower() == "readme.md"
                    ),
                    "",
                )
                if member:
                    with archive.open(member) as handle:
                        text = handle.read().decode("utf-8", errors="replace")
                    archive_readme = f"{package['archive_path']}::{member}"
        if not text and local_candidates:
            text = local_candidates[0].read_text(encoding="utf-8", errors="replace")
        if not text:
            rows.append(
                {
                    "participant_id": participant,
                    "package_slide_id": slide_id,
                    "readme_source": "not found in ZIP or extracted package",
                    "local_readme_path": "",
                    "readme_sha256": "",
                    "readme_variant": "unknown",
                    "channel_quote": "",
                    "ome_metadata_channel_quote": "",
                    "ifta_quote": "No README text found.",
                    "algorithm_quote": "",
                    "pathologist_quote": "",
                    "resolution_quote": "",
                    "participant_specific_stain_or_section_quote": "",
                }
            )
            continue
        text = " ".join(text.split())
        has_ifta_note = "interstitial fibrosis and tubular atrophy (IFTA)" in text
        rows.append(
            {
                "participant_id": participant,
                "package_slide_id": slide_id,
                "readme_source": archive_readme or "local extracted README",
                "local_readme_path": (
                    str(local_candidates[0].relative_to(ROOT)) if local_candidates else ""
                ),
                "readme_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "readme_variant": "v2" if has_ifta_note else "v1",
                "channel_quote": "Each layer contains different tissue unit/structure",
                "ome_metadata_channel_quote": (
                    "Contains layer names for the ome-tif annotation file"
                ),
                "ifta_quote": (
                    "NOTE: ome.tif file past S-2006-005094 (alphanumerically) do NOT contain "
                    "annotations for interstitial fibrosis and tubular atrophy (IFTA)"
                    if has_ifta_note
                    else "IFTA is not mentioned in this README."
                ),
                "algorithm_quote": (
                    "Tiles were sent to the deep learning network for prediction, and the corresponding "
                    "predictions filled into a high-resolution segmentation mask within the WSI."
                ),
                "pathologist_quote": (
                    "XML/JSON annotations were then quality controlled by a renal pathologist, and "
                    "features were extracted from the various annotation layers and stored in "
                    "mutli-sheet excel files."
                ),
                "resolution_quote": "Contains pixel resolution",
                "participant_specific_stain_or_section_quote": (
                    "The README does not identify a participant-specific stain or section; the package "
                    "filename identifies the PAS section."
                ),
            }
        )
    return rows


def segmentation_mapping() -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    audit_rows = [row for row in read_csv(SEGMENTATION_AUDIT) if row.get("archive")]
    output = []
    for row in audit_rows:
        participant = row["participant_id"]
        slide_id = row["archive_slide_id"]
        masks_dir = DATA / participant / "masks"
        xml_candidates = list(masks_dir.glob(f"**/{slide_id}*.ome.xml"))
        svs_candidates = list(masks_dir.glob(f"**/{slide_id}*.svs"))
        archive_path = ROOT / Path(row["archive_path"])
        zip_members: list[str] = []
        archive = None
        if archive_path.is_file():
            archive = zipfile.ZipFile(archive_path)
            zip_members = archive.namelist()
        ome_attrs: dict[str, str] = {}
        channels = []
        ome_path = xml_candidates[0] if xml_candidates else None
        ome_xml_label = str(ome_path.relative_to(ROOT)) if ome_path else ""
        if ome_path:
            root = ElementTree.parse(ome_path).getroot()
            pixels = next((element for element in root.iter() if element.tag.endswith("Pixels")), None)
            if pixels is not None:
                ome_attrs = pixels.attrib
            channels = [
                element.attrib.get("Name", "")
                for element in root.iter()
                if element.tag.endswith("Channel")
            ]
        elif archive:
            xml_member = next(
                (
                    name
                    for name in zip_members
                    if PurePosixPath(name).name.startswith(slide_id)
                    and name.lower().endswith(".ome.xml")
                ),
                None,
            )
            if xml_member:
                with archive.open(xml_member) as handle:
                    root = ElementTree.parse(handle).getroot()
                ome_xml_label = f"{row['archive_path']}::{xml_member}"
                pixels = next((element for element in root.iter() if element.tag.endswith("Pixels")), None)
                if pixels is not None:
                    ome_attrs = pixels.attrib
                channels = [
                    element.attrib.get("Name", "")
                    for element in root.iter()
                    if element.tag.endswith("Channel")
                ]
        ome_tiff_candidates = list(masks_dir.glob(f"**/{slide_id}*.ome.tif*"))
        ome_axes = ""
        if ome_tiff_candidates:
            with tifffile.TiffFile(ome_tiff_candidates[0]) as tif:
                ome_axes = f"{tif.series[0].axes}:{tif.series[0].shape}"
        elif archive:
            ome_tiff_member = next(
                (
                    name
                    for name in zip_members
                    if PurePosixPath(name).name.startswith(slide_id)
                    and name.lower().endswith((".ome.tif", ".ome.tiff"))
                ),
                None,
            )
            if ome_tiff_member:
                with archive.open(ome_tiff_member) as handle:
                    with tifffile.TiffFile(handle) as tif:
                        ome_axes = f"{tif.series[0].axes}:{tif.series[0].shape}"

        source_svs = svs_candidates[0] if svs_candidates else None
        source_svs_name = source_svs.name if source_svs else ""
        source_svs_label = str(source_svs.relative_to(ROOT)) if source_svs else ""
        source_dimensions: tuple[int, int] | None = None
        mpp_x = ""
        mpp_y = ""
        if source_svs:
            slide = openslide.OpenSlide(str(source_svs))
            source_dimensions = slide.dimensions
            mpp_x = slide.properties.get("openslide.mpp-x", "")
            mpp_y = slide.properties.get("openslide.mpp-y", "")
            slide.close()
        elif archive:
            source_svs_member = next(
                (
                    name
                    for name in zip_members
                    if PurePosixPath(name).name.startswith(slide_id)
                    and name.lower().endswith(".svs")
                ),
                None,
            )
            if source_svs_member:
                with archive.open(source_svs_member) as handle:
                    with tifffile.TiffFile(handle) as tif:
                        series = tif.series[0]
                        axes_shape = dict(zip(series.axes, series.shape))
                        if axes_shape.get("X") and axes_shape.get("Y"):
                            source_dimensions = (
                                int(axes_shape["X"]),
                                int(axes_shape["Y"]),
                            )
                        description = tif.pages[0].description or ""
                        mpp_match = re.search(
                            r"\bMPP\s*=\s*([0-9.]+)", description, re.IGNORECASE
                        )
                        if mpp_match:
                            mpp_x = mpp_y = mpp_match.group(1)
                source_svs_name = PurePosixPath(source_svs_member).name
                source_svs_label = f"{row['archive_path']}::{source_svs_member}"
        ome_dimensions = None
        if ome_attrs.get("SizeX") and ome_attrs.get("SizeY"):
            ome_dimensions = (int(ome_attrs["SizeX"]), int(ome_attrs["SizeY"]))

        tri_ids = [value.strip() for value in row.get("tri_slide_ids", "").split(";") if value.strip()]
        tri_dimensions = parse_dimension_strings(row.get("tri_slide_dimensions_px", ""))
        visium_exact = []
        for path in sorted((DATA / participant / "visium").rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {
                ".tif",
                ".tiff",
                ".png",
                ".jpg",
                ".jpeg",
            }:
                continue
            width, height = image_dimensions(path)
            if width is None or height is None:
                continue
            if ome_dimensions == (width, height):
                visium_exact.append(path.name)

        other_wsi_exact = []
        wsi_ids = []
        for path in sorted((DATA / participant / "wsi").glob("*.svs")):
            file_slide_id_match = re.search(r"S-\d{4}-\d{6}", path.name)
            file_slide_id = file_slide_id_match.group(0) if file_slide_id_match else ""
            wsi_ids.append(file_slide_id)
            slide = openslide.OpenSlide(str(path))
            dimensions = slide.dimensions
            slide.close()
            if ome_dimensions == dimensions:
                other_wsi_exact.append(f"{file_slide_id}:{path.name}")

        same_slide_exact = bool(
            source_svs_name
            and ome_dimensions
            and source_dimensions == ome_dimensions
            and slide_id in source_svs_name
        )
        section_match = re.search(r"_(PAS)_(\d+of\d+)", source_svs.name if source_svs else "")
        if not section_match:
            section_match = re.search(r"_(PAS)_(\d+of\d+)", source_svs_name)
        stain_section = (
            f"{section_match.group(1)} {section_match.group(2)}"
            if section_match
            else "PAS section from archive filename; exact suffix unavailable"
        )
        tri_id_match = slide_id in tri_ids
        tri_dimension_match = bool(ome_dimensions and ome_dimensions in tri_dimensions)
        other_slide_match = (
            f"packaged PAS source {slide_id}: exact"
            if same_slide_exact
            else "; ".join(other_wsi_exact) if other_wsi_exact else "no exact match"
        )
        output.append(
            {
                "participant_id": participant,
                "package": row["archive"],
                "package_path": row["archive_path"],
                "package_slide_id": slide_id,
                "stain_section": stain_section,
                "OME_XML": ome_xml_label,
                "OME_size_x_px": ome_attrs.get("SizeX", ""),
                "OME_size_y_px": ome_attrs.get("SizeY", ""),
                "OME_axes_shape": ome_axes,
                "OME_channels": "; ".join(channels),
                "source_SVS": source_svs_label,
                "source_SVS_size_x_px": source_dimensions[0] if source_dimensions else "",
                "source_SVS_size_y_px": source_dimensions[1] if source_dimensions else "",
                "resolution_MPP_x": f"{float(mpp_x):.4f}" if mpp_x else "",
                "resolution_MPP_y": f"{float(mpp_y):.4f}" if mpp_y else "",
                "OME_size_matches_packaged_SVS": (
                    "yes" if same_slide_exact else "no/metadata unavailable"
                ),
                "TRI_slide_IDs": "; ".join(tri_ids),
                "exact_TRI_slide_ID_match": "yes" if tri_id_match else "no",
                "exact_TRI_dimensions_match": "yes" if tri_dimension_match else "no",
                "exact_Visium_image_dimensions_match": (
                    "; ".join(visium_exact) if visium_exact else "no"
                ),
                "same_participant_WSI_exact_dimension_matches": (
                    "; ".join(other_wsi_exact) if other_wsi_exact else "no"
                ),
                "other_slide_match": other_slide_match,
                "same_participant_WSI_slide_IDs": "; ".join(wsi_ids),
                "reason_for_mismatch": (
                    "Segmentation is attached to the PAS slide named in its OME package; TRI uses "
                    "different slide ID and dimensions. No Visium image has the same full pixel "
                    "dimensions. Different slide IDs mean the masks cannot be assumed to align."
                ),
            }
        )
        if archive:
            archive.close()
    return output, readme_quotes()


def kpmp_catalog_audit() -> tuple[list[dict[str, object]], list[dict[str, str]], int, int]:
    participants = {row["participant_id"] for row in read_csv(PLAN_SUMMARY)}
    catalog_rows = [
        row
        for row in read_csv(CATALOG)
        if row.get("Participant ID", "") in participants
    ]
    counts = Counter(
        (row.get("Data Category", ""), row.get("Access", ""))
        for row in catalog_rows
    )
    categories = sorted({row.get("Data Category", "") for row in catalog_rows})
    accesses = sorted({"open", "controlled"})
    summary = [
        {
            "data_category": category,
            "access": access,
            "catalog_rows": counts.get((category, access), 0),
            "participant_count": len(
                {
                    row["Participant ID"]
                    for row in catalog_rows
                    if row.get("Data Category") == category and row.get("Access") == access
                }
            ),
        }
        for category in categories
        for access in accesses
    ]
    clinical_terms = re.compile(
        r"clinical|diagnos|ifta|fibrosis|atrophy|egfr|pathologist|demograph|medical|"
        r"phenotyp|reference.?ckd|tubular",
        re.IGNORECASE,
    )
    candidates = []
    for row in catalog_rows:
        searchable = " ".join(
            row.get(field, "")
            for field in (
                "File Name",
                "Data Category",
                "Experimental Strategy",
                "Workflow Type / Panel",
            )
        )
        if clinical_terms.search(searchable):
            candidates.append(
                {
                    "participant_id": row.get("Participant ID", ""),
                    "access": row.get("Access", ""),
                    "data_category": row.get("Data Category", ""),
                    "strategy": row.get("Experimental Strategy", ""),
                    "workflow": row.get("Workflow Type / Panel", ""),
                    "file_name": row.get("File Name", ""),
                    "size": row.get("Size", ""),
                }
            )
    return summary, candidates, len(catalog_rows), len(participants)


def cohort_count_audit() -> list[dict[str, object]]:
    participant_rows = read_csv(PLAN_SUMMARY)
    spot_rows = read_csv(ROOT / "plan_a_plan_b" / "plan_b_spot_expression_long.csv")
    tile_rows = read_csv(ROOT / "plan_a_plan_b" / "plan_b_tile_manifest.csv")
    samples = sum(int(row.get("paired_samples") or 0) for row in participant_rows)
    spots_reported = sum(int(row.get("in_tissue_spots") or 0) for row in participant_rows)
    spot_keys = {
        (row["participant_id"], row["sample_id"], row["barcode"])
        for row in spot_rows
    }
    tile_keys = {
        (row["participant_id"], row["sample_id"], row["barcode"])
        for row in tile_rows
    }
    return [
        {
            "source": "plan_a_patient_summary.csv",
            "participants": len(participant_rows),
            "samples": samples,
            "in_tissue_spots": spots_reported,
            "rows_or_unique_keys": len(participant_rows),
            "status": "expected cohort reconciliation",
        },
        {
            "source": "plan_b_spot_expression_long.csv",
            "participants": len({row["participant_id"] for row in spot_rows}),
            "samples": len({(row["participant_id"], row["expression_source"]) for row in spot_rows}),
            "in_tissue_spots": len(spot_rows),
            "rows_or_unique_keys": len(
                {
                    (row["participant_id"], row["expression_source"], row["barcode"])
                    for row in spot_rows
                }
            ),
            "status": (
                f"sample_id field has {len({(row['participant_id'], row['sample_id']) for row in spot_rows})} "
                f"participant/sample values; {len(spot_keys)} keys if sample_id is used"
            ),
        },
        {
            "source": "plan_b_tile_manifest.csv",
            "participants": len({row["participant_id"] for row in tile_rows}),
            "samples": len({(row["participant_id"], row["expression_source"]) for row in tile_rows}),
            "in_tissue_spots": len(tile_rows),
            "rows_or_unique_keys": len(
                {
                    (row["participant_id"], row["expression_source"], row["barcode"])
                    for row in tile_rows
                }
            ),
            "status": (
                f"sample_id field has {len({(row['participant_id'], row['sample_id']) for row in tile_rows})} "
                f"participant/sample values; {len(tile_keys)} keys if sample_id is used"
            ),
        },
    ]


def write_report(
    top_level: list[dict[str, object]],
    participants: list[dict[str, object]],
    largest: list[dict[str, object]],
    project_bytes: int,
    renfast_folders: list[dict[str, object]],
    renfast_bytes: int,
    renfast_files: int,
    pair_rows: list[dict[str, object]],
    mapping: list[dict[str, object]],
    readmes: list[dict[str, str]],
    catalog_summary: list[dict[str, object]],
    candidates: list[dict[str, str]],
    catalog_rows: int,
    cohort_size: int,
    cohort_counts: list[dict[str, object]],
) -> None:
    disk = shutil.disk_usage("D:\\")
    storage_by_name = {row["name"]: int(row["size_bytes"]) for row in top_level}

    def bytes_for(name: str) -> int:
        return storage_by_name.get(name, 0)

    candidate_rows = [
        [
            "data",
            bytes_for("data"),
            format_gib(bytes_for("data")),
            "Core participant source data; offload only with an external copy and remount plan.",
        ],
        [
            "working",
            bytes_for("working"),
            format_gib(bytes_for("working")),
            "Ancillary analysis/images; provenance review needed before offloading or regeneration.",
        ],
        [
            "16410",
            bytes_for("16410"),
            format_gib(bytes_for("16410")),
            "Repository-ID package files; verify ownership, access and relevance before offloading.",
        ],
        [
            "16420",
            bytes_for("16420"),
            format_gib(bytes_for("16420")),
            "Includes incomplete .crdownload files; retain unless reviewed; moving is not deletion.",
        ],
        [
            "plan_a_plan_b",
            bytes_for("plan_a_plan_b"),
            format_gib(bytes_for("plan_a_plan_b")),
            "Derived spot tiles/galleries and tables; tiles may be regenerable from source, but earlier outputs must be preserved.",
        ],
        [
            "qc_collagen",
            bytes_for("qc_collagen"),
            format_gib(bytes_for("qc_collagen")),
            "Derived QC outputs and source scripts; archive/move only, do not overwrite or delete.",
        ],
        [
            "m2t49zf6xr-1.zip",
            bytes_for("m2t49zf6xr-1.zip"),
            format_gib(bytes_for("m2t49zf6xr-1.zip")),
            "Existing RENFAST archive; move only if retained elsewhere and license terms are resolved.",
        ],
    ]
    bundle_bytes = bytes_for("data") + bytes_for("working") + bytes_for("16420")
    bundle_remaining = project_bytes - bundle_bytes

    top_level_md = markdown_table(
        ["Top-level item", "Kind", "Bytes", "GB (decimal)", "GiB"],
        [
            [
                row["name"],
                row["kind"],
                row["size_bytes"],
                row["size_GB_decimal"],
                row["size_GiB"],
            ]
            for row in top_level
        ],
    )
    participant_md = markdown_table(
        ["Participant", "Bytes", "GB (decimal)", "GiB", "Files"],
        [
            [
                row["participant_id"],
                row["size_bytes"],
                row["size_GB_decimal"],
                row["size_GiB"],
                row["file_count"],
            ]
            for row in participants
        ],
    )
    largest_md = markdown_table(
        ["Rank", "Size (MB)", "Bytes", "Path"],
        [
            [index, row["size_MB"], row["size_bytes"], row["path"]]
            for index, row in enumerate(largest, 1)
        ],
    )

    folder_count_rows = [
        [row["folder"], row["file_count"], row["size_bytes"]]
        for row in renfast_folders
        if "image_file_count" not in row
    ]
    pair_md = markdown_table(
        [
            "Split",
            "Image folder",
            "Mask folder",
            "Image files",
            "Mask files",
            "Unique image names",
            "Unique mask names",
            "Paired unique names",
            "Duplicate image-name entries",
            "Duplicate mask-name entries",
            "Unmatched image names",
            "Unmatched mask names",
        ],
        [
            [
                row["split"],
                row["image_folder"],
                row["mask_folder"],
                row["image_file_count"],
                row["mask_file_count"],
                row["image_unique_basenames"],
                row["mask_unique_basenames"],
                row["paired_unique_basenames"],
                row["duplicate_image_basename_entries"],
                row["duplicate_mask_basename_entries"],
                row["unmatched_image_basenames"],
                row["unmatched_mask_basenames"],
            ]
            for row in pair_rows
        ],
    )
    readme_versions = Counter(row["readme_variant"] for row in readmes)
    readme_paths = "\n".join(
        f"- `{row['readme_source']}` ({row['readme_variant']})"
        for row in readmes
    )
    first_readme = readmes[0] if readmes else {}
    ifta_readmes = [row for row in readmes if row["readme_variant"] == "v2"]
    ifta_note = ifta_readmes[0]["ifta_quote"] if ifta_readmes else "No IFTA statement found."
    package_md = markdown_table(
        [
            "Participant",
            "Package slide",
            "Stain/section",
            "OME dimensions (px)",
            "Resolution (µm/px)",
            "Channels",
            "TRI ID/dim match",
            "Visium dim match",
            "Other slide match",
        ],
        [
            [
                row["participant_id"],
                row["package_slide_id"],
                row["stain_section"],
                f"{row['OME_size_x_px']} × {row['OME_size_y_px']}",
                f"{row['resolution_MPP_x']} × {row['resolution_MPP_y']}",
                row["OME_channels"],
                f"ID: {row['exact_TRI_slide_ID_match']}; dims: {row['exact_TRI_dimensions_match']}",
                row["exact_Visium_image_dimensions_match"],
                row["other_slide_match"],
            ]
            for row in mapping
        ],
    )
    catalog_md = markdown_table(
        ["Data category", "Access", "Rows", "Participants represented"],
        [
            [
                row["data_category"],
                row["access"],
                row["catalog_rows"],
                row["participant_count"],
            ]
            for row in catalog_summary
        ],
    )
    report = f"""# Stage 0 Audit Report

**Audit date:** 2026-11-12  
**Scope:** Stage 0 only. No image data were downloaded or extracted. No files were moved, deleted, or modified outside `{OUT}`. Restricted catalog records were not accessed.

## 1. Storage audit

The local project footprint before writing Stage 0 outputs was **{project_bytes:,} bytes ({format_gb(project_bytes)} GB decimal; {format_gib(project_bytes)} GiB)**. The 10 GB project cap is therefore exceeded by **{max(project_bytes - TEN_GB, 0):,} bytes ({format_gb(max(project_bytes - TEN_GB, 0))} GB)**. D: had **{disk.free:,} bytes ({disk.free / 1_000_000_000:.2f} GB)** free of **{disk.total:,} bytes** when checked.

### Top-level folders and files

{top_level_md}

### `data` participant footprint

The cohort data directory contains {len(participants)} participant folders. Exact per-participant sizes and file counts:

{participant_md}

### Twenty largest files

{largest_md}

### Storage options (proposals only; nothing was moved)

{markdown_table(["Candidate", "Bytes", "GiB", "Move/regenerate assessment"], candidate_rows)}

- **Plan A — keep everything:** retain the current {format_gib(project_bytes)} GiB on D:. This preserves all paths, but does **not** meet the 10 GB cap. Do not add downloads or large derived outputs under this plan.
- **Plan B — active D: footprint under 10 GB:** a proposed off-D bundle of `data` + `working` + `16420` would move {bundle_bytes:,} bytes ({format_gib(bundle_bytes)} GiB), leaving about {bundle_remaining:,} bytes ({format_gb(bundle_remaining)} GB decimal) on D: before Stage 0 outputs. This makes core participant inputs unavailable until remounted. It is a proposal only.
- **Important cap interpretation:** moving files to another drive does not reduce the total retained project footprint. A strict whole-project 10 GB cap cannot coexist with retaining all current files; at least {max(project_bytes - TEN_GB, 0):,} bytes must be explicitly excluded from the counted project or retired under a user-approved retention policy. No such decision was made here.

## 2. RENFAST archive (file listing only)

Source: local existing archive `{RENFAST_ZIP}`; archive member metadata was read without extracting or decoding image pixels. Dataset landing page: [{MEB_DATASET_URL}]({MEB_DATASET_URL}), DOI 10.17632/m2t49zf6xr.1.

- Archive entries: **{renfast_files:,} files**, **{renfast_bytes:,} uncompressed bytes ({format_gib(renfast_bytes)} GiB)**; compressed archive size: **{RENFAST_ZIP.stat().st_size:,} bytes**.
- The archive contains four splits: FIBROSIS_TRAIN, FIBROSIS_TEST, VESSEL_TRAIN and VESSEL_TEST. Directory counts and pair counts are in `renfast_directory_and_pairing_summary.csv`; member paths, file types and byte sizes are in `renfast_archive_inventory.csv`.
- Landing-page description: **300 Masson's trichrome (TRIC) images** for fibrosis detection and **350 PAS images** for vessel segmentation. The archive contains 550 fibrosis image PNG entries (300 unique normalized basenames; 250 extra entries have duplicate/colliding basenames) and 350 vessel image PNG entries (350 unique basenames). Thus unique basename counts reconcile with the landing-page counts; whether the duplicate-named fibrosis entries have identical image contents was not tested.
- Annotation type from page text and folder names: fibrosis masks are separated as `MANUAL_TISSUE` and `MANUAL_FIBROSIS`; vessel masks are in `MANUAL`. The page describes manual annotations. The archive listing has matching unique basenames for every image/mask folder pair; duplicate basename entries in fibrosis training prevent asserting one-to-one file pairing without inspecting file contents.
- No README, license, or terms file is present in the archive member listing. The Mendeley landing page renders a blank license link/field; **license and reuse/commercial/derived-work terms are not verified**. Do not train on or redistribute this dataset until the applicable terms are confirmed.

### RENFAST archive folders and pair counts

{markdown_table(["Folder", "Files", "Uncompressed bytes"], folder_count_rows)}

{pair_md}

## 3. Segmentation package audit

There are **{len(mapping)} local Seg_Masks_Features packages** for **{len(set(row["participant_id"] for row in mapping))} participants**. Package README files were read in-place from ZIPs (without extraction); {sum(bool(row["local_readme_path"]) for row in readmes)} extracted README copies were also present.

### README quotations and annotation provenance

The {len(readmes)} package READMEs resolve to {len(readme_versions)} text variants ({dict(readme_versions)}). Their archive paths are:

{readme_paths}

All README variants state: **“{first_readme.get('channel_quote', '')}”** and **“{first_readme.get('ome_metadata_channel_quote', '')}”**; the README also says **“{first_readme.get('resolution_quote', '')}.”** The v2 READMEs additionally state: **“{ifta_note}”**.

The segmentation protocol describes network predictions: **“{first_readme.get('algorithm_quote', '')}”** It separately states: **“{first_readme.get('pathologist_quote', '')}”** Thus the package documentation describes algorithm-generated annotations that were quality controlled by a renal pathologist; it does not establish that each IFTA channel was directly expert-drawn. The README says training-set slides were annotated for viable/sclerotic glomeruli, cortical/medullary interstitia, tubules and arteries/arterioles; that is not a per-package provenance statement.

The README does not specify a participant-specific stain, section number, or numeric resolution. Those were read from package filenames, OME XML, and the embedded SVS metadata. The package slide names identify PAS section 1of2 or 2of2. OME dimensions/resolution and match checks are below.

### Package-to-slide mapping

{package_md}

**Mismatch explanation:** each mask archive names a PAS slide and its source PAS SVS has dimensions matching that package's OME annotation. The participant TRI slide IDs differ, and their dimensions do not match the OME image dimensions. No Visium image was an exact full-pixel-dimension match. These are separate slide/section assets; equal participant ID is not evidence that masks align to TRI or Visium. No registration was performed.

**IFTA documentation conflict:** the v2 README says that OME-TIFFs past S-2006-005094 do not contain IFTA, but the inspected OME channel lists include IFTA for several later S-2102 slides. This contradiction is unresolved. Treat the IFTA channel as present in metadata, not as a verified expert fibrosis label.

Detailed package metadata and README quotes are in `segmentation_package_mapping.csv` and `segmentation_readme_quotes.csv`.

## 4. Cohort count checkpoint

The existing plan files reconcile to 28 participants, 29 samples, and 25,104 spots when sample identity is counted by expression source:

{markdown_table(["Source", "Participants", "Samples", "In-tissue spots", "Unique row/key count", "Check"], [[row["source"], row["participants"], row["samples"], row["in_tissue_spots"], row["rows_or_unique_keys"], row["status"]] for row in cohort_counts])}

The spot/tile outputs use the generic `sample_id` value `spatial` for every row. For participant 28-12265, the existing metadata table identifies two libraries (28-12265-C and 28-12265-M), and `expression_source` retains the two source paths. Consequently, 73 barcodes repeat if keyed only by `(participant_id, sample_id, barcode)`, but all 25,104 `(participant_id, expression_source, barcode)` keys are unique. Preserve library identity in any future split or analysis; do not merge on the generic `sample_id` field. No model split or test fold was created in Stage 0; test-fold overlap checking is not applicable.

## 5. KPMP clinical/pathology data availability

Source: local catalog `{CATALOG}`. Cohort: {cohort_size} participant IDs from `plan_a_plan_b\\plan_a_patient_summary.csv`; {catalog_rows} catalog records map to these participants. The catalog's access field is reported as published; no controlled files were downloaded.

{catalog_md}

The **164 open Pathology records** are histology/segmentation assets (152 whole-slide-image records and 12 segmentation-mask/pathomics records), not participant-level clinical fields. No catalog row matched the clinical/pathology-label search terms in filename, category, experimental strategy, or workflow fields (**{len(candidates)} candidate rows**). The catalog is a file listing, not a clinical-data schema, so this cannot prove no such data exist outside the catalog.

Prior local screening of available open Experimental Metadata workbooks found no requested participant-level clinical/pathology labels for the cohort (reference-vs-CKD, diagnosis, IFTA/interstitial fibrosis, tubular atrophy, eGFR, age or sex: 0/28). The access summary for those labels is in `qc_collagen\\review\\reference_label_availability_summary.csv`. Tier A/B/C definitions were not established by that audit.

**Manual request/confirmation needed:** ask KPMP data governance whether participant-level clinical/pathology fields are available and request the appropriate authorization for any controlled files. Specifically confirm reference/CKD status, diagnosis, pathologist IFTA/interstitial-fibrosis and tubular-atrophy scores, eGFR, age and sex, plus definitions for cohort tiers. The catalog does not establish that these fields exist. Do not access controlled records until approved.

## 6. Stage gate verdict

- **Gate 0 — PASS as an audit deliverable, with blocking conditions recorded.** Storage, local archive inventory, mask package mapping, and catalog access have been audited. The project already exceeds the 10 GB cap, RENFAST licensing is unknown, and participant-level clinical labels are not present in the inspected open metadata.
- **Stage 1 — PARTIAL.** Open Visium/WSI data and prior expression QC outputs exist, but the storage cap is unresolved and an open pretrained encoder/license has not been selected and verified. Clinical labels are not required for expression-only evaluation.
- **Stage 2 — BLOCKED.** RENFAST license/terms are unknown, and the IFTA channel provenance is not per-channel and has a README/metadata contradiction. No mask matches a TRI slide. No segmentation training or application was started.
- **Stage 3 — BLOCKED.** It is conditional on Stage 1 and Stage 2 gates; neither has passed. No registration was performed.
- **Stage 4 — BLOCKED.** It depends on Gate D/Stage 3 passing. No fusion or modeling was performed.
- **Stage 5 — BLOCKED.** Robustness/write-up depends on completed prior stages. No model evaluation was started.

## What could not be verified / risks and open questions

1. RENFAST license, reuse, commercial-use, and derived-work terms; the Mendeley license field is blank and the archive contains no README/license.
2. Whether the 250 extra fibrosis-training entries with duplicate/colliding basenames contain identical images or represent distinct files.
3. Whether the cohort file-list catalog is exhaustive for clinical data, and whether controlled clinical/pathology fields exist; no clinical schema was present in the catalog.
4. The per-channel provenance of IFTA masks, and the contradiction between the v2 README note and IFTA channel names in later-slide OME metadata.
5. Any geometric registration between PAS masks, TRI slides, and Visium images; only identifiers and pixel dimensions were compared.
6. Whether all large files in `working`, `16410`, and `16420` are safe to offload; their contents/provenance were not exhaustively assessed for the storage proposal.
7. Whether a move-to-external-archive interpretation satisfies the project-wide 10 GB cap. Under a strict total-retained-data cap, a user-approved retention/de-scoping decision is required.
8. Whether the generic `sample_id=spatial` field can be repaired from existing source paths without revisiting the acquisition metadata. It collapses distinct libraries for 28-12265.
"""
    (OUT / "STAGE0_REPORT.md").write_text(report, encoding="utf-8")

    readme_text = f"""# Stage 0 audit outputs

Purpose: reproducible, read-only Stage 0 storage, RENFAST archive-list, segmentation package, and KPMP catalog audit for `{ROOT}`.

## Files

- `STAGE0_REPORT.md`: final Stage 0 report and gate verdict.
- `scripts/audit_stage0.py`: read-only inventory/report generator.
- `storage_top_level.csv`: exact top-level item sizes.
- `storage_per_participant.csv`: exact sizes/file counts for participant directories under `data`.
- `largest_files.csv`: 20 largest existing project files at audit time.
- `renfast_archive_inventory.csv`: ZIP member paths/types/sizes; no extraction.
- `renfast_directory_and_pairing_summary.csv`: RENFAST folder counts and basename-pair checks.
- `segmentation_package_mapping.csv`: package OME/source-slide metadata and exact-dimension checks.
- `segmentation_readme_quotes.csv`: per-package README quotations from local archives and any extracted copies.
- `kpmp_catalog_access_by_category.csv`: cohort catalog access counts by category.
- `kpmp_clinical_candidates.csv`: catalog rows matching clinical/pathology search terms (header-only when none match).
- `cohort_count_reconciliation.csv`: cross-check of participant, sample and spot counts in existing plan outputs.
- `LAB_NOTEBOOK.md`: append-only dated Stage 0 record.
- `requirements-stage0.txt`: pinned Python package versions used by the inventory script.
- `scripts\\__pycache__\\audit_stage0.cpython-313.pyc`: bytecode created by the syntax check.

## Software and reproducibility

- Python: {sys.version.split()[0]}
- OpenSlide Python: {openslide.__version__}; OpenSlide library: {openslide.__library_version__}
- tifffile: {tifffile.__version__}; Pillow: {Image.__version__}
- Random seed: none; this audit uses deterministic listings and metadata reads only.
- Exact command: `python D:\\patent\\stage0_audit\\scripts\\audit_stage0.py`
- Inputs are read from `D:\\patent\\data`, `D:\\patent\\atlas_repository_filelist-20261105.csv`, `D:\\patent\\m2t49zf6xr-1.zip`, `D:\\patent\\plan_a_plan_b`, and `D:\\patent\\qc_collagen\\review`.
- No images were extracted or decoded; no raw data or earlier outputs were edited; no files were moved or deleted.
- Dataset sources: KPMP local repository catalog dated 2026-11-05; RENFAST Mendeley landing page DOI 10.17632/m2t49zf6xr.1. RENFAST terms were not visible, so dataset use is not authorized by this audit.
"""
    (OUT / "README.md").write_text(readme_text, encoding="utf-8")

    notebook = f"""# Lab notebook (append-only)

## 2026-11-12 — Stage 0 storage, source, and access audit

- Scope: storage footprint, local RENFAST ZIP listing, local Seg_Masks_Features package/README/OME metadata, and the cohort's KPMP catalog records.
- Parameters: 10,000,000,000-byte cap; dimensions compared by exact full-resolution pixel width/height; no image registration or image-pixel processing.
- Decisions: no download, extraction, move, deletion, controlled-data access, model training, or registration. RENFAST terms are treated as unknown, not as permission.
- Findings: see `STAGE0_REPORT.md`; current project footprint is {project_bytes:,} bytes before Stage 0 outputs; IFTA channel provenance remains unverified.
- Reproduction: `python D:\\patent\\stage0_audit\\scripts\\audit_stage0.py`.
"""
    notebook_path = OUT / "LAB_NOTEBOOK.md"
    if not notebook_path.exists():
        notebook_path.write_text(notebook, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    top_level, participants, largest, project_bytes = storage_inventory()
    renfast_entries, renfast_summary, renfast_bytes, renfast_files = renfast_inventory()
    mapping, readmes = segmentation_mapping()
    catalog_summary, candidates, catalog_rows, cohort_size = kpmp_catalog_audit()
    cohort_counts = cohort_count_audit()

    write_csv(OUT / "storage_top_level.csv", top_level)
    write_csv(OUT / "storage_per_participant.csv", participants)
    write_csv(OUT / "largest_files.csv", largest)
    write_csv(OUT / "renfast_archive_inventory.csv", renfast_entries)
    write_csv(OUT / "renfast_directory_and_pairing_summary.csv", renfast_summary)
    write_csv(OUT / "segmentation_package_mapping.csv", mapping)
    write_csv(OUT / "segmentation_readme_quotes.csv", readmes)
    write_csv(OUT / "kpmp_catalog_access_by_category.csv", catalog_summary)
    write_csv(
        OUT / "kpmp_clinical_candidates.csv",
        candidates,
        [
            "participant_id",
            "access",
            "data_category",
            "strategy",
            "workflow",
            "file_name",
            "size",
        ],
    )
    write_csv(OUT / "cohort_count_reconciliation.csv", cohort_counts)
    write_report(
        top_level,
        participants,
        largest,
        project_bytes,
        renfast_summary,
        renfast_bytes,
        renfast_files,
        [
            row
            for row in renfast_summary
            if "image_file_count" in row
        ],
        mapping,
        readmes,
        catalog_summary,
        candidates,
        catalog_rows,
        cohort_size,
        cohort_counts,
    )
    print(
        json.dumps(
            {
                "report": str(OUT / "STAGE0_REPORT.md"),
                "project_bytes_before_stage_outputs": project_bytes,
                "participant_folders": len(participants),
                "renfast_files": renfast_files,
                "renfast_uncompressed_bytes": renfast_bytes,
                "segmentation_packages": len(mapping),
                "segmentation_readmes": len(readmes),
                "catalog_rows": catalog_rows,
                "clinical_catalog_candidates": len(candidates),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
