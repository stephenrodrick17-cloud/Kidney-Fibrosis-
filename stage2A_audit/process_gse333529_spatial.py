import argparse
import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path, PurePosixPath

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from scipy.io import mmread


SAMPLES = {
    "P1": "GSM9767741",
    "P2": "GSM9767742",
    "P3": "GSM9767743",
    "P4": "GSM9767744",
}
GENES = ("COL1A1", "COL3A1", "FN1")
SUFFIXES = (
    "_barcodes.tsv.gz",
    "_features.tsv.gz",
    "_matrix.mtx.gz",
    "_scalefactors_json.json.gz",
    "_tissue_hires_image.png.gz",
    "_tissue_positions.csv.gz",
)


def read_member_gzip(archive, member_name):
    member = archive.extractfile(member_name)
    if member is None:
        raise ValueError(f"Missing archive member: {member_name}")
    with member, gzip.GzipFile(fileobj=member) as stream:
        return stream.read()


def inspect_archive(archive):
    members = {}
    for member in archive.getmembers():
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or not member.isfile():
            raise ValueError(f"Unexpected archive path or member type: {member.name}")
        if len(path.parts) != 1:
            raise ValueError(f"Unexpected nested archive member: {member.name}")
        members[member.name] = member

    for sample, gsm in SAMPLES.items():
        prefix = f"{gsm}_{sample}"
        for suffix in SUFFIXES:
            name = prefix + suffix
            if name not in members:
                raise ValueError(f"Missing required archive member: {name}")
    return members


def load_sample(archive, sample, gsm):
    prefix = f"{gsm}_{sample}"
    features = pd.read_csv(
        io.BytesIO(read_member_gzip(archive, prefix + "_features.tsv.gz")),
        sep="\t",
        header=None,
    )
    barcodes = read_member_gzip(
        archive, prefix + "_barcodes.tsv.gz"
    ).decode("utf-8").splitlines()
    matrix = mmread(
        io.BytesIO(read_member_gzip(archive, prefix + "_matrix.mtx.gz")),
        spmatrix=True,
    ).tocsr()
    positions = pd.read_csv(
        io.BytesIO(read_member_gzip(archive, prefix + "_tissue_positions.csv.gz"))
    )
    scales = json.loads(
        read_member_gzip(archive, prefix + "_scalefactors_json.json.gz")
    )
    image = Image.open(
        io.BytesIO(read_member_gzip(archive, prefix + "_tissue_hires_image.png.gz"))
    ).convert("RGB")

    if features.shape[1] < 2:
        raise ValueError(f"Unexpected feature table for {sample}")
    if matrix.shape != (len(features), len(barcodes)):
        raise ValueError(
            f"Feature/barcode matrix mismatch for {sample}: "
            f"{matrix.shape}, {len(features)}, {len(barcodes)}"
        )
    required_columns = {
        "barcode",
        "in_tissue",
        "pxl_row_in_fullres",
        "pxl_col_in_fullres",
    }
    if not required_columns.issubset(positions.columns):
        raise ValueError(f"Unexpected tissue-position columns for {sample}")

    tissue = positions.loc[positions["in_tissue"].astype(int) == 1].copy()
    barcode_to_column = {barcode: index for index, barcode in enumerate(barcodes)}
    if tissue["barcode"].duplicated().any():
        raise ValueError(f"Duplicate in-tissue barcode in {sample}")
    if set(tissue["barcode"]) != set(barcodes):
        raise ValueError(f"In-tissue barcodes do not match matrix for {sample}")
    tissue["matrix_column"] = tissue["barcode"].map(barcode_to_column)

    scale = float(scales["tissue_hires_scalef"])
    tissue["image_x"] = tissue["pxl_col_in_fullres"] * scale
    tissue["image_y"] = tissue["pxl_row_in_fullres"] * scale
    if (
        tissue["image_x"].min() < 0
        or tissue["image_y"].min() < 0
        or tissue["image_x"].max() >= image.width
        or tissue["image_y"].max() >= image.height
    ):
        raise ValueError(f"Scaled tissue coordinates fall outside image for {sample}")

    symbols = features.iloc[:, 1].astype(str)
    symbol_rows = {}
    for gene in GENES:
        matches = np.flatnonzero(symbols.to_numpy() == gene)
        if len(matches) != 1:
            raise ValueError(
                f"Expected one {gene} feature in {sample}, found {len(matches)}"
            )
        symbol_rows[gene] = int(matches[0])

    spot_columns = tissue["matrix_column"].to_numpy(dtype=int)
    library_sizes = np.asarray(matrix.sum(axis=0)).ravel()[spot_columns]
    if np.any(library_sizes <= 0):
        raise ValueError(f"Empty in-tissue expression library in {sample}")

    expression = {}
    long_rows = []
    summary_rows = []
    for gene, feature_row in symbol_rows.items():
        raw_counts = matrix.getrow(feature_row).toarray().ravel()[spot_columns]
        normalized = np.log1p(raw_counts / library_sizes * 10000.0)
        expression[gene] = normalized
        for spot, count, value in zip(
            tissue.itertuples(index=False), raw_counts, normalized
        ):
            long_rows.append(
                {
                    "sample": sample,
                    "barcode": spot.barcode,
                    "gene": gene,
                    "raw_count": int(count),
                    "log1p_normalized_count_per_10k": float(value),
                    "image_x": float(spot.image_x),
                    "image_y": float(spot.image_y),
                }
            )
        summary_rows.append(
            {
                "sample": sample,
                "gene": gene,
                "in_tissue_spots": int(len(tissue)),
                "spots_with_detected_transcript": int(np.count_nonzero(raw_counts)),
                "fraction_spots_detected": float(np.mean(raw_counts > 0)),
                "median_log1p_normalized_count_per_10k": float(
                    np.median(normalized)
                ),
                "max_raw_count": int(raw_counts.max()),
            }
        )

    return {
        "sample": sample,
        "image": image,
        "scale": scale,
        "tissue": tissue,
        "expression": expression,
        "long_rows": long_rows,
        "summary_rows": summary_rows,
        "feature_count": int(len(features)),
        "matrix_shape": list(matrix.shape),
    }


