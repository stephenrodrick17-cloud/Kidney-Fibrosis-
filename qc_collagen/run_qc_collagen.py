import csv
import importlib.metadata
import json
import math
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(r"D:\patent")
sys.dont_write_bytecode = True
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cv2
import matplotlib
import numpy as np
import openslide
import pandas as pd
import PIL
import scipy
import tifffile
from matplotlib import pyplot as plt
from scipy import sparse
from scipy.stats import rankdata, t as student_t
from sklearn.decomposition import PCA
from skimage.color import rgb2lab
from skimage.morphology import remove_small_holes, remove_small_objects
from PIL import Image, ImageDraw, ImageFont

import analyze_cohort_plan_a_b as cohort


DATA = ROOT / "data"
OUT = ROOT / "qc_collagen"
CHECKLIST = ROOT / "tier_a_download_checklist.csv"
REPOSITORY_FILELIST = ROOT / "atlas_repository_filelist-20261105.csv"
PATIENT_SUMMARY = ROOT / "plan_a_plan_b" / "plan_a_patient_summary.csv"
GENES = (
    "COL1A1",
    "COL1A2",
    "COL3A1",
    "FN1",
    "TGFB1",
    "CCN2",
    "SERPINE1",
    "ACTA2",
    "MMP2",
    "MMP9",
    "TIMP1",
    "HAVCR1",
    "LCN2",
)
MODULES = {
    "ECM_collagen": ("COL1A1", "COL1A2", "COL3A1", "FN1"),
    "myofibroblast_pro-fibrotic": ("ACTA2", "TGFB1", "CCN2", "SERPINE1"),
    "matrix_remodelling": ("MMP2", "TIMP1"),
}
ENSEMBL_IDS = {
    "COL1A1": "ENSG00000108821",
    "COL1A2": "ENSG00000164692",
    "COL3A1": "ENSG00000168542",
    "FN1": "ENSG00000115414",
    "TGFB1": "ENSG00000105329",
    "CCN2": "ENSG00000118523",
    "SERPINE1": "ENSG00000106366",
    "ACTA2": "ENSG00000107796",
    "MMP2": "ENSG00000087245",
    "MMP9": "ENSG00000100985",
    "TIMP1": "ENSG00000102265",
    "HAVCR1": "ENSG00000113249",
    "LCN2": "ENSG00000148346",
}
GENE_ALIASES = {"CCN2": {"CCN2", "CTGF"}}
VISIUM_ID_RE = re.compile(r"V\d{2}[A-Z]\d{2}-\d+_XY\d{2}_\d{2}[-_]\d+", re.I)
SLIDE_ID_RE = re.compile(r"S-\d{4}-\d{6}", re.I)
RANDOM_SEED = 20261111
BOOTSTRAP_SEED = 20261112
BOOTSTRAP_REPLICATES = 5000
QC_PERCENTILE = 10.0
TARGET_MPP_UM = 3.0
MIN_OBJECT_AREA_MM2 = 0.005
MIN_HOLE_AREA_MM2 = 0.0025
GRID_BLOCK_UM = 256
HSV_HUE_LOW = 75
HSV_HUE_HIGH = 140
HSV_MIN_SATURATION = 35


def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalized_text(value):
    return str(value or "").strip().upper()


def gene_match_rows(features, gene):
    accepted = GENE_ALIASES.get(gene, {gene})
    ensembl = ENSEMBL_IDS[gene]
    matches = []
    for index, feature in enumerate(features):
        feature_id = normalized_text(feature[0] if feature else "").split(".")[0]
        feature_name = normalized_text(feature[1] if len(feature) > 1 else "")
        if feature_name == gene:
            matches.append((index, "symbol"))
        elif feature_name in accepted:
            matches.append((index, "alias"))
        elif feature_id == ensembl:
            matches.append((index, "Ensembl ID"))
    return matches


def feature_label(feature):
    feature_id = str(feature[0]).strip() if feature else ""
    feature_name = str(feature[1]).strip() if len(feature) > 1 else ""
    if feature_name and not feature_name.upper().startswith("ENSG"):
        label = feature_name.upper()
    else:
        label = feature_id.upper()
    for gene, aliases in GENE_ALIASES.items():
        if label in {alias.upper() for alias in aliases}:
            return gene
    for gene, ensembl in ENSEMBL_IDS.items():
        if label.split(".")[0] == ensembl:
            return gene
    return label or feature_id


def mitochondrial_rows(features):
    rows = []
    for index, feature in enumerate(features):
        feature_id = normalized_text(feature[0] if feature else "").split(".")[0]
        feature_name = normalized_text(feature[1] if len(feature) > 1 else "")
        if feature_name.startswith(("MT-", "MT.")) or feature_id.startswith(("MT-", "MT.")):
            rows.append(index)
    return rows


def sample_identifier(sample, participant_dir, sample_index, n_samples):
    search_paths = [sample["positions_path"]]
    search_paths.extend(sample["positions_path"].parents)
    for path in search_paths:
        match = VISIUM_ID_RE.search(str(path))
        if match:
            return match.group(0)
    for path in search_paths:
        match = re.search(
            rf"{re.escape(participant_dir.name)}-([A-Z])_extracted",
            str(path),
            re.I,
        )
        if match:
            return f"{participant_dir.name}-{match.group(1).upper()}"
    if n_samples == 1:
        candidates = sorted(
            {
                match.group(0)
                for path in (participant_dir / "visium").glob("*")
                if (match := VISIUM_ID_RE.search(path.name))
            }
        )
        if len(candidates) == 1:
            return candidates[0]
    return f"{participant_dir.name}-library-{sample_index:02d}"


def pair_expression_source(participant_dir, spatial_sample, sources):
    positions = cohort.read_positions(spatial_sample["positions_path"])
    in_tissue = positions.loc[positions["in_tissue"].astype(int) == 1].copy()
    if in_tissue.empty:
        raise ValueError(f"{spatial_sample['positions_path']}: no in-tissue spots")
    spatial_barcodes = set(in_tissue["barcode"].astype(str))
    scored = [
        (
            len(spatial_barcodes.intersection(set(source["barcodes"]))),
            cohort.shared_context_depth(
                source["path"],
                spatial_sample["positions_path"],
                participant_dir / "visium",
            ),
            source,
        )
        for source in sources
    ]
    scored.sort(key=lambda item: (item[0], item[1], len(item[2]["barcodes"])), reverse=True)
    if not scored or scored[0][0] != len(spatial_barcodes):
        matched = scored[0][0] if scored else 0
        raise ValueError(
            f"{spatial_sample['positions_path']}: incomplete expression barcode coverage "
            f"({matched}/{len(spatial_barcodes)})"
        )
    overlap, context_depth, _ = scored[0]
    candidates = [
        item[2]
        for item in scored
        if item[0] == overlap and item[1] == context_depth
    ]
    unique = []
    for candidate in candidates:
        if not any(
            cohort.equivalent_expression_sources(candidate, existing)
            for existing in unique
        ):
            unique.append(candidate)
    if len(unique) != 1:
        raise ValueError(
            f"{spatial_sample['positions_path']}: {len(unique)} non-equivalent expression "
            "matrices have complete matching barcode coverage"
        )
    barcode_to_col = {barcode: index for index, barcode in enumerate(unique[0]["barcodes"])}
    matched_positions = in_tissue.loc[
        in_tissue["barcode"].astype(str).isin(barcode_to_col)
    ].copy()
    if len(matched_positions) != len(in_tissue):
        raise ValueError(f"{spatial_sample['positions_path']}: barcode pairing changed")
    indices = np.asarray(
        [barcode_to_col[str(barcode)] for barcode in matched_positions["barcode"]],
        dtype=int,
    )
    return unique[0], matched_positions, indices


def load_cohort_inputs(checklist):
    for row in checklist:
        participant_id = row["participant_id"]
        participant_dir = DATA / participant_id
        sources = cohort.load_expression_sources(participant_dir)
        spatial_samples = cohort.find_spatial_samples(participant_dir)
        if not sources or not spatial_samples:
            raise RuntimeError(
                f"{participant_id}: expression sources or spatial samples are missing"
            )
        for sample_index, spatial_sample in enumerate(spatial_samples, 1):
            source, positions, indices = pair_expression_source(
                participant_dir, spatial_sample, sources
            )
            sample_id = sample_identifier(
                spatial_sample, participant_dir, sample_index, len(spatial_samples)
            )
            yield {
                "participant_id": participant_id,
                "tier": row.get("tier", ""),
                "sample_id": sample_id,
                "positions": positions,
                "spatial": spatial_sample,
                "source": source,
                "spot_indices": indices,
            }


def counts_per_label(source):
    labels = [feature_label(feature) for feature in source["features"]]
    unique_labels = list(dict.fromkeys(labels))
    label_index = {label: index for index, label in enumerate(unique_labels)}
    row_index = np.arange(len(labels), dtype=np.int64)
    collapse = sparse.csr_matrix(
        (
            np.ones(len(labels), dtype=np.int8),
            (np.asarray([label_index[label] for label in labels]), row_index),
        ),
        shape=(len(unique_labels), len(labels)),
    )
    return unique_labels, collapse @ source["matrix"]


def repository_platforms(participant_ids):
    result = defaultdict(set)
    if not REPOSITORY_FILELIST.exists():
        return result
    with REPOSITORY_FILELIST.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if (
                row.get("Participant ID", "").strip() in participant_ids
                and row.get("Experimental Strategy", "").strip()
                == "Spatial Transcriptomics Visium"
                and row.get("Workflow Type / Panel", "").strip() == "Expression Matrix"
            ):
                value = row.get("Platform", "").strip()
                if value:
                    result[row["Participant ID"].strip()].add(value)
    return result


