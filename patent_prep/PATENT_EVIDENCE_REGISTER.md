# Evidence Register

Draft for review by a patent attorney. Plain-language summary only; this is not legal advice.

## What these measurements mean

Ground truth for Phase A was the RENFAST expert-made manual fibrosis masks. The Phase A report notes that annotator identity and independent adjudication were not verified. The test units are filename families, not verified patients or slides. There are 10 test families, which limits precision. No external validation against an independent reference exists.

For Phase A, "image macro" gives equal weight to each image; "family macro" first averages images within each filename family and then gives each family equal weight. Primary 95% CIs resample the 10 test filename families; secondary CIs resample images within each fixed family. For Phase C, the reported CIs resample the 10 test filename families. A CI describes variation under that resampling scheme; it does not establish patient-level performance.

## Phase A clean test

Source for all values in this table: `D:\patent\stage2A_audit\PHASEA_final_metrics.json`. The colour threshold is the frozen `B - R >= 2` rule. The Phase A report uses the same values at a shorter displayed precision.

| Model | Metric | Image macro | Family macro | Primary family-bootstrap 95% CI | Secondary within-family image-bootstrap 95% CI | Resampling unit | What it does NOT show |
|---|---|---:|---:|---|---|---|---|
| U-Net | Dice | 0.9153306335833998 | 0.9119221709930561 | [0.8872443729453038, 0.9340497987561561] | [0.8998038891267194, 0.9229224543701018] | Filename family; secondary view resamples images within each family | Does not show clinical accuracy or performance on verified patients. |
| U-Net | IoU | 0.8484173067065782 | 0.8425865364383514 | [0.8031840172289404, 0.8783522806932251] | [0.8239076393560376, 0.8596293794305807] | Filename family; secondary view resamples images within each family | Does not show clinical accuracy or performance on verified patients. |
| U-Net | Precision | 0.9298397785448145 | 0.9459572199005368 | [0.9255775659344087, 0.9640410127697217] | [0.9335718321233623, 0.9560995176933914] | Filename family; secondary view resamples images within each family | Does not show clinical accuracy or performance on verified patients. |
| U-Net | Recall | 0.9138991282706682 | 0.8911280987663487 | [0.8435059478896895, 0.9336090722236453] | [0.8701373866156433, 0.9112408859088978] | Filename family; secondary view resamples images within each family | Does not show clinical accuracy or performance on verified patients. |
| Colour threshold | Dice | 0.8417142123880947 | 0.824923731160496 | [0.79265735096275, 0.8550585550910383] | [0.8060036805158183, 0.8428896412965697] | Filename family; secondary view resamples images within each family | Does not show clinical accuracy or performance on verified patients. |
| Colour threshold | IoU | 0.7346856588587296 | 0.7094853976975414 | [0.6651366896931149, 0.751638540595113] | [0.684239583706452, 0.7336755597038191] | Filename family; secondary view resamples images within each family | Does not show clinical accuracy or performance on verified patients. |
| Colour threshold | Precision | 0.8245420934120662 | 0.8290850926004147 | [0.810513666761985, 0.848723348517997] | [0.8151275592845325, 0.8413608091046852] | Filename family; secondary view resamples images within each family | Does not show clinical accuracy or performance on verified patients. |
| Colour threshold | Recall | 0.8793571862359024 | 0.8389207108435063 | [0.7760083016621925, 0.9011566993219196] | [0.8079894772960964, 0.8689028796844684] | Filename family; secondary view resamples images within each family | Does not show clinical accuracy or performance on verified patients. |

### Paired Phase A Dice difference

Source: `D:\patent\stage2A_audit\PHASEA_final_metrics.json`. The reported contrast is U-Net minus colour-threshold Dice.

| Result | Exact value | 95% CI | Resampling unit | What it does NOT show |
|---|---:|---|---|---|
| Family-macro paired difference | 0.08699843983256006 | Primary: [0.07315876056020197, 0.09962074456605957]; secondary: [0.07856573117382186, 0.09553955260064735] | Primary: paired filename-family bootstrap; secondary: images within fixed families | Does not establish independent-cohort or clinical performance. |

