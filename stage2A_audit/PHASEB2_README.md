# Phase B2 README

**Run date:** 2026-11-16  
**Purpose:** prepare a blinded annotation set and preregistered evaluation plan for 20 regions from Phase B.  
**Scope:** package preparation and synthetic-only analysis-script testing; no training, downloads, or model changes.

## Inputs and registered design

- Input manifest and raw selected tiles: `PHASEB_region_manifest.csv` and `PHASEB_region_images\`.
- Selection seed: `20261119`; 5 regions selected from each of four `colour_stratum` groups using region IDs and stratum labels only.
- Annotator-visible tile size: `512 × 512` RGB PNG; pixel data re-saved without source metadata.
- Participant is the planned bootstrap resampling unit; bootstrap seed `20261120`, 10,000 replicates.
- Checkpoint and colour baseline are frozen Phase B outputs; no model code or weights are loaded or changed by the annotation preparation script.
- No real annotations were available. The analysis script was executed only with `--self-test`.

## Runtime and tool record

- Python 3.13.1
- NumPy 2.2.6
- Pillow 11.1.0
- Recommended annotation tool: GIMP. The official GIMP site links the GNU GPL; its linked `COPYING` text is GNU GPL Version 3. See `PHASEB2_LICENCE_REGISTER.md`. GIMP was not installed or used in this phase.
- No packages were installed and no data were downloaded.

## Commands run

```powershell
& 'C:\Users\asus\python.exe' 'D:\patent\stage2A_audit\PHASEB2_prepare_package.py'
& 'C:\Users\asus\python.exe' 'D:\patent\stage2A_audit\PHASEB2_verify_package.py'
& 'C:\Users\asus\python.exe' 'D:\patent\stage2A_audit\PHASEB2_analyze_annotations.py' --self-test
```

The analysis script's real-data command is documented but **must not be run until annotation is complete and locked**:

```powershell
& 'C:\Users\asus\python.exe' 'D:\patent\stage2A_audit\PHASEB2_analyze_annotations.py' --annotations-dir 'D:\patent\stage2A_audit\PHASEB2_ANNOTATIONS_RETURNED' --output-dir 'D:\patent\stage2A_audit\PHASEB2_ANALYSIS_OUTPUT'
```

Each script refuses to overwrite its named outputs. The analysis outputs will be written only to a new `PHASEB2_ANALYSIS_OUTPUT` directory.
The analysis output directory will contain `PHASEB2_REGION_METRICS.csv`, `PHASEB2_PARTICIPANT_METRICS.csv`, `PHASEB2_INTERANNOTATOR_METRICS.csv`, `PHASEB2_DATA_QUALITY.csv`, and `PHASEB2_ANALYSIS_SUMMARY.json`.

## Phase B2 files

- Protocol: `PHASEB2_PREREG.md`
- Scripts: `PHASEB2_prepare_package.py`, `PHASEB2_verify_package.py`, `PHASEB2_analyze_annotations.py`
- Private key: `PHASEB2_KEY_DO_NOT_SHARE.csv`
- Blinded package: `PHASEB2_ANNOTATOR_PACKAGE\` (20 opaque-ID input PNGs, instructions, return template)
- Held unblinded packet: `PHASEB2_UNBLINDED_REVIEW_PACKET\` (20 input PNGs, U-Net and colour overlays, blank rating form, hold notice)
- Expected annotation return: `PHASEB2_ANNOTATIONS_RETURNED\<annotator_id>\` with `PHASEB2_ANNOTATION_STATUS.csv` and the listed binary masks
- Audit evidence: `PHASEB2_PACKAGE_AUDIT.json`, `PHASEB2_VERIFICATION.json`
- Documentation: `PHASEB2_REPORT.md`, `PHASEB2_LICENCE_REGISTER.md`, `PHASEB2_DEVIATIONS.md`, `PHASEB2_INTEGRITY_CHECK.md`

Every new file name has the `PHASEB2_` prefix. Existing files were not overwritten. Do not send the key or unblinded packet to annotators.
