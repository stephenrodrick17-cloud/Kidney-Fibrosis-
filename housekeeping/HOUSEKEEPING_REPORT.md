# Housekeeping Phase A - Read-only audit report

**Generated:** 2026-11-13T10:22:13+05:30  
**Scope:** D:\patent; Phase A only. `D:\patent\housekeeping` is excluded from the baseline census.  
**Changes:** no downloads, extractions, archives, moves, overwrites, or deletions were performed.

## Storage snapshot

- Baseline before Phase A outputs: **28,982 files** in **483 folders**, **32,566,724,377 bytes (32.567 GB; 30.330 GiB)**.
- Housekeeping outputs currently total **5,251,649 bytes**; current `D:\patent` footprint including these outputs is **32,571,976,026 bytes (32.572 GB)**.
- D: capacity: **262,134,947,840 bytes**.
- D: free before Phase A output creation: **117,831,090,176 bytes**; after report creation: **117,825,515,520 bytes**. Scan errors: **0**. Full folder totals are in [FOLDER_TOTALS.csv](FOLDER_TOTALS.csv); full per-file classifications are in [FULL_FILE_INVENTORY.csv](FULL_FILE_INVENTORY.csv); folders >50 MB are in [FOLDERS_OVER_50MB.csv](FOLDERS_OVER_50MB.csv); files >50 MB are in [FILES_OVER_50MB.csv](FILES_OVER_50MB.csv); largest 20 files are in [TOP_20_LARGEST_FILES.csv](TOP_20_LARGEST_FILES.csv).

### Top-level folder totals

| Folder | Bytes | GB decimal | Last modified |
|---|---:|---:|---|
| `data` | 15,817,172,196 | 15.817 | 2026-11-11T13:40:51+05:30 |
| `working` | 5,825,101,778 | 5.825 | 2026-11-06T10:01:06+05:30 |
| `16410` | 2,714,018,836 | 2.714 | 2026-11-06T13:49:45+05:30 |
| `plan_a_plan_b` | 2,122,184,153 | 2.122 | 2026-11-11T16:05:24+05:30 |
| `16420` | 1,477,889,058 | 1.478 | 2026-11-06T13:49:42+05:30 |
| `stage1_expression` | 259,417,938 | 0.259 | 2026-11-12T20:13:26+05:30 |
| `stage1b_expression` | 60,193,964 | 0.060 | 2026-11-12T23:03:32+05:30 |
| `qc_collagen` | 43,079,305 | 0.043 | 2026-11-12T00:20:03+05:30 |
| `stage0_audit` | 308,295 | 0.000 | 2026-11-12T12:16:23+05:30 |
| `stage1c_confirm` | 223,693 | 0.000 | 2026-11-13T10:03:36+05:30 |
| `__pycache__` | 196,066 | 0.000 | 2026-11-12T00:24:26+05:30 |

### `data` per participant/folder

See [DATA_PER_PARTICIPANT.csv](DATA_PER_PARTICIPANT.csv) for exact bytes and file counts. `data` total: **15,817,172,196 bytes (15.817 GB)** across 28 participant folders.

### 20 largest files

See [TOP_20_LARGEST_FILES.csv](TOP_20_LARGEST_FILES.csv); exact byte sizes and last-modified timestamps are included.

## Phase A classification and evidence

