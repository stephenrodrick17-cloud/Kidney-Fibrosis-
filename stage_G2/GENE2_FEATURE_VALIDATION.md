# GENE2 Saved-Feature Validation

**EXPLORATORY, NOT CONFIRMATORY.**  
**RESEARCH-ONLY — derived from ResNet-50/ImageNet features whose licence terms remain unverified.**

**Checked:** 2026-11-17, before any GENE2 model run.

## Result: all preregistered feature/key gates passed

| Check | Stage 1 development set | Stage 1d set | Result |
|---|---:|---:|---|
| Saved feature shape | `(25104, 2048)` | `(9631, 2048)` | PASS |
| Feature dtype | `float16` | `float16` | PASS |
| Non-finite feature values | 0 | 0 | PASS |
| Feature rows match participant/library/barcode key lengths | 25,104/25,104 | 9,631/9,631 | PASS |
| Duplicate full spot keys | 0 | 0 | PASS |
| Participant coverage | 28/28 local Stage 1 folders | 12/12 Stage 1d manifest participants | PASS |
| Independent key reconciliation | Feature keys exactly match all rows of `targets_by_spot.csv` | Per-library feature-key counts exactly match `spatial_mapping_qc.csv` | PASS |
| Mapping QC | Not recalculated in this feature check | All 12 libraries report matched barcodes, centers inside the image, all target genes present, and primary module members present | PASS |

Across both sets, the participant cohorts are disjoint, all 40 expected participants are present, and all 34,735 full spot keys are unique. These checks cover saved feature arrays and their existing keys; they do not establish any image-to-expression prediction performance.

## Runtime and source integrity

- Validation interpreter: `C:\Users\asus\python.exe`, Python `3.13.1`, NumPy `2.2.6`.
- Stage 1 features: `D:\patent\stage1_expression\spot_embeddings.npz`, SHA-256 `6130ad5fcdc4bbc3315296e05d58965f290b61bf88e9c3a369844edd870b4183`.
- Stage 1 key/target table: `D:\patent\stage1_expression\targets_by_spot.csv`, SHA-256 `8dade8a328018e49c2c4bc6d5e63aed1347c18d03eba6ce295356add27fd2aa6`.
- Stage 1d features and keys: `D:\patent\stage1d_confirm\confirmation_predictions.npz`, SHA-256 `a9d99c422deb8dff54394f5181eee5d771383206cc9ad38029c7eef340589e3b`.
- Stage 1d input manifest: `D:\patent\stage1d_confirm\data_manifest.csv`, SHA-256 `1809c54da6637b03615db59fe810b54c96d20f5ac0d789fe0259a31a7da0b149`.
- Stage 1d spatial map audit: `D:\patent\stage1d_confirm\spatial_mapping_qc.csv`, SHA-256 `e378871ef3e448e1846b7822d2b4667bc3d7cd81aacbeccc260529b77eec27b0`.

The Stage 1 and Stage 1d arrays were read to validate feature values, shapes, keys, and row alignment. No model was loaded or fitted, no image pixels were read, no Phase B2 materials were accessed, and no files outside `D:\patent\stage_G2\` were changed.