def local_sample_metadata(participant_ids):
    records = {}
    audit_rows = []
    metadata_files = []
    for participant_id in participant_ids:
        metadata_dir = DATA / participant_id / "metadata"
        if not metadata_dir.exists():
            continue
        metadata_files.extend(
            sorted(path for path in metadata_dir.glob("*.xlsx") if "metadata" in path.name.lower())
        )
    for path in metadata_files:
        workbook = pd.ExcelFile(path)
        for sheet_name in workbook.sheet_names:
            if sheet_name not in {"FASTQ", "Expression Matrix"}:
                continue
            frame = pd.read_excel(path, sheet_name=sheet_name, header=None)
            if len(frame.index) < 5:
                continue
            headers = [
                str(value).strip() if pd.notna(value) else ""
                for value in frame.iloc[1].tolist()
            ]
            for _, row in frame.iloc[4:].iterrows():
                values = {
                    header: row.iloc[index]
                    for index, header in enumerate(headers)
                    if header and index < len(row)
                }
                participant_id = str(values.get("REDCap ID", "")).strip()
                if participant_id not in participant_ids:
                    continue
                file_values = " ".join(
                    str(values.get(key, ""))
                    for key in (
                        "Associated FASTQ File Name:",
                        "Associated FASTQ File Name (Paired End):",
                        "Matrix File Name:",
                    )
                )
                match = VISIUM_ID_RE.search(file_values)
                visium_id = match.group(0) if match else participant_id
                record = records.setdefault(
                    (participant_id, visium_id),
                    {
                        "participant_id": participant_id,
                        "visium_library_id": visium_id,
                        "metadata_file": str(path.relative_to(ROOT)),
                    },
                )
                if sheet_name == "FASTQ":
                    for field in (
                        "Sequencing Platform",
                        "Sequencer Model",
                        "Sequencer Software / Version",
                        "Sequencing Center",
                        "Sequencing Date",
                        "Total Raw Reads",
                        "Q30 Score (Percentage)",
                    ):
                        value = values.get(field)
                        if pd.notna(value):
                            record[field] = (
                                value.isoformat() if hasattr(value, "isoformat") else value
                            )
                else:
                    for field in (
                        "RNA Downstream Analysis Platform",
                        "RNA Downstream Analysis Platform Version",
                        "Sequencing Saturation",
                        "Number of Cells/Nuclei/Spots Sequenced Post-QC",
                        "Median Genes Detected (per cell/nucleus/spot)",
                        "Median UMI Detected (per cell/nucleus/spot)",
                    ):
                        value = values.get(field)
                        if pd.notna(value):
                            record[field] = value
                audit_rows.append(
                    {
                        "participant_id": participant_id,
                        "metadata_file": str(path.relative_to(ROOT)),
                        "sheet": sheet_name,
                        "visium_library_id": visium_id,
                        "fields_read": "; ".join(
                            key for key in values if key not in {"REDCap ID", "Internal TIS ID"}
                        ),
                    }
                )
    return records, audit_rows, metadata_files


def masked_color_stats(image_rgb, tissue_mask, saturation_threshold):
    height, width = tissue_mask.shape
    stride = max(1, int(math.ceil(math.sqrt((height * width) / 800_000))))
    sampled_image = image_rgb[::stride, ::stride]
    sampled_mask = tissue_mask[::stride, ::stride]
    sampled = sampled_image[sampled_mask]
    if sampled.size == 0:
        return {}, None, "no tissue pixels available for colour statistics"

    lab = rgb2lab(sampled.reshape(-1, 1, 3) / 255.0).reshape(-1, 3)
    background = cv2.cvtColor(image_rgb[::stride, ::stride], cv2.COLOR_RGB2HSV)
    background_mask = (
        (background[:, :, 1] <= saturation_threshold)
        & (background[:, :, 2] >= 180)
    )
    background_rgb = sampled_image[background_mask]
    if len(background_rgb):
        white_reference = np.median(background_rgb, axis=0)
        background_v = background[:, :, 2][background_mask]
        background_v_cv = (
            float(np.std(background_v) / np.mean(background_v))
            if np.mean(background_v) > 0
            else ""
        )
    else:
        white_reference = np.array([255.0, 255.0, 255.0])
        background_v_cv = ""
    reliable = bool(np.all(white_reference >= 160))
    normalized = np.empty_like(image_rgb)
    if reliable:
        for channel in range(3):
            gain = 255.0 / float(white_reference[channel])
            normalized[:, :, channel] = cv2.convertScaleAbs(
                image_rgb[:, :, channel], alpha=gain, beta=0
            )
        normalization_status = "per-channel white-reference balance applied"
    else:
        normalized[:] = image_rgb
        normalization_status = "not applied: unreliable bright background reference"

    normalized_sampled = normalized[::stride, ::stride][sampled_mask]
    hsv = cv2.cvtColor(normalized, cv2.COLOR_RGB2HSV)
    tissue_hsv = hsv[::stride, ::stride][sampled_mask]
    norm_lab = rgb2lab(normalized_sampled.reshape(-1, 1, 3) / 255.0).reshape(-1, 3)
    stats = {
        "sample_stride_px": stride,
        "background_reference_R": float(white_reference[0]),
        "background_reference_G": float(white_reference[1]),
        "background_reference_B": float(white_reference[2]),
        "background_value_cv": background_v_cv,
        "raw_tissue_median_R": float(np.median(sampled[:, 0])),
        "raw_tissue_median_G": float(np.median(sampled[:, 1])),
        "raw_tissue_median_B": float(np.median(sampled[:, 2])),
        "raw_tissue_median_Lab_L": float(np.median(lab[:, 0])),
        "raw_tissue_median_Lab_a": float(np.median(lab[:, 1])),
        "raw_tissue_median_Lab_b": float(np.median(lab[:, 2])),
        "normalized_tissue_median_R": float(np.median(normalized_sampled[:, 0])),
        "normalized_tissue_median_G": float(np.median(normalized_sampled[:, 1])),
        "normalized_tissue_median_B": float(np.median(normalized_sampled[:, 2])),
        "normalized_tissue_median_hue_cv": float(
            np.std(tissue_hsv[:, 0]) / max(float(np.mean(tissue_hsv[:, 0])), 1.0)
        ),
        "normalized_tissue_median_saturation": float(np.median(tissue_hsv[:, 1])),
        "normalized_tissue_median_value": float(np.median(tissue_hsv[:, 2])),
        "normalized_tissue_median_Lab_L": float(np.median(norm_lab[:, 0])),
        "normalized_tissue_median_Lab_a": float(np.median(norm_lab[:, 1])),
        "normalized_tissue_median_Lab_b": float(np.median(norm_lab[:, 2])),
    }
    return stats, normalized, normalization_status


def tissue_blur_metric(image, mask):
    max_dim = 3000
    scale = min(1.0, max_dim / max(image.shape[:2]))
    width = max(1, int(round(image.shape[1] * scale)))
    height = max(1, int(round(image.shape[0] * scale)))
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    gray = cv2.resize(gray, (width, height), interpolation=cv2.INTER_AREA)
    small_mask = cv2.resize(
        mask.astype(np.uint8),
        (width, height),
        interpolation=cv2.INTER_NEAREST,
    ).astype(bool)
    laplacian = cv2.Laplacian(gray, cv2.CV_32F)
    values = laplacian[small_mask]
    return float(np.var(values)) if values.size else ""


def grid_proxy_values(tissue_mask, collagen_mask, mpp_x, mpp_y):
    if not mpp_x or not mpp_y:
        return []
    block_w = max(1, int(round(GRID_BLOCK_UM / mpp_x)))
    block_h = max(1, int(round(GRID_BLOCK_UM / mpp_y)))
    values = []
    height, width = tissue_mask.shape
    for y0 in range(0, height, block_h):
        y1 = min(height, y0 + block_h)
        for x0 in range(0, width, block_w):
            x1 = min(width, x0 + block_w)
            tissue_count = int(np.count_nonzero(tissue_mask[y0:y1, x0:x1]))
            if tissue_count < 100:
                continue
            collagen_count = int(np.count_nonzero(collagen_mask[y0:y1, x0:x1]))
            values.append(collagen_count / tissue_count)
    return values


def save_slide_composite(image, tissue_mask, collagen_mask, output_path, slide_id):
    base = Image.fromarray(image)
    base.thumbnail((850, 650), Image.Resampling.LANCZOS)
    size = base.size
    mask = Image.fromarray((tissue_mask.astype(np.uint8) * 255), mode="L").resize(
        size, Image.Resampling.NEAREST
    ).convert("RGB")
    overlay_array = image.copy()
    if np.any(collagen_mask):
        overlay_array[collagen_mask] = (
            overlay_array[collagen_mask].astype(np.uint16) * 45 // 100
            + np.array([20, 90, 255], dtype=np.uint16) * 55 // 100
        ).astype(np.uint8)
    overlay = Image.fromarray(overlay_array)
    overlay.thumbnail((850, 650), Image.Resampling.LANCZOS)
    panel_width, panel_height = size
    title_height = 30
    canvas = Image.new("RGB", (panel_width * 3, panel_height + title_height), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    labels = [
        f"{slide_id} | analysis image",
        "Otsu saturation tissue mask",
        "Fixed HSV blue/green collagen-proxy overlay",
    ]
    for index, (panel, label) in enumerate(zip((base, mask, overlay), labels)):
        x = index * panel_width
        draw.text((x + 5, 6), label, fill="black", font=font)
        canvas.paste(panel, (x, title_height))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)