- **48 extracted-copy folders** matched retained ZIP member names, uncompressed sizes, and CRC32 values. Excluding the report-bearing `Analyses_and_QC` extraction, candidate duplicate bytes total **4,826,762,048 B**. See [DUPLICATE_CHECKS.csv](DUPLICATE_CHECKS.csv). This is not the SHA-256 test required before Phase C deletion.
- `plan_a_plan_b\tiles`: **2,063,606,489 B**; `plan_a_plan_b\galleries`: **46,126,195 B**. Derived by `analyze_cohort_plan_a_b.py` (224x224 tiles, seed 20261110). Inputs: `tier_a_download_checklist.csv`, source expression ZIPs, and extracted Visium positions, scalefactors and hires images. The script hard-codes `OUT=plan_a_plan_b` and rewrites CSV summaries; safe regeneration requires an isolated copy/output and preservation of protected files.
- Root `__pycache__`: **196,066 B**. An in-memory ZIP_DEFLATED sample of 4 files (196,066 B raw) saved 99,985 B; no archive was created.
- `working\m2t49zf6xr-1`: **520,111,286 B**, exact member copy of retained `m2t49zf6xr-1.zip`; duplicate candidate only after later SHA-256 verification.
- `working\1d27486e-08ec-4993-979c-066cf74fdc24_Analyses_and_QC`: protected because it contains analysis/QC workbooks and outputs, despite archive-member equivalence. Root archive is also protected.
- `16410` (**2,714,018,836 B**) and `16420` (**1,477,889,058 B**) are UNKNOWN; provenance, purpose and completeness were not established. Do not archive/move/delete them; incomplete `.crdownload` files may be active.
- RENFAST ZIP `m2t49zf6xr-1.zip` is already compressed (**518,896,940 B**). External move could free that amount on D:, but no move occurred.
- Candidate/action details are in [PHASEA_ARCHIVE_MANIFEST.csv](PHASEA_ARCHIVE_MANIFEST.csv); it is not a manifest of created archives. No archives exist.

## Proposed storage plans (not executed)

### (a) Keep everything

- Keep all inventoried files on D:. Project footprint after the new audit reports: **32,571,976,023 B (32.572 GB)**. No space is freed; D: free after report generation was **117,825,515,520 B**.

### (b) Target a local D: working set below 10 GB

- Required reduction from the current D:\patent tree: at least **22,571,976,026 B (22.572 GB)**.
- Hypothetical route: move `data` (**15,817,172,196 B**) and UNKNOWN `16410`/`16420` (**4,191,907,894 B combined**) to approved external storage; remove/regenerate tiles and galleries (**2,109,732,684 B**) and remove the verified RENFAST extracted copy (**520,111,286 B**) after required checks. Estimated local remainder: **9,933,051,966 B (9.933 GB)**.
- This only puts the local D: working set under 10 GB if external copies are excluded from the cap. It does not reduce whole-project storage, relocates protected cohort inputs and UNKNOWN folders, and is not authorized. No safe whole-project <10-GB plan can be claimed under current constraints.

## Stage 1d gate

- **BLOCKED - do not run Stage 1d.** The Stage 1c preregistration specifies a frozen one-hidden-layer MLP trained on the original 28 participants. The only model-like checkpoint found in `stage1_expression` is `model_cache\checkpoints\resnet50-11ad3fa6.pth` (102,540,417 B), the ResNet-50 encoder, not the trained prediction head. Stage 1b `.npz` files are predictions, not trained weights. No trained predictor checkpoint was found; no Stage 1d data were downloaded and no model was fitted.
- Stage 1 Gate A remains FAIL; Stage 1b remains exploratory, post-hoc.

## What could not be verified / risks

- File-level SHA-256 equality for every extracted duplicate was not computed; Phase C must do so before any deletion. Current duplicate evidence is ZIP member names, sizes and CRC32.
- Purpose, provenance, completeness and licensing of `16410`/`16420` were not verified; they remain UNKNOWN.
- Whether an external drive exists, whether external copies count toward the 10-GB whole-project cap, and which original datasets may leave D: were not specified.
- End-to-end reproducibility of tile generation into an isolated output directory is not verified; the current script rewrites other outputs.
- Post-report D: free space was measured at **117,825,515,520 bytes**; no source files were altered.

## Required next instruction

Review [ARCHIVE_PLAN.md](ARCHIVE_PLAN.md) and the CSV inventories. To proceed to Phase B, explicitly approve the Phase A plan. No files will be deleted unless you later send the exact phrase **APPROVE DELETE**. Stage 1d requires the frozen trained prediction checkpoint or an approved deterministic retraining protocol; otherwise it stays blocked.
