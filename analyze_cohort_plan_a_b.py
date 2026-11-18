import csv
import gzip
import io
import json
import os
import random
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import cv2
import h5py
import numpy as np
import pandas as pd
import scipy
import tifffile
from PIL import Image, ImageDraw, ImageFont
from scipy import sparse
from scipy.io import mmread


ROOT = Path(r"D:\patent")
DATA = ROOT / "data"
OUT = ROOT / "plan_a_plan_b"
CHECKLIST = ROOT / "tier_a_download_checklist.csv"
TARGET_GENES = ("COL1A1", "COL3A1", "FN1", "TGFB1", "ACTA2")
TILE_SIZE = 224
EXPRESSION_PREVALENCE_THRESHOLD = 0.10
RANDOM_SEED = 20261110
GALLERY_SAMPLES = 20


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_expression_zip(path):
    with zipfile.ZipFile(path) as archive:
        members = {Path(name).name.lower(): name for name in archive.namelist()}
        barcode_name = next(
            (name for base, name in members.items() if base.endswith("barcodes.tsv.gz")),
            None,
        )
        feature_name = next(
            (name for base, name in members.items() if base.endswith("features.tsv.gz")),
            None,
        )
        matrix_name = next(
            (name for base, name in members.items() if base.endswith("matrix.mtx.gz")),
            None,
        )
        if not (barcode_name and feature_name and matrix_name):
            return None
        barcodes = gzip.decompress(archive.read(barcode_name)).decode("utf-8").splitlines()
        features = [
            line.split("\t")
            for line in gzip.decompress(archive.read(feature_name))
            .decode("utf-8")
            .splitlines()
        ]
        matrix = mmread(
            io.BytesIO(gzip.decompress(archive.read(matrix_name))), spmatrix=True
        ).tocsr()
    if matrix.shape != (len(features), len(barcodes)):
        raise ValueError(f"{path}: matrix shape does not match feature/barcode counts")
    return {
        "path": path,
        "barcodes": barcodes,
        "features": features,
        "matrix": matrix,
        "format": "Matrix Market zip",
    }


def read_expression_directory(path):
    barcode = next(path.glob("*barcodes.tsv*"), None)
    feature = next(path.glob("*features.tsv*"), None)
    matrix_path = next(path.glob("matrix.mtx*"), None)
    if not (barcode and feature and matrix_path):
        return None

    def read_text(file_path):
        raw = file_path.read_bytes()
        if file_path.name.lower().endswith(".gz"):
            raw = gzip.decompress(raw)
        return raw.decode("utf-8").splitlines()

    barcodes = read_text(barcode)
    features = [line.split("\t") for line in read_text(feature)]
    raw_matrix = matrix_path.read_bytes()
    if matrix_path.name.lower().endswith(".gz"):
        raw_matrix = gzip.decompress(raw_matrix)
    matrix = mmread(io.BytesIO(raw_matrix), spmatrix=True).tocsr()
    if matrix.shape != (len(features), len(barcodes)):
        raise ValueError(f"{path}: matrix shape does not match feature/barcode counts")
    return {
        "path": path,
        "barcodes": barcodes,
        "features": features,
        "matrix": matrix,
        "format": "Matrix Market directory",
    }


def read_expression_h5(path):
    with h5py.File(path, "r") as handle:
        if "matrix" not in handle:
            return None
        group = handle["matrix"]
        if not all(name in group for name in ("data", "indices", "indptr", "shape", "barcodes", "features")):
            return None
        shape = tuple(int(value) for value in group["shape"][:])
        matrix = sparse.csc_matrix(
            (
                group["data"][:],
                group["indices"][:],
                group["indptr"][:],
            ),
            shape=shape,
        ).tocsr()
        barcodes = [
            value.decode("utf-8") if isinstance(value, bytes) else str(value)
            for value in group["barcodes"][:]
        ]
        feature_group = group["features"]
        names = feature_group["name"][:]
        ids = feature_group["id"][:] if "id" in feature_group else names
        features = []
        for feature_id, name in zip(ids, names):
            if isinstance(feature_id, bytes):
                feature_id = feature_id.decode("utf-8")
            if isinstance(name, bytes):
                name = name.decode("utf-8")
            features.append([str(feature_id), str(name), "Gene Expression"])
    if matrix.shape != (len(features), len(barcodes)):
        raise ValueError(f"{path}: HDF5 matrix shape does not match features/barcodes")
    return {
        "path": path,
        "barcodes": barcodes,
        "features": features,
        "matrix": matrix,
        "format": "10x HDF5",
    }