def process_slide(path, tier):
    participant_id = path.parts[-3]
    slide_match = SLIDE_ID_RE.search(path.name)
    slide_id = slide_match.group(0) if slide_match else path.stem
    slide = openslide.OpenSlide(str(path))
    dimensions = slide.dimensions
    properties = slide.properties
    mpp_x = float(properties[openslide.PROPERTY_NAME_MPP_X]) if properties.get(
        openslide.PROPERTY_NAME_MPP_X
    ) else None
    mpp_y = float(properties[openslide.PROPERTY_NAME_MPP_Y]) if properties.get(
        openslide.PROPERTY_NAME_MPP_Y
    ) else None
    objective = properties.get(openslide.PROPERTY_NAME_OBJECTIVE_POWER, "")
    if mpp_x and mpp_y:
        level = min(
            range(slide.level_count),
            key=lambda index: abs(
                math.sqrt(
                    mpp_x
                    * mpp_y
                    * slide.level_downsamples[index]
                    * slide.level_downsamples[index]
                )
                - TARGET_MPP_UM
            ),
        )
    else:
        level = min(
            range(slide.level_count),
            key=lambda index: abs(slide.level_downsamples[index] - TARGET_MPP_UM / 0.25),
        )
    downsample = float(slide.level_downsamples[level])
    analysis_mpp_x = mpp_x * downsample if mpp_x else None
    analysis_mpp_y = mpp_y * downsample if mpp_y else None
    image = np.asarray(
        slide.read_region((0, 0), level, slide.level_dimensions[level]).convert("RGB")
    )
    slide.close()

    hsv_raw = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    otsu_threshold, raw_binary = cv2.threshold(
        hsv_raw[:, :, 1], 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    if analysis_mpp_x and analysis_mpp_y:
        pixel_area_mm2 = analysis_mpp_x * analysis_mpp_y / 1_000_000.0
        min_object_px = max(1, int(math.ceil(MIN_OBJECT_AREA_MM2 / pixel_area_mm2)))
        min_hole_px = max(1, int(math.ceil(MIN_HOLE_AREA_MM2 / pixel_area_mm2)))
    else:
        min_object_px = 500
        min_hole_px = 250
    tissue_mask = remove_small_objects(raw_binary.astype(bool), min_size=min_object_px)
    tissue_mask = remove_small_holes(tissue_mask, area_threshold=min_hole_px)

    color_stats, normalized_image, normalization_status = masked_color_stats(
        image, tissue_mask, otsu_threshold
    )
    if normalized_image is None:
        normalized_image = image
    hsv = cv2.cvtColor(normalized_image, cv2.COLOR_RGB2HSV)
    collagen_mask = (
        tissue_mask
        & (hsv[:, :, 0] >= HSV_HUE_LOW)
        & (hsv[:, :, 0] <= HSV_HUE_HIGH)
        & (hsv[:, :, 1] >= HSV_MIN_SATURATION)
    )
    collagen_color = np.asarray(hsv[collagen_mask], dtype=np.uint8)
    color_stats.update(
        {
            "collagen_candidate_pixel_count": int(len(collagen_color)),
            "collagen_candidate_median_hue": (
                float(np.median(collagen_color[:, 0])) if len(collagen_color) else ""
            ),
            "collagen_candidate_median_saturation": (
                float(np.median(collagen_color[:, 1])) if len(collagen_color) else ""
            ),
            "collagen_candidate_median_value": (
                float(np.median(collagen_color[:, 2])) if len(collagen_color) else ""
            ),
        }
    )
    tissue_px = int(np.count_nonzero(tissue_mask))
    collagen_px = int(np.count_nonzero(collagen_mask))
    tissue_fraction = tissue_px / tissue_mask.size if tissue_mask.size else 0.0
    proxy = collagen_px / tissue_px if tissue_px else ""
    if pixel_area_mm2 := (
        analysis_mpp_x * analysis_mpp_y / 1_000_000.0
        if analysis_mpp_x and analysis_mpp_y
        else None
    ):
        tissue_area_mm2 = tissue_px * pixel_area_mm2
        collagen_area_mm2 = collagen_px * pixel_area_mm2
    else:
        tissue_area_mm2 = ""
        collagen_area_mm2 = ""
    grids = grid_proxy_values(
        tissue_mask, collagen_mask, analysis_mpp_x, analysis_mpp_y
    )
    blur_metric = tissue_blur_metric(normalized_image, tissue_mask)
    color_stats.update(
        {
            "participant_id": participant_id,
            "tier": tier,
            "slide_id": slide_id,
            "file_name": path.name,
            "path": str(path.relative_to(ROOT)),
            "slide_width_px": dimensions[0],
            "slide_height_px": dimensions[1],
            "openslide_level": level,
            "level_downsample": downsample,
            "mpp_x_um": mpp_x if mpp_x else "",
            "mpp_y_um": mpp_y if mpp_y else "",
            "analysis_mpp_x_um": analysis_mpp_x if analysis_mpp_x else "",
            "analysis_mpp_y_um": analysis_mpp_y if analysis_mpp_y else "",
            "objective_power": objective,
            "mpp_missing_flag": not bool(mpp_x and mpp_y),
            "analysis_image_width_px": image.shape[1],
            "analysis_image_height_px": image.shape[0],
            "tissue_mask_otsu_saturation_threshold": float(otsu_threshold),
            "minimum_object_pixels": min_object_px,
            "minimum_hole_pixels": min_hole_px,
            "tissue_area_px": tissue_px,
            "tissue_area_mm2": tissue_area_mm2,
            "collagen_positive_area_px": collagen_px,
            "collagen_positive_area_mm2": collagen_area_mm2,
            "trichrome_collagen_proxy": proxy,
            "grid_block_size_um": GRID_BLOCK_UM if analysis_mpp_x and analysis_mpp_y else "",
            "grid_block_count": len(grids),
            "grid_proxy_std": float(np.std(grids, ddof=0)) if grids else "",
            "grid_proxy_p90": float(np.percentile(grids, 90)) if grids else "",
            "tissue_fraction_of_analysis_image": tissue_fraction,
            "color_normalization_status": normalization_status,
            "collagen_threshold_hsv_h_low": HSV_HUE_LOW,
            "collagen_threshold_hsv_h_high": HSV_HUE_HIGH,
            "collagen_threshold_hsv_s_min": HSV_MIN_SATURATION,
            "blur_laplacian_variance": blur_metric,
            "mask_failure_flag": not tissue_px or tissue_fraction < 0.0005 or tissue_fraction > 0.90,
            "manual_pen_fold_blur_review": "required; not automatically classified",
            "pen_mark_visual_review_required": True,
            "fold_visual_review_required": True,
            "blur_visual_review_required": True,
            "tissue_area_scope": (
                "all masked tissue including glomeruli, vessels, capsule, and medulla; "
                "not interstitial fibrosis"
            ),
            "error": "",
        }
    )
    output_path = OUT / "slides" / participant_id / f"{slide_id}_qc.png"
    save_slide_composite(
        normalized_image, tissue_mask, collagen_mask, output_path, slide_id
    )
    color_stats["qc_image"] = str(output_path.relative_to(ROOT))
    return color_stats, grids


def inspect_compartment_masks(participant_ids):
    rows = []
    for participant_id in participant_ids:
        mask_dir = DATA / participant_id / "masks"
        archives = sorted(mask_dir.glob("*Seg_Masks_Features*.zip")) if mask_dir.exists() else []
        if not archives:
            rows.append(
                {
                    "participant_id": participant_id,
                    "archive": "",
                    "ome_channels": "",
                    "compartment_availability": "no local segmentation archive",
                }
            )
            continue
        for archive_path in archives:
            channels = []
            with zipfile.ZipFile(archive_path) as archive:
                ome_files = [
                    name
                    for name in archive.namelist()
                    if name.lower().endswith((".ome.tif", ".ome.tiff"))
                ]
                for ome_name in ome_files:
                    with archive.open(ome_name) as ome_stream:
                        with tifffile.TiffFile(ome_stream) as tif:
                            if tif.ome_metadata:
                                metadata = ElementTree.fromstring(tif.ome_metadata)
                                channels.extend(
                                    element.attrib.get("Name", "")
                                    for element in metadata.iter()
                                    if element.tag.endswith("Channel")
                                )
            rows.append(
                {
                    "participant_id": participant_id,
                    "archive": archive_path.name,
                    "ome_channels": "; ".join(filter(None, channels)),
                    "compartment_availability": (
                        "channel names listed only; masks not used in collagen proxy"
                        if channels
                        else "archive present; no readable OME channel names"
                    ),
                }
            )
    return rows


def inspect_pathologist_scores(participant_ids):
    rows = []
    score_pattern = re.compile(
        r"\b(IFTA|fibros(?:is|tic)|pathologist|tubulointerstitial.{0,20}score)\b",
        re.I,
    )
    for participant_id in participant_ids:
        metadata_dir = DATA / participant_id / "metadata"
        workbooks = (
            sorted(metadata_dir.glob("*.xlsx"))
            if metadata_dir.exists()
            else []
        )
        fields_found = []
        for path in workbooks:
            workbook = pd.ExcelFile(path)
            for sheet_name in workbook.sheet_names:
                frame = pd.read_excel(path, sheet_name=sheet_name, header=None)
                for row_index in range(len(frame.index)):
                    row = frame.iloc[row_index]
                    for column_index in range(len(row)):
                        value = row.iloc[column_index]
                        if pd.isna(value):
                            continue
                        text = str(value).strip()
                        if score_pattern.search(text):
                            fields_found.append(
                                f"{path.name}:{sheet_name}:R{row_index + 1}"
                                f"C{column_index + 1}:{text[:120]}"
                            )
        rows.append(
            {
                "participant_id": participant_id,
                "local_metadata_workbooks_inspected": "; ".join(
                    str(path.relative_to(ROOT)) for path in workbooks
                ),
                "candidate_pathologist_score_fields": "; ".join(fields_found),
                "score_value_available": "yes" if fields_found else "no",
                "search_scope": "local files under D:\\patent\\data only",
            }
        )
    return rows


def bh_adjust(p_values):
    p_values = np.asarray(p_values, dtype=float)
    order = np.argsort(p_values)
    adjusted = np.empty_like(p_values)
    running = 1.0
    count = len(p_values)
    for reverse_rank in range(count - 1, -1, -1):
        index = order[reverse_rank]
        rank = reverse_rank + 1
        running = min(running, p_values[index] * count / rank)
        adjusted[index] = running
    return adjusted


def bootstrap_spearman(x, y, seed):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    observed = float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])
    if abs(observed) >= 1.0:
        p_value = 0.0
    else:
        statistic = observed * math.sqrt((len(x) - 2) / max(1e-15, 1 - observed**2))
        p_value = float(2 * student_t.sf(abs(statistic), df=len(x) - 2))
    generator = np.random.default_rng(seed)
    estimates = []
    for _ in range(BOOTSTRAP_REPLICATES):
        indices = generator.integers(0, len(x), size=len(x))
        result = np.corrcoef(
            rankdata(x[indices]), rankdata(y[indices])
        )[0, 1]
        if np.isfinite(result):
            estimates.append(float(result))
    if estimates:
        low, high = np.percentile(estimates, [2.5, 97.5])
    else:
        low, high = np.nan, np.nan
    return observed, p_value, float(low), float(high), len(estimates)


