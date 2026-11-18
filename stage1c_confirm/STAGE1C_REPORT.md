# Stage 1c — confirmation-test plan and read-only audit

**Report timestamp:** 2026-11-13T10:00:58+05:30  
**Scope:** local catalog and existing Stage 1b output audit; confirmation plan only.  
**Stage 1 Gate A:** **FAIL** (unchanged). Stage 1b is **exploratory, post-hoc** (unchanged).

## 1. Extra open Visium data audit

I compared the `Spatial Transcriptomics Visium` rows in `D:\patent\atlas_repository_filelist-20261105.csv` against the 28 participant IDs in the Stage 1b participant metrics. **12 participants outside the existing 28** have both an open expression-matrix row and an open spatial-imaging-data row:

| Participant | Open expression matrix (catalog size) | Open spatial bundle (catalog size) | Same-sample Visium TIFF candidate (catalog size) |
|---|---|---|---|
| 164-10 | `b3444b1a-f7f0-42c6-a3fd-6794920b329c_expression_matrix.zip` (2.59 MB) | `4d750d76-a6bb-478b-99c5-929831ee79cd_spatial_V14B09-279_XY04_25-0277.tar.gz` (7.07 MB) | — |
| 164-22 | `8c12e227-a959-4009-9879-fe131bfa87ab_expression_matrix.zip` (14.7 MB) | `38b3728e-2369-47aa-b4b6-fc809ccaf03b_spatial_V13Y22-309_XY01_23-0158.tar.gz` (14.3 MB) | — |
| 27-10123 | `5f4d81bf-8f28-4e3c-b3f4-ec46f141b4fc_expression_matrix.zip` (6.86 MB) | `003bc7fd-f40c-4783-a8d2-fc2ae8fa3f52_spatial_V13M27-060_XY01_23-0142.tar.gz` (10.2 MB) | `0f26f7b9-d744-4594-b177-b3c421fee9f5_V13M27-060_XY01_23-0142.tif` (1.28 GB) |
| 27-10166 | `e01e6294-dbe5-4de7-95dd-4e93c6bc41d5_expression_matrix.zip` (3.03 MB) | `53f19705-f8b2-4b5a-96d0-a71597c0195e_spatial_V14Y20-275_XY04_24-0189_fl.tar.gz` (8.31 MB) | — |
| 27-10229 | `313e6afc-c7da-4309-821c-42b649878c34_expression_matrix.zip` (9.6 MB) | `ff7c69e4-5b78-42be-bcab-b0f42845c48e_spatial_V14S09-326_XY04_24-0195.tar.gz` (10.2 MB) | — |
| 29-10277 | `2a30da95-47c8-47f5-9ed7-8f5feb9266df_expression_matrix.zip` (8.64 MB) | `f9ca163d-c9f4-4163-9e59-e143fbc64303_spatial_V13J17-332_XY01_23-0119.zip` (9.82 MB) | `5c595c55-fd30-4e86-8f51-f582f541a5ec_V13J17-332_XY01_23-0119.tif` (355 MB) |
| 29-10282 | `deb3c13e-b49f-4812-9932-3760a3f20dd8_expression_matrix.zip` (8.31 MB) | `db0c2b08-f356-4847-9e47-99adcd3eae6a_space_ranger_outs_29-10282.zip` (286 MB) | — |
| 30-11081 | `78815e28-7ece-4bc3-a908-83df225678de_expression_matrix.zip` (10.4 MB) | `0cdf9bf2-83e9-4c16-a3e6-7bfa4b4962bb_spatial_V12U21-009_XY03_22-0089.zip` (12.4 MB) | `f1b51328-529b-4e6f-be9b-861a7ac588f0_V12U21-009_XY03_22-0089.tif` (1.27 GB) |
| 34-11042 | `52dfa91b-54e4-4aa7-9452-22ff0cd3a547_expression_matrix.zip` (4.22 MB) | `acbaa880-3c57-431a-9c1d-45e892205240_spatial_V13L19-321_XY02_25_0245.tar.gz` (8.91 MB) | — |
| 34-11048 | `b3264217-69e5-43f0-9d8e-35b4e9db76ae_expression_matrix.zip` (5.59 MB) | `83baad2a-864e-4047-93d4-b1f6fe8b7fa0_spatial_V13L19-321_XY01_25_0244.tar.gz` (8.78 MB) | — |
| 933-10271 | `f9991c00-fa12-4c53-b1f5-0207b6ac0dcf_expression_matrix.zip` (7.04 MB) | `3067a14f-73c6-4f0f-a9cc-7f2e25cf6cc4_spatial_V14Y20-295_XY04_24-0174_fl.tar.gz` (9.47 MB) | `eee229e5-4e0d-4016-b9c5-5ff04ed1e8e1_V14Y20-295_XY04_24-0174_fl.tif` (1.34 GB) |
| 933-11258 | `28560640-6e3d-44dd-a43d-87368e3bd6c6_expression_matrix.zip` (11.3 MB) | `a5880135-d18a-4e75-bbc5-73f659d4f589_spatial_V14B09-278_XY03_25-0272.tar.gz` (10.6 MB) | `41679d29-a8d7-41a5-98d1-00e5819f348f_V14B09-278_XY03_25-0272.tif` (1.36 GB) |

