# GENE2 Verification — EXPLORATORY, NOT CONFIRMATORY

**RESEARCH-ONLY — saved ResNet-50/ImageNet features.**

## Independent recomputation from saved out-of-fold predictions

| Headline value | Recomputed value | Check |
|---|---:|---|
| Primary paired mean difference | -0.020747018651 | MATCH |
| Primary 95% CI lower bound | -0.13005740517 | MATCH |
| Primary 95% CI upper bound | 0.0859326809899 | MATCH |
| Image participant-macro Spearman | 0.115375966663 | MATCH |
| Image pooled region Spearman | 0.131449372476 | MATCH |
| Image region MAE | 0.455770432931 | MATCH |

Paired participants: 40; saved OOF regions: 4635.

## Fold, key, and output verification

- paired_delta_mean: MATCH (-0.020747018651)
- paired_delta_ci95_low: MATCH (-0.13005740517)
- paired_delta_ci95_high: MATCH (0.0859326809899)
- image_participant_macro_spearman: MATCH (0.115375966663)
- saved_primary_mean: MATCH (-0.020747018651)
- saved_primary_ci_low: MATCH (-0.13005740517)
- saved_primary_ci_high: MATCH (0.0859326809899)
- outer/inner fold overlap: PASS (participant, library, and region grouping)
- eligible spot-key coverage: PASS (31880 unique full keys)
- eligible region coverage: PASS (4635 regions)
- Preregistered main nested-CV fits: 810; selected-model label-shuffle fits saved across the five completed outer folds: 20; completed fit calls from failed attempts: 10; total actual fit calls: 840. The preregistered maximum was 830; any overage is disclosed as a deviation.
- Largest recorded individual fit: 8.44 seconds; longest inner command: 47.82 seconds; longest outer command: 17.94 seconds.
- The failed first outer-fold-0 attempt did not save its fit-duration or command-duration record; its exact runtime is **NOT AVAILABLE**. It failed during output assembly after all 10 fit calls had completed. The maxima above cover saved successful-fold records.
- Finalize analysis command: 4890.26 seconds; output size: 137608601 bytes (1-GB cap).
- No GENE2 checkpoint weights were saved; this nested-CV run has no final frozen model, so frozen-GENE2-weight hash verification is **NOT APPLICABLE**. The frozen Stage 1d model and ResNet checkpoint were not loaded or changed; only saved feature arrays were used.
- Preflight source hashes were rechecked. Any changed hashes were limited to the runner or the listed preregistration/deviation/licence documents, which were updated before or after this run; current hashes are listed below.

## Environment and seeds

- Python `3.13.1`; NumPy `2.2.6`; pandas `3.0.6`; SciPy `1.18.1`; scikit-learn `1.6.1`.
- PyTorch `2.7.1+cu118`; torchvision `0.22.1+cu118`; MLP device: `NVIDIA GeForce RTX 3050 Laptop GPU (CUDA available)`.
- Outer participant folds `20261120`; MLP `20261121`, `20261122`, `20261123`; paired bootstrap `20261124`; label shuffle `20261125`; secondary sign-flip `20261126`.

## Exact commands

```text
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py preflight
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold 0 --inner-fold 0
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold 0 --inner-fold 1
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold 0 --inner-fold 2
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold 0 --inner-fold 3
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold 1 --inner-fold 0
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold 1 --inner-fold 1
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold 1 --inner-fold 2
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold 1 --inner-fold 3
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold 2 --inner-fold 0
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold 2 --inner-fold 1
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold 2 --inner-fold 2
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold 2 --inner-fold 3
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold 3 --inner-fold 0
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold 3 --inner-fold 1
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold 3 --inner-fold 2
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold 3 --inner-fold 3
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold 4 --inner-fold 0
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold 4 --inner-fold 1
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold 4 --inner-fold 2
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py run-inner --outer-fold 4 --inner-fold 3
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py fit-outer --outer-fold 0
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py fit-outer --outer-fold 1
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py fit-outer --outer-fold 2
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py fit-outer --outer-fold 3
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py fit-outer --outer-fold 4
C:\Users\asus\python.exe D:\patent\stage_G2\GENE2_RUNNER.py finalize
```

