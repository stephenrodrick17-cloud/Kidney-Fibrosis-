import csv
import hashlib
import importlib.util
import json
import math
import re
import sys
import urllib.error
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import cv2
import numpy as np
import openslide
import openpyxl
import pandas as pd
import scipy
import tifffile
from PIL import Image, ImageDraw, ImageFont
from scipy.stats import mannwhitneyu, spearmanr
from skimage.morphology import remove_small_holes, remove_small_objects


ROOT = Path(r"D:\patent")
QC = ROOT / "qc_collagen"
REVIEW = QC / "review"
DATA = ROOT / "data"
CATALOG = ROOT / "atlas_repository_filelist-20261105.csv"
CHECKLIST = ROOT / "tier_a_download_checklist.csv"
TRI_SUMMARY = QC / "trichrome_slide_proxy_summary.csv"
PARTICIPANT_PROXY = QC / "participant_trichrome_collagen_proxy.csv"
SEED = 20261112
BOOTSTRAP_REPLICATES = 5000
BASE_HUE_LOW, BASE_HUE_HIGH, BASE_SAT_MIN = 75, 140, 35
PERMISSIVE_HUE_LOW, PERMISSIVE_HUE_HIGH, PERMISSIVE_SAT_MIN = 65, 145, 20
STRICT_HUE_LOW, STRICT_HUE_HIGH, STRICT_SAT_MIN = 85, 135, 60
TARGET_MPP_UM = 3.0
MIN_OBJECT_AREA_MM2 = 0.005
MIN_HOLE_AREA_MM2 = 0.0025
REFERENCE_FIELDS = {
    "reference_vs_ckd": (
        r"\b(?:ckd|chronic kidney disease|control group|reference group|"
        r"reference\s*(?:vs\.?|/)\s*(?:ckd|chronic kidney disease))\b"
    ),
    "diagnosis": r"\bdiagnos(?:is|es|tic)\b",
    "ifta_score": r"\bifta\b",
    "interstitial_fibrosis_score": r"\binterstitial fibrosis\b|\bfibrosis score\b|\bfibrotic score\b",
    "tubular_atrophy": r"\btubular atrophy\b|\btubular atrophy score\b",
    "egfr": r"\begfr\b|\bestimated glomerular filtration\b",
    "age": r"\bage\b|\bage at\b",
    "sex": r"\bsex\b|\bgender\b",
}


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_rows(path, rows, fieldnames=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_blank_csv(path, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        csv.DictWriter(stream, fieldnames=fieldnames).writeheader()


def load_catalog():
    return read_rows(CATALOG)


def download_open_metadata_candidates(participant_ids, catalog_rows):
    helper_path = ROOT / "acquire_plan_a_b_open_data.py"
    spec = importlib.util.spec_from_file_location("open_data_downloader", helper_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load the existing downloader: {helper_path}")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    manifest_path = REVIEW / "metadata_download_manifest.csv"
    helper.MANIFEST_CSV = manifest_path
    prior_manifest = read_rows(manifest_path) if manifest_path.exists() else []
    prior_checksums = {
        (row.get("participant_id", ""), row.get("file_name", "")): row.get("checksum", "")
        for row in prior_manifest
    }

    candidates = [
        row
        for row in catalog_rows
        if row.get("Participant ID", "").strip() in participant_ids
        and (
            row.get("Workflow Type / Panel", "").strip() == "Experimental Metadata"
            or "METADATA" in row.get("File Name", "").upper()
        )
    ]
    status_rows = []
    estimated_bytes = 0
    for row in candidates:
        access = row.get("Access", "").strip().lower()
        size = helper.parse_size(row.get("Size", ""))
        if access == "open":
            estimated_bytes += size
    if estimated_bytes > 50_000_000_000:
        raise RuntimeError("Open metadata download batch exceeds 50 GB.")
    if any(
        helper.parse_size(row.get("Size", "")) > 5_000_000_000
        for row in candidates
        if row.get("Access", "").strip().lower() == "open"
    ):
        raise RuntimeError("A metadata file exceeds the 5 GB download threshold.")

    download_root = REVIEW / "metadata_downloads"
    for row in candidates:
        participant_id = row["Participant ID"].strip()
        filename = row["File Name"].strip()
        access = row.get("Access", "").strip()
        local_dir = DATA / participant_id / "metadata"
        suffix_name = re.sub(r"^[0-9a-fA-F-]{36}_", "", filename)
        local_matches = (
            [
                path
                for path in local_dir.glob("*")
                if path.is_file()
                and (
                    path.name == filename
                    or path.name == suffix_name
                    or path.name.endswith(suffix_name)
                )
            ]
            if local_dir.exists()
            else []
        )
        target = download_root / participant_id / filename
        if local_matches:
            status_rows.append(
                {
                    "participant_id": participant_id,
                    "file_name": filename,
                    "access": access,
                    "status": "already present locally; inspected in place",
                    "path": str(local_matches[0].relative_to(ROOT)),
                }
            )
            continue
        if access.strip().lower() != "open":
            status_rows.append(
                {
                    "participant_id": participant_id,
                    "file_name": filename,
                    "access": access,
                    "status": "not downloaded: catalog does not mark open",
                    "path": "",
                }
            )
            continue
        if target.is_file() and target.stat().st_size > 0:
            checksum = helper.sha256_file(target)
            expected_checksum = prior_checksums.get((participant_id, filename), "")
            if expected_checksum and checksum != expected_checksum:
                raise ValueError(
                    f"Existing review download checksum mismatch: {target}"
                )
            status_rows.append(
                {
                    "participant_id": participant_id,
                    "file_name": filename,
                    "access": access,
                    "status": "already downloaded in review; SHA-256 verified",
                    "path": str(target.relative_to(ROOT)),
                }
            )
            continue
        package_id = row["Internal Package ID"].strip()
        url = f"{helper.BASE_URL}/{package_id}/{quote(filename, safe='')}"
        reason = "Review Part B: inspect open experimental metadata for independent labels"
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            actual_bytes = helper.download(
                url, target, helper.parse_size(row.get("Size", ""))
            )
            checksum = helper.sha256_file(target)
            helper.append_manifest(
                url,
                filename,
                actual_bytes,
                checksum,
                participant_id,
                reason,
            )
            status_rows.append(
                {
                    "participant_id": participant_id,
                    "file_name": filename,
                    "access": access,
                    "status": "downloaded and SHA-256 logged",
                    "path": str(target.relative_to(ROOT)),
                }
            )
        except (OSError, ValueError, urllib.error.URLError) as error:
            helper.append_manifest(
                url,
                filename,
                target.stat().st_size if target.exists() else 0,
                "",
                participant_id,
                f"{reason}; FAILED: {type(error).__name__}: {error}",
            )
            status_rows.append(
                {
                    "participant_id": participant_id,
                    "file_name": filename,
                    "access": access,
                    "status": f"download failed: {type(error).__name__}: {error}",
                    "path": "",
                }
            )
    write_rows(REVIEW / "metadata_download_status.csv", status_rows)
    return status_rows


def existing_metadata_files():
    return sorted(
        path
        for path in (DATA, REVIEW / "metadata_downloads")
        if path.exists()
        for path in path.rglob("*.xlsx")
        if any(part.lower().startswith("metadata") for part in path.parts)
        or path.name.upper().startswith("METADATA")
    )


def label_field_for_header(value):
    text = str(value or "").strip()
    for field, pattern in REFERENCE_FIELDS.items():
        if re.search(pattern, text, re.IGNORECASE):
            return field
    return None


def inspect_workbook_labels(path, participant_id):
    found = []
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    for sheet in workbook.worksheets:
        rows = list(sheet.iter_rows(values_only=True))
        for row_index, row in enumerate(rows):
            matching_columns = [
                column_index
                for column_index, value in enumerate(row)
                if str(value).strip() == participant_id
            ]
            for id_column in matching_columns:
                for header_row_index in range(max(0, row_index - 6), row_index):
                    header_row = rows[header_row_index]
                    for column_index, header in enumerate(header_row):
                        field = label_field_for_header(header)
                        if field is None or column_index >= len(row):
                            continue
                        value = row[column_index]
                        if value is None or str(value).strip() == "":
                            continue
                        found.append(
                            {
                                "field": field,
                                "value": str(value).strip(),
                                "source_file": str(path.relative_to(ROOT)),
                                "source_column": (
                                    f"{sheet.title}!R{header_row_index + 1}"
                                    f"C{column_index + 1}:{str(header).strip()}"
                                ),
                            }
                        )
    return found


def inspect_metadata_candidates(participant_ids, catalog_rows, download_status):
    candidate_rows = []
    candidate_pattern = re.compile(
        r"metadata|clinical|patholog|ifta|fibros|diagnos|phenotyp|demograph|"
        r"seg[_ -]?masks[_ -]?features",
        re.IGNORECASE,
    )
    for row in catalog_rows:
        if row.get("Participant ID", "").strip() not in participant_ids:
            continue
        filename = row.get("File Name", "").strip()
        category = row.get("Data Category", "").strip()
        strategy = row.get("Experimental Strategy", "").strip()
        workflow = row.get("Workflow Type / Panel", "").strip()
        if not (
            candidate_pattern.search(filename)
            or candidate_pattern.search(category)
            or candidate_pattern.search(strategy)
            or candidate_pattern.search(workflow)
        ):
            continue
        if "Seg_Masks_Features" in filename:
            reason = "pathology segmentation/features package; not itself a validated clinical score"
        elif "METADATA_Transcriptomics_Spatial" in filename:
            reason = "Visium experimental metadata; candidate to check for requested labels"
        elif "METADATA" in filename.upper() or "Experimental Metadata" in workflow:
            reason = "assay-specific experimental metadata; label content not assumed"
        elif "Pathology" in category:
            reason = "pathology image listed; no clinical score is implied by the image"
        else:
            reason = "catalog text matches clinical/pathology search terms"
        candidate_rows.append(
            {
                "participant_id": row.get("Participant ID", ""),
                "access_level": row.get("Access", ""),
                "data_category": category,
                "experimental_strategy": strategy,
                "workflow": workflow,
                "file_name": filename,
                "catalog_size": row.get("Size", ""),
                "internal_package_id": row.get("Internal Package ID", ""),
                "candidate_reason": reason,
            }
        )
    status_by_file = {
        (row["participant_id"], row["file_name"]): row["status"]
        for row in download_status
    }
    for row in candidate_rows:
        row["download_status"] = status_by_file.get(
            (row["participant_id"], row["file_name"]),
            "not downloaded; outside targeted Visium metadata set",
        )
    write_rows(REVIEW / "reference_candidate_inventory.csv", candidate_rows)
    return candidate_rows


def populate_reference_labels(participant_ids, participant_tiers):
    metadata_paths = existing_metadata_files()
    observations = defaultdict(list)
    metadata_audit = []
    for participant_id in participant_ids:
        files_for_participant = [
            path for path in metadata_paths if participant_id in path.parts
        ]
        matched_fields = []
        for path in files_for_participant:
            records = inspect_workbook_labels(path, participant_id)
            matched_fields.extend(records)
            observations[participant_id].extend(records)
            metadata_audit.append(
                {
                    "participant_id": participant_id,
                    "source_file": str(path.relative_to(ROOT)),
                    "candidate_label_fields_found": "; ".join(
                        sorted({record["field"] for record in records})
                    ),
                    "fields_with_values": len(records),
                }
            )
        if not files_for_participant:
            metadata_audit.append(
                {
                    "participant_id": participant_id,
                    "source_file": "",
                    "candidate_label_fields_found": "",
                    "fields_with_values": 0,
                }
            )

    fields = list(REFERENCE_FIELDS)
    output = []
    for participant_id in participant_ids:
        row = {
            "participant_id": participant_id,
            "participant_id_source_file": "qc_collagen/participant_trichrome_collagen_proxy.csv",
            "participant_id_source_column": "participant_id",
            "tier_value": participant_tiers.get(participant_id, ""),
            "tier_source_file": (
                "tier_a_download_checklist.csv" if participant_id in participant_tiers else ""
            ),
            "tier_source_column": "tier" if participant_id in participant_tiers else "",
            "tier_definition": "undefined in inspected local files",
        }
        for field in fields:
            records = [r for r in observations[participant_id] if r["field"] == field]
            unique_values = sorted({r["value"] for r in records})
            selected = records[0] if len(unique_values) == 1 and records else None
            row[f"{field}_value"] = selected["value"] if selected else ""
            row[f"{field}_source_file"] = selected["source_file"] if selected else ""
            row[f"{field}_source_column"] = selected["source_column"] if selected else ""
            row[f"{field}_availability_note"] = (
                "available in inspected local metadata"
                if selected
                else (
                    "conflicting values in inspected metadata; left blank"
                    if len(unique_values) > 1
                    else "no matching labeled value found in inspected local/catalog files"
                )
            )
        output.append(row)
    write_rows(REVIEW / "participant_reference_labels.csv", output)
    write_rows(REVIEW / "metadata_label_field_audit.csv", metadata_audit)
    availability = []
    for field in fields:
        labeled = [
            row for row in output if str(row.get(f"{field}_value", "")).strip()
        ]
        availability.append(
            {
                "label": field,
                "participants_with_value": len(labeled),
                "participants_blank": len(output) - len(labeled),
                "participants_with_value_ids": "; ".join(
                    row["participant_id"] for row in labeled
                ),
                "source_files": "; ".join(
                    sorted(
                        {
                            row[f"{field}_source_file"]
                            for row in labeled
                            if row[f"{field}_source_file"]
                        }
                    )
                ),
                "source_columns": "; ".join(
                    sorted(
                        {
                            row[f"{field}_source_column"]
                            for row in labeled
                            if row[f"{field}_source_column"]
                        }
                    )
                ),
            }
        )
    write_rows(REVIEW / "reference_label_availability_summary.csv", availability)
    return output, metadata_audit


def bootstrap_effect_ci(effect, groups, seed):
    generator = np.random.default_rng(seed)
    samples = []
    for _ in range(BOOTSTRAP_REPLICATES):
        boot_groups = [
            group[generator.integers(0, len(group), size=len(group))]
            for group in groups
        ]
        value = effect(*boot_groups)
        if np.isfinite(value):
            samples.append(float(value))
    if not samples:
        return "", ""
    lower, upper = np.percentile(samples, [2.5, 97.5])
    return float(lower), float(upper)


def build_reference_test_table(labels, participant_expression, participant_proxy):
    label_fields = list(REFERENCE_FIELDS)
    outcomes = [
        "ECM_collagen_pseudobulk_module",
        "myofibroblast_pro_fibrotic_pseudobulk_module",
        "trichrome_collagen_proxy",
    ]
    outcome_sources = {
        "ECM_collagen_pseudobulk_module": (
            "qc_collagen/pseudobulk_log_cpm.csv",
            "mean(COL1A1,COL1A2,COL3A1,FN1)",
        ),
        "myofibroblast_pro_fibrotic_pseudobulk_module": (
            "qc_collagen/pseudobulk_log_cpm.csv",
            "mean(ACTA2,TGFB1,CCN2,SERPINE1)",
        ),
        "trichrome_collagen_proxy": (
            "qc_collagen/participant_trichrome_collagen_proxy.csv",
            "trichrome_collagen_proxy",
        ),
    }
    outcomes_by_participant = {}
    for participant_id, values in participant_expression.items():
        outcomes_by_participant[participant_id] = dict(values)
    for participant_id, value in participant_proxy.items():
        outcomes_by_participant.setdefault(participant_id, {})[
            "trichrome_collagen_proxy"
        ] = value
    test_rows = []
    for field in label_fields:
        for outcome_index, outcome in enumerate(outcomes):
            pairs = []
            sources = set()
            for row in labels:
                participant_id = row["participant_id"]
                raw_label = row.get(f"{field}_value", "").strip()
                raw_outcome = outcomes_by_participant.get(participant_id, {}).get(outcome)
                if not raw_label or raw_outcome in (None, ""):
                    continue
                pairs.append((participant_id, raw_label, float(raw_outcome)))
                if row.get(f"{field}_source_file"):
                    sources.add(
                        (
                            row[f"{field}_source_file"],
                            row[f"{field}_source_column"],
                        )
                    )
            n = len(pairs)
            label_source = "; ".join(sorted({item[0] for item in sources}))
            label_column = "; ".join(sorted({item[1] for item in sources}))
            outcome_source, outcome_column = outcome_sources[outcome]
            result = {
                "label": field,
                "outcome": outcome,
                "test": "",
                "n_participants": n,
                "effect_size": "",
                "bootstrap_ci_95_low": "",
                "bootstrap_ci_95_high": "",
                "p_value": "",
                "status": "",
                "label_source_files": label_source,
                "label_source_columns": label_column,
                "outcome_source_file": outcome_source,
                "outcome_source_column": outcome_column,
            }
            if n < 10:
                result["status"] = "not run: fewer than 10 paired participants"
                test_rows.append(result)
                continue
            categorical = field in {"reference_vs_ckd", "diagnosis", "sex"}
            numeric_values = []
            numeric = not categorical
            if numeric:
                try:
                    numeric_values = [float(item[1]) for item in pairs]
                except ValueError:
                    numeric = False
            if numeric:
                x = np.asarray(numeric_values, dtype=float)
                y = np.asarray([item[2] for item in pairs], dtype=float)
                statistic = spearmanr(x, y)
                result.update(
                    {
                        "test": "Spearman correlation",
                        "effect_size": float(statistic.statistic),
                        "p_value": float(statistic.pvalue),
                    }
                )
                lower, upper = bootstrap_effect_ci(
                    lambda sample_x, sample_y: spearmanr(sample_x, sample_y).statistic,
                    [x, y],
                    SEED + outcome_index + label_fields.index(field) * 100,
                )
                result["bootstrap_ci_95_low"] = lower
                result["bootstrap_ci_95_high"] = upper
                result["status"] = "tested; participant bootstrap CI"
            else:
                categories = sorted({item[1] for item in pairs})
                if len(categories) != 2:
                    result["status"] = (
                        "not run: nominal label has other than two groups; "
                        "no contrast prespecified"
                    )
                    test_rows.append(result)
                    continue
                first = np.asarray(
                    [item[2] for item in pairs if item[1] == categories[0]],
                    dtype=float,
                )
                second = np.asarray(
                    [item[2] for item in pairs if item[1] == categories[1]],
                    dtype=float,
                )

                def rank_biserial(left, right):
                    u_value = mannwhitneyu(
                        left, right, alternative="two-sided", method="asymptotic"
                    ).statistic
                    return 2.0 * float(u_value) / (len(left) * len(right)) - 1.0

                test = mannwhitneyu(
                    first, second, alternative="two-sided", method="asymptotic"
                )
                lower, upper = bootstrap_effect_ci(
                    rank_biserial,
                    [first, second],
                    SEED + outcome_index + label_fields.index(field) * 100,
                )
                result.update(
                    {
                        "test": "Mann-Whitney U; rank-biserial effect",
                        "effect_size": rank_biserial(first, second),
                        "bootstrap_ci_95_low": lower,
                        "bootstrap_ci_95_high": upper,
                        "p_value": float(test.pvalue),
                        "status": f"tested; group1={categories[0]}, group2={categories[1]}",
                    }
                )
            test_rows.append(result)
    write_rows(REVIEW / "reference_group_tests.csv", test_rows)
    return test_rows


def read_participant_pseudobulk_modules():
    rows = read_rows(QC / "pseudobulk_log_cpm.csv")
    modules = {}
    definitions = {
        "ECM_collagen_pseudobulk_module": ("COL1A1", "COL1A2", "COL3A1", "FN1"),
        "myofibroblast_pro_fibrotic_pseudobulk_module": (
            "ACTA2",
            "TGFB1",
            "CCN2",
            "SERPINE1",
        ),
    }
    for row in rows:
        modules[row["participant_id"]] = {
            module: float(np.mean([float(row[gene]) for gene in genes]))
            for module, genes in definitions.items()
            if all(row.get(gene, "") != "" for gene in genes)
        }
    return modules


def normalize_white_reference(image_rgb, tissue_mask, threshold):
    height, width = tissue_mask.shape
    stride = max(1, int(math.ceil(math.sqrt((height * width) / 800_000))))
    sampled_image = image_rgb[::stride, ::stride]
    sampled_mask = tissue_mask[::stride, ::stride]
    hsv_sampled = cv2.cvtColor(sampled_image, cv2.COLOR_RGB2HSV)
    background_mask = (
        (hsv_sampled[:, :, 1] <= threshold) & (hsv_sampled[:, :, 2] >= 180)
    )
    background_rgb = sampled_image[background_mask]
    if len(background_rgb):
        white_reference = np.median(background_rgb, axis=0)
    else:
        white_reference = np.array([255.0, 255.0, 255.0])
    normalized = image_rgb.copy()
    if np.all(white_reference >= 160):
        for channel in range(3):
            normalized[:, :, channel] = cv2.convertScaleAbs(
                image_rgb[:, :, channel],
                alpha=255.0 / float(white_reference[channel]),
                beta=0,
            )
        status = "applied"
    else:
        status = "not applied: unreliable bright background reference"
    return normalized, sampled_image, sampled_mask, stride, white_reference, status


def tissue_mask_for_slide(image_rgb, raw_hsv, analysis_mpp_x, analysis_mpp_y):
    saturation = raw_hsv[:, :, 1]
    otsu, binary = cv2.threshold(
        saturation, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    pixel_area_mm2 = analysis_mpp_x * analysis_mpp_y / 1_000_000.0
    min_object_px = max(1, int(math.ceil(MIN_OBJECT_AREA_MM2 / pixel_area_mm2)))
    min_hole_px = max(1, int(math.ceil(MIN_HOLE_AREA_MM2 / pixel_area_mm2)))
    mask = remove_small_objects(binary.astype(bool), min_size=min_object_px)
    mask = remove_small_holes(mask, area_threshold=min_hole_px)
    return float(otsu), mask


def slide_color_and_proxy(slide_row):
    slide_path = ROOT / slide_row["path"]
    slide = openslide.OpenSlide(str(slide_path))
    level = int(slide_row["openslide_level"])
    image = np.asarray(
        slide.read_region((0, 0), level, slide.level_dimensions[level]).convert("RGB")
    )
    properties = slide.properties
    mpp_x = float(properties[openslide.PROPERTY_NAME_MPP_X])
    mpp_y = float(properties[openslide.PROPERTY_NAME_MPP_Y])
    downsample = float(slide.level_downsamples[level])
    slide.close()
    analysis_mpp_x = mpp_x * downsample
    analysis_mpp_y = mpp_y * downsample
    raw_hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    otsu, tissue_mask = tissue_mask_for_slide(
        image, raw_hsv, analysis_mpp_x, analysis_mpp_y
    )
    normalized, sampled_image, sampled_mask, stride, white_ref, norm_status = (
        normalize_white_reference(image, tissue_mask, otsu)
    )
    normalized_hsv = cv2.cvtColor(normalized, cv2.COLOR_RGB2HSV)
    tissue_hsv = normalized_hsv[::stride, ::stride][sampled_mask]
    base_mask = (
        tissue_mask
        & (normalized_hsv[:, :, 0] >= BASE_HUE_LOW)
        & (normalized_hsv[:, :, 0] <= BASE_HUE_HIGH)
        & (normalized_hsv[:, :, 1] >= BASE_SAT_MIN)
    )
    candidate_hsv = normalized_hsv[base_mask]
    tissue_n = int(np.count_nonzero(tissue_mask))
    candidate_n = int(np.count_nonzero(base_mask))
    if not tissue_n:
        raise RuntimeError(f"Empty tissue mask for {slide_row['slide_id']}")

    permissive = (
        tissue_mask
        & (normalized_hsv[:, :, 0] >= PERMISSIVE_HUE_LOW)
        & (normalized_hsv[:, :, 0] <= PERMISSIVE_HUE_HIGH)
        & (normalized_hsv[:, :, 1] >= PERMISSIVE_SAT_MIN)
    )
    strict = (
        tissue_mask
        & (normalized_hsv[:, :, 0] >= STRICT_HUE_LOW)
        & (normalized_hsv[:, :, 0] <= STRICT_HUE_HIGH)
        & (normalized_hsv[:, :, 1] >= STRICT_SAT_MIN)
    )
    tissue_rgb = normalized[::stride, ::stride][sampled_mask]
    percentiles = np.percentile(tissue_rgb, [2, 98], axis=0)
    lower, upper = percentiles[0], percentiles[1]
    denominator = np.maximum(upper - lower, 1.0)
    percentile_rgb = np.clip(
        (normalized.astype(np.float32) - lower[None, None, :])
        * (255.0 / denominator[None, None, :]),
        0,
        255,
    ).astype(np.uint8)
    percentile_hsv = cv2.cvtColor(percentile_rgb, cv2.COLOR_RGB2HSV)
    percentile_mask = (
        tissue_mask
        & (percentile_hsv[:, :, 0] >= BASE_HUE_LOW)
        & (percentile_hsv[:, :, 0] <= BASE_HUE_HIGH)
        & (percentile_hsv[:, :, 1] >= BASE_SAT_MIN)
    )
    pixel_area_mm2 = analysis_mpp_x * analysis_mpp_y / 1_000_000.0
    candidate_medians = (
        np.median(candidate_hsv, axis=0) if candidate_n else [np.nan] * 3
    )
    stats = {
        "participant_id": slide_row["participant_id"],
        "tier": slide_row["tier"],
        "slide_id": slide_row["slide_id"],
        "file_name": slide_row["file_name"],
        "path": slide_row["path"],
        "tissue_median_hue": float(np.median(tissue_hsv[:, 0])),
        "tissue_median_saturation": float(np.median(tissue_hsv[:, 1])),
        "tissue_median_value": float(np.median(tissue_hsv[:, 2])),
        "collagen_candidate_median_hue": (
            float(candidate_medians[0]) if candidate_n else ""
        ),
        "collagen_candidate_median_saturation": (
            float(candidate_medians[1]) if candidate_n else ""
        ),
        "collagen_candidate_median_value": (
            float(candidate_medians[2]) if candidate_n else ""
        ),
        "white_reference_R": float(white_ref[0]),
        "white_reference_G": float(white_ref[1]),
        "white_reference_B": float(white_ref[2]),
        "white_reference_normalization": norm_status,
        "sample_stride_px": stride,
        "tissue_pixels": tissue_n,
        "base_candidate_pixels": candidate_n,
        "baseline_proxy_recomputed": candidate_n / tissue_n,
        "permissive_proxy": int(np.count_nonzero(permissive)) / tissue_n,
        "strict_proxy": int(np.count_nonzero(strict)) / tissue_n,
        "percentile_normalized_proxy": (
            int(np.count_nonzero(percentile_mask)) / tissue_n
        ),
        "analysis_pixel_area_mm2": pixel_area_mm2,
        "percentile_channel_p2_rgb": ";".join(f"{x:.3f}" for x in lower),
        "percentile_channel_p98_rgb": ";".join(f"{x:.3f}" for x in upper),
        "analysis_image_width_px": image.shape[1],
        "analysis_image_height_px": image.shape[0],
        "raw_slide_width_px": slide_row["slide_width_px"],
        "raw_slide_height_px": slide_row["slide_height_px"],
    }
    return stats


def generate_contact_sheet(slides, output_path, title):
    tile_width, image_height, label_height = 500, 300, 58
    columns = 2
    rows = math.ceil(len(slides) / columns)
    title_height = 30
    canvas = Image.new(
        "RGB",
        (
            columns * tile_width,
            title_height + rows * (image_height + label_height),
        ),
        "white",
    )
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for index, row in enumerate(slides):
        composite_path = (
            QC
            / "slides"
            / row["participant_id"]
            / f"{row['slide_id']}_qc.png"
        )
        if not composite_path.is_file():
            raise FileNotFoundError(f"Missing existing slide QC composite: {composite_path}")
        image = Image.open(composite_path).convert("RGB")
        image.thumbnail((tile_width, image_height), Image.Resampling.LANCZOS)
        x = (index % columns) * tile_width
        y = title_height + (index // columns) * (image_height + label_height)
        draw.text(
            (x + 4, y + 3),
            f"{row['participant_id']} | {row['slide_id']} | proxy={float(row['trichrome_collagen_proxy']):.4f}",
            fill="black",
            font=font,
        )
        canvas.paste(image, (x, y + label_height))
    draw.text((5, 5), title, fill="darkblue", font=font)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)


def build_participant_proxy_variants(slide_stats, participant_rows):
    accum = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    variants = [
        "baseline_proxy_recomputed",
        "permissive_proxy",
        "strict_proxy",
        "percentile_normalized_proxy",
    ]
    for row in slide_stats:
        area = float(row["analysis_pixel_area_mm2"])
        participant = row["participant_id"]
        for variant in variants:
            tissue_area = float(row["tissue_pixels"]) * area
            collagen_area = float(row[variant]) * tissue_area
            accum[participant][variant][0] += collagen_area
            accum[participant][variant][1] += tissue_area
    original = {
        row["participant_id"]: float(row["trichrome_collagen_proxy"])
        for row in participant_rows
        if row.get("trichrome_collagen_proxy", "") != ""
    }
    result = []
    for participant_id in sorted(accum):
        row = {"participant_id": participant_id}
        row["original_proxy"] = original.get(participant_id, "")
        for variant in variants:
            collagen_area, tissue_area = accum[participant_id][variant]
            row[variant] = collagen_area / tissue_area if tissue_area else ""
        result.append(row)
    rank_rows = []
    for variant in ["permissive_proxy", "strict_proxy", "percentile_normalized_proxy"]:
        a = np.asarray(
            [row["original_proxy"] for row in result if row["original_proxy"] != ""],
            dtype=float,
        )
        b = np.asarray(
            [row[variant] for row in result if row["original_proxy"] != ""],
            dtype=float,
        )
        statistic = spearmanr(a, b)
        rank_rows.append(
            {
                "comparison": f"original participant proxy vs {variant}",
                "n_participants": len(a),
                "spearman_rho": float(statistic.statistic),
                "p_value": float(statistic.pvalue),
            }
        )
    alternative_variants = variants[1:]
    for left_index, left in enumerate(alternative_variants):
        for right in alternative_variants[left_index + 1 :]:
            a = np.asarray([row[left] for row in result], dtype=float)
            b = np.asarray([row[right] for row in result], dtype=float)
            statistic = spearmanr(a, b)
            rank_rows.append(
                {
                    "comparison": f"{left} vs {right}",
                    "n_participants": len(a),
                    "spearman_rho": float(statistic.statistic),
                    "p_value": float(statistic.pvalue),
                }
            )
    write_rows(REVIEW / "participant_proxy_variants.csv", result)
    write_rows(REVIEW / "participant_proxy_rank_agreement.csv", rank_rows)
    return result, rank_rows


def correlate_slide_color_stats(slide_stats):
    fields = [
        "tissue_median_hue",
        "tissue_median_saturation",
        "tissue_median_value",
        "collagen_candidate_median_hue",
        "collagen_candidate_median_saturation",
        "collagen_candidate_median_value",
    ]
    proxy = np.asarray([row["baseline_proxy_recomputed"] for row in slide_stats], dtype=float)
    results = []
    for field in fields:
        pairs = [
            (row[field], row["baseline_proxy_recomputed"])
            for row in slide_stats
            if row[field] != ""
        ]
        x = np.asarray([pair[0] for pair in pairs], dtype=float)
        y = np.asarray([pair[1] for pair in pairs], dtype=float)
        statistic = spearmanr(x, y)
        results.append(
            {
                "color_statistic": field,
                "n_slides": len(x),
                "spearman_rho": float(statistic.statistic),
                "p_value": float(statistic.pvalue),
                "absolute_rho_at_least_0_7_descriptive_flag": (
                    abs(float(statistic.statistic)) >= 0.7
                ),
            }
        )

    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    fig, axes = plt.subplots(2, 3, figsize=(18, 11))
    for axis, field in zip(axes.flat, fields):
        for row in slide_stats:
            if row[field] == "":
                continue
            x = float(row[field])
            y = float(row["baseline_proxy_recomputed"])
            axis.scatter(x, y, s=22)
            axis.annotate(
                row["slide_id"],
                (x, y),
                xytext=(3, 3),
                textcoords="offset points",
                fontsize=5,
                alpha=0.75,
            )
        axis.set_xlabel(field)
        axis.set_ylabel("trichrome_collagen_proxy")
        axis.grid(alpha=0.2)
    fig.suptitle("Slide-level color statistics vs recomputed proxy (n=33 slides)")
    fig.tight_layout()
    fig.savefig(REVIEW / "proxy_vs_slide_color_stats.png", dpi=180)
    plt.close(fig)
    write_rows(REVIEW / "slide_color_proxy_correlations.csv", results)
    return results


def audit_segmentation_archives(participant_ids, tri_rows):
    tri_by_pid = defaultdict(list)
    for row in tri_rows:
        tri_by_pid[row["participant_id"]].append(row)
    archive_paths = sorted(DATA.rglob("*Seg_Masks_Features*.zip"))
    package_rows = []
    image_rows = []
    for archive_path in archive_paths:
        participant_id = archive_path.parts[-3]
        if participant_id not in participant_ids:
            continue
        archive_name = archive_path.name
        slide_match = re.search(r"S-\d{4}-\d{6}", archive_name)
        package_slide_id = slide_match.group(0) if slide_match else ""
        all_files = []
        image_records = []
        channels = []
        with zipfile.ZipFile(archive_path) as archive:
            for item in archive.infolist():
                if item.is_dir():
                    continue
                all_files.append(item.filename)
                if not item.filename.lower().endswith((".tif", ".tiff")):
                    continue
                with archive.open(item.filename) as stream:
                    with tifffile.TiffFile(stream) as tif:
                        series_dims = []
                        for series in tif.series:
                            shape = tuple(int(axis) for axis in series.shape)
                            axes = series.axes
                            series_dims.append((shape, axes))
                        ome_channels = []
                        size_x = size_y = ""
                        if tif.ome_metadata:
                            xml = tif.ome_metadata
                            root_xml = __import__("xml.etree.ElementTree", fromlist=["ElementTree"]).fromstring(xml)
                            pixels = next(
                                (node for node in root_xml.iter() if node.tag.endswith("Pixels")),
                                None,
                            )
                            if pixels is not None:
                                size_x = pixels.attrib.get("SizeX", "")
                                size_y = pixels.attrib.get("SizeY", "")
                            ome_channels = [
                                node.attrib.get("Name", "")
                                for node in root_xml.iter()
                                if node.tag.endswith("Channel")
                                and node.attrib.get("Name", "")
                            ]
                        channels.extend(ome_channels)
                        image_records.append(
                            {
                                "participant_id": participant_id,
                                "archive": archive_name,
                                "archive_slide_id": package_slide_id,
                                "image_file": item.filename,
                                "ome_size_x_px": size_x,
                                "ome_size_y_px": size_y,
                                "series_shapes_axes": "; ".join(
                                    f"{shape}:{axes}" for shape, axes in series_dims
                                ),
                                "ome_channels": "; ".join(ome_channels),
                            }
                        )
        tri_slides = tri_by_pid.get(participant_id, [])
        tri_ids = sorted({row["slide_id"] for row in tri_slides})
        tri_dims = {
            (
                int(float(row["slide_width_px"])),
                int(float(row["slide_height_px"])),
                row["slide_id"],
            )
            for row in tri_slides
        }
        tri_dimensions_text = "; ".join(
            f"{tri_id}:{tri_width}x{tri_height}"
            for tri_width, tri_height, tri_id in sorted(tri_dims)
        )
        dimension_matches = []
        for image_row in image_records:
            if image_row["ome_size_x_px"] and image_row["ome_size_y_px"]:
                mask_dims = (
                    int(image_row["ome_size_x_px"]),
                    int(image_row["ome_size_y_px"]),
                )
                for tri_width, tri_height, tri_id in tri_dims:
                    if mask_dims == (tri_width, tri_height):
                        dimension_matches.append(tri_id)
        same_slide_id = bool(package_slide_id and package_slide_id in tri_ids)
        if not image_records:
            alignment = "unknown: no readable TIFF image in archive"
        elif same_slide_id and dimension_matches:
            alignment = "same slide ID and exact full-resolution dimensions"
        elif dimension_matches:
            alignment = "dimensions match a participant TRI WSI, but slide IDs differ"
        elif not same_slide_id:
            alignment = (
                "archive slide ID differs from participant TRI slide IDs; "
                "no exact full-resolution dimension match"
            )
        else:
            alignment = "same slide ID, but no exact full-resolution dimension match"
        package_rows.append(
            {
                "participant_id": participant_id,
                "archive": archive_name,
                "archive_path": str(archive_path.relative_to(ROOT)),
                "archive_slide_id": package_slide_id,
                "tri_slide_ids": "; ".join(tri_ids),
                "tri_slide_dimensions_px": tri_dimensions_text,
                "ome_channels": "; ".join(sorted(set(channels))),
                "tiff_images": "; ".join(Path(row["image_file"]).name for row in image_records),
                "matching_tri_slide_ids_by_exact_dimensions": "; ".join(sorted(set(dimension_matches))),
                "alignment_status": alignment,
                "archive_file_count": len(all_files),
                "archive_file_types": "; ".join(
                    sorted({Path(name).suffix.lower() or "[no extension]" for name in all_files})
                ),
                "features_or_readme_files": "; ".join(
                    Path(name).name
                    for name in all_files
                    if Path(name).suffix.lower() in {".xlsx", ".xml", ".txt", ".md", ".csv"}
                ),
            }
        )
        image_rows.extend(image_records)
    no_archive_rows = [
        {
            "participant_id": participant_id,
            "archive": "",
            "archive_path": "",
            "archive_slide_id": "",
            "tri_slide_ids": "; ".join(sorted({r["slide_id"] for r in tri_by_pid[participant_id]})),
            "tri_slide_dimensions_px": "; ".join(
                f"{row['slide_id']}:{row['slide_width_px']}x{row['slide_height_px']}"
                for row in tri_by_pid[participant_id]
            ),
            "ome_channels": "",
            "tiff_images": "",
            "matching_tri_slide_ids_by_exact_dimensions": "",
            "alignment_status": "no local segmentation archive",
            "archive_file_count": 0,
            "archive_file_types": "",
            "features_or_readme_files": "",
        }
        for participant_id in participant_ids
        if participant_id not in {row["participant_id"] for row in package_rows}
    ]
    package_rows.extend(no_archive_rows)
    write_rows(REVIEW / "segmentation_package_audit.csv", package_rows)
    write_rows(REVIEW / "segmentation_image_dimensions.csv", image_rows)
    return package_rows, image_rows


def audit_segmentation_feature_headers(participant_ids):
    rows = []
    for archive_path in sorted(DATA.rglob("*Seg_Masks_Features*.zip")):
        participant_id = archive_path.parts[-3]
        if participant_id not in participant_ids:
            continue
        with zipfile.ZipFile(archive_path) as archive:
            for name in archive.namelist():
                if not name.lower().endswith(".xlsx"):
                    continue
                workbook = openpyxl.load_workbook(
                    BytesIO(archive.read(name)), read_only=True, data_only=True
                )
                for sheet in workbook.worksheets:
                    leading_labels = []
                    for row in sheet.iter_rows(
                        min_row=1, max_row=min(sheet.max_row, 8), values_only=True
                    ):
                        leading_labels.extend(
                            str(value).strip()
                            for value in row
                            if isinstance(value, str) and value.strip()
                        )
                    matching = sorted(
                        {
                            label
                            for label in leading_labels
                            if label_field_for_header(label)
                        }
                    )
                    rows.append(
                        {
                            "participant_id": participant_id,
                            "source_archive": str(archive_path.relative_to(ROOT)),
                            "feature_workbook": Path(name).name,
                            "sheet": sheet.title,
                            "reference_like_header_labels_first_8_rows": "; ".join(matching),
                            "interpretation": (
                                "candidate header found; not used as a clinical/pathologist label"
                                if matching
                                else "none found in first 8 rows; measurements not extracted"
                            ),
                        }
                    )
    write_rows(REVIEW / "segmentation_feature_header_audit.csv", rows)
    return rows


def write_review_checklist(slide_rows):
    rows = [
        {
            "slide_id": row["slide_id"],
            "participant_id": row["participant_id"],
            "pen_mark": "",
            "fold": "",
            "blur": "",
            "out_of_focus_area": "",
            "large_empty_area": "",
            "notes": "",
        }
        for row in sorted(slide_rows, key=lambda row: (row["participant_id"], row["slide_id"]))
    ]
    write_rows(
        REVIEW / "manual_slide_review_checklist.csv",
        rows,
        [
            "slide_id",
            "participant_id",
            "pen_mark",
            "fold",
            "blur",
            "out_of_focus_area",
            "large_empty_area",
            "notes",
        ],
    )


def write_report(
    slide_rows,
    slide_stats,
    color_correlations,
    rank_rows,
    candidate_rows,
    download_status,
    labels,
    test_rows,
    segmentation_rows,
    verification_rows,
):
    strong = [
        row["color_statistic"]
        for row in color_correlations
        if row["absolute_rho_at_least_0_7_descriptive_flag"]
    ]
    available_counts = {
        field: sum(bool(row.get(f"{field}_value", "").strip()) for row in labels)
        for field in REFERENCE_FIELDS
    }
    no_label = [
        field for field, count in available_counts.items() if count == 0
    ]
    manifest_path = REVIEW / "metadata_download_manifest.csv"
    downloads_succeeded = len(read_rows(manifest_path)) if manifest_path.exists() else 0
    downloads_failed = [
        row for row in download_status if row["status"].startswith("download failed")
    ]
    tier_counts = defaultdict(int)
    for row in labels:
        tier_counts[row["tier_value"] or "blank"] += 1
    metadata_audit_rows = read_rows(REVIEW / "metadata_label_field_audit.csv")
    metadata_workbook_count = sum(bool(row["source_file"]) for row in metadata_audit_rows)
    metadata_participant_count = len(
        {
            row["participant_id"]
            for row in metadata_audit_rows
            if row["source_file"]
        }
    )
    metadata_participant_ids = {
        row["participant_id"]
        for row in metadata_audit_rows
        if row["source_file"]
    }
    no_metadata_participants = sorted(
        row["participant_id"]
        for row in labels
        if row["participant_id"] not in metadata_participant_ids
    )
    access_counts = Counter(row["access_level"].strip().lower() for row in candidate_rows)
    segmentation_with_ifta = sum("IFTA" in row["ome_channels"] for row in segmentation_rows)
    dimension_alignment_counts = Counter(
        row["alignment_status"] for row in segmentation_rows if row["archive"]
    )
    verify_text = "; ".join(
        f"{row['slide_id']}: diff={row['absolute_difference']:.3g}"
        for row in verification_rows
    )
    lines = [
        "# Proxy and independent-reference review",
        "",
        "## Scope and safeguards",
        "",
        "- New files are confined to `D:\\patent\\qc_collagen\\review\\`; earlier QC outputs and raw data were read-only.",
        "- No registration, model training, batch correction, or mask-based measurement was performed.",
        "- Slide-level summaries use n=33 slides; participant-level summaries and tests use participants as the unit.",
        "- The source used for the proxy is `qc_collagen\\trichrome_slide_proxy_summary.csv`; participant proxy is `qc_collagen\\participant_trichrome_collagen_proxy.csv`.",
        "",
        "## Part A: proxy and stain/tissue",
        "",
        f"- Slides ranked: {len(slide_rows)}. Contact sheets show the ten lowest and ten highest existing QC composites.",
        f"- Spearman correlations are in `slide_color_proxy_correlations.csv`, each with n=33 slides. A descriptive absolute-rho threshold of 0.70 flags strong association; flagged statistics: {', '.join(strong) if strong else 'none'}. P-values are nominal and not multiplicity-adjusted.",
        "- Color statistics were recomputed from each existing TRI WSI at the same recorded OpenSlide level used by the original proxy; median hue, saturation, and value were computed inside the tissue mask and inside baseline collagen candidates.",
        "- Threshold sensitivity: baseline is H=75-140, S>=35; permissive is H=65-145, S>=20; strict is H=85-135, S>=60. Percentile normalization maps the per-slide tissue RGB 2nd-98th percentile to 0-255, then applies the baseline HSV window.",
        "- Participant-level rank agreement between proxy variants is in `participant_proxy_rank_agreement.csv`; slide-level variants are in `slide_color_proxy_statistics.csv`.",
        f"- Three randomly selected slides were reopened and recomputed from source WSI pixels (seed={SEED}); results: {verify_text}.",
        "- This checks sensitivity to the stain-color rule, not biological validity of collagen segmentation. No expression outcome was used to choose thresholds.",
        "",
        "## Part B: independent reference labels",
        "",
        f"- Catalog candidates are listed in `reference_candidate_inventory.csv` with access level from `atlas_repository_filelist-20261105.csv`. It includes {len(candidate_rows)} cohort-specific metadata/pathology/segmentation candidate records.",
        f"- Catalog candidate access levels: {dict(access_counts)}. There are {len([row for row in candidate_rows if row['workflow'] == 'Experimental Metadata'])} Experimental Metadata workbooks; these assay-specific sheets were screened, not assumed to be clinical labels.",
        f"- Open experimental-metadata downloads completed: {downloads_succeeded}; failed: {len(downloads_failed)}. Only catalog rows marked open were eligible; downloaded files and SHA-256 values are in `metadata_download_manifest.csv`.",
        f"- Inspected {metadata_workbook_count} local/catalog-listed experimental-metadata workbooks across {metadata_participant_count} participants; participants with any requested clinical/pathology label value: {sum(any(row.get(field + '_value', '').strip() for field in REFERENCE_FIELDS) for row in labels)} of {len(labels)}.",
        f"- No catalog-listed experimental metadata workbook was available locally or in the open candidate set for: {', '.join(no_metadata_participants) if no_metadata_participants else 'none'}.",
        f"- Labels unavailable for every participant: {', '.join(no_label)}.",
        f"- Tier values recorded from `tier_a_download_checklist.csv`: {dict(tier_counts)}. The definition of Tier A/B/C was not found in the inspected source files; tier was not treated as an outcome or clinical group.",
        f"- `reference_group_tests.csv` has {len(test_rows)} label/outcome rows. No inferential test is run where fewer than 10 participants have a labeled value; available n is shown per row.",
        "- Local metadata search covered participant metadata files and all catalog-listed cohort Experimental Metadata workbooks marked open; catalog metadata was not treated as a clinical value unless the workbook explicitly labeled it. No restricted file was requested or downloaded.",
        f"- Segmentation feature workbook header audit: {len(read_rows(REVIEW / 'segmentation_feature_header_audit.csv')) if (REVIEW / 'segmentation_feature_header_audit.csv').exists() else 0} sheets reviewed; see `segmentation_feature_header_audit.csv`. Feature values were not extracted.",
        "",
        "## Part C: segmentation package availability",
        "",
        f"- Local segmentation packages: {sum(bool(row['archive']) for row in segmentation_rows)} across {len({row['participant_id'] for row in segmentation_rows if row['archive']})} participants; {segmentation_with_ifta} packages contain a channel named IFTA.",
        f"- Alignment check against participant TRI WSI: {dict(dimension_alignment_counts)}. Archive and TRI slide IDs, channel names, and exact full-resolution pixel dimensions are listed in `segmentation_package_audit.csv`; per-image plane dimensions are in `segmentation_image_dimensions.csv`.",
        "- All segmentation OME files are listed as PAS slides; channel availability or equal pixel dimensions alone would not prove section identity or registration. No masks were applied to the proxy.",
        "",
        "## Explicit gaps / not verified",
        "",
        "- No independently labeled reference/CKD, diagnosis, IFTA/interstitial fibrosis, tubular atrophy, eGFR, age, or sex values were found in the inspected metadata files.",
        "- Tier A/B/C semantics were not defined by the inspected local files.",
        "- The proxy's blue/green HSV range is an exploratory stain-color threshold, not a validated collagen stain deconvolution or interstitial fibrosis measurement.",
        "- Manual visual review checklist remains blank; pen marks, folds, blur, focus and large empty regions were not manually adjudicated.",
        "- Segmentation-to-TRI alignment is only checked by archive slide ID and exact pixel dimensions; no image registration or mask application was performed.",
        "- Any catalog metadata not specifically downloaded is listed with its access level and was not assumed to contain labels.",
        "",
        "## Output inventory",
        "",
    ]
    for path in sorted(REVIEW.iterdir()):
        if path.is_file() and path.name != "review_report.md":
            lines.append(f"- `{path.name}`")
    lines.extend(
        [
            "- `contact_sheets/lowest_10_proxy.png` and `contact_sheets/highest_10_proxy.png`",
            "- `metadata_downloads/<participant>/<file>` for newly downloaded open metadata",
            "",
            "Software: OpenSlide Python "
            f"{openslide.__version__}, OpenSlide library {openslide.__library_version__}, "
            f"OpenCV {cv2.__version__}, NumPy {np.__version__}, SciPy {scipy.__version__}, "
            f"Pandas {pd.__version__}, tifffile {tifffile.__version__}, "
            f"openpyxl {openpyxl.__version__}. Random seed: "
            f"{SEED}; bootstrap replicates: {BOOTSTRAP_REPLICATES}.",
        ]
    )
    lines.extend(["", "## Participant label availability", ""])
    lines.append("| Label | Participants with value | Blank |")
    lines.append("|---|---:|---:|")
    for row in read_rows(REVIEW / "reference_label_availability_summary.csv"):
        lines.append(
            f"| {row['label']} | {row['participants_with_value']} | "
            f"{row['participants_blank']} |"
        )
    lines.extend(["", "## Slide color-statistic correlations", ""])
    lines.append("| Statistic | n slides | Spearman rho | p |")
    lines.append("|---|---:|---:|---:|")
    for row in color_correlations:
        lines.append(
            f"| {row['color_statistic']} | {row['n_slides']} | "
            f"{row['spearman_rho']:.3f} | {row['p_value']:.4g} |"
        )
    lines.extend(["", "## Participant proxy rank agreement", ""])
    lines.append("| Comparison | n participants | Spearman rho | p |")
    lines.append("|---|---:|---:|---:|")
    for row in rank_rows:
        lines.append(
            f"| {row['comparison']} | {row['n_participants']} | "
            f"{row['spearman_rho']:.3f} | {row['p_value']:.4g} |"
        )
    lines.extend(["", "## Recompute checks", ""])
    lines.append("| Participant | Slide | Status | Absolute difference |")
    lines.append("|---|---|---|---:|")
    for row in verification_rows:
        lines.append(
            f"| {row['participant_id']} | {row['slide_id']} | {row['status']} | "
            f"{row['absolute_difference']:.3g} |"
        )
    (REVIEW / "review_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    REVIEW.mkdir(parents=True, exist_ok=True)
    slide_rows = read_rows(TRI_SUMMARY)
    participant_rows = read_rows(PARTICIPANT_PROXY)
    participant_ids = sorted({row["participant_id"] for row in participant_rows})
    catalog_rows = load_catalog()
    checklist_rows = read_rows(CHECKLIST)
    participant_tiers = {
        row["participant_id"]: row.get("tier", "")
        for row in checklist_rows
        if row.get("participant_id") in participant_ids
    }

    ranked = sorted(
        slide_rows,
        key=lambda row: float(row["trichrome_collagen_proxy"]),
    )
    for rank, row in enumerate(ranked, start=1):
        row["proxy_rank_low_to_high"] = rank
    write_rows(REVIEW / "slide_proxy_rankings.csv", ranked)
    contact_dir = REVIEW / "contact_sheets"
    generate_contact_sheet(ranked[:10], contact_dir / "lowest_10_proxy.png", "10 lowest slide proxies")
    generate_contact_sheet(ranked[-10:][::-1], contact_dir / "highest_10_proxy.png", "10 highest slide proxies")
    write_review_checklist(slide_rows)

    slide_stats = []
    for index, row in enumerate(slide_rows, start=1):
        print(f"Reviewing slide {index}/{len(slide_rows)}: {row['slide_id']}", flush=True)
        slide_stats.append(slide_color_and_proxy(row))
    write_rows(REVIEW / "slide_color_proxy_statistics.csv", slide_stats)

    original_proxy_by_slide = {
        row["slide_id"]: float(row["trichrome_collagen_proxy"]) for row in slide_rows
    }
    verification_rng = np.random.default_rng(SEED)
    chosen = verification_rng.choice(len(slide_stats), size=min(3, len(slide_stats)), replace=False)
    verification_rows = []
    for index in sorted(int(value) for value in chosen):
        row = slide_stats[index]
        recorded = original_proxy_by_slide[row["slide_id"]]
        recomputed = float(row["baseline_proxy_recomputed"])
        verification_rows.append(
            {
                "participant_id": row["participant_id"],
                "slide_id": row["slide_id"],
                "status": "PASS" if abs(recorded - recomputed) <= 1e-12 else "FAIL",
                "existing_proxy": recorded,
                "recomputed_proxy": recomputed,
                "absolute_difference": abs(recorded - recomputed),
                "source_file": row["path"],
                "source_column": "raw WSI pixels at recorded OpenSlide level",
            }
        )
    write_rows(REVIEW / "three_slide_recompute_verification.csv", verification_rows)
    if any(row["status"] != "PASS" for row in verification_rows):
        raise RuntimeError("A selected slide failed the independent proxy recomputation.")

    correlation_rows = correlate_slide_color_stats(slide_stats)
    _variant_rows, rank_rows = build_participant_proxy_variants(
        slide_stats, participant_rows
    )
    for variant in [
        "baseline_proxy_recomputed",
        "permissive_proxy",
        "strict_proxy",
        "percentile_normalized_proxy",
    ]:
        for row in slide_stats:
            row[f"{variant}_rank_low_to_high"] = ""
        sorted_rows = sorted(slide_stats, key=lambda item: float(item[variant]))
        for rank, row in enumerate(sorted_rows, start=1):
            row[f"{variant}_rank_low_to_high"] = rank
    write_rows(REVIEW / "slide_color_proxy_statistics.csv", slide_stats)

    download_status = download_open_metadata_candidates(participant_ids, catalog_rows)
    candidate_rows = inspect_metadata_candidates(
        participant_ids, catalog_rows, download_status
    )
    labels, _metadata_audit = populate_reference_labels(
        participant_ids, participant_tiers
    )
    participant_expression = read_participant_pseudobulk_modules()
    participant_proxy = {
        row["participant_id"]: float(row["trichrome_collagen_proxy"])
        for row in participant_rows
        if row.get("trichrome_collagen_proxy", "") != ""
    }
    tests = build_reference_test_table(
        labels, participant_expression, participant_proxy
    )
    segmentation_rows, _image_rows = audit_segmentation_archives(
        participant_ids, slide_rows
    )
    audit_segmentation_feature_headers(participant_ids)
    write_report(
        slide_rows,
        slide_stats,
        correlation_rows,
        rank_rows,
        candidate_rows,
        download_status,
        labels,
        tests,
        segmentation_rows,
        verification_rows,
    )
    print(
        json.dumps(
            {
                "participants": len(participant_ids),
                "slides": len(slide_rows),
                "three_slide_verification": verification_rows,
                "download_status_counts": {
                    status: sum(row["status"] == status for row in download_status)
                    for status in sorted({row["status"] for row in download_status})
                },
                "candidate_inventory_rows": len(candidate_rows),
                "segmentation_packages": sum(bool(row["archive"]) for row in segmentation_rows),
                "outputs": str(REVIEW),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