def load_expression_sources(participant_dir):
    visium_dir = participant_dir / "visium"
    if not visium_dir.exists():
        return []
    sources = []
    for path in visium_dir.rglob("*expression_matrix*.zip"):
        if path.name.endswith(".part"):
            continue
        source = read_expression_zip(path)
        if source:
            sources.append(source)
    for path in visium_dir.rglob("filtered_feature_bc_matrix"):
        if path.is_dir():
            source = read_expression_directory(path)
            if source:
                sources.append(source)
    for path in visium_dir.rglob("filtered_feature_bc_matrix.h5"):
        source = read_expression_h5(path)
        if source:
            sources.append(source)
    unique = {}
    for source in sources:
        key = (str(source["path"]), tuple(source["barcodes"][:3]), source["matrix"].shape)
        unique[key] = source
    return list(unique.values())


def equivalent_expression_sources(first, second):
    if first["barcodes"] != second["barcodes"] or first["features"] != second["features"]:
        return False
    if first["matrix"].shape != second["matrix"].shape:
        return False
    return (first["matrix"] != second["matrix"]).nnz == 0


def shared_context_depth(first_path, second_path, root):
    common = Path(os.path.commonpath((str(first_path.resolve()), str(second_path.resolve()))))
    try:
        return len(common.relative_to(root.resolve()).parts)
    except ValueError:
        return -1


def find_spatial_samples(participant_dir):
    visium_dir = participant_dir / "visium"
    samples = []
    seen = set()
    positions_paths = [
        path
        for path in visium_dir.rglob("tissue_positions*.csv")
        if path.name.lower() in {"tissue_positions.csv", "tissue_positions_list.csv"}
    ]
    for positions_path in positions_paths:
        spatial_dir = positions_path.parent
        scale_path = spatial_dir / "scalefactors_json.json"
        image_path = spatial_dir / "tissue_hires_image.png"
        if not (scale_path.exists() and image_path.exists()):
            continue
        key = (positions_path.resolve(), image_path.resolve())
        if key in seen:
            continue
        seen.add(key)
        samples.append(
            {
                "spatial_dir": spatial_dir,
                "positions_path": positions_path,
                "scale_path": scale_path,
                "image_path": image_path,
            }
        )
    return samples


def read_positions(path):
    positions = pd.read_csv(path)
    if "barcode" not in positions.columns:
        if path.name.lower() != "tissue_positions_list.csv":
            raise ValueError(f"{path}: missing barcode column")
        positions = pd.read_csv(
            path,
            header=None,
            names=[
                "barcode",
                "in_tissue",
                "array_row",
                "array_col",
                "pxl_row_in_fullres",
                "pxl_col_in_fullres",
            ],
        )
    required = {
        "barcode",
        "in_tissue",
        "pxl_row_in_fullres",
        "pxl_col_in_fullres",
    }
    if not required.issubset(positions.columns):
        raise ValueError(f"{path}: missing required tissue position columns")
    return positions