def make_plots(spot_rows, gene_summary_rows, pca_frame, pca_metadata, correlations):
    plot_dir = OUT / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    umi = np.asarray([row["umi"] for row in spot_rows], dtype=float)
    genes = np.asarray([row["genes_detected"] for row in spot_rows], dtype=float)
    mito = np.asarray(
        [
            row["pct_mitochondrial_umi"]
            for row in spot_rows
            if row["pct_mitochondrial_umi"] != ""
        ],
        dtype=float,
    )
    umi_threshold = float(np.percentile(umi, QC_PERCENTILE))
    gene_threshold = float(np.percentile(genes, QC_PERCENTILE))
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    axes[0].hist(np.log10(umi + 1), bins=60, color="#356b91")
    axes[0].axvline(np.log10(umi_threshold + 1), color="red", linestyle="--")
    axes[0].set_title(f"UMI/spot; P{QC_PERCENTILE:g}={umi_threshold:.0f}")
    axes[0].set_xlabel("log10(UMI + 1)")
    axes[1].hist(genes, bins=60, color="#4d9560")
    axes[1].axvline(gene_threshold, color="red", linestyle="--")
    axes[1].set_title(f"Detected features; P{QC_PERCENTILE:g}={gene_threshold:.0f}")
    axes[1].set_xlabel("Genes/features detected")
    if mito.size:
        axes[2].hist(mito, bins=60, color="#9b6aa5")
        axes[2].set_title("Mitochondrial reads per spot")
        axes[2].set_xlabel("% total UMI")
    else:
        axes[2].text(0.5, 0.5, "Mitochondrial symbols unavailable", ha="center")
        axes[2].set_axis_off()
    for axis in axes:
        axis.set_ylabel("Spot count")
    fig.tight_layout()
    fig.savefig(plot_dir / "spot_qc_distributions.png", dpi=160)
    plt.close(fig)

    gene_summary = defaultdict(dict)
    for row in gene_summary_rows:
        gene_summary[row["gene"]]["participants_ge10"] = row["participants_ge10pct"]
        gene_summary[row["gene"]]["participants_ge5"] = row["participants_ge5pct"]
    names = list(gene_summary)
    ge10 = [gene_summary[name]["participants_ge10"] for name in names]
    ge5 = [gene_summary[name]["participants_ge5"] for name in names]
    fig, axis = plt.subplots(figsize=(11, 6))
    y = np.arange(len(names))
    axis.barh(y - 0.18, ge10, height=0.35, label=">=10% spots")
    axis.barh(y + 0.18, ge5, height=0.35, label=">=5% spots")
    axis.axvline(14, color="red", linestyle="--", label="Half of 28 participants")
    axis.set_yticks(y, names)
    axis.set_xlim(0, max(28, max(ge5 + ge10, default=0)))
    axis.set_xlabel("Participants")
    axis.legend()
    axis.set_title("Gene detection prevalence by participant")
    fig.tight_layout()
    fig.savefig(plot_dir / "gene_detection_prevalence.png", dpi=160)
    plt.close(fig)

    pca_variables = [
        ("tier", "PCA by tier"),
        ("fibrosis_status", "PCA by local fibrosis-score availability"),
        ("visium_library_ids", "PCA by Visium library"),
        ("sequencer_model", "PCA by sequencer model"),
        ("sequencing_platform", "PCA by sequencing platform"),
        ("repository_platform", "PCA by repository platform"),
    ]
    merged = pca_frame.merge(pca_metadata, on="participant_id", how="left")
    for variable, title in pca_variables:
        if variable not in merged:
            continue
        values = merged[variable].fillna("unknown").astype(str)
        categories = sorted(values.unique())
        fig, axis = plt.subplots(figsize=(8, 6))
        cmap = plt.get_cmap("tab20", max(1, len(categories)))
        for category_index, category in enumerate(categories):
            mask = values == category
            axis.scatter(
                merged.loc[mask, "PC1"],
                merged.loc[mask, "PC2"],
                label=category,
                color=cmap(category_index),
                s=48,
                alpha=0.85,
            )
        if len(categories) <= 10:
            axis.legend(title=variable, fontsize=8, loc="best")
        else:
            for _, point in merged.iterrows():
                axis.annotate(
                    point["participant_id"],
                    (point["PC1"], point["PC2"]),
                    xytext=(3, 3),
                    textcoords="offset points",
                    fontsize=6,
                )
        axis.set_xlabel(f"PC1 ({pca_metadata['PC1_variance_percent'].iloc[0]:.1f}%)")
        axis.set_ylabel(f"PC2 ({pca_metadata['PC2_variance_percent'].iloc[0]:.1f}%)")
        axis.set_title(title)
        fig.tight_layout()
        fig.savefig(plot_dir / f"pca_by_{variable}.png", dpi=160)
        plt.close(fig)

    scatter_dir = plot_dir / "correlations"
    scatter_dir.mkdir(parents=True, exist_ok=True)
    for row in correlations:
        feature = row["feature"]
        subset = [
            item
            for item in row["points"]
            if item["trichrome_collagen_proxy"] != "" and item["value"] != ""
        ]
        if len(subset) < 3:
            continue
        fig, axis = plt.subplots(figsize=(7, 5))
        x = [item["trichrome_collagen_proxy"] for item in subset]
        y = [item["value"] for item in subset]
        axis.scatter(x, y, color="#336c8e", alpha=0.85)
        for item in subset:
            axis.annotate(
                item["participant_id"],
                (item["trichrome_collagen_proxy"], item["value"]),
                xytext=(3, 3),
                textcoords="offset points",
                fontsize=7,
            )
        axis.set_xlabel("Participant trichrome_collagen_proxy (tissue-area weighted)")
        axis.set_ylabel(row["measure"])
        axis.set_title(
            f"{feature}: Spearman rho={row['spearman_rho']:.2f} "
            f"(n={row['n_participants']})"
        )
        fig.tight_layout()
        fig.savefig(scatter_dir / f"{feature}.png", dpi=160)
        plt.close(fig)


