import csv
import gzip
import io
import json
import random
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import cv2
import numpy as np
import pandas as pd
import tifffile
from PIL import Image, ImageDraw, ImageFont
import scipy
from scipy.io import mmread


ROOT = Path(r"D:\patent")
DATA = ROOT / "data"
OUT = ROOT / "plan_a_plan_b"
CHECKLIST = ROOT / "tier_a_download_checklist.csv"
PARTICIPANT = "27-10207"
TARGET_GENES = ("COL1A1", "COL3A1", "FN1", "TGFB1", "ACTA2")
TILE_SIZE = 224
EXPRESSION_PREVALENCE_THRESHOLD = 0.10
RANDOM_SEED = 20261110


def load_matrix(participant_dir):
    matrix_zip = participant_dir / "visium" / "expression_matrix.zip"
    if not matrix_zip.exists():
        return None

    with zipfile.ZipFile(matrix_zip) as archive:
        members = {Path(name).name: name for name in archive.namelist()}
        barcode_name = next(name for base, name in members.items() if base.endswith("barcodes.tsv.gz"))
        feature_name = next(name for base, name in members.items() if base.endswith("features.tsv.gz"))
        matrix_name = next(name for base, name in members.items() if base.endswith("matrix.mtx.gz"))

        barcodes = gzip.decompress(archive.read(barcode_name)).decode("utf-8").splitlines()
        feature_lines = gzip.decompress(archive.read(feature_name)).decode("utf-8").splitlines()
        feature_rows = [line.split("\t") for line in feature_lines]
        matrix_bytes = gzip.decompress(archive.read(matrix_name))
        matrix = mmread(io.BytesIO(matrix_bytes), spmatrix=True).tocsr()

    if matrix.shape != (len(feature_rows), len(barcodes)):
        raise ValueError(
            f"Matrix shape {matrix.shape} does not match {len(feature_rows)} features "
            f"and {len(barcodes)} barcodes"
        )
    return matrix, barcodes, feature_rows