### Phase A per-family Dice

Source: `D:\patent\stage2A_audit\PHASEA_final_per_group_metrics.csv`. No per-family confidence intervals are recorded, so the CI column is NOT AVAILABLE.

| Filename family | Images | U-Net Dice | Colour-threshold Dice | 95% CI |
|---|---:|---:|---:|---|
| 1004762 | 4 | 0.8842467265272838 | 0.7853120555094167 | NOT AVAILABLE |
| 1004764 | 3 | 0.9196961279668673 | 0.8331258767522671 | NOT AVAILABLE |
| 1004766 | 5 | 0.9427521080098851 | 0.8813378050860242 | NOT AVAILABLE |
| 1004768 | 9 | 0.9468381777599101 | 0.8898962857116864 | NOT AVAILABLE |
| 1004774 | 14 | 0.9298185045788656 | 0.8801251758270308 | NOT AVAILABLE |
| 1004780 | 5 | 0.9088872086166001 | 0.8184338298512909 | NOT AVAILABLE |
| 1004784 | 2 | 0.9276567346240634 | 0.8202237174282703 | NOT AVAILABLE |
| 1004788 | 1 | 0.8680143495928048 | 0.7620798145388309 | NOT AVAILABLE |
| 1004790 | 6 | 0.8317235101978638 | 0.7268355118289147 | NOT AVAILABLE |
| 1004798 | 1 | 0.9595882620564149 | 0.8518672390712274 | NOT AVAILABLE |

These are filename families, not verified patient or slide IDs.

## Phase C robustness

Source for the paired-mean rows and resolution results: `D:\patent\stage2A_audit\PHASEC_REPORT.md`. CIs are 95% filename-family bootstrap CIs. For directional colour changes, the registered paired mean across two directions is shown. The paired change is U-Net Dice minus that model's clean-input Dice.