## SHA-256 of source and analysis files read

| File | SHA-256 |
|---|---|
| `D:\patent\data\27-10157\visium\outs\spatial\tissue_hires_image.png` | `c5a6eebd191ea83b75c0633f7d196b19cbc3a5ff646d362ce9bebbdb799cc4a1` |
| `D:\patent\data\27-10201\visium\outs\spatial\tissue_hires_image.png` | `d7680f992e07f53dcb07a46fd4241eb10ea834c228914e6d272015c5651d1126` |
| `D:\patent\data\27-10206\visium\outs\spatial\tissue_hires_image.png` | `60a555a754178f2610dd21f55771f5ab367db5cfc6bf9087cbf42aae9e43095f` |
| `D:\patent\data\27-10207\visium\outs\spatial\tissue_hires_image.png` | `2bd2723cf4bdf71a5355b6b481e1e4ed6af2b379cbea71b9ffcc4c47f8f7de05` |
| `D:\patent\data\27-10228\visium\outs\spatial\tissue_hires_image.png` | `ff8f3c6241e1ef865ddb76de9369f6d932da4dbc5dd109672a83da20a5503e83` |
| `D:\patent\data\27-10262\visium\outs\spatial\tissue_hires_image.png` | `e9a6f46790e2f7bbe802f72a5cca4988b617a23e19774c2a521a2b0dbda7805a` |
| `D:\patent\data\27-10371\visium\outs\spatial\tissue_hires_image.png` | `33ac39d459167d07da778a744b38e9405ddcc1432ff53d11341efb71dd33c3b5` |
| `D:\patent\data\28-12265\visium\01e4bee9-72ce-4538-a086-3adc593e2181_space_ranger_outs_28-12265-M_extracted\nfs\corenfs\pathology-kpmp\PROD_INBOX\e3674410-aca1-42cf-88a7-daebccee1968\outs\spatial\tissue_hires_image.png` | `545529ce271b7375ddf040fb77fde8de4ce8b581407cfd79e995106ffa8d642b` |
| `D:\patent\data\28-12265\visium\cf0c92b2-2808-403a-8612-e59d5d195913_space_ranger_outs_28-12265-C_extracted\nfs\corenfs\pathology-kpmp\PROD_INBOX\f02e6164-8bb9-4a3b-bd61-5839b9f99243\outs\spatial\tissue_hires_image.png` | `c20ae478d940c56a7771440facdc08e2f48d30c689637815d2726b6921cf358b` |
| `D:\patent\data\28-12557\visium\outs\spatial\tissue_hires_image.png` | `9dce56e87cfb0d3b1379d8c085b1da914859cad9353299f5484987b66896215e` |
| `D:\patent\data\28-12626\visium\outs\spatial\tissue_hires_image.png` | `78c6ec945ae5de68897c7ceb7b6c9ac82a913230e66972bd921ee8be43abe7a4` |
| `D:\patent\data\29-10394\visium\outs\spatial\tissue_hires_image.png` | `a6dbf50754f07d976a1e081912d5131426ce7d9da197ccdc8f110f85a81ac38e` |
| `D:\patent\data\29-10400\visium\outs\spatial\tissue_hires_image.png` | `dabead458f1b41b58877a4992db58de33f32a2139484e62d9fa40e63420f6fcc` |
| `D:\patent\data\29-10422\visium\9c8bd648-43f0-4b0d-94c7-be03ead43386_spatial_V12U21-007_XY03_22-0093_extracted\V12U21-007_XY03_22-0093\outs\spatial\tissue_hires_image.png` | `3c97fd420eb1ad2822e08553007474718b4c20d3886429baceaed9271044185d` |
| `D:\patent\data\29-10439\visium\outs\spatial\tissue_hires_image.png` | `343d73d06a5d1ab995388481ad50f0513a08ad23a9744f8f1308e72e7c9ebcca` |
| `D:\patent\data\30-10125\visium\a858efbd-c119-40bf-9080-17227e2564ce_space_ranger_outs_30-10125_extracted\nfs\corenfs\pathology-kpmp\PROD_INBOX\e8efde0d-cf06-46b5-8fb3-a264b1730f19\outs\spatial\tissue_hires_image.png` | `f725aa1afa3a28a5cc7e8e6543820a2d00a28474bbbfedd1f5b0f23762d13265` |
| `D:\patent\data\30-11084\visium\599babf2-a4a0-4d53-9cb8-26563ed35dce_spatial_V12U06-350_XY03_22-0097_extracted\V12U06-350_XY03_22-0097\outs\spatial\tissue_hires_image.png` | `11e41a1f4c16a908b34b4193b60205c61fee33ccb62da82b885620b1474dd56d` |
| `D:\patent\data\30-11141\visium\outs\spatial\tissue_hires_image.png` | `9b33dd9ecf58f6c1101033fc0824fe85b2e2ced32fc4353e80b713a0212de686` |
| `D:\patent\data\30-11192\visium\outs\spatial\tissue_hires_image.png` | `f25065cf4e6c7acfae1d0411b3e8706abec7ce4101c218e16a3d53c9f702e709` |
| `D:\patent\data\30-11197\visium\outs\spatial\tissue_hires_image.png` | `335cf5d01cbcd04e1dd2889b78ee0aed65cb14d84bc7af2784d60b4c1ea1a0d7` |
| `D:\patent\data\31-10013\visium\outs\spatial\tissue_hires_image.png` | `32ea59f6e4924c5500569c303846a3c22a2be3590e82df636ce9c60980d24132` |
| `D:\patent\data\31-10078\visium\outs\spatial\tissue_hires_image.png` | `0f7152dc91851e23f522428d890515617a6a8cf4e022122a139ba4c74b89488d` |
| `D:\patent\data\31-10340\visium\outs\spatial\tissue_hires_image.png` | `46d85fc3e274d0fb4ba1e8e6472362da565330ff3573475e22473c8ead086b46` |
| `D:\patent\data\32-10205\visium\876dab9e-d4a0-4855-bd03-32587ca842a2_spatial_V12N14-057_XY02_23-0116_extracted\V12N14-057_XY02_23-0116\outs\spatial\tissue_hires_image.png` | `66c0cc249fadca1f0ba4b32fdd844aae01d5ce11ee65584d705643e970fbe9b1` |
| `D:\patent\data\33-10005\visium\e33dc3ae-a248-403e-95f4-7f6f2c693787_spatial_V12N14-057_XY01_20-0042_extracted\V12N14-057_XY01_20-0042\outs\spatial\tissue_hires_image.png` | `fc02b6c935a2f78fd17a89d067fbe78df70edd128b68b815e7fbb048cbddf55d` |
| `D:\patent\data\34-11066\visium\outs\spatial\tissue_hires_image.png` | `aeebe4234f99bd971d2184ce8848f9d280de0fe07a168ef4776176ef1be0a090` |
| `D:\patent\data\934-10003\visium\outs\spatial\tissue_hires_image.png` | `3be74db9ae427588cd62efbbf743b5a9e9d080ece88453f8e57ca6de4c1e15f8` |
| `D:\patent\data\934-10007\visium\outs\spatial\tissue_hires_image.png` | `1aac378c2bdf8836ce4cdfda9baa12c1495b08b848608bd796cb7c6b8008ede8` |
| `D:\patent\data\936-10217\visium\outs\spatial\tissue_hires_image.png` | `7b668ffa2071528870d87bb1556a6ec009e858449ac7f7f4aa205d801a380c57` |
| `D:\patent\stage1_expression\color_statistics.npz` | `f0d5d4ecf14f646f8347ba2374bc645f22973d1e824038cac984e2d9736d6264` |
| `D:\patent\stage1_expression\scripts\run_stage1.py` | `fc4a8e1eeee18b79b029aa5ecf1fb97ccf4a99d4fbe11f16a28d2e766a9b8d4c` |
| `D:\patent\stage1_expression\spot_embeddings.npz` | `6130ad5fcdc4bbc3315296e05d58965f290b61bf88e9c3a369844edd870b4183` |
| `D:\patent\stage1_expression\stage1_config.json` | `cbf5c252944f833523ff3c439694e162eb5ecdd6c372042ddbc3d9c65fbb4027` |
| `D:\patent\stage1_expression\targets_by_spot.csv` | `8dade8a328018e49c2c4bc6d5e63aed1347c18d03eba6ce295356add27fd2aa6` |
| `D:\patent\stage1d_confirm\confirmation_predictions.npz` | `a9d99c422deb8dff54394f5181eee5d771383206cc9ad38029c7eef340589e3b` |
| `D:\patent\stage1d_confirm\data_manifest.csv` | `1809c54da6637b03615db59fe810b54c96d20f5ac0d789fe0259a31a7da0b149` |
| `D:\patent\stage1d_confirm\run_frozen_confirmation.py` | `ee11e4075c63b5de1d531feb6bf1e96c5a190f49a033ccfefefb92ce14f0dab9` |
| `D:\patent\stage1d_confirm\spatial_mapping_qc.csv` | `e378871ef3e448e1846b7822d2b4667bc3d7cd81aacbeccc260529b77eec27b0` |
| `D:\patent\stage1d_freeze\residualization_parameters.csv` | `d3be232fc951b36b33fccf68ecfe4c6d4e6d2914e4015208d58084ce2d9c5157` |
| `D:\patent\stage_G2\GENE2_ALIGNMENT_AUDIT.csv` | `c60450356e9a83f600de8f6a0bdf34baa9be8d088efcee6f39624ffbd561f10e` |
| `D:\patent\stage_G2\GENE2_DEVIATIONS.md` | `677fb318225386bc59781aba3ca332c8acc5dc42c5754b54376c5486bde920d8` |
| `D:\patent\stage_G2\GENE2_FOLD_MEMBERSHIP.csv` | `485328e1510715f30c81236629d54c2ece7701a8a52fe45955c219ba08195fad` |
| `D:\patent\stage_G2\GENE2_INNER_O0_I0.csv` | `6ea2c5bfdbdfb6ced7f95af94f8c1d8f1c55562a0863fad3cd8ce7cf7c30ed6d` |
| `D:\patent\stage_G2\GENE2_INNER_O0_I1.csv` | `fe804e970405278ad39d080602182da0a4568ba8bb79430f9bcd6931cabf0548` |
| `D:\patent\stage_G2\GENE2_INNER_O0_I2.csv` | `86c589cca27a3e1007280e867c788e7c8b247d72dc462d35feeddfa7cbc034fa` |
| `D:\patent\stage_G2\GENE2_INNER_O0_I3.csv` | `369411822d3b1d21c74fbacd58ba14ca5a035c964bd67409cf7b7ce879175e28` |
| `D:\patent\stage_G2\GENE2_INNER_O1_I0.csv` | `9cace4fe43f23c0f68e5775fb6cd75135a55a6de4bdf654594f161b8b27ebcf3` |
| `D:\patent\stage_G2\GENE2_INNER_O1_I1.csv` | `27add0770b0b5d79f9e0185f07d04a8f0942591651bdf792da5462ba8993fc11` |
| `D:\patent\stage_G2\GENE2_INNER_O1_I2.csv` | `e24c759caff84848ed502dd8a09c246188fe4699a100faeb9eb812c81e8cf86a` |
| `D:\patent\stage_G2\GENE2_INNER_O1_I3.csv` | `4281946b80f67ae6311f43b8b09710ad4e807d937b3d9668a6c97878ab860513` |
| `D:\patent\stage_G2\GENE2_INNER_O2_I0.csv` | `d2f848fd22cb10815dce66dbe720fb92081bc0fa693653028c0eb8fee68027b5` |
| `D:\patent\stage_G2\GENE2_INNER_O2_I1.csv` | `45213e2b6c84dbf0d810cfed7859933be64ecdbb850dada4c80ec371672479a7` |
| `D:\patent\stage_G2\GENE2_INNER_O2_I2.csv` | `fcba83d00cefe8ca6a5c129326887aac2cc1ceba402286ceff256d2c9a7a131a` |
| `D:\patent\stage_G2\GENE2_INNER_O2_I3.csv` | `1f1e920e26b2c87f2dbfdfb181e2934b53662620796a865674e6d02626558c76` |
| `D:\patent\stage_G2\GENE2_INNER_O3_I0.csv` | `0b10b59a151aefbe323932013b4de4373f68c701fea3b1b215c26dcc79d26f73` |
| `D:\patent\stage_G2\GENE2_INNER_O3_I1.csv` | `9ae7ad146dc5212221bb2095e618eea4645eea6414428c3b62541ea2135a5a06` |
| `D:\patent\stage_G2\GENE2_INNER_O3_I2.csv` | `90af591bdf9ee0b465df8ce5ee7039c0c063866cc905f9d92020347686108921` |
| `D:\patent\stage_G2\GENE2_INNER_O3_I3.csv` | `518fe1c79d62e2badfebd67f1c736b53bbf65cce63795e06f70056b33dcd6733` |
| `D:\patent\stage_G2\GENE2_INNER_O4_I0.csv` | `1ef55ece29d4b34cfb99981d2e463e5e799b4ae5fc8064fc38c35d259173418c` |
| `D:\patent\stage_G2\GENE2_INNER_O4_I1.csv` | `2c0a7f0f5a3ef186dfcc1659775ab08ceaae1336eb5f89fe20736bcd2d503b46` |
| `D:\patent\stage_G2\GENE2_INNER_O4_I2.csv` | `b31c0ef275efc59cf8697ad01c8138aab042eebf83446cc8baad24db2991c33e` |
| `D:\patent\stage_G2\GENE2_INNER_O4_I3.csv` | `71f954e6a2aedb5b2ee3f25c86287530d9339925da488c811617ed8cc2ec0734` |
| `D:\patent\stage_G2\GENE2_LABEL_SHUFFLE.csv` | `0bfc4ad8c30d37b2e893d4cb34d7d98c277965af4fad3419307e0b8a5706b9ac` |
| `D:\patent\stage_G2\GENE2_LICENCE_NOTE.md` | `e1c43bd06c7903f656f24223643402b1aaa35a4973b016da9777e04a61b4187b` |
| `D:\patent\stage_G2\GENE2_METRIC_SUMMARIES.csv` | `545274a654e8b5866bbf4f66ec42dc0326f780bc8aaef258761416a76df1fcce` |
| `D:\patent\stage_G2\GENE2_OOF_REGION_PREDICTIONS.csv` | `5058f79a74d6f917c81534663b2a3707403bc80bf38e89df040a8f89056e5424` |
| `D:\patent\stage_G2\GENE2_OOF_SPOT_PREDICTIONS.csv` | `57fdc31f154208f16b20a07990f9a74ef6de4b0b0c7bf3474de85945229912af` |
| `D:\patent\stage_G2\GENE2_OUTER_FOLD_0.csv` | `9978d0471f39165cb367356d9a207fc6b9819b09858d3cc878b57eb12ff4a400` |
| `D:\patent\stage_G2\GENE2_OUTER_FOLD_1.csv` | `26c9332a1d85b8219a02889c598a8c0da44bd7fd4fcb3965272e946d65e7caf5` |
| `D:\patent\stage_G2\GENE2_OUTER_FOLD_2.csv` | `142fcf9a6164e852225f982bda7e66c3ee1477283aee62e213bd851df8e59527` |
| `D:\patent\stage_G2\GENE2_OUTER_FOLD_3.csv` | `bc3439226975e8905040151bf1b2756b3142d2041d7181c6b0c7cc43c349226f` |
| `D:\patent\stage_G2\GENE2_OUTER_FOLD_4.csv` | `88d8b20a863df991e623d7933244494d55d7fea91575bdd6b7461fcd09922eb7` |
| `D:\patent\stage_G2\GENE2_PARTIAL_CORRELATIONS.csv` | `1261a4eced8a522b27646dd718beaf3e4530b068eb401f6ee56b853df7c9d5bb` |
| `D:\patent\stage_G2\GENE2_PER_PARTICIPANT_SPEARMAN.csv` | `0c633b8c60c125059d74d45a5908b307ceab520dab01c987f9acad3e54fe99ca` |
| `D:\patent\stage_G2\GENE2_PREFLIGHT.json` | `ee9c3e32f2f7207f63823bcba1418baba26e71c24776bdd5921559e8adb5a288` |
| `D:\patent\stage_G2\GENE2_PREREG.md` | `6a98c4375d3543f4b8a7dbaf0febbfc48e9031e3156a56388ffefbc49aeafcd7` |
| `D:\patent\stage_G2\GENE2_PRIMARY_ENDPOINT.csv` | `c7f0353fa9916abd9de1a6de8c5b821d5a4e320e768e904d7cf9ff5c1c32e955` |
| `D:\patent\stage_G2\GENE2_REGION_DATA.npz` | `186161ad231aac758c884163fd4e36f96a91d0bc52b17a22ef67fe0bfd2f3447` |
| `D:\patent\stage_G2\GENE2_RESULTS.md` | `ab277df479529942001ca0718b5b996a43941e4c25ac19ba153486fe03432082` |
| `D:\patent\stage_G2\GENE2_RETRY_ACCOUNTING.json` | `e10ed4534998fe0a651f3b12a43d75022ef78a0122dae771a664befc2d41e9b6` |
| `D:\patent\stage_G2\GENE2_RUNNER.py` | `764693c290dd76b9f63fcb1034d0face36fcd4ad582ebb0d79eba24a34726eeb` |
| `D:\patent\stage_G2\GENE2_SANITY.md` | `48442c320fcb3b71dc9a622c08a8b94591403797361e61d09f4929e4b210d5c0` |
| `D:\patent\stage_G2\GENE2_SECONDARY_HOLM.csv` | `482c9fe6d48b3cb368614a69d906761d68087d6ac8ae0b6d9e905589c00a0037` |
| `D:\patent\stage_G2\GENE2_SELECTION_O0.json` | `d4ee5942c7114ef19d2188fdbdddb5e1e555d3693386d1b48c48c360c34195d9` |
| `D:\patent\stage_G2\GENE2_SELECTION_O1.json` | `ab2bcde5d4217c8d5d96651b66461590363ae1176619a747efb5fd85e4a57b35` |
| `D:\patent\stage_G2\GENE2_SELECTION_O2.json` | `3e4161c04d6397c76a352026b21273151cee299d27af86f3a722aafef15e19b8` |
| `D:\patent\stage_G2\GENE2_SELECTION_O3.json` | `2e8085526ff8199774400d70c808b5707dbad850c8df8e1b7a50a6f52914e5d3` |
| `D:\patent\stage_G2\GENE2_SELECTION_O4.json` | `26c63d1f78e5a18db03b5e754debc60fa14242e86aeb6991dac7c0d28dd9b25a` |
| `D:\patent\stage_G2\GENE2_SPOT_TARGETS.csv` | `e5b48ac10e826e8908a553122afd16465f83e8b6b13524cb7c926847eced6a01` |
| `D:\patent\stage_G2\GENE2_TARGET_COMPARISONS.csv` | `5759ffdfd12d3695f3fb36ff62306045ccca3dca01eb6f31ff7f46f8a3d6e8f0` |
| `data\27-10157\visium\outs\spatial\tissue_positions.csv` | `d9ea03e0be692535638d52e65d459214fda813d3076fc87a54c5525a031ae834` |
| `data\27-10201\visium\outs\spatial\tissue_positions.csv` | `81d1a4b4a664059d25ce51f5a3a3b54c3f31c0d0be43f56467b264293e40099a` |
| `data\27-10206\visium\outs\spatial\tissue_positions.csv` | `60ee93795e449f0ea8c32714362223262c28a48bce1d4f2277e4412395d05d5d` |
| `data\27-10207\visium\outs\spatial\tissue_positions.csv` | `31efef88463552412f3d1e944d3b12f60b7c6d0928ee2149717635a8029cf6ea` |
| `data\27-10228\visium\outs\spatial\tissue_positions.csv` | `7a299d39356795224cb73ea37660cfb3a754d8cc5c41677fde57f749e7af0435` |
| `data\27-10262\visium\outs\spatial\tissue_positions.csv` | `1b888bdc79b4bd2ce06262cbb81014ed7874b25b2a11a2c396b541cd603246c2` |
| `data\27-10371\visium\outs\spatial\tissue_positions.csv` | `645fe22fe1a82a69eafb442b4ad53d6e06c264c5a1c72256f6f57384b2246bc6` |
| `data\28-12265\visium\01e4bee9-72ce-4538-a086-3adc593e2181_space_ranger_outs_28-12265-M_extracted\nfs\corenfs\pathology-kpmp\PROD_INBOX\e3674410-aca1-42cf-88a7-daebccee1968\outs\spatial\tissue_positions_list.csv` | `60766567c0b59afc8dc306981bfd1fcac9ec977cea3c7172e71d82fbd14e8f39` |
| `data\28-12265\visium\cf0c92b2-2808-403a-8612-e59d5d195913_space_ranger_outs_28-12265-C_extracted\nfs\corenfs\pathology-kpmp\PROD_INBOX\f02e6164-8bb9-4a3b-bd61-5839b9f99243\outs\spatial\tissue_positions_list.csv` | `c54df38ad1e3ec28164ce0adf6f7246edfaef48b07abe7025c82bb5449e908f0` |
| `data\28-12557\visium\outs\spatial\tissue_positions.csv` | `4385061d0a0a4788c95e46741f681d618130600e9ea5845102ef28b1d9a0a517` |
| `data\28-12626\visium\outs\spatial\tissue_positions.csv` | `393daa3449c0e928c6e46322356c5c40ba9f14269dcd788adb99e897d791380a` |
| `data\29-10394\visium\outs\spatial\tissue_positions.csv` | `10b8f6d2d467a626cc17ee18972ebefa66b9493037ccd164515e206b84b1ef82` |
| `data\29-10400\visium\outs\spatial\tissue_positions.csv` | `de9443725c99d433391153809d515cd8e6adff746ae3a4deb8320252251235aa` |
| `data\29-10422\visium\9c8bd648-43f0-4b0d-94c7-be03ead43386_spatial_V12U21-007_XY03_22-0093_extracted\V12U21-007_XY03_22-0093\outs\spatial\tissue_positions_list.csv` | `19b1f17495b86928d9ebd4ccd124e6341d659127d3ce62bd1bf3013204fe9cdc` |
| `data\29-10439\visium\outs\spatial\tissue_positions.csv` | `28c05363ec7a6ebacdf036b4e4d68e4040eaee3c8847bf1a0d74335b9217cd3b` |
| `data\30-10125\visium\a858efbd-c119-40bf-9080-17227e2564ce_space_ranger_outs_30-10125_extracted\nfs\corenfs\pathology-kpmp\PROD_INBOX\e8efde0d-cf06-46b5-8fb3-a264b1730f19\outs\spatial\tissue_positions_list.csv` | `6e1a88d73a6b7a26bee87c633e2b8e975b5d2c40936a2353460d18c20ea9a59d` |
| `data\30-11084\visium\599babf2-a4a0-4d53-9cb8-26563ed35dce_spatial_V12U06-350_XY03_22-0097_extracted\V12U06-350_XY03_22-0097\outs\spatial\tissue_positions.csv` | `7bbc5e529778b208b9c41d30a5546cf4c9368d11bfbafbd8f77f1a59037f9e14` |
| `data\30-11141\visium\outs\spatial\tissue_positions.csv` | `56f6c34964d8945b3b22c97ff43de8c8b1a21745763fe294cd3b9280b240cd72` |
| `data\30-11192\visium\outs\spatial\tissue_positions.csv` | `c72e24f43900acc3f6bd775233a5759f98c17ed3019a05ec49ae76b398764ca0` |
| `data\30-11197\visium\outs\spatial\tissue_positions.csv` | `60b3cb7dd0342cedc2747bcb37c3aa9ffe4e8923bec722fcc7da2a2ff86baab1` |
| `data\31-10013\visium\outs\spatial\tissue_positions.csv` | `14e8df9e8c84313db64f0d09503e3e759154f5491073bed43707faae6ba3f34a` |
| `data\31-10078\visium\outs\spatial\tissue_positions.csv` | `ac51afd8e67d6a61a711105a376c1274b0aa3d62d0a24f386bce7714948bb284` |
| `data\31-10340\visium\outs\spatial\tissue_positions.csv` | `940fa9d70a98ac8e922fac39228315ffd4c8ec5aa8b5ef8a373d290b285263c4` |
| `data\32-10205\visium\876dab9e-d4a0-4855-bd03-32587ca842a2_spatial_V12N14-057_XY02_23-0116_extracted\V12N14-057_XY02_23-0116\outs\spatial\tissue_positions.csv` | `ac7a883f005c77aa5966c66cf556511358763f7022020f56c590fb4292148b60` |
| `data\33-10005\visium\e33dc3ae-a248-403e-95f4-7f6f2c693787_spatial_V12N14-057_XY01_20-0042_extracted\V12N14-057_XY01_20-0042\outs\spatial\tissue_positions.csv` | `bef8f69ed1373326a1f03b680c3df384b1cb272e9849dfb3e0277742e5ea185e` |
| `data\34-11066\visium\outs\spatial\tissue_positions.csv` | `75f082bac923d5ab73b5edaab4f3142b79387f277a84de12a33687861395c5a6` |
| `data\934-10003\visium\outs\spatial\tissue_positions.csv` | `dd8001070b741e4139481df8351bd7e6518ba5fb4e2ec2bbb0568ee1d983cc21` |
| `data\934-10007\visium\outs\spatial\tissue_positions.csv` | `4400bd3d417fbff157fb376af4cbd47ac2b97739e9ffd06b4519beee0357f078` |
| `data\936-10217\visium\outs\spatial\tissue_positions.csv` | `291509c1e4b95abd3719a372663c1053f2f93e4e17bb2a16263dee91a9e5b2b3` |
- Changed since original preflight: `D:\patent\stage_G2\GENE2_DEVIATIONS.md`.
- Changed since original preflight: `D:\patent\stage_G2\GENE2_PREREG.md`.
- Changed since original preflight: `D:\patent\stage_G2\GENE2_RUNNER.py`.
- After finalization, `GENE2_LICENCE_NOTE.md` was updated from pre-run to completed-run status; its current SHA-256 is refreshed above. No input data or prediction outputs changed.