def read_segmentation_status(participant_dir):
    archive_path = next(
        (participant_dir / "masks").glob("*Seg_Masks_Features.zip"), None
    )
    if archive_path is None:
        return "not locally available", []

    with zipfile.ZipFile(archive_path) as archive:
        ome_member = next(
            (name for name in archive.namelist() if name.lower().endswith(".ome.tiff")),
            None,
        )
        if ome_member is None:
            return "archive lacks OME-TIFF annotation", []
        with tifffile.TiffFile(io.BytesIO(archive.read(ome_member))) as tif:
            ome = ElementTree.fromstring(tif.ome_metadata)
        channels = [
            elem.attrib.get("Name", "")
            for elem in ome.iter()
            if elem.tag.endswith("Channel")
        ]

    has_fibrosis_layer = any(
        re.search(r"interstit|fibros|collagen", channel, re.IGNORECASE)
        for channel in channels
    )
    if has_fibrosis_layer:
        status = "candidate layer present; fibrosis definition still requires validation"
    else:
        status = (
            "not computable from this archive: no interstitium, fibrosis, or collagen "
            "annotation channel; feature tables are structure pathomics"
        )
    return status, channels


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def crop_tile(image, x, y, tile_size):
    half = tile_size // 2
    left, top = x - half, y - half
    right, bottom = left + tile_size, top + tile_size
    pad_left, pad_top = max(0, -left), max(0, -top)
    pad_right, pad_bottom = max(0, right - image.shape[1]), max(0, bottom - image.shape[0])
    if pad_left or pad_top or pad_right or pad_bottom:
        image = cv2.copyMakeBorder(
            image,
            pad_top,
            pad_bottom,
            pad_left,
            pad_right,
            cv2.BORDER_REFLECT_101,
        )
        left += pad_left
        right += pad_left
        top += pad_top
        bottom += pad_top
    return image[top:bottom, left:right]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with CHECKLIST.open(encoding="utf-8-sig", newline="") as stream:
        checklist = list(csv.DictReader(stream))
    participants = [row["participant_id"] for row in checklist]
    if PARTICIPANT not in participants:
        raise ValueError(f"{PARTICIPANT} is not in {CHECKLIST}")

    participant_dir = DATA / PARTICIPANT
    spatial_dir = participant_dir / "visium" / "outs" / "spatial"
    positions_path = spatial_dir / "tissue_positions.csv"
    scale_path = spatial_dir / "scalefactors_json.json"
    hires_path = spatial_dir / "tissue_hires_image.png"
    for path in (positions_path, scale_path, hires_path):
        if not path.exists():
            raise FileNotFoundError(path)

    matrix_data = load_matrix(participant_dir)
    if matrix_data is None:
        raise FileNotFoundError(participant_dir / "visium" / "expression_matrix.zip")
    matrix, barcodes, feature_rows = matrix_data
    positions = pd.read_csv(positions_path)
    in_tissue = positions.loc[positions["in_tissue"].astype(int) == 1].copy()
    matrix_barcodes = set(barcodes)
    position_barcodes = set(in_tissue["barcode"].astype(str))
    if matrix_barcodes != position_barcodes:
        raise ValueError(
            "Matrix barcodes and in-tissue tissue_positions barcodes differ: "
            f"{len(matrix_barcodes - position_barcodes)} matrix-only and "
            f"{len(position_barcodes - matrix_barcodes)} position-only"
        )

    barcode_index = {barcode: index for index, barcode in enumerate(barcodes)}
    column_indices = np.array([barcode_index[b] for b in in_tissue["barcode"]], dtype=int)
    matrix = matrix[:, column_indices]
    libsize = np.asarray(matrix.sum(axis=0)).ravel().astype(np.float64)
    genes_by_symbol = {}
    for row_index, feature in enumerate(feature_rows):
        symbol = feature[1] if len(feature) > 1 else feature[0]
        if symbol in TARGET_GENES:
            genes_by_symbol.setdefault(symbol, []).append(row_index)

    if not set(TARGET_GENES).issubset(genes_by_symbol):
        missing = sorted(set(TARGET_GENES) - set(genes_by_symbol))
        raise ValueError(f"Target genes absent from matrix: {missing}")

    spot_rows = []
    gene_stats = {}
    for gene in TARGET_GENES:
        counts = np.asarray(matrix[genes_by_symbol[gene], :].sum(axis=0)).ravel().astype(np.int64)
        normalized = np.divide(
            counts * 10000.0,
            libsize,
            out=np.zeros_like(counts, dtype=np.float64),
            where=libsize > 0,
        )
        detected = counts > 0
        gene_stats[gene] = {
            "raw_mean_per_in_tissue_spot": float(counts.mean()),
            "mean_counts_per_10k": float(normalized.mean()),
            "spots_detected": int(detected.sum()),
            "spots_total": int(len(counts)),
            "detected_percent": float(100 * detected.mean()),
            "enough_spots_at_10_percent": bool(
                detected.mean() >= EXPRESSION_PREVALENCE_THRESHOLD
            ),
        }
        for idx, barcode in enumerate(in_tissue["barcode"].astype(str)):
            spot_rows.append(
                {
                    "participant_id": PARTICIPANT,
                    "barcode": barcode,
                    "gene": gene,
                    "raw_count": int(counts[idx]),
                    "counts_per_10000": float(normalized[idx]),
                    "detected": bool(detected[idx]),
                }
            )

    spot_expression_path = OUT / "plan_b_spot_expression_long.csv"
    write_csv(
        spot_expression_path,
        spot_rows,
        [
            "participant_id",
            "barcode",
            "gene",
            "raw_count",
            "counts_per_10000",
            "detected",
        ],
    )

    scale_factors = json.loads(scale_path.read_text(encoding="utf-8"))
    hires_scale = float(scale_factors["tissue_hires_scalef"])
    spot_diameter = float(scale_factors["spot_diameter_fullres"]) * hires_scale
    hires_bgr = cv2.imread(str(hires_path), cv2.IMREAD_COLOR)
    if hires_bgr is None:
        raise ValueError(f"Could not read {hires_path}")
    hires_rgb = cv2.cvtColor(hires_bgr, cv2.COLOR_BGR2RGB)
    tile_dir = OUT / "tiles" / PARTICIPANT
    tile_dir.mkdir(parents=True, exist_ok=True)
    tile_manifest = []
    wide_counts = {}
    for gene in TARGET_GENES:
        idxs = genes_by_symbol[gene]
        vals = np.asarray(matrix[idxs, :].sum(axis=0)).ravel().astype(np.int64)
        wide_counts[gene] = vals

    for spot_idx, (_, row) in enumerate(in_tissue.iterrows()):
        x = int(round(float(row["pxl_col_in_fullres"]) * hires_scale))
        y = int(round(float(row["pxl_row_in_fullres"]) * hires_scale))
        if not (0 <= x < hires_rgb.shape[1] and 0 <= y < hires_rgb.shape[0]):
            raise ValueError(f"Scaled center for {row['barcode']} is outside hires image")
        tile = crop_tile(hires_rgb, x, y, TILE_SIZE)
        if tile.shape[:2] != (TILE_SIZE, TILE_SIZE):
            raise ValueError(f"Unexpected tile dimensions for {row['barcode']}: {tile.shape}")
        tile_path = tile_dir / f"{row['barcode']}.png"
        Image.fromarray(tile).save(tile_path)
        item = {
            "participant_id": PARTICIPANT,
            "barcode": str(row["barcode"]),
            "tile_path": str(tile_path.relative_to(ROOT)),
            "center_x_hires_px": x,
            "center_y_hires_px": y,
            "tile_size_px": TILE_SIZE,
            "spot_diameter_hires_px": spot_diameter,
            "padded_at_image_edge": bool(
                x < TILE_SIZE // 2
                or y < TILE_SIZE // 2
                or x >= hires_rgb.shape[1] - TILE_SIZE // 2
                or y >= hires_rgb.shape[0] - TILE_SIZE // 2
            ),
        }
        for gene in TARGET_GENES:
            counts = wide_counts[gene]
            item[f"{gene}_raw_count"] = int(counts[spot_idx])
        tile_manifest.append(item)

    tile_fields = list(tile_manifest[0])
    write_csv(OUT / "plan_b_tile_manifest.csv", tile_manifest, tile_fields)

    # Deterministic gallery sample for QC; the complete per-spot tiles are saved above.
    sample_n = min(20, len(tile_manifest))
    sample_indices = sorted(random.Random(RANDOM_SEED).sample(range(len(tile_manifest)), sample_n))
    cell, label_h, cols = 224, 52, 4
    rows = (sample_n + cols - 1) // cols
    gallery = Image.new("RGB", (cols * cell, rows * (cell + label_h)), "white")
    draw = ImageDraw.Draw(gallery)
    font = ImageFont.load_default()
    for gallery_idx, spot_idx in enumerate(sample_indices):
        item = tile_manifest[spot_idx]
        tile = Image.open(ROOT / item["tile_path"]).convert("RGB")
        gx, gy = (gallery_idx % cols) * cell, (gallery_idx // cols) * (cell + label_h)
        gallery.paste(tile, (gx, gy + label_h))
        draw.text((gx + 3, gy + 2), item["barcode"], fill="black", font=font)
        label = " ".join(
            f"{gene}:{item[f'{gene}_raw_count']}" for gene in TARGET_GENES
        )
        draw.text((gx + 3, gy + 18), label[:43], fill="black", font=font)
    gallery_path = OUT / f"{PARTICIPANT}_tile_gallery.png"
    gallery.save(gallery_path)

    seg_status, seg_channels = read_segmentation_status(participant_dir)
    patient_rows = []
    for checklist_row in checklist:
        pid = checklist_row["participant_id"]
        local = pid == PARTICIPANT
        row = {
            "participant_id": pid,
            "tier": checklist_row["tier"],
            "data_available_locally": "yes" if local else "no",
            "fibrosis_percent": "",
            "fibrosis_status": (
                seg_status if local else "not computed: participant files not downloaded"
            ),
            "in_tissue_spots": len(in_tissue) if local else "",
        }
        for gene in TARGET_GENES:
            stats = gene_stats.get(gene, {}) if local else {}
            row[f"{gene}_mean_raw_counts_per_spot"] = stats.get(
                "raw_mean_per_in_tissue_spot", ""
            )
            row[f"{gene}_mean_counts_per_10000"] = stats.get(
                "mean_counts_per_10k", ""
            )
            row[f"{gene}_detected_spots"] = stats.get("spots_detected", "")
            row[f"{gene}_detected_percent"] = stats.get("detected_percent", "")
            row[f"{gene}_enough_spots_10pct"] = stats.get(
                "enough_spots_at_10_percent", ""
            )
        patient_rows.append(row)
    patient_fields = list(patient_rows[0])
    write_csv(OUT / "plan_a_patient_summary.csv", patient_rows, patient_fields)

    spot_summary = [
        {
            "participant_id": PARTICIPANT,
            "in_tissue_spots": len(in_tissue),
            "matrix_barcodes": len(barcodes),
            "tile_size_px": TILE_SIZE,
            "tissue_hires_scalef": hires_scale,
            "spots_with_tiles": len(tile_manifest),
            "gene": gene,
            **stats,
        }
        for gene, stats in gene_stats.items()
    ]
    write_csv(
        OUT / "plan_b_gene_spot_check.csv",
        spot_summary,
        [
            "participant_id",
            "in_tissue_spots",
            "matrix_barcodes",
            "tile_size_px",
            "tissue_hires_scalef",
            "spots_with_tiles",
            "gene",
            "raw_mean_per_in_tissue_spot",
            "mean_counts_per_10k",
            "spots_detected",
            "spots_total",
            "detected_percent",
            "enough_spots_at_10_percent",
        ],
    )

    config = {
        "random_seed": RANDOM_SEED,
        "target_genes": list(TARGET_GENES),
        "tile_size_px": TILE_SIZE,
        "tile_image": str(hires_path.relative_to(ROOT)),
        "spot_coordinate_mapping": "pxl_col/row_in_fullres multiplied by tissue_hires_scalef",
        "gene_normalization": "raw counts per spot / all-gene spot library size * 10000",
        "sufficient_expression_screen": (
            f"detected in at least {EXPRESSION_PREVALENCE_THRESHOLD:.0%} "
            "of in-tissue spots; exploratory threshold, not a prediction criterion"
        ),
        "input_matrix": str((participant_dir / "visium" / "expression_matrix.zip").relative_to(ROOT)),
        "in_tissue_spots": len(in_tissue),
        "matrix_barcodes_match_in_tissue_positions": True,
        "segmentation_channels": seg_channels,
        "segmentation_fibrosis_status": seg_status,
        "package_versions": {
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "opencv": cv2.__version__,
            "tifffile": tifffile.__version__,
            "pillow": Image.__version__,
            "scipy": scipy.__version__,
        },
    }
    (OUT / "analysis_config.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )

    print(json.dumps({"participant": PARTICIPANT, "spot_count": len(in_tissue), "genes": gene_stats,
                      "segmentation_status": seg_status, "segmentation_channels": seg_channels,
                      "tiles_written": len(tile_manifest), "gallery": str(gallery_path),
                      "output_dir": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