def run_expression_qc(
    checklist, samples, local_metadata, local_metadata_audit, repo_platforms
):
    participant_tiers = {row["participant_id"]: row.get("tier", "") for row in checklist}
    spot_rows = []
    spot_expression_rows = []
    module_spot_rows = []
    gene_match_rows_out = []
    participant_gene_accum = defaultdict(
        lambda: {
            "spots": 0,
            "sample_count": 0,
            "gene_counts": defaultdict(int),
            "gene_detected": defaultdict(int),
            "gene_lognorm_sum": defaultdict(float),
            "gene_samples_present": defaultdict(int),
            "module_lognorm_sum": defaultdict(float),
            "module_detected": defaultdict(int),
            "pseudobulk_counts": defaultdict(int),
            "pseudobulk_labels_present": None,
            "total_umi": 0,
            "sample_ids": [],
        }
    )
    sample_rows = []
    sample_metadata_rows = []

    for sample in samples:
        participant_id = sample["participant_id"]
        source = sample["source"]
        features = source["features"]
        matrix = source["matrix"].tocsr()
        indices = sample["spot_indices"]
        positions = sample["positions"]
        selected = matrix[:, indices].tocsr()
        library_sizes = np.asarray(selected.sum(axis=0)).ravel().astype(np.int64)
        genes_detected = np.asarray(selected.getnnz(axis=0)).ravel().astype(np.int32)
        mito_features = mitochondrial_rows(features)
        if mito_features:
            mito_counts = np.asarray(
                selected[mito_features, :].sum(axis=0)
            ).ravel().astype(np.int64)
            pct_mito = np.divide(
                mito_counts * 100.0,
                library_sizes,
                out=np.full(len(indices), np.nan, dtype=float),
                where=library_sizes > 0,
            )
        else:
            mito_counts = np.full(len(indices), np.nan)
            pct_mito = np.full(len(indices), np.nan)

        per_gene_counts = {}
        per_gene_lognorm = {}
        per_gene_matches = {}
        for gene in GENES:
            matches = gene_match_rows(features, gene)
            indices_for_gene = [index for index, _ in matches]
            if indices_for_gene:
                counts = np.asarray(
                    selected[indices_for_gene, :].sum(axis=0)
                ).ravel().astype(np.int64)
                cp10k = np.divide(
                    counts * 10000.0,
                    library_sizes,
                    out=np.full(len(indices), np.nan, dtype=float),
                    where=library_sizes > 0,
                )
                lognorm = np.log1p(cp10k)
                per_gene_counts[gene] = counts
                per_gene_lognorm[gene] = lognorm
                methods = sorted({method for _, method in matches})
                match_source = "; ".join(methods)
            else:
                counts = np.full(len(indices), np.nan)
                lognorm = np.full(len(indices), np.nan)
                per_gene_counts[gene] = counts
                per_gene_lognorm[gene] = lognorm
                match_source = "not found"
            per_gene_matches[gene] = bool(indices_for_gene)
            gene_match_rows_out.append(
                {
                    "participant_id": participant_id,
                    "sample_id": sample["sample_id"],
                    "expression_source": str(source["path"].relative_to(ROOT)),
                    "gene": gene,
                    "feature_rows_matched": len(indices_for_gene),
                    "matched_by": match_source,
                    "matched_feature_ids": "; ".join(
                        str(features[index][0]) for index in indices_for_gene
                    ),
                    "matched_feature_names": "; ".join(
                        str(features[index][1] if len(features[index]) > 1 else "")
                        for index in indices_for_gene
                    ),
                    "status": "present" if indices_for_gene else "mismatch/missing",
                }
            )

        participant_accum = participant_gene_accum[participant_id]
        participant_accum["spots"] += len(indices)
        participant_accum["sample_count"] += 1
        participant_accum["sample_ids"].append(sample["sample_id"])
        participant_accum["total_umi"] += int(np.sum(library_sizes))
        for gene in GENES:
            if per_gene_matches[gene]:
                values = per_gene_counts[gene]
                normalized = per_gene_lognorm[gene]
                participant_accum["gene_counts"][gene] += int(np.sum(values))
                participant_accum["gene_detected"][gene] += int(np.count_nonzero(values))
                participant_accum["gene_lognorm_sum"][gene] += float(np.sum(normalized))
                participant_accum["gene_samples_present"][gene] += 1

        for label, grouped_counts in [counts_per_label(source)]:
            participant_accum["pseudobulk_labels_present"] = (
                set(label)
                if participant_accum["pseudobulk_labels_present"] is None
                else participant_accum["pseudobulk_labels_present"].intersection(label)
            )
            summed = np.asarray(grouped_counts[:, indices].sum(axis=1)).ravel()
            for gene_label, count in zip(label, summed):
                participant_accum["pseudobulk_counts"][gene_label] += int(count)

        module_values = {}
        module_detection = {}
        for module, member_genes in MODULES.items():
            if all(per_gene_matches[gene] for gene in member_genes):
                member_log_norms = np.vstack(
                    [per_gene_lognorm[gene] for gene in member_genes]
                )
                module_values[module] = np.mean(member_log_norms, axis=0)
                module_detection[module] = np.any(
                    np.vstack(
                        [per_gene_counts[gene] > 0 for gene in member_genes]
                    ),
                    axis=0,
                )
                participant_accum["module_lognorm_sum"][module] += float(
                    np.sum(module_values[module])
                )
                participant_accum["module_detected"][module] += int(
                    np.count_nonzero(module_detection[module])
                )
            else:
                module_values[module] = np.full(len(indices), np.nan)
                module_detection[module] = np.full(len(indices), False)

        for spot_index, (_, spot) in enumerate(positions.iterrows()):
            row = {
                "participant_id": participant_id,
                "tier": sample["tier"],
                "sample_id": sample["sample_id"],
                "barcode": str(spot["barcode"]),
                "umi": int(library_sizes[spot_index]),
                "genes_detected": int(genes_detected[spot_index]),
                "mitochondrial_umi": (
                    int(mito_counts[spot_index]) if mito_features else ""
                ),
                "pct_mitochondrial_umi": (
                    float(pct_mito[spot_index])
                    if mito_features and np.isfinite(pct_mito[spot_index])
                    else ""
                ),
                "mitochondrial_gene_rows_detected": len(mito_features),
            }
            spot_rows.append(row)
            expression_row = {
                "participant_id": participant_id,
                "tier": sample["tier"],
                "sample_id": sample["sample_id"],
                "barcode": str(spot["barcode"]),
                "library_size_umi": int(library_sizes[spot_index]),
            }
            for gene in GENES:
                count = per_gene_counts[gene][spot_index]
                lognorm = per_gene_lognorm[gene][spot_index]
                expression_row[f"{gene}_raw_count"] = (
                    int(count) if np.isfinite(count) else ""
                )
                expression_row[f"{gene}_log1p_cp10k"] = (
                    float(lognorm) if np.isfinite(lognorm) else ""
                )
            spot_expression_rows.append(expression_row)
            module_row = {
                "participant_id": participant_id,
                "tier": sample["tier"],
                "sample_id": sample["sample_id"],
                "barcode": str(spot["barcode"]),
            }
            for module in MODULES:
                value = module_values[module][spot_index]
                module_row[f"{module}_mean_log1p_cp10k"] = (
                    float(value) if np.isfinite(value) else ""
                )
                module_row[f"{module}_any_member_detected"] = bool(
                    module_detection[module][spot_index]
                )
            module_spot_rows.append(module_row)

        sample_rows.append(
            {
                "participant_id": participant_id,
                "tier": sample["tier"],
                "sample_id": sample["sample_id"],
                "expression_source": str(source["path"].relative_to(ROOT)),
                "in_tissue_spots": len(indices),
                "median_umi_per_spot": float(np.median(library_sizes)),
                "median_genes_per_spot": float(np.median(genes_detected)),
                "median_pct_mitochondrial_umi": (
                    float(np.nanmedian(pct_mito)) if mito_features else ""
                ),
                "mitochondrial_feature_rows": len(mito_features),
                "genes_found": sum(per_gene_matches.values()),
                "genes_tested": len(GENES),
            }
        )
        metadata_record = local_metadata.get(
            (participant_id, sample["sample_id"]), {}
        )
        if not metadata_record:
            candidates = [
                value
                for (pid, _), value in local_metadata.items()
                if pid == participant_id
            ]
            metadata_record = candidates[0] if len(candidates) == 1 else {}
        sample_metadata_rows.append(
            {
                "participant_id": participant_id,
                "tier": sample["tier"],
                "sample_id": sample["sample_id"],
                "expression_source": str(source["path"].relative_to(ROOT)),
                "local_metadata_file": metadata_record.get("metadata_file", ""),
                "sequencing_platform": metadata_record.get("Sequencing Platform", ""),
                "sequencer_model": metadata_record.get("Sequencer Model", ""),
                "sequencer_software_version": metadata_record.get(
                    "Sequencer Software / Version", ""
                ),
                "sequencing_center": metadata_record.get("Sequencing Center", ""),
                "total_raw_reads": metadata_record.get("Total Raw Reads", ""),
                "q30_score": metadata_record.get("Q30 Score (Percentage)", ""),
                "cellranger_platform": metadata_record.get(
                    "RNA Downstream Analysis Platform", ""
                ),
                "cellranger_version": metadata_record.get(
                    "RNA Downstream Analysis Platform Version", ""
                ),
                "repository_platform": "; ".join(
                    sorted(repo_platforms.get(participant_id, set()))
                ),
                "metadata_availability": (
                    "local sample metadata found"
                    if metadata_record
                    else "not locally available"
                ),
            }
        )

    all_umi = np.asarray([row["umi"] for row in spot_rows], dtype=float)
    all_genes = np.asarray([row["genes_detected"] for row in spot_rows], dtype=float)
    umi_threshold = max(1.0, float(np.percentile(all_umi, QC_PERCENTILE)))
    gene_threshold = max(1.0, float(np.percentile(all_genes, QC_PERCENTILE)))
    for row in spot_rows:
        row["data_derived_umi_threshold_p10"] = umi_threshold
        row["data_derived_genes_threshold_p10"] = gene_threshold
        row["low_umi_flag"] = row["umi"] < umi_threshold
        row["low_genes_flag"] = row["genes_detected"] < gene_threshold
        row["low_quality_screen_flag"] = row["low_umi_flag"] or row["low_genes_flag"]
        row["threshold_interpretation"] = (
            "empirical pooled 10th-percentile screening flag; retained, not filtered"
        )
    for row in sample_rows:
        rows = [
            spot
            for spot in spot_rows
            if spot["participant_id"] == row["participant_id"]
            and spot["sample_id"] == row["sample_id"]
        ]
        row["umi_threshold_p10"] = umi_threshold
        row["genes_threshold_p10"] = gene_threshold
        row["pct_below_umi_threshold"] = 100.0 * np.mean(
            [spot["umi"] < umi_threshold for spot in rows]
        )
        row["pct_below_genes_threshold"] = 100.0 * np.mean(
            [spot["genes_detected"] < gene_threshold for spot in rows]
        )
        row["pct_flagged_low_quality_screen"] = 100.0 * np.mean(
            [spot["low_quality_screen_flag"] for spot in rows]
        )
        row["low_quality_spots_retained"] = sum(
            spot["low_quality_screen_flag"] for spot in rows
        )

    gene_participant_rows = []
    for participant_id in sorted(participant_gene_accum):
        values = participant_gene_accum[participant_id]
        tier = participant_tiers[participant_id]
        for gene in GENES:
            sample_coverage = values["gene_samples_present"][gene]
            complete = sample_coverage == values["sample_count"]
            spots_total = values["spots"]
            gene_participant_rows.append(
                {
                    "participant_id": participant_id,
                    "tier": tier,
                    "gene": gene,
                    "paired_samples": values["sample_count"],
                    "samples_with_gene_features": sample_coverage,
                    "paired_spots": spots_total,
                    "detected_spots": (
                        values["gene_detected"][gene] if complete else ""
                    ),
                    "detected_percent": (
                        100.0 * values["gene_detected"][gene] / spots_total
                        if complete and spots_total
                        else ""
                    ),
                    "mean_log1p_cp10k": (
                        values["gene_lognorm_sum"][gene] / spots_total
                        if complete and spots_total
                        else ""
                    ),
                    "summed_raw_counts": (
                        values["gene_counts"][gene] if complete else ""
                    ),
                    "matrix_coverage_status": (
                        "complete" if complete else "gene missing in one or more sample matrices"
                    ),
                }
            )

    gene_summary_rows = []
    for gene in GENES:
        rows = [row for row in gene_participant_rows if row["gene"] == gene]
        complete_rows = [row for row in rows if row["detected_percent"] != ""]
        pct10 = sum(float(row["detected_percent"]) >= 10 for row in complete_rows)
        pct5 = sum(float(row["detected_percent"]) >= 5 for row in complete_rows)
        gene_summary_rows.append(
            {
                "gene": gene,
                "participants_total": len(participant_gene_accum),
                "participants_with_complete_matrix_coverage": len(complete_rows),
                "participants_ge10pct_detection": pct10,
                "participants_ge5pct_detection": pct5,
                "cohort_mean_participant_detection_percent": (
                    float(np.mean([float(row["detected_percent"]) for row in complete_rows]))
                    if complete_rows
                    else ""
                ),
                "usable_for_prediction_rule": pct10 >= math.ceil(len(participant_gene_accum) / 2),
                "rule": ">=10% spot detection in >=half of participants",
            }
        )
    for row in gene_summary_rows:
        count = row["participants_ge10pct_detection"]
        row["participants_ge10pct"] = count
        row["participants_ge5pct"] = row["participants_ge5pct_detection"]

    participant_module_rows = []
    for participant_id, values in participant_gene_accum.items():
        for module, members in MODULES.items():
            complete = all(
                values["gene_samples_present"][gene] == values["sample_count"]
                for gene in members
            )
            detected = values["module_detected"][module]
            participant_module_rows.append(
                {
                    "participant_id": participant_id,
                    "tier": participant_tiers[participant_id],
                    "module": module,
                    "member_genes": "; ".join(members),
                    "paired_spots": values["spots"],
                    "spots_any_member_detected": detected if complete else "",
                    "spots_any_member_detection_percent": (
                        100.0 * detected / values["spots"]
                        if complete and values["spots"]
                        else ""
                    ),
                    "mean_spot_module_score": (
                        values["module_lognorm_sum"][module] / values["spots"]
                        if complete and values["spots"]
                        else ""
                    ),
                    "matrix_coverage_status": "complete" if complete else "one or more genes missing",
                }
            )
    module_summary = []
    for module in MODULES:
        rows = [row for row in participant_module_rows if row["module"] == module]
        complete = [row for row in rows if row["spots_any_member_detection_percent"] != ""]
        eligible = sum(
            float(row["spots_any_member_detection_percent"]) >= 10 for row in complete
        )
        module_summary.append(
            {
                "module": module,
                "participants_ge10pct_module_detection": eligible,
                "participants_ge5pct_module_detection": sum(
                    float(row["spots_any_member_detection_percent"]) >= 5 for row in complete
                ),
                "usable_for_prediction_rule": eligible
                >= math.ceil(len(participant_gene_accum) / 2),
                "module_detection_definition": (
                    "at least one module member gene detected in the spot; "
                    "module score is mean member log1p(CP10K)"
                ),
                "score_method": "simple mean; no control-gene matching",
            }
        )

    pseudobulk_rows = []
    participant_ids = sorted(participant_gene_accum)
    all_labels = sorted(
        set().union(
            *(set(values["pseudobulk_counts"]) for values in participant_gene_accum.values())
        )
    )
    pca_metadata_rows = []
    participant_pseudobulk = {}
    for participant_id in participant_ids:
        values = participant_gene_accum[participant_id]
        present = values["pseudobulk_labels_present"] or set()
        total_counts = values["total_umi"]
        row = {
            "participant_id": participant_id,
            "tier": participant_tiers[participant_id],
            "paired_samples": values["sample_count"],
            "in_tissue_spots": values["spots"],
            "visium_library_ids": "; ".join(sorted(set(values["sample_ids"]))),
            "repository_platform": "; ".join(sorted(repo_platforms.get(participant_id, set())))
            or "",
        }
        gene_logcpm = {}
        for label in all_labels:
            if label not in present:
                row[label] = ""
                gene_logcpm[label] = np.nan
            elif total_counts > 0:
                count = values["pseudobulk_counts"][label]
                logcpm = math.log1p(count * 1_000_000.0 / total_counts)
                row[label] = logcpm
                gene_logcpm[label] = logcpm
            else:
                row[label] = ""
                gene_logcpm[label] = np.nan
        for module, members in MODULES.items():
            if all(np.isfinite(gene_logcpm.get(gene, np.nan)) for gene in members):
                module_score = float(np.mean([gene_logcpm[gene] for gene in members]))
            else:
                module_score = np.nan
            row[f"{module}_pseudobulk_mean_log_cpm"] = (
                module_score if np.isfinite(module_score) else ""
            )
        pseudobulk_rows.append(row)
        participant_pseudobulk[participant_id] = gene_logcpm
        metadata_rows = [
            value
            for (pid, _), value in local_metadata.items()
            if pid == participant_id
        ]
        pca_metadata_rows.append(
            {
                "participant_id": participant_id,
                "tier": participant_tiers[participant_id],
                "fibrosis_status": "unknown",
                "visium_library_ids": row["visium_library_ids"] or "unknown",
                "sequencer_model": "; ".join(
                    sorted(
                        {
                            str(value.get("Sequencer Model"))
                            for value in metadata_rows
                            if value.get("Sequencer Model")
                        }
                    )
                )
                or "unknown",
                "sequencing_platform": "; ".join(
                    sorted(
                        {
                            str(value.get("Sequencing Platform"))
                            for value in metadata_rows
                            if value.get("Sequencing Platform")
                        }
                    )
                )
                or "unknown",
                "repository_platform": row["repository_platform"] or "unknown",
            }
        )

    common_labels = [
        label
        for label in all_labels
        if all(np.isfinite(participant_pseudobulk[pid].get(label, np.nan)) for pid in participant_ids)
    ]
    matrix = np.asarray(
        [[participant_pseudobulk[pid][label] for label in common_labels] for pid in participant_ids],
        dtype=float,
    )
    if matrix.size == 0 or matrix.shape[1] < 2:
        raise RuntimeError("Too few common pseudobulk features for PCA")
    variances = np.var(matrix, axis=0)
    variable_indices = np.flatnonzero(variances > 0)
    variable_indices = variable_indices[
        np.argsort(variances[variable_indices])[::-1][: min(2000, len(variable_indices))]
    ]
    pca_features = [common_labels[index] for index in variable_indices]
    pca = PCA(n_components=2, random_state=RANDOM_SEED)
    coordinates = pca.fit_transform(matrix[:, variable_indices])
    pca_scores = pd.DataFrame(
        {
            "participant_id": participant_ids,
            "PC1": coordinates[:, 0],
            "PC2": coordinates[:, 1],
        }
    )
    pca_metadata = pd.DataFrame(pca_metadata_rows)
    variance_percent = pca.explained_variance_ratio_ * 100.0
    pca_metadata["PC1_variance_percent"] = variance_percent[0]
    pca_metadata["PC2_variance_percent"] = variance_percent[1]

    pca_association_rows = []
    for variable in (
        "tier",
        "fibrosis_status",
        "visium_library_ids",
        "sequencer_model",
        "sequencing_platform",
        "repository_platform",
    ):
        values = pca_metadata[variable].fillna("unknown").astype(str).to_numpy()
        counts = Counter(values)
        high_cardinality = len(counts) >= max(10, len(values) // 2)
        for component in ("PC1", "PC2"):
            scores = pca_scores[component].to_numpy(dtype=float)
            mean = float(np.mean(scores))
            total_ss = float(np.sum((scores - mean) ** 2))
            between_ss = sum(
                int(count) * (float(np.mean(scores[values == label])) - mean) ** 2
                for label, count in counts.items()
            )
            eta_squared = between_ss / total_ss if total_ss > 0 else ""
            min_group = min(counts.values()) if counts else 0
            if len(counts) < 2:
                status = "not estimable: metadata has no variation"
                permutation_p = ""
            elif high_cardinality:
                status = "descriptive only: high-cardinality library identifier"
                permutation_p = ""
            elif min_group < 2:
                status = "descriptive only: at least one group has fewer than 2 participants"
                permutation_p = ""
            else:
                rng = np.random.default_rng(RANDOM_SEED + len(pca_association_rows))
                observed = float(eta_squared)
                exceed = 0
                for _ in range(1999):
                    permuted = rng.permutation(values)
                    perm_between = sum(
                        int(count) * (float(np.mean(scores[permuted == label])) - mean) ** 2
                        for label, count in counts.items()
                    )
                    exceed += (perm_between / total_ss) >= observed
                permutation_p = (exceed + 1) / 2000.0
                status = "participant-level permutation test; descriptive, not corrected"
            pca_association_rows.append(
                {
                    "variable": variable,
                    "component": component,
                    "category_count": len(counts),
                    "category_counts": json.dumps(dict(counts), sort_keys=True),
                    "eta_squared": eta_squared,
                    "permutation_p": permutation_p,
                    "status": status,
                }
            )

    return {
        "spot_rows": spot_rows,
        "spot_expression_rows": spot_expression_rows,
        "module_spot_rows": module_spot_rows,
        "sample_rows": sample_rows,
        "gene_match_rows": gene_match_rows_out,
        "gene_participant_rows": gene_participant_rows,
        "gene_summary_rows": gene_summary_rows,
        "module_participant_rows": participant_module_rows,
        "module_summary": module_summary,
        "pseudobulk_rows": pseudobulk_rows,
        "participant_pseudobulk": participant_pseudobulk,
        "pca_scores": pca_scores,
        "pca_metadata": pca_metadata,
        "pca_features": pca_features,
        "pca_associations": pca_association_rows,
        "sample_metadata_rows": sample_metadata_rows,
        "local_metadata_audit": local_metadata_audit,
        "umi_threshold": umi_threshold,
        "gene_threshold": gene_threshold,
    }


def participant_collagen_proxy(slide_rows, participant_ids):
    grouped = defaultdict(list)
    for row in slide_rows:
        grouped[row["participant_id"]].append(row)
    rows = []
    for participant_id in participant_ids:
        slides = grouped.get(participant_id, [])
        valid = [
            row
            for row in slides
            if row["trichrome_collagen_proxy"] != "" and row["tissue_area_mm2"] != ""
        ]
        tissue_area = sum(float(row["tissue_area_mm2"]) for row in valid)
        collagen_area = sum(float(row["collagen_positive_area_mm2"]) for row in valid)
        rows.append(
            {
                "participant_id": participant_id,
                "tier": next((row["tier"] for row in slides), ""),
                "tri_slide_count": len(slides),
                "slides_with_valid_proxy": len(valid),
                "tissue_area_mm2_sum": tissue_area if valid else "",
                "collagen_positive_area_mm2_sum": collagen_area if valid else "",
                "trichrome_collagen_proxy": (
                    collagen_area / tissue_area if tissue_area > 0 else ""
                ),
                "aggregation": (
                    "sum of collagen-positive area / sum of tissue area across local TRI slides"
                ),
                "not_interstitial_fibrosis": True,
            }
        )
    return rows


def compute_correlations(expression, collagen_rows):
    collagen = {
        row["participant_id"]: row["trichrome_collagen_proxy"]
        for row in collagen_rows
    }
    feature_specs = [(gene, gene, "pseudobulk log1p(CPM)") for gene in GENES]
    feature_specs.extend(
        (
            module,
            f"{module}_pseudobulk_mean_log_cpm",
            "pseudobulk mean member log1p(CPM)",
        )
        for module in MODULES
    )
    pseudo_by_pid = {row["participant_id"]: row for row in expression["pseudobulk_rows"]}
    results = []
    for index, (feature, column, measure) in enumerate(feature_specs):
        points = []
        for participant_id in sorted(pseudo_by_pid):
            x_value = collagen.get(participant_id, "")
            y_value = pseudo_by_pid[participant_id].get(column, "")
            if x_value == "" or y_value == "":
                continue
            points.append(
                {
                    "participant_id": participant_id,
                    "trichrome_collagen_proxy": float(x_value),
                    "value": float(y_value),
                }
            )
        if len(points) >= 3:
            x = [point["trichrome_collagen_proxy"] for point in points]
            y = [point["value"] for point in points]
            rho, p_value, ci_low, ci_high, bootstrap_valid = bootstrap_spearman(
                x, y, BOOTSTRAP_SEED + index
            )
        else:
            rho = p_value = ci_low = ci_high = ""
            bootstrap_valid = 0
        results.append(
            {
                "feature": feature,
                "measure": measure,
                "n_participants": len(points),
                "spearman_rho": rho,
                "p_value_asymptotic": p_value,
                "bootstrap_ci_95_low": ci_low,
                "bootstrap_ci_95_high": ci_high,
                "bootstrap_valid_replicates": bootstrap_valid,
                "fdr_q_gene_only": "",
                "participant_unit": True,
                "points": points,
            }
        )
    gene_indices = [index for index, row in enumerate(results) if row["feature"] in GENES]
    valid_gene_indices = [
        index
        for index in gene_indices
        if results[index]["p_value_asymptotic"] != ""
    ]
    if valid_gene_indices:
        adjusted = bh_adjust(
            [results[index]["p_value_asymptotic"] for index in valid_gene_indices]
        )
        for index, value in zip(valid_gene_indices, adjusted):
            results[index]["fdr_q_gene_only"] = float(value)
    return results


def write_verdict(expression, slide_rows, correlations, score_audit):
    usable_genes = [
        row["gene"]
        for row in expression["gene_summary_rows"]
        if row["usable_for_prediction_rule"]
    ]
    not_usable_genes = [
        row["gene"]
        for row in expression["gene_summary_rows"]
        if not row["usable_for_prediction_rule"]
    ]
    usable_modules = [
        row["module"]
        for row in expression["module_summary"]
        if row["usable_for_prediction_rule"]
    ]
    not_usable_modules = [
        row["module"]
        for row in expression["module_summary"]
        if not row["usable_for_prediction_rule"]
    ]
    missing_mpp = sum(bool(row["mpp_missing_flag"]) for row in slide_rows)
    mask_failures = [
        row["slide_id"] for row in slide_rows if row["mask_failure_flag"]
    ]
    lines = [
        "# QC verdict",
        "",
        f"- Paired expression cohort: {len(expression['pseudobulk_rows'])} participants, "
        f"{sum(int(row['paired_samples']) for row in expression['pseudobulk_rows'])} samples, "
        f"{sum(int(row['in_tissue_spots']) for row in expression['pseudobulk_rows'])} spots.",
        f"- Empirical low-quality screen: UMI < {expression['umi_threshold']:.0f} or "
        f"detected features < {expression['gene_threshold']:.0f}; 10th percentile cutoffs "
        "pooled across spots; flagged spots were retained.",
        "- Prediction-screen genes (>=10% detection in >=half of participants): "
        + (", ".join(usable_genes) if usable_genes else "none"),
        "- Below that gene screen: "
        + (", ".join(not_usable_genes) if not_usable_genes else "none"),
        "- Prediction-screen modules (at least one member detected in >=10% of spots "
        "in >=half of participants): "
        + (", ".join(usable_modules) if usable_modules else "none"),
        "- Modules below that screen: "
        + (", ".join(not_usable_modules) if not_usable_modules else "none"),
        f"- TRI slides analyzed: {len(slide_rows)}; slides missing MPP: {missing_mpp}; "
        f"mask-failure flags: {len(mask_failures)}"
        + (f" ({', '.join(mask_failures)})" if mask_failures else "."),
        f"- Pathologist score fields found in local metadata: "
        f"{sum(row['score_value_available'] == 'yes' for row in score_audit)} of "
        f"{len(score_audit)} participants.",
        "- Correlations use one participant-level value per participant, no spot-level "
        "collagen assignment, and bootstrap resampling of participants. The cohort "
        "size (n=28 maximum) gives low power; results are exploratory.",
        "- `trichrome_collagen_proxy` is a fixed-HSV color proxy over all masked tissue. "
        "The mask includes glomeruli, vessels, capsule, and medulla and is not an "
        "interstitial-fibrosis measure.",
        "- Not done: image registration, model training, batch correction, or assigning "
        "collagen values to Visium spots.",
        "- Limitations: pen marks, folds, and blur require manual review of the saved "
        "slide composites; they were not automatically classified.",
    ]
    lines.extend(
        [
            "",
            "## PCA batch checks",
            "",
            "| Variable | Component | Eta-squared | Permutation p | Status |",
            "|---|---|---:|---:|---|",
        ]
    )
    for row in expression["pca_associations"]:
        eta = (
            f"{row['eta_squared']:.3f}"
            if isinstance(row["eta_squared"], (float, int))
            else "NA"
        )
        permutation_p = (
            f"{row['permutation_p']:.4g}"
            if isinstance(row["permutation_p"], (float, int))
            else "NA"
        )
        lines.append(
            f"| {row['variable']} | {row['component']} | {eta} | "
            f"{permutation_p} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "PCA associations are descriptive participant-level diagnostics, not batch "
            "correction. Fibrosis-score status is unknown for the cohort; sequencing "
            "metadata is locally available only for sample rows listed in "
            "`sample_metadata_audit.csv`.",
            "",
            "## Participant-level correlations",
            "",
            "| Feature | n | Spearman rho | 95% participant bootstrap CI | p (asymptotic) | BH q (genes only) |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in correlations:
        if row["spearman_rho"] == "":
            rho = low = high = p_value = q_value = "NA"
        else:
            rho = f"{row['spearman_rho']:.3f}"
            low = f"{row['bootstrap_ci_95_low']:.3f}"
            high = f"{row['bootstrap_ci_95_high']:.3f}"
            p_value = f"{row['p_value_asymptotic']:.4g}"
            q_value = (
                f"{row['fdr_q_gene_only']:.4g}"
                if row["fdr_q_gene_only"] != ""
                else "—"
            )
        lines.append(
            f"| {row['feature']} | {row['n_participants']} | {rho} | "
            f"[{low}, {high}] | {p_value} | {q_value} |"
        )
    (OUT / "qc_verdict.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(config, counts, output_names):
    lines = [
        "# Spatial expression and trichrome proxy QC",
        "",
        "This analysis uses only files already present under `D:\\patent\\data`. "
        "It does not register slides, train models, correct batches, or assign "
        "slide-derived collagen values to Visium spots.",
        "",
        "## Re-run",
        "",
        "```powershell",
        "python D:\\patent\\qc_collagen\\run_qc_collagen.py",
        "```",
        "",
        "The script imports the verified expression/spatial readers and barcode-coverage "
        "pairing helpers from `D:\\patent\\analyze_cohort_plan_a_b.py`.",
        "",
        "## Methods",
        "",
        f"- Confirmed cohort: {counts['participants']} participants, {counts['samples']} "
        f"paired spatial-expression samples, {counts['spots']:,} in-tissue spots.",
        f"- Per-spot expression is `log1p(counts / all-gene spot UMI * 10,000)`; raw "
        "target-gene counts are retained. Missing matrix features remain blank and "
        "are listed in `gene_feature_match_audit.csv`.",
        "- Mitochondrial fraction is calculated from mitochondrial UMIs in the "
        "expression matrix; read-level mitochondrial percentages are unavailable "
        "from these matrices.",
        f"- Low-quality screen cutoffs are pooled empirical {QC_PERCENTILE:g}th-percentile "
        f"thresholds: UMI < {config['umi_threshold']:.0f} or detected features < "
        f"{config['genes_detected_threshold']:.0f}. Both distributions are plotted; "
        "the flags are "
        "screening annotations only and no spot is removed.",
        "- Module score is a simple arithmetic mean of member-gene log1p(CP10K), with "
        "no control-gene matching. Module spot detection means at least one member "
        "gene has a positive raw count; module output is blank if a required member "
        "feature is missing from any paired sample matrix.",
        "- Pseudobulk sums raw counts across every paired in-tissue spot for a "
        "participant, then computes `log1p(CPM)`. PCA uses common features with "
        "nonzero between-participant variance (up to 2,000 highest-variance features). "
        "Batch associations are participant-level diagnostics only; no correction "
        "is performed.",
        f"- TRI analysis uses OpenSlide level nearest {TARGET_MPP_UM:g} µm/pixel. "
        "All local slides are read at a pyramid level, not full resolution. The tissue "
        "mask uses per-slide Otsu thresholding of HSV saturation, then removes objects "
        f"smaller than {MIN_OBJECT_AREA_MM2:g} mm² and fills holes smaller than "
        f"{MIN_HOLE_AREA_MM2:g} mm².",
        f"- Collagen proxy uses the same white-reference balance and HSV rule on every "
        f"slide: OpenCV hue {HSV_HUE_LOW}–{HSV_HUE_HIGH}, saturation >= "
        f"{HSV_MIN_SATURATION}, inside the tissue mask. This fixed blue/green window "
        "is an exploratory color proxy, not a validated collagen stain deconvolution. "
        "Slide-specific color and illumination statistics are saved to expose "
        "between-slide staining/scanner variation.",
        f"- Participant proxy is tissue-area weighted across the participant's local "
        f"TRI slides. Grid heterogeneity uses {GRID_BLOCK_UM} µm blocks with at least "
        "100 tissue pixels. Tissue includes glomeruli, vessels, capsule, and medulla; "
        "it is not interstitial fibrosis.",
        "- The quality composites are for manual review. Pen marks, folds, and blur "
        "are not reliably auto-classified; review is marked as required. A relative "
        "Laplacian sharpness metric and data-derived low-sharpness flag are supplied.",
        "- Participant-level Spearman correlations use asymptotic p-values, 5,000 "
        "participant bootstrap replicates for 95% CIs, and BH correction across the "
        "13 gene tests only. Module correlations are not multiplicity-corrected. "
        "With at most 28 participants, power is low.",
        "- Local pathologist-score search checks files under `D:\\patent\\data` only. "
        "No external search, download, or access request was made.",
        "",
        "## Reproducibility",
        "",
        f"- Seeds: PCA/diagnostics={RANDOM_SEED}; bootstrap={BOOTSTRAP_SEED}; "
        f"three-slide recomputation={RANDOM_SEED + 99}; bootstrap replicates="
        f"{BOOTSTRAP_REPLICATES}.",
        "- The run checks final participant/sample/spot counts against "
        "`plan_a_plan_b\\plan_a_patient_summary.csv`.",
        "",
        "Software versions:",
    ]
    lines.extend(
        f"- {package}: {version}"
        for package, version in config["software_versions"].items()
    )
    lines.extend(
        [
            "",
            "## Outputs",
            "",
        ]
    )
    lines.extend(f"- `{name}`" for name in output_names)
    lines.extend(
        [
            "- `slides\\<participant_id>\\<slide_id>_qc.png`: one composite per TRI "
            "slide (analysis-level thumbnail, tissue mask, collagen proxy overlay).",
            "- `plots\\correlations\\<feature>.png`: participant-labeled scatter plot "
            "for each gene/module correlation.",
            "",
            "See `qc_verdict.md` for the data-derived usability screen, slide flags, "
            "correlation table, and explicit limitations.",
        ]
    )
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with CHECKLIST.open(encoding="utf-8-sig", newline="") as stream:
        checklist = list(csv.DictReader(stream))
    participant_ids = sorted({row["participant_id"] for row in checklist})
    local_metadata, local_metadata_audit, _ = local_sample_metadata(
        set(participant_ids)
    )
    repo_platforms = repository_platforms(set(participant_ids))
    expression = run_expression_qc(
        checklist,
        load_cohort_inputs(checklist),
        local_metadata,
        local_metadata_audit,
        repo_platforms,
    )

    expected = {}
    with PATIENT_SUMMARY.open(encoding="utf-8-sig", newline="") as stream:
        expected_rows = list(csv.DictReader(stream))
    expected = {
        "participants": len(expected_rows),
        "samples": sum(int(row["paired_samples"]) for row in expected_rows),
        "spots": sum(int(row["in_tissue_spots"]) for row in expected_rows),
    }
    observed = {
        "participants": len(expression["pseudobulk_rows"]),
        "samples": sum(int(row["paired_samples"]) for row in expression["pseudobulk_rows"]),
        "spots": sum(int(row["in_tissue_spots"]) for row in expression["pseudobulk_rows"]),
    }
    if observed != expected:
        raise RuntimeError(f"Cohort reconciliation failed: expected {expected}, observed {observed}")

    slide_paths = sorted(
        path
        for path in DATA.rglob("*.svs")
        if "_tri_" in path.name.lower()
        and path.parts[-3] in participant_ids
    )
    tier_by_pid = {row["participant_id"]: row.get("tier", "") for row in checklist}
    slide_rows = []
    slide_grids = []
    slide_errors = []
    for path in slide_paths:
        try:
            row, grids = process_slide(path, tier_by_pid[path.parts[-3]])
            slide_rows.append(row)
            slide_grids.append(
                {
                    "participant_id": row["participant_id"],
                    "slide_id": row["slide_id"],
                    "grid_proxy_values": grids,
                }
            )
            print(
                f"TRI {row['participant_id']} {row['slide_id']}: "
                f"proxy={row['trichrome_collagen_proxy']}, "
                f"mask_failure={row['mask_failure_flag']}"
            )
        except (openslide.OpenSlideError, OSError, ValueError, RuntimeError) as error:
            slide_errors.append(
                {
                    "participant_id": path.parts[-3],
                    "file_name": path.name,
                    "path": str(path.relative_to(ROOT)),
                    "error": f"{type(error).__name__}: {error}",
                }
            )
            print(f"TRI ERROR {path}: {type(error).__name__}: {error}")
    if not slide_rows:
        raise RuntimeError("No TRI slides were successfully processed")

    blur_values = np.asarray(
        [
            row["blur_laplacian_variance"]
            for row in slide_rows
            if row["blur_laplacian_variance"] != ""
        ],
        dtype=float,
    )
    blur_threshold = (
        float(np.percentile(blur_values, 10)) if blur_values.size else np.nan
    )
    for row in slide_rows:
        metric = row["blur_laplacian_variance"]
        row["blur_candidate_flag"] = (
            bool(metric != "" and float(metric) <= blur_threshold)
            if np.isfinite(blur_threshold)
            else ""
        )
        row["blur_candidate_threshold_p10"] = (
            blur_threshold if np.isfinite(blur_threshold) else ""
        )

    collagen_rows = participant_collagen_proxy(slide_rows, participant_ids)
    correlations = compute_correlations(expression, collagen_rows)
    mask_rows = inspect_compartment_masks(participant_ids)
    score_audit = inspect_pathologist_scores(participant_ids)

    write_csv(OUT / "spot_qc_table.csv", expression["spot_rows"])
    write_csv(OUT / "sample_qc_summary.csv", expression["sample_rows"])
    write_csv(OUT / "gene_expression_by_spot.csv", expression["spot_expression_rows"])
    write_csv(OUT / "gene_detection_by_participant.csv", expression["gene_participant_rows"])
    write_csv(OUT / "gene_detection_cohort_summary.csv", expression["gene_summary_rows"])
    write_csv(OUT / "gene_feature_match_audit.csv", expression["gene_match_rows"])
    write_csv(OUT / "module_scores_by_spot.csv", expression["module_spot_rows"])
    write_csv(OUT / "module_detection_by_participant.csv", expression["module_participant_rows"])
    write_csv(OUT / "module_detection_cohort_summary.csv", expression["module_summary"])
    write_csv(OUT / "pseudobulk_log_cpm.csv", expression["pseudobulk_rows"])
    write_csv(OUT / "pca_participant_scores.csv", expression["pca_scores"].to_dict("records"))
    write_csv(OUT / "pca_metadata_associations.csv", expression["pca_associations"])
    write_csv(OUT / "sample_metadata_audit.csv", expression["sample_metadata_rows"])
    write_csv(OUT / "local_metadata_fields_read.csv", expression["local_metadata_audit"])
    write_csv(OUT / "trichrome_slide_proxy_summary.csv", slide_rows)
    write_csv(OUT / "participant_trichrome_collagen_proxy.csv", collagen_rows)
    write_csv(OUT / "segmentation_compartment_availability.csv", mask_rows)
    write_csv(OUT / "pathologist_score_metadata_audit.csv", score_audit)
    write_csv(OUT / "slide_processing_errors.csv", slide_errors)

    make_plots(
        expression["spot_rows"],
        expression["gene_summary_rows"],
        expression["pca_scores"],
        expression["pca_metadata"],
        correlations,
    )
    write_csv(
        OUT / "participant_collagen_expression_correlations.csv",
        [
            {key: value for key, value in row.items() if key != "points"}
            for row in correlations
        ],
    )

    generator = np.random.default_rng(RANDOM_SEED + 99)
    verify_indices = generator.choice(len(slide_paths), size=min(3, len(slide_paths)), replace=False)
    slide_by_path = {row["path"]: row for row in slide_rows}
    verification_rows = []
    for slide_index in verify_indices:
        path = slide_paths[int(slide_index)]
        row = slide_by_path.get(str(path.relative_to(ROOT)))
        if row is None:
            verification_rows.append(
                {
                    "path": str(path.relative_to(ROOT)),
                    "status": "not reprocessed: initial slide processing failed",
                    "table_proxy": "",
                    "recomputed_proxy": "",
                    "absolute_difference": "",
                }
            )
            continue
        verification, _ = process_slide(path, tier_by_pid[path.parts[-3]])
        difference = abs(
            float(row["trichrome_collagen_proxy"])
            - float(verification["trichrome_collagen_proxy"])
        )
        verification_rows.append(
            {
                "path": str(path.relative_to(ROOT)),
                "status": "PASS" if difference <= 1e-12 else "FAIL",
                "table_proxy": row["trichrome_collagen_proxy"],
                "recomputed_proxy": verification["trichrome_collagen_proxy"],
                "absolute_difference": difference,
                "reopened_level": verification["openslide_level"],
                "reopened_mpp_x_um": verification["mpp_x_um"],
                "reopened_mpp_y_um": verification["mpp_y_um"],
            }
        )
    write_csv(OUT / "three_slide_recompute_verification.csv", verification_rows)
    if any(row["status"] != "PASS" for row in verification_rows):
        raise RuntimeError("Three-slide independent recomputation did not pass")

    no_spot_proxy_columns = []
    for filename in (
        "spot_qc_table.csv",
        "gene_expression_by_spot.csv",
        "module_scores_by_spot.csv",
    ):
        with (OUT / filename).open(encoding="utf-8-sig", newline="") as stream:
            headers = next(csv.reader(stream))
        forbidden = {
            "trichrome_collagen_proxy",
            "collagen_proxy_fraction",
            "collagen_positive_area",
            "collagen_positive_area_mm2",
        }
        if any(header.lower() in forbidden for header in headers):
            no_spot_proxy_columns.append(filename)
    if no_spot_proxy_columns:
        raise RuntimeError(
            f"Forbidden spot-level collagen field found in: {no_spot_proxy_columns}"
        )

    config = {
        "random_seed": RANDOM_SEED,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "participant_unit_for_statistics": True,
        "spot_qc_percentile": QC_PERCENTILE,
        "umi_threshold": expression["umi_threshold"],
        "genes_detected_threshold": expression["gene_threshold"],
        "spot_expression_transform": "log1p(raw target counts / total spot UMI * 10000)",
        "pseudobulk_transform": "log1p(summed feature counts / summed participant UMI * 1000000)",
        "module_scoring": "simple mean of member log1p(CP10K); no control genes",
        "trichrome_collagen_proxy_method": (
            "Otsu saturation tissue mask; per-slide white-reference balance; "
            "fixed OpenCV HSV blue/green hue 75-140, saturation >=35"
        ),
        "trichrome_target_mpp_um": TARGET_MPP_UM,
        "trichrome_grid_um": GRID_BLOCK_UM,
        "random_verification_slide_seed": RANDOM_SEED + 99,
        "counts": observed,
        "slide_files_discovered": len(slide_paths),
        "slides_successfully_processed": len(slide_rows),
        "slide_processing_errors": len(slide_errors),
        "software_versions": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "opencv": cv2.__version__,
            "openslide_python": openslide.__version__,
            "openslide_library": openslide.__library_version__,
            "scikit_learn": __import__("sklearn").__version__,
            "scikit_image": __import__("skimage").__version__,
            "matplotlib": matplotlib.__version__,
            "pillow": PIL.__version__,
            "tifffile": importlib.metadata.version("tifffile"),
        },
        "registration_run": False,
        "model_training_run": False,
        "batch_correction_run": False,
        "spot_level_collagen_assignment": False,
    }
    (OUT / "analysis_config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )
    write_verdict(expression, slide_rows, correlations, score_audit)
    output_names = [
        "analysis_config.json",
        "run_qc_collagen.py",
        "requirements-qc.txt",
        "spot_qc_table.csv",
        "sample_qc_summary.csv",
        "gene_expression_by_spot.csv",
        "gene_detection_by_participant.csv",
        "gene_detection_cohort_summary.csv",
        "gene_feature_match_audit.csv",
        "module_scores_by_spot.csv",
        "module_detection_by_participant.csv",
        "module_detection_cohort_summary.csv",
        "pseudobulk_log_cpm.csv",
        "pca_participant_scores.csv",
        "pca_metadata_associations.csv",
        "sample_metadata_audit.csv",
        "local_metadata_fields_read.csv",
        "trichrome_slide_proxy_summary.csv",
        "participant_trichrome_collagen_proxy.csv",
        "participant_collagen_expression_correlations.csv",
        "segmentation_compartment_availability.csv",
        "pathologist_score_metadata_audit.csv",
        "slide_processing_errors.csv",
        "three_slide_recompute_verification.csv",
        "qc_verdict.md",
        "plots\\spot_qc_distributions.png",
        "plots\\gene_detection_prevalence.png",
        "plots\\pca_by_tier.png",
        "plots\\pca_by_fibrosis_status.png",
        "plots\\pca_by_visium_library_ids.png",
        "plots\\pca_by_sequencer_model.png",
        "plots\\pca_by_sequencing_platform.png",
        "plots\\pca_by_repository_platform.png",
    ]
    write_readme(config, observed, output_names)
    print(json.dumps(config, indent=2))
    print(f"Outputs written under {OUT}")


if __name__ == "__main__":
    main()