| Condition | U-Net family Dice [95% CI] | U-Net paired change [95% CI] | Colour-threshold family Dice [95% CI] | Source / note |
|---|---|---|---|---|
| Hue ±5° | 0.9118 [0.8875, 0.9340] | -0.0001 [-0.0005, 0.0002] | 0.8253 [0.7930, 0.8565] | PHASEC_REPORT.md |
| Hue ±10° | 0.9111 [0.8868, 0.9334] | -0.0008 [-0.0016, -0.0002] | 0.8251 [0.7932, 0.8560] | PHASEC_REPORT.md |
| Hue ±20° | 0.9067 [0.8814, 0.9300] | -0.0052 [-0.0083, -0.0028] | 0.8212 [0.7907, 0.8508] | PHASEC_REPORT.md |
| Saturation (0.8, 1.2) | 0.9106 [0.8862, 0.9328] | -0.0014 [-0.0030, 0.0000] | 0.8247 [0.7920, 0.8565] | PHASEC_REPORT.md |
| Saturation (0.6, 1.4) | 0.9059 [0.8806, 0.9287] | -0.0060 [-0.0119, -0.0011] | 0.8245 [0.7913, 0.8567] | PHASEC_REPORT.md |
| Saturation (0.4, 1.6) | 0.8931 [0.8684, 0.9147] | -0.0188 [-0.0303, -0.0081] | 0.8241 [0.7901, 0.8573] | PHASEC_REPORT.md |
| Brightness (0.9, 1.1) | 0.9116 [0.8874, 0.9336] | -0.0003 [-0.0007, 0.0000] | 0.8291 [0.7966, 0.8606] | PHASEC_REPORT.md |
| Brightness (0.75, 1.25) | 0.9098 [0.8869, 0.9305] | -0.0022 [-0.0043, -0.0001] | 0.8349 [0.8023, 0.8668] | PHASEC_REPORT.md |
| Brightness (0.5, 1.5) | 0.8680 [0.8403, 0.8927] | -0.0440 [-0.0568, -0.0319] | 0.8435 [0.8095, 0.8776] | FAIL: paired-change CI lower bound is not greater than -0.05. |
| Contrast (0.9, 1.1) | 0.9114 [0.8870, 0.9338] | -0.0005 [-0.0007, -0.0003] | 0.8251 [0.7925, 0.8567] | PHASEC_REPORT.md |
| Contrast (0.75, 1.25) | 0.9090 [0.8839, 0.9319] | -0.0029 [-0.0038, -0.0021] | 0.8304 [0.7977, 0.8620] | PHASEC_REPORT.md |
| Contrast (0.5, 1.5) | 0.9005 [0.8748, 0.9239] | -0.0114 [-0.0163, -0.0074] | 0.8326 [0.7998, 0.8651] | PHASEC_REPORT.md |
| OD rotation ±5° | 0.9116 [0.8874, 0.9338] | -0.0003 [-0.0006, -0.0001] | 0.8250 [0.7930, 0.8561] | PHASEC_REPORT.md |
| OD rotation ±10° | 0.9107 [0.8867, 0.9327] | -0.0012 [-0.0022, -0.0005] | 0.8239 [0.7924, 0.8544] | PHASEC_REPORT.md |
| OD rotation ±15° | 0.9090 [0.8853, 0.9305] | -0.0029 [-0.0050, -0.0012] | 0.8225 [0.7922, 0.8519] | PHASEC_REPORT.md |
| Resolution 0.50× | 0.8733 [0.8511, 0.8942] | -0.0386 [-0.0431, -0.0345] | 0.8136 [0.7825, 0.8435] | PHASEC_REPORT.md |
| Resolution 0.75× | 0.8895 [0.8665, 0.9108] | -0.0224 [-0.0249, -0.0200] | 0.8192 [0.7878, 0.8493] | PHASEC_REPORT.md |
| Resolution 1.25× | 0.9015 [0.8772, 0.9237] | -0.0104 [-0.0115, -0.0094] | 0.8223 [0.7904, 0.8531] | PHASEC_REPORT.md |
| Resolution 1.50× | 0.9038 [0.8790, 0.9263] | -0.0081 [-0.0098, -0.0065] | 0.8236 [0.7915, 0.8547] | PHASEC_REPORT.md |
| Center crop 256×256 | 0.9157 [0.8875, 0.9395] | 0.0037 [-0.0026, 0.0097] | 0.8213 [0.7903, 0.8539] | PHASEC_REPORT.md |
| Center crop 384×384 | 0.9149 [0.8906, 0.9371] | 0.0030 [0.0017, 0.0043] | 0.8260 [0.7949, 0.8571] | PHASEC_REPORT.md |
| Center crop 512×512 (reference) | 0.9119221709930561 [0.8875951361229354, 0.9341902189786933] | 0.0 [0.0, 0.0] | 0.824923731160496 [0.7924400477282565, 0.8563880421099435] | Corrected summary CSV |

Two additional individual-direction failures are recorded in `PHASEC_REPORT.md` and the corrected `PHASEC_robustness_summary_corrected.csv`:

| Individual direction | U-Net family Dice [95% CI] | U-Net change [95% CI] | Colour-threshold family Dice [95% CI] | Source / note |
|---|---|---|---|---|
| Saturation multiplier 0.40 | 0.8827971665888462 [0.8456848775040513, 0.911930940905988] | -0.029125004404209703 [-0.05711192528376772, -0.004777503524148359] | 0.8257979225112981 [0.7891423328098249, 0.8625916667437791] | Corrected summary CSV; direction fails registered -0.05 lower-bound rule. |
| Brightness multiplier 0.50 | 0.8399839915436932 [0.8080408744378229, 0.8688869327652957] | -0.07193817944936275 [-0.0936262958492087, -0.049966596910506283] | 0.8262898363596289 [0.7910337888721574, 0.8612522347521759] | Corrected summary CSV; direction fails registered -0.05 lower-bound rule. |

The 0.50× resolution condition has a reported U-Net paired Dice change of -0.0386 [-0.0431, -0.0345]. This is a sensitivity result, not a separate claim about physical scale.