The 24 expression-matrix and spatial-bundle rows total approximately **488.34 MB** using the catalog's rounded sizes. Five same-sample `.tif` records are also listed under the Visium strategy; adding them gives 29 candidate files and approximately **6.09334 GB**. The TIFF role/resolution is not specified in those catalog rows, so they are called candidates rather than verified hires images. Whole-slide-image and FASTQ rows, cloupe files, and metadata workbooks were excluded.

At the final audit check, D: had **117,831,102,464 bytes (about 117.83 GB) free**. The full catalog-size estimate fits, leaving about **111.74 GB**. This is a physical free-space comparison, not approval to download. Four TIFFs individually exceed 1 GB and require explicit approval before any download. The overall project 10 GB cap remains unresolved; Stage 0 already recorded that the existing project exceeds it.

**License and terms:** the catalog marks these files `open`. Twenty asset rows cite DOI collection [10.48698/16dd-vj20](https://doi.org/10.48698/16dd-vj20); one of those rows also cites [10.48698/3z31-8924](https://doi.org/10.48698/3z31-8924). Both KPMP DOI collection pages state **Creative Commons Attribution 4.0 International (CC BY 4.0)**, which requires attribution and indication of changes. Nine rows have no DOI in the catalog, so their file-specific license is not verified here. `Access=open` alone is not treated as a license. The complete file-by-file audit, including sizes, access, format, workflow, and DOI, is [open_visium_extra_assets.csv](open_visium_extra_assets.csv).

The catalog lists each spatial archive's formats as `h5 jpg csv png json` and workflow as `Spatial Imaging Data`. Because this task prohibited extraction, I did **not** verify the archive members or confirm that every bundle contains `tissue_positions`, `scalefactors`, and a hires image. The TIFF-to-spatial-bundle association is by participant and matching Visium sample identifier only; its exact image role remains unverified.

## 2. Stage 1b module driver check

This is a read-only reanalysis of Stage 1b's existing per-participant spot Spearman table; no model was fitted. For a focused driver assessment and the planned primary hypothesis, the tables below show the image-only `mlp_spot` model. The supplementary [module_driver_participant_rhos.csv](module_driver_participant_rhos.csv) contains participant-sorted rho values for this model, both Ridge baselines, Elastic Net, and image-plus-depth models. Leave-one-out (LOO) means and percentile 95% participant-bootstrap CIs resample participants (10,000 draws, seed 20261113). Each table reports the range over the 28 separate omissions.

| Target variant | Module | Mean Spearman (95% bootstrap CI), n=28 | Positive participants | LOO mean range | LOO CI lower-bound min to upper-bound max | All 28 LOO CIs above zero? |
|---|---|---:|---:|---:|---:|---|
| depth_residualized | ECM/collagen | 0.069 (0.035, 0.103) | 20/28 | 0.063–0.074 | 0.029–0.107 | Yes |
| depth_residualized | myofibroblast/profibrotic | 0.114 (0.087, 0.140) | 27/28 | 0.108–0.120 | 0.083–0.144 | Yes |
| depth_residualized | matrix-remodelling | 0.043 (0.026, 0.061) | 22/28 | 0.039–0.046 | 0.023–0.064 | Yes |
| depth_residualized_neighbor_mean | ECM/collagen | 0.094 (0.051, 0.137) | 21/28 | 0.086–0.103 | 0.044–0.145 | Yes |
| depth_residualized_neighbor_mean | myofibroblast/profibrotic | 0.195 (0.149, 0.239) | 26/28 | 0.187–0.205 | 0.143–0.247 | Yes |
| depth_residualized_neighbor_mean | matrix-remodelling | 0.080 (0.046, 0.116) | 22/28 | 0.073–0.087 | 0.039–0.122 | Yes |

### Per-participant Spearman values (sorted by rho)

Each entry is `participant_id=rho`, rounded to three decimals. The CSV retains full precision.

**depth_residualized — ECM/collagen (20/28 positive):**  
28-12265=-0.084; 936-10217=-0.083; 27-10371=-0.067; 30-11141=-0.038; 31-10078=-0.031; 29-10394=-0.015; 32-10205=-0.010; 934-10007=-0.004; 31-10340=0.004; 28-12557=0.015; 934-10003=0.024; 30-10125=0.029; 27-10157=0.030; 34-11066=0.066; 29-10400=0.081; 28-12626=0.087; 30-11192=0.091; 30-11197=0.091; 33-10005=0.146; 29-10439=0.155; 27-10228=0.156; 29-10422=0.157; 27-10206=0.157; 27-10201=0.163; 27-10207=0.186; 27-10262=0.200; 30-11084=0.205; 31-10013=0.214.

**depth_residualized — myofibroblast/profibrotic (27/28 positive):**  
936-10217=-0.060; 33-10005=0.013; 28-12557=0.024; 29-10394=0.032; 29-10422=0.047; 27-10371=0.053; 30-11197=0.053; 27-10157=0.069; 27-10201=0.070; 34-11066=0.089; 30-10125=0.100; 934-10003=0.102; 30-11141=0.104; 27-10262=0.107; 31-10078=0.115; 32-10205=0.118; 27-10207=0.145; 28-12626=0.149; 31-10340=0.151; 29-10439=0.152; 30-11192=0.160; 28-12265=0.171; 27-10206=0.174; 30-11084=0.177; 29-10400=0.181; 934-10007=0.193; 27-10228=0.218; 31-10013=0.276.

**depth_residualized — matrix-remodelling (22/28 positive):**  
27-10201=-0.036; 29-10439=-0.020; 31-10340=-0.017; 936-10217=-0.015; 30-11141=-0.014; 27-10157=-0.007; 28-12626=0.002; 934-10003=0.015; 27-10371=0.015; 29-10394=0.017; 34-11066=0.022; 30-10125=0.025; 28-12557=0.025; 29-10400=0.045; 28-12265=0.047; 32-10205=0.056; 30-11192=0.057; 31-10078=0.059; 29-10422=0.062; 27-10262=0.063; 33-10005=0.066; 934-10007=0.071; 30-11197=0.081; 27-10228=0.084; 27-10206=0.086; 30-11084=0.129; 27-10207=0.139; 31-10013=0.155.

**depth_residualized_neighbor_mean — ECM/collagen (21/28 positive):**  
28-12265=-0.147; 27-10371=-0.066; 33-10005=-0.058; 936-10217=-0.043; 29-10394=-0.033; 31-10078=-0.017; 32-10205=-0.008; 934-10007=0.021; 30-11141=0.025; 34-11066=0.056; 28-12557=0.059; 934-10003=0.063; 27-10157=0.068; 31-10340=0.073; 30-10125=0.081; 27-10207=0.098; 28-12626=0.098; 27-10201=0.117; 31-10013=0.134; 29-10400=0.154; 30-11197=0.166; 30-11192=0.212; 30-11084=0.224; 29-10422=0.234; 29-10439=0.247; 27-10228=0.275; 27-10206=0.295; 27-10262=0.299.

**depth_residualized_neighbor_mean — myofibroblast/profibrotic (26/28 positive):**  
30-11141=-0.077; 936-10217=-0.032; 29-10394=0.033; 34-11066=0.073; 28-12557=0.079; 30-11197=0.095; 30-10125=0.115; 27-10201=0.122; 27-10207=0.129; 27-10371=0.144; 27-10157=0.150; 33-10005=0.152; 29-10400=0.176; 31-10078=0.190; 27-10262=0.198; 32-10205=0.203; 29-10422=0.222; 30-11084=0.224; 934-10003=0.250; 28-12626=0.255; 27-10206=0.277; 31-10340=0.324; 31-10013=0.332; 30-11192=0.344; 29-10439=0.351; 28-12265=0.353; 934-10007=0.369; 27-10228=0.397.

**depth_residualized_neighbor_mean — matrix-remodelling (22/28 positive):**  
28-12265=-0.092; 29-10394=-0.063; 30-11141=-0.055; 934-10003=-0.039; 27-10157=-0.033; 31-10078=-0.015; 33-10005=0.004; 34-11066=0.008; 30-11084=0.018; 27-10371=0.037; 29-10400=0.054; 30-10125=0.080; 936-10217=0.086; 27-10201=0.089; 28-12626=0.091; 934-10007=0.098; 31-10340=0.103; 32-10205=0.112; 27-10207=0.114; 28-12557=0.119; 29-10422=0.128; 31-10013=0.136; 30-11192=0.147; 29-10439=0.179; 27-10228=0.186; 27-10262=0.212; 30-11197=0.254; 27-10206=0.294.

### Driver interpretation for the proposed primary comparison

In Stage 1b, `mlp_spot` for the neighbor-smoothed myofibroblast/profibrotic module had paired mean Spearman difference **+0.231** versus depth-only (n=28; bootstrap 95% CI **+0.136 to +0.329**) and **+0.067** versus color-only (n=28; **+0.002 to +0.133**). This motivated the narrow Stage 1c hypothesis, but it remains post-hoc.

For the candidate model's raw rho, every single-participant omission retained a positive mean and a 95% CI above zero (LOO means **0.187–0.205**; envelope of LOO CI endpoints **0.143–0.247**). Across all 378 pairs of omitted participants, the candidate raw-rho mean remained positive. Thus one or two people do not drive the positive raw association.

The paired advantage over depth-only was less sensitive: all 28 LOO CIs remained above zero (LOO mean range **0.210–0.250**); after the two most adverse omissions (`27-10228`, `31-10013`), the paired mean was **+0.191**, CI **+0.102 to +0.277**. The paired advantage over color-only was more fragile: all 378 two-participant-deletion means remained positive (minimum **+0.041**), but the worst pair (`31-10013`, `31-10078`) had CI **−0.021 to +0.099**; some single-deletion CIs also crossed zero. Therefore no pair reverses the mean sign, but small-sample uncertainty around the color-only advantage is sensitive to which participants are omitted. See [module_driver_loo_summary.csv](module_driver_loo_summary.csv) and [primary_driver_robustness.csv](primary_driver_robustness.csv) for the full calculations.

## 3. Confirmation protocol

The timestamped, pre-run protocol is [PREREG_CONFIRM.md](PREREG_CONFIRM.md). It fixes one primary hypothesis: on the 12 new participants only, the frozen ResNet-50 spot embedding plus the Stage 1b 128-unit MLP will outperform both color-only Ridge and depth-only Ridge for the neighbor-smoothed, depth-residualized myofibroblast/profibrotic module.

The MLP will be trained on the original 28 participants only, for one fixed epoch (the median Stage 1b selected epoch for this exact target/model). New participants are held out from every fitting and tuning operation. Primary success requires at least 10 eligible new participants and a 10,000-resample participant-bootstrap 95% CI for candidate-minus-baseline Spearman entirely above zero against **both** baselines. If either CI includes zero or fewer than 10 participants are eligible, the conclusion is no confirmation / inconclusive; no post-hoc target/model substitution is allowed.

Other modules, unsmoothed targets, Elastic Net, image-plus-depth models, genes, and spatial blocks are explicitly secondary and exploratory.

## 4. What could not be verified and stop condition

- The spatial archive member lists, including exact `tissue_positions`, `scalefactors`, and hires-image presence, were not checked because no extraction was allowed.
- The standalone TIFF roles and resolutions are not stated in the catalog; sample association is based on participant ID and matching Visium sample identifier.
- Nine candidate asset rows have no DOI in the catalog, so file-specific license terms could not be confirmed. Collection-level CC BY 4.0 is verified only for assets linked to the two cited DOI collections.
- No new cohort files were locally opened or checked for data completeness, quality, participant/library key reconciliation, or compatibility with Stage 1 processing. The stated 12 are catalog candidates, not verified usable samples.
- Catalog sizes are rounded; totals are approximate. No download was performed, and physical-space fit does not resolve the project-wide 10 GB storage cap.
- No new model, embedding, target, or test metric was generated. The report's Stage 1b correlations are re-summaries of existing outputs only.

**Stop here.** Stage 1c is an audit and preregistration only. Wait for explicit instruction before downloading, extracting, or running the confirmation test. No registration or fusion was performed or recommended. Stage 1 Gate A remains **FAIL**; Stage 1b remains **exploratory, post-hoc**.

## Files created

- `STAGE1C_REPORT.md` — this report.
- `PREREG_CONFIRM.md` — timestamped confirmation protocol.
- `README.md` — output inventory, methods, and environment versions.
- `LAB_NOTEBOOK.md` — dated append-only audit decisions and scope.
- `open_visium_extra_assets.csv` — exact catalog rows for expression and relevant spatial assets for the 12 additional participants.
- `module_driver_participant_rhos.csv` — participant Spearman values for all six models shown, both target variants, and all three modules.
- `module_driver_loo_summary.csv` — participant-bootstrap mean/CI and all leave-one-participant-out summaries.
- `primary_driver_robustness.csv` — paired primary Stage 1b comparison and leave-one-/leave-two-participant sensitivity.
