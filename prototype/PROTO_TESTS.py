from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import math
import random
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np
import torch
from PIL import Image

import PROTO_ASSOCIATE as associate
import PROTO_QUANTIFY as quantify
import PROTO_VALIDATE as validate

ROOT = validate.PROTO_ROOT
PHASEA_DIR = Path(r"D:\patent\stage2A_audit")
PHASEA_ARCHIVE = Path(r"D:\patent\m2t49zf6xr-1.zip")
PHASEA_SPLIT = PHASEA_DIR / "PHASEA_final_split_manifest.csv"
PHASEA_METRICS = PHASEA_DIR / "PHASEA_final_per_image_metrics.csv"
FA_SPOT_TABLE = Path(r"D:\patent\stage_FA\FA_SPOT_ANALYSIS_FINAL.csv")
FA_EFFECT_TABLE = Path(r"D:\patent\stage_FA\FA_PER_PARTICIPANT_EFFECTS_FINAL.csv")
FORBIDDEN_STRINGS = (
    "cause",
    "causes",
    "causal",
    "driver",
    "responsible",
    "diagnose",
    "grade",
    "stage",
    "prognosis",
    "treat",
)
MANDATED_CAUSAL_SENTENCE = "This sample alone cannot show that these genes cause fibrosis."


def _import_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load test reference: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _image_bytes(mode: str = "RGB", fill: int = 100) -> bytes:
    image = Image.new(mode, (32, 32), color=fill if mode == "L" else (fill, fill, fill))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _synthetic_spatial_inputs() -> tuple[validate.ImageAssessment, quantify.QuantificationResult, dict, dict, dict]:
    height = width = 200
    image = np.full((height, width, 3), (100, 100, 100), dtype=np.uint8)
    unet = np.zeros((height, width), dtype=bool)
    unet[:, 100:] = True
    colour = np.zeros((height, width), dtype=bool)
    assessment = validate.ImageAssessment(
        source_name="synthetic.png",
        image_format="PNG",
        original_rgb=image.copy(),
        scaled_rgb=image.copy(),
        input_sha256=hashlib.sha256(image.tobytes()).hexdigest(),
        input_bytes=image.nbytes,
        input_mpp=4.1,
        scale_factor=1.0,
        tissue_fraction=1.0,
        rgb_features={},
        feature_z_scores={},
        status="IN RANGE",
        reasons=(),
        stats_sha256="0" * 64,
    )
    result = quantify.QuantificationResult(
        assessment=assessment,
        unet_mask_scaled=unet,
        colour_mask_scaled=colour,
        unet_mask_original=unet.copy(),
        colour_mask_original=colour.copy(),
        unet_percent_tissue=50.0,
        colour_percent_tissue=0.0,
        tissue_pixels=height * width,
        differing_by_more_than_15_pp=True,
        checkpoint_sha256=validate.EXPECTED_CHECKPOINT_SHA256,
        runtime_seconds=0.0,
    )
    barcodes = []
    positions = {}
    left = []
    right = []
    for row in range(9):
        for col in range(10):
            barcode = f"BC{row:02d}{col:02d}"
            barcodes.append(barcode)
            x = 20.0 + col * 18.0
            y = 20.0 + row * 20.0
            positions[barcode] = {
                "barcode": barcode,
                "in_tissue": 1,
                "array_row": row,
                "array_col": col,
                "pixel_row_fullres": y,
                "pixel_col_fullres": x,
            }
            (right if col >= 5 else left).append(barcode)
    left_set = set(left)
    raw_counts = {}
    for gene_index, gene in enumerate(associate.GENES):
        raw_counts[gene] = np.asarray(
            [
                5 + ((index + gene_index) % 13)
                if barcode in left_set
                else 500 + ((index + gene_index) % 31)
                for index, barcode in enumerate(barcodes)
            ],
            dtype=np.float64,
        )
    counts = {
        "barcodes": barcodes,
        "library_sizes": np.full(len(barcodes), 20_000.0),
        "raw_counts": raw_counts,
        "missing_genes": [],
        "files": [],
    }
    return assessment, result, counts, positions, {
        "tissue_hires_scalef": 1.0,
        "spot_diameter_fullres": 55.0 / 4.1,
    }