def make_overlay(samples, output_path):
    fig, axes = plt.subplots(
        nrows=len(GENES),
        ncols=len(samples),
        figsize=(18, 12),
        constrained_layout=True,
    )
    for row, gene in enumerate(GENES):
        all_values = np.concatenate(
            [sample["expression"][gene] for sample in samples]
        )
        vmax = max(float(np.quantile(all_values, 0.99)), 0.1)
        for col, sample in enumerate(samples):
            ax = axes[row, col]
            ax.imshow(sample["image"])
            spots = sample["tissue"]
            points = ax.scatter(
                spots["image_x"],
                spots["image_y"],
                c=sample["expression"][gene],
                cmap="viridis",
                vmin=0,
                vmax=vmax,
                s=18,
                alpha=0.82,
                linewidths=0,
            )
            ax.set_title(f'{sample["sample"]} - {gene}')
            ax.set_axis_off()
            fig.colorbar(points, ax=ax, fraction=0.046, pad=0.02)
    fig.suptitle(
        "GSE333529: spatial transcript counts over tissue images "
        "(not fibrosis scores)",
        fontsize=14,
    )
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(
        description="Validate and plot GSE333529 Visium expression overlays."
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=Path(__file__).parent
        / "external_datasets"
        / "GSE333529"
        / "GSE333529_RAW.tar",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent
        / "external_datasets"
        / "GSE333529"
        / "processed",
    )
    args = parser.parse_args()
    if not args.archive.is_file():
        parser.error(f"Archive not found: {args.archive}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    viewer_dir = args.output_dir / "viewer_images"
    viewer_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(args.archive, "r:*") as archive:
        inspect_archive(archive)
        samples = [
            load_sample(archive, sample, gsm) for sample, gsm in SAMPLES.items()
        ]

    viewer_images = []
    for sample in samples:
        image_path = viewer_dir / f'GSE333529_{sample["sample"]}_tissue_hires.png'
        sample["image"].save(image_path)
        viewer_images.append(image_path.name)

    long_rows = [row for sample in samples for row in sample["long_rows"]]
    summary_rows = [row for sample in samples for row in sample["summary_rows"]]
    pd.DataFrame(long_rows).to_csv(
        args.output_dir / "spatial_expression_spots.csv", index=False
    )
    pd.DataFrame(summary_rows).to_csv(
        args.output_dir / "gene_detection_summary.csv", index=False
    )
    make_overlay(samples, args.output_dir / "spatial_expression_overlays.png")

    result = {
        "accession": "GSE333529",
        "archive": args.archive.name,
        "archive_size_bytes": args.archive.stat().st_size,
        "archive_sha256": sha256_file(args.archive),
        "samples": [
            {
                "sample": sample["sample"],
                "features": sample["feature_count"],
                "matrix_shape": sample["matrix_shape"],
                "in_tissue_spots": int(len(sample["tissue"])),
                "image_size_pixels": list(sample["image"].size),
                "high_resolution_scale_factor": sample["scale"],
            }
            for sample in samples
        ],
        "genes_visualized": list(GENES),
        "viewer_images": viewer_images,
        "normalization": "log1p(raw gene count / spot total counts * 10000)",
        "coordinate_check": (
            "All matrix barcodes matched in-tissue position rows; scaled "
            "coordinates were within the supplied high-resolution images."
        ),
        "interpretation_limit": (
            "Exploratory spatial expression visualization only; not fibrosis "
            "ground truth, a fibrosis grade, or validation of the RENFAST model."
        ),
    }
    (args.output_dir / "processing_summary.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