def read_fibrosis_status(participant_dir):
    mask_dir = participant_dir / "masks"
    archives = list(mask_dir.glob("*Seg_Masks_Features*.zip")) if mask_dir.exists() else []
    if not archives:
        return "not locally available", "", []

    summaries = []
    channels_seen = []
    explicit_fibrosis = False
    explicit_tissue_denominator = False
    for archive_path in archives:
        with zipfile.ZipFile(archive_path) as archive:
            ome_files = [name for name in archive.namelist() if name.lower().endswith(".ome.tiff")]
            readmes = [name for name in archive.namelist() if Path(name).name.lower() == "readme.md"]
            workbook_names = [name for name in archive.namelist() if name.lower().endswith(".xlsx")]
            text = ""
            if readmes:
                text = archive.read(readmes[0]).decode("utf-8", "replace")
            relevant_headers = []
            for workbook in workbook_names:
                try:
                    sheets = pd.read_excel(io.BytesIO(archive.read(workbook)), sheet_name=None, nrows=0)
                    for sheet, frame in sheets.items():
                        relevant_headers.extend(
                            str(column)
                            for column in frame.columns
                            if re.search(r"fibros|collagen|interstit", str(column), re.I)
                        )
                except (ValueError, OSError, zipfile.BadZipFile):
                    continue
            channels = []
            if ome_files:
                with archive.open(ome_files[0]) as ome_stream:
                    with tifffile.TiffFile(ome_stream) as tif:
                        if tif.ome_metadata is None:
                            raise ValueError(f"{archive_path}: OME-TIFF is missing OME metadata")
                        metadata = ElementTree.fromstring(tif.ome_metadata)
                channels = [
                    elem.attrib.get("Name", "")
                    for elem in metadata.iter()
                    if elem.tag.endswith("Channel")
                ]
            channels_seen.extend(channels)
            fibrosis_layers = [
                channel
                for channel in channels
                if re.search(r"fibros|collagen", channel, re.I)
            ]
            tissue_layers = [
                channel
                for channel in channels
                if re.search(r"whole.?tissue|total.?tissue|tissue.?area", channel, re.I)
            ]
            explicit_fibrosis = explicit_fibrosis or bool(fibrosis_layers) or any(
                re.search(r"fibros|collagen", header, re.I)
                for header in relevant_headers
            ) or bool(
                re.search(r"fibros(?:is|tic).*?(?:area|fraction|percent|mask)", text, re.I)
            )
            explicit_tissue_denominator = explicit_tissue_denominator or bool(tissue_layers)
            summaries.append(
                {
                    "archive": archive_path.name,
                    "ome_channels": channels,
                    "fibrosis_related_feature_headers": relevant_headers,
                }
            )

    if explicit_fibrosis and explicit_tissue_denominator:
        status = "explicit fibrosis annotation and tissue denominator present; computation requires validated layer semantics"
    elif explicit_fibrosis:
        status = "fibrosis/collagen annotation may be present, but no explicit tissue denominator; percentage not computed"
    else:
        status = "not computable: available feature/mask package does not expose an explicit fibrosis/collagen area measure"
    return status, "; ".join(channels_seen), summaries


def normalized_gene_values(source, spot_indices):
    feature_rows = source["features"]
    matrix = source["matrix"]
    gene_rows = {}
    for idx, feature in enumerate(feature_rows):
        symbol = feature[1] if len(feature) > 1 else feature[0]
        if symbol in TARGET_GENES:
            gene_rows.setdefault(symbol, []).append(idx)
    libsize = np.asarray(matrix[:, spot_indices].sum(axis=0)).ravel().astype(np.float64)
    values = {}
    for gene in TARGET_GENES:
        rows = gene_rows.get(gene, [])
        if not rows:
            values[gene] = None
            continue
        counts = np.asarray(matrix[rows, :][:, spot_indices].sum(axis=0)).ravel().astype(np.int64)
        cp10k = np.divide(
            counts * 10000.0,
            libsize,
            out=np.zeros_like(counts, dtype=np.float64),
            where=libsize > 0,
        )
        values[gene] = (counts, cp10k)
    return values, gene_rows


def extract_tile(image, x, y):
    half = TILE_SIZE // 2
    left, top = x - half, y - half
    pad_left = max(0, -left)
    pad_top = max(0, -top)
    pad_right = max(0, left + TILE_SIZE - image.shape[1])
    pad_bottom = max(0, top + TILE_SIZE - image.shape[0])
    padded = cv2.copyMakeBorder(
        image,
        pad_top,
        pad_bottom,
        pad_left,
        pad_right,
        cv2.BORDER_REFLECT_101,
    )
    crop_left = left + pad_left
    crop_top = top + pad_top
    return padded[
        crop_top : crop_top + TILE_SIZE,
        crop_left : crop_left + TILE_SIZE,
    ]