def _scan_user_text(text: str) -> list[str]:
    cleaned = text
    for warning in validate.load_warnings():
        cleaned = cleaned.replace(warning, "")
    cleaned = cleaned.replace(MANDATED_CAUSAL_SENTENCE, "")
    lowered = cleaned.casefold()
    return [word for word in FORBIDDEN_STRINGS if word in lowered]


class PrototypeValidationTests(unittest.TestCase):
    def test_hash_matches_and_wrong_hash_is_refused(self) -> None:
        self.assertEqual(validate.verify_checkpoint_hash(), validate.EXPECTED_CHECKPOINT_SHA256)
        expected = validate.EXPECTED_CHECKPOINT_SHA256
        try:
            validate.EXPECTED_CHECKPOINT_SHA256 = "0" * 64
            with self.assertRaises(validate.ValidationError):
                validate.verify_checkpoint_hash()
        finally:
            validate.EXPECTED_CHECKPOINT_SHA256 = expected

    def test_missing_scale_is_refused(self) -> None:
        with self.assertRaisesRegex(validate.ValidationError, "Micrometres per pixel is required"):
            validate.validate_image(_image_bytes(), None, "rgb.png")

    def test_scale_outside_registered_range_is_refused(self) -> None:
        with self.assertRaisesRegex(validate.ValidationError, "outside the allowed"):
            validate.validate_image(_image_bytes(), 4.1 * 1.6, "scale.png")

    def test_grayscale_is_refused(self) -> None:
        with self.assertRaisesRegex(validate.ValidationError, "must be readable RGB"):
            validate.validate_image(_image_bytes("L"), 4.1, "gray.png")

    def test_blank_and_low_tissue_images_are_refused_cleanly(self) -> None:
        with self.assertRaises(validate.ValidationError) as blank_error:
            validate.validate_image(_image_bytes("RGB", 255), 4.1, "blank.png")
        self.assertEqual(blank_error.exception.status, "REFUSED")
        self.assertIn("Tissue fraction", str(blank_error.exception))

    def test_too_few_spots_and_mismatched_barcodes_are_refused(self) -> None:
        rows = [{"barcode": str(i), "unet_fibrosis_fraction": i / 57} for i in range(57)]
        with self.assertRaisesRegex(ValueError, "At least 20 spots"):
            associate.make_groups(rows, "unet_fibrosis_fraction")
        positions = {"known": {"in_tissue": 1}}
        with self.assertRaisesRegex(ValueError, "no spatial position"):
            associate.validate_barcode_match(["unknown"], positions)

    def test_shuffled_spot_locations_reduce_synthetic_effect(self) -> None:
        assessment, result, counts, positions, scale = _synthetic_spatial_inputs()
        original_rows, _ = associate._make_spot_rows(result, counts, positions, scale)
        original_grouped = associate.make_groups(original_rows, "unet_fibrosis_fraction")
        original_fit = associate.fit_adjusted(original_grouped, "collagen_module")
        self.assertTrue(original_fit["valid"])

        shuffled_positions = dict(positions)
        coordinates = [
            (positions[barcode]["pixel_row_fullres"], positions[barcode]["pixel_col_fullres"])
            for barcode in counts["barcodes"]
        ]
        random.Random(20261118).shuffle(coordinates)
        for barcode, (pixel_row, pixel_col) in zip(counts["barcodes"], coordinates):
            shuffled_positions[barcode] = {
                **positions[barcode],
                "pixel_row_fullres": pixel_row,
                "pixel_col_fullres": pixel_col,
            }
        shuffled_rows, _ = associate._make_spot_rows(
            result, counts, shuffled_positions, scale
        )
        shuffled_grouped = associate.make_groups(
            shuffled_rows, "unet_fibrosis_fraction"
        )
        shuffled_fit = associate.fit_adjusted(
            shuffled_grouped, "collagen_module"
        )
        self.assertTrue(shuffled_fit["valid"])
        self.assertLess(
            abs(shuffled_fit["effect"]),
            abs(original_fit["effect"]) * 0.5,
            msg=(
                f"synthetic effect original={original_fit['effect']:.12g}; "
                f"shuffled={shuffled_fit['effect']:.12g}"
            ),
        )
        self.__class__.shuffle_summary = {
            "synthetic_original_effect": original_fit["effect"],
            "synthetic_shuffled_effect": shuffled_fit["effect"],
        }

    def test_spatial_block_interval_uses_fixed_resample_count(self) -> None:
        _, result, counts, positions, scale = _synthetic_spatial_inputs()
        rows, _ = associate._make_spot_rows(result, counts, positions, scale)
        grouped = associate.make_groups(rows, "unet_fibrosis_fraction")
        low, high = associate._bootstrap_ci(
            grouped,
            "collagen_module",
            associate.BOOTSTRAP_SEED,
            time.monotonic() + 60,
        )
        self.assertTrue(math.isfinite(low))
        self.assertTrue(math.isfinite(high))
        self.assertLessEqual(low, high)

    def test_png_outputs_carry_all_five_warnings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="PROTO_png_test_", dir=ROOT) as folder:
            path = Path(folder) / "PROTO_warning_test.png"
            quantify._write_png(
                path,
                Image.new("RGB", (4, 4), (0, 0, 0)),
                validate.load_warnings(),
            )
            with Image.open(path) as output:
                self.assertEqual(
                    [output.info.get(f"W{index}") for index in range(1, 6)],
                    validate.load_warnings(),
                )

    def test_compact_count_csv_is_read(self) -> None:
        with tempfile.TemporaryDirectory(prefix="PROTO_counts_test_", dir=ROOT) as folder:
            path = Path(folder) / "PROTO_counts.csv"
            fieldnames = ["barcode", "library_size_umi"] + [
                f"raw_{gene}" for gene in associate.GENES
            ]
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                for index in range(3):
                    writer.writerow(
                        {
                            "barcode": f"BC{index}",
                            "library_size_umi": 1000 + index,
                            **{
                                f"raw_{gene}": index + gene_index + 1
                                for gene_index, gene in enumerate(associate.GENES)
                            },
                        }
                    )
            result = associate.load_counts(path)
            self.assertEqual(result["barcodes"], ["BC0", "BC1", "BC2"])
            self.assertEqual(len(result["raw_counts"]["COL1A1"]), 3)

    def test_required_warning_scan_allows_only_required_phrases(self) -> None:
        warnings = validate.load_warnings()
        self.assertEqual(len(warnings), 5)
        self.assertEqual(
            _scan_user_text("\n".join(warnings) + "\n" + MANDATED_CAUSAL_SENTENCE),
            [],
        )

    def test_streamlit_interface_shows_warnings_and_acknowledgement(self) -> None:
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_file(str(ROOT / "PROTO_APP.py"), default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual([item.value for item in app.warning], validate.load_warnings())
        self.assertEqual(len(app.checkbox), 1)


class PrototypeRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        started = time.monotonic()
        cls.model, cls.device, cls.checkpoint_hash = quantify.load_frozen_model()
        cls.phasea = _import_module(
            "proto_test_phasea",
            PHASEA_DIR / "PHASEA_run_audit.py",
        )
        with PHASEA_SPLIT.open("r", encoding="utf-8-sig", newline="") as handle:
            split_rows = [
                row for row in csv.DictReader(handle) if row["assignment"] == "official_test"
            ]
        cls.test_records = sorted(split_rows, key=lambda row: row["stem"])[:5]
        if len(cls.test_records) != 5:
            raise RuntimeError("Five Phase A test images are not available.")
        with PHASEA_METRICS.open("r", encoding="utf-8-sig", newline="") as handle:
            cls.saved_metrics = {
                row["stem"]: row for row in csv.DictReader(handle)
            }
        cls.image_results = []
        with zipfile.ZipFile(PHASEA_ARCHIVE) as archive, torch.inference_mode():
            for record in cls.test_records:
                image_bytes = archive.read(record["image_member"])
                with Image.open(io.BytesIO(image_bytes)) as image:
                    rgb = np.asarray(image, dtype=np.uint8).copy()
                if rgb.shape[:2] != (512, 512):
                    raise RuntimeError(
                        f"Phase A regression image is not 512-by-512: {record['stem']}"
                    )
                reference = cls.phasea.run_unet(rgb, cls.model, cls.device)
                prototype = quantify.run_unet(
                    cls.model,
                    rgb,
                    cls.device,
                    time.monotonic() + quantify.MAX_RUNTIME_SECONDS,
                )
                if not np.array_equal(reference, prototype):
                    raise AssertionError(
                        f"Frozen mask differs from Phase A inference for {record['stem']}."
                    )
                mask_bytes = archive.read(record["mask_member"])
                with Image.open(io.BytesIO(mask_bytes)) as mask:
                    target = np.asarray(mask.convert("L"), dtype=np.uint8) == 255
                intersection = int(np.logical_and(prototype, target).sum())
                denominator = int(prototype.sum() + target.sum())
                dice = 1.0 if denominator == 0 else 2.0 * intersection / denominator
                saved = cls.saved_metrics[record["stem"]]
                if not math.isclose(dice, float(saved["unet_dice"]), rel_tol=0, abs_tol=1e-12):
                    raise AssertionError(
                        f"Dice mismatch for {record['stem']}: {dice} vs {saved['unet_dice']}."
                    )
                cls.image_results.append(
                    {
                        "stem": record["stem"],
                        "mask_bit_identical_to_phase_a_function": True,
                        "saved_phase_a_mask_available": False,
                        "dice": dice,
                        "input_micrometres_per_pixel": "NOT AVAILABLE",
                        "fibrosis_percentage": "NOT AVAILABLE",
                    }
                )
        cls.phasea_seconds = time.monotonic() - started

    def test_five_phase_a_masks_and_saved_dice_match(self) -> None:
        self.assertEqual(len(self.image_results), 5)
        self.assertTrue(all(row["mask_bit_identical_to_phase_a_function"] for row in self.image_results))

    def test_three_stage_fa_participant_effects_match(self) -> None:
        participants = ("27-10157", "27-10201", "27-10206")
        targets = set(participants)
        spot_rows: dict[str, list[dict[str, object]]] = {item: [] for item in participants}
        with FA_SPOT_TABLE.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                participant = row["participant_id"]
                if participant not in targets:
                    continue
                spot_rows[participant].append(
                    {
                        "group": row["unet_group"],
                        "collagen_module": float(row["collagen_module"]),
                        "log_library_size": float(row["log_library_size"]),
                        "tissue_fraction": float(row["tissue_fraction"]),
                        "tissue_depth_um": float(row["tissue_depth_um"]),
                    }
                )
        reference_effects: dict[str, float] = {}
        with FA_EFFECT_TABLE.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if (
                    row["mask"] == "unet"
                    and row["target"] == "collagen_module"
                    and row["participant_id"] in targets
                    and row["fit_status"] == "PASS"
                ):
                    reference_effects[row["participant_id"]] = float(
                        row["participant_effect_high_minus_low"]
                    )
        results = {}
        for participant in participants:
            fit = associate.fit_adjusted(spot_rows[participant], "collagen_module")
            self.assertTrue(fit["valid"], msg=f"{participant}: {fit.get('reason')}")
            self.assertIn(participant, reference_effects)
            difference = abs(fit["effect"] - reference_effects[participant])
            self.assertLessEqual(difference, 1e-9)
            results[participant] = {
                "prototype_effect": fit["effect"],
                "stage_fa_final_effect": reference_effects[participant],
                "absolute_difference": difference,
                "tolerance": 1e-9,
            }
        self.__class__.participant_parity = results


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(
        json.dumps(
            {
                "tests_run": result.testsRun,
                "failures": len(result.failures),
                "errors": len(result.errors),
                "phase_a_seconds": getattr(
                    PrototypeRegressionTests, "phasea_seconds", None
                ),
                "phase_a_images": getattr(PrototypeRegressionTests, "image_results", []),
                "participant_parity": getattr(
                    PrototypeRegressionTests, "participant_parity", {}
                ),
                "shuffle_summary": getattr(
                    PrototypeValidationTests, "shuffle_summary", {}
                ),
                "warnings": validate.load_warnings(),
            },
            indent=2,
        )
    )
    sys.exit(0 if result.wasSuccessful() else 1)