def process_participant(pid, tier, gallery_dir):
    participant_dir = DATA / pid
    sources = load_expression_sources(participant_dir)
    samples = find_spatial_samples(participant_dir)
    status, channels, mask_details = read_fibrosis_status(participant_dir)
    all_spot_rows = []
    all_tile_rows = []
    sample_status = []
    paired_samples = []
    for sample_idx, sample in enumerate(samples, 1):
        positions = read_positions(sample["positions_path"])
        in_tissue = positions.loc[positions["in_tissue"].astype(int) == 1].copy()
        if in_tissue.empty:
            sample_status.append("no in-tissue coordinates")
            continue
        spatial_barcodes = set(in_tissue["barcode"].astype(str))
        candidate_scores = [
            (
                len(spatial_barcodes.intersection(set(source["barcodes"]))),
                shared_context_depth(
                    source["path"], sample["positions_path"], participant_dir / "visium"
                ),
                source,
            )
            for source in sources
        ]
        candidate_scores.sort(
            key=lambda item: (item[0], item[1], len(item[2]["barcodes"])),
            reverse=True,
        )
        if not candidate_scores or candidate_scores[0][0] == 0:
            sample_status.append(
                f"no matching expression barcodes for {sample['positions_path'].relative_to(participant_dir)}"
            )
            continue
        overlap, context_depth, source = candidate_scores[0]
        if overlap != len(spatial_barcodes):
            sample_status.append(
                f"incomplete expression match for {sample['positions_path'].relative_to(participant_dir)}: "
                f"{overlap}/{len(spatial_barcodes)} in-tissue barcodes"
            )
            continue
        top_sources = [
            candidate
            for candidate_overlap, candidate_context, candidate in candidate_scores
            if candidate_overlap == overlap and candidate_context == context_depth
        ]
        unique_sources = []
        for candidate in top_sources:
            if not any(
                equivalent_expression_sources(candidate, existing)
                for existing in unique_sources
            ):
                unique_sources.append(candidate)
        if len(unique_sources) != 1:
            sample_status.append(
                f"ambiguous expression match for {sample['positions_path'].relative_to(participant_dir)}: "
                f"{len(unique_sources)} non-equivalent matrices cover all in-tissue barcodes"
            )
            continue
        source = unique_sources[0]
        barcode_to_col = {barcode: index for index, barcode in enumerate(source["barcodes"])}
        matched = in_tissue[in_tissue["barcode"].astype(str).isin(barcode_to_col)].copy()
        if matched.empty:
            sample_status.append("barcode overlap did not produce matched tissue spots")
            continue
        indices = np.array([barcode_to_col[str(barcode)] for barcode in matched["barcode"]], dtype=int)
        gene_values, gene_rows = normalized_gene_values(source, indices)
        scale_factors = json.loads(sample["scale_path"].read_text(encoding="utf-8"))
        hires_scale = float(scale_factors["tissue_hires_scalef"])
        spot_diameter = float(scale_factors.get("spot_diameter_fullres", 0)) * hires_scale
        image_bgr = cv2.imread(str(sample["image_path"]), cv2.IMREAD_COLOR)
        if image_bgr is None:
            sample_status.append(f"could not read {sample['image_path']}")
            continue
        image = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        sample_label = sample["positions_path"].parent.name
        paired_samples.append(
            {
                "sample": sample,
                "source": source,
                "matched": matched,
                "indices": indices,
                "gene_values": gene_values,
                "gene_rows": gene_rows,
                "image": image,
                "scale": hires_scale,
                "spot_diameter": spot_diameter,
                "label": sample_label,
                "barcode_overlap": overlap,
            }
        )
        sample_status.append(
            f"paired {len(matched)}/{len(in_tissue)} tissue spots with {source['path'].name}"
        )

    stats_by_gene = {}
    for gene in TARGET_GENES:
        counts_all = []
        cp10k_all = []
        detected_count = 0
        for sample in paired_samples:
            values = sample["gene_values"].get(gene)
            if values is None:
                continue
            counts, cp10k = values
            counts_all.append(counts)
            cp10k_all.append(cp10k)
            detected_count += int((counts > 0).sum())
        if counts_all:
            counts = np.concatenate(counts_all)
            cp10k = np.concatenate(cp10k_all)
            total_spots = len(counts)
            stats_by_gene[gene] = {
                "mean_raw_counts_per_spot": float(counts.mean()),
                "mean_counts_per_10000": float(cp10k.mean()),
                "detected_spots": int((counts > 0).sum()),
                "spots_total": total_spots,
                "detected_percent": float(100 * (counts > 0).mean()),
                "enough_spots_10pct": bool(
                    (counts > 0).mean() >= EXPRESSION_PREVALENCE_THRESHOLD
                ),
            }
        else:
            stats_by_gene[gene] = {
                "mean_raw_counts_per_spot": "",
                "mean_counts_per_10000": "",
                "detected_spots": "",
                "spots_total": 0,
                "detected_percent": "",
                "enough_spots_10pct": False,
            }

    total_spots = 0
    for sample_idx, sample in enumerate(paired_samples, 1):
        total_spots += len(sample["matched"])
        sample_dir = OUT / "tiles" / pid / f"sample_{sample_idx:02d}"
        sample_dir.mkdir(parents=True, exist_ok=True)
        for idx, (_, spot) in enumerate(sample["matched"].iterrows()):
            x = int(round(float(spot["pxl_col_in_fullres"]) * sample["scale"]))
            y = int(round(float(spot["pxl_row_in_fullres"]) * sample["scale"]))
            if not (0 <= x < sample["image"].shape[1] and 0 <= y < sample["image"].shape[0]):
                raise ValueError(f"{pid} {spot['barcode']}: scaled coordinate outside hires image")
            tile = extract_tile(sample["image"], x, y)
            if tile.shape[:2] != (TILE_SIZE, TILE_SIZE):
                raise ValueError(f"{pid} {spot['barcode']}: unexpected tile size {tile.shape}")
            tile_path = sample_dir / f"{spot['barcode']}.png"
            Image.fromarray(tile).save(tile_path)
            tile_row = {
                "participant_id": pid,
                "sample_id": sample["label"],
                "barcode": str(spot["barcode"]),
                "tile_path": str(tile_path.relative_to(ROOT)),
                "center_x_hires_px": x,
                "center_y_hires_px": y,
                "tile_size_px": TILE_SIZE,
                "tissue_hires_scalef": sample["scale"],
                "spot_diameter_hires_px": sample["spot_diameter"],
                "expression_source": str(sample["source"]["path"].relative_to(ROOT)),
            }
            spot_row = {
                "participant_id": pid,
                "sample_id": sample["label"],
                "barcode": str(spot["barcode"]),
                "expression_source": str(sample["source"]["path"].relative_to(ROOT)),
            }
            for gene in TARGET_GENES:
                values = sample["gene_values"].get(gene)
                if values is None:
                    raw, cp10k = 0, 0.0
                else:
                    counts, normalized = values
                    raw, cp10k = int(counts[idx]), float(normalized[idx])
                tile_row[f"{gene}_raw_count"] = raw
                spot_row[f"{gene}_raw_count"] = raw
                spot_row[f"{gene}_counts_per_10000"] = cp10k
                spot_row[f"{gene}_detected"] = raw > 0
            all_tile_rows.append(tile_row)
            all_spot_rows.append(spot_row)

    if paired_samples:
        rng = random.Random(RANDOM_SEED + sum(ord(char) for char in pid))
        selected = rng.sample(
            range(len(all_tile_rows)), min(GALLERY_SAMPLES, len(all_tile_rows))
        )
        gallery_dir.mkdir(parents=True, exist_ok=True)
        columns = 4
        cell = TILE_SIZE
        label_h = 58
        rows = (len(selected) + columns - 1) // columns
        gallery = Image.new("RGB", (columns * cell, rows * (cell + label_h)), "white")
        draw = ImageDraw.Draw(gallery)
        font = ImageFont.load_default()
        for gallery_idx, manifest_idx in enumerate(selected):
            item = all_tile_rows[manifest_idx]
            tile = Image.open(ROOT / item["tile_path"]).convert("RGB")
            gx = (gallery_idx % columns) * cell
            gy = (gallery_idx // columns) * (cell + label_h)
            gallery.paste(tile, (gx, gy + label_h))
            draw.text((gx + 2, gy + 2), f"{pid} {item['barcode']}", fill="black", font=font)
            label = " ".join(
                f"{gene}:{item[f'{gene}_raw_count']}" for gene in TARGET_GENES
            )
            draw.text((gx + 2, gy + 19), label[:48], fill="black", font=font)
        gallery.save(gallery_dir / f"{pid}_tile_gallery.png")

    return {
        "participant_id": pid,
        "tier": tier,
        "local_data_available": bool(paired_samples),
        "fibrosis_percent": "",
        "fibrosis_status": status,
        "segmentation_channels": channels,
        "mask_archive_details": mask_details,
        "paired_samples": len(paired_samples),
        "in_tissue_spots": total_spots,
        "sample_status": " | ".join(sample_status) if sample_status else "no local Visium spatial data",
        "gene_stats": stats_by_gene,
        "spot_rows": all_spot_rows,
        "tile_rows": all_tile_rows,
    }


def update_audit(results):
    audit_path = ROOT / "audit_table.csv"
    with audit_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    new_fields = [
        "local_folder_present",
        "local_visium_expression",
        "local_visium_spatial",
        "local_trichrome",
        "local_seg_masks",
        "plan_a_b_status",
    ]
    for field in new_fields:
        if field not in fields:
            fields.append(field)
    result_by_pid = {result["participant_id"]: result for result in results}
    for row in rows:
        pid = row.get("participant_id", "")
        participant_dir = DATA / pid
        files = [path for path in participant_dir.rglob("*") if path.is_file()] if participant_dir.exists() else []
        names = [path.name.lower() for path in files]
        row["local_folder_present"] = "yes" if participant_dir.exists() else "no"
        row["local_visium_expression"] = "yes" if any("expression_matrix" in name and name.endswith(".zip") for name in names) or any(name == "filtered_feature_bc_matrix.h5" for name in names) else "no"
        row["local_visium_spatial"] = "yes" if (
            any(path.name.lower() in {"tissue_positions.csv", "tissue_positions_list.csv"} for path in files)
            and any(path.name.lower() == "scalefactors_json.json" for path in files)
            and any(path.name.lower() == "tissue_hires_image.png" for path in files)
        ) else "no"
        row["local_trichrome"] = "yes" if any("_tri_" in name and name.endswith(".svs") for name in names) else "no"
        row["local_seg_masks"] = "yes" if any("seg_masks_features" in name and name.endswith(".zip") for name in names) else "no"
        result = result_by_pid.get(pid)
        row["plan_a_b_status"] = (
            result["sample_status"] if result else "not in Tier A/B analysis cohort"
        )
        for field in fields:
            row.setdefault(field, "")
    with audit_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with CHECKLIST.open(encoding="utf-8-sig", newline="") as stream:
        checklist = list(csv.DictReader(stream))
    results = [
        process_participant(row["participant_id"], row["tier"], OUT / "galleries")
        for row in checklist
    ]
    patient_rows = []
    gene_rows = []
    segmentation_rows = []
    all_spot_rows = []
    all_tile_rows = []
    for result in results:
        row = {
            "participant_id": result["participant_id"],
            "tier": result["tier"],
            "local_data_available": result["local_data_available"],
            "paired_samples": result["paired_samples"],
            "in_tissue_spots": result["in_tissue_spots"],
            "fibrosis_percent": result["fibrosis_percent"],
            "fibrosis_status": result["fibrosis_status"],
            "segmentation_channels": result["segmentation_channels"],
            "sample_status": result["sample_status"],
        }
        details = result["mask_archive_details"]
        if details:
            for detail in details:
                segmentation_rows.append(
                    {
                        "participant_id": result["participant_id"],
                        "fibrosis_status": result["fibrosis_status"],
                        "archive": detail["archive"],
                        "ome_channels": "; ".join(detail["ome_channels"]),
                        "fibrosis_related_feature_headers": "; ".join(
                            detail["fibrosis_related_feature_headers"]
                        ),
                    }
                )
        else:
            segmentation_rows.append(
                {
                    "participant_id": result["participant_id"],
                    "fibrosis_status": result["fibrosis_status"],
                    "archive": "",
                    "ome_channels": "",
                    "fibrosis_related_feature_headers": "",
                }
            )
        for gene in TARGET_GENES:
            stats = result["gene_stats"][gene]
            row[f"{gene}_mean_raw_counts_per_spot"] = stats["mean_raw_counts_per_spot"]
            row[f"{gene}_mean_counts_per_10000"] = stats["mean_counts_per_10000"]
            row[f"{gene}_detected_spots"] = stats["detected_spots"]
            row[f"{gene}_detected_percent"] = stats["detected_percent"]
            row[f"{gene}_enough_spots_10pct"] = stats["enough_spots_10pct"]
            gene_rows.append(
                {
                    "participant_id": result["participant_id"],
                    "tier": result["tier"],
                    "in_tissue_spots": result["in_tissue_spots"],
                    "gene": gene,
                    **stats,
                }
            )
        patient_rows.append(row)
        all_spot_rows.extend(result["spot_rows"])
        all_tile_rows.extend(result["tile_rows"])

    write_csv(OUT / "plan_a_patient_summary.csv", patient_rows, list(patient_rows[0]))
    write_csv(
        OUT / "plan_b_gene_spot_check.csv",
        gene_rows,
        list(gene_rows[0]) if gene_rows else ["participant_id", "gene"],
    )
    write_csv(
        OUT / "plan_a_segmentation_audit.csv",
        segmentation_rows,
        [
            "participant_id",
            "fibrosis_status",
            "archive",
            "ome_channels",
            "fibrosis_related_feature_headers",
        ],
    )
    write_csv(
        OUT / "plan_b_spot_expression_long.csv",
        all_spot_rows,
        list(all_spot_rows[0]) if all_spot_rows else ["participant_id", "barcode"],
    )
    write_csv(
        OUT / "plan_b_tile_manifest.csv",
        all_tile_rows,
        list(all_tile_rows[0]) if all_tile_rows else ["participant_id", "barcode"],
    )

    config = {
        "random_seed": RANDOM_SEED,
        "targets": list(TARGET_GENES),
        "tile_size_px": TILE_SIZE,
        "spot_mapping": "full-resolution pixel coordinates multiplied by tissue_hires_scalef",
        "gene_normalization": "raw counts / all-gene spot library size * 10000",
        "enough_spots_threshold": EXPRESSION_PREVALENCE_THRESHOLD,
        "sparse_threshold_interpretation": "exploratory detection prevalence screen only",
        "cohort_participants": len(checklist),
        "participants_with_paired_spatial_expression": sum(
            result["local_data_available"] for result in results
        ),
        "package_versions": {
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "opencv": cv2.__version__,
            "h5py": h5py.__version__,
            "tifffile": tifffile.__version__,
            "pillow": Image.__version__,
        },
        "registration_or_training_run": False,
    }
    (OUT / "analysis_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    update_audit(results)
    print(json.dumps(config, indent=2))
    for result in results:
        print(
            result["participant_id"],
            result["tier"],
            "samples", result["paired_samples"],
            "spots", result["in_tissue_spots"],
            "status", result["sample_status"],
        )
        for gene, stats in result["gene_stats"].items():
            if stats["spots_total"]:
                print(
                    " ", gene,
                    f"{stats['detected_spots']}/{stats['spots_total']}",
                    f"({stats['detected_percent']:.1f}%)",
                    "enough_10pct", stats["enough_spots_10pct"],
                )


if __name__ == "__main__":
    main()
