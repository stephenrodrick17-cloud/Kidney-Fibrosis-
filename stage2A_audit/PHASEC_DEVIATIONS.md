# Phase C Deviations

## 2026-11-16 — DeepLab batch-normalization compatibility

The first training-only preflight failed before any registered model training or test-pixel access. In torchvision `0.22.1+cu118`, the DeepLabV3 ASPP global-pooling branch applies `BatchNorm2d` to a `[1, 256, 1, 1]` tensor with the registered Phase A batch size of one, which raises a runtime error.

For the timing preflight only, the ASPP global-pooling sub-branch was put in evaluation mode so its 1x1 BatchNorm operation could be timed with batch size one. This is a compatibility workaround that would be needed if a future DeepLab run with batch size one were explicitly approved. No DeepLab optimizer update or checkpoint was produced. The preregistered architecture, data split, seed, thresholds, metrics, and success rules are unchanged.

An initial split-label mismatch was also detected before any data pixels were read: the saved manifest uses `official_test` rather than `test`. The runner now maps that saved label to the registered test split without altering assignments. The failed preflight did not save model weights or read test pixels.

## 2026-11-16 — DeepLab runtime budget

The corrected training-only preflight estimated the maximum 100-epoch runtime at **8,070.79 seconds** for the registered DeepLabV3-ResNet50 run, exceeding the **7,200-second** limit. That run is blocked and will not be launched. The same preflight estimated each registered U-Net run at **1,350.43 seconds**, below the limit; only those two U-Net ensemble-member runs may proceed. The DeepLab threshold will not be selected and no test comparison against DeepLab will be reported; the registered stronger-baseline comparison is blocked.

## 2026-11-16 — Direction-summary correction and inference warning

After the registered outputs were visible, review found that the first grouped robustness summary combined the two directional rows for paired perturbations while displaying the first direction's label. The per-image source rows and paired per-image means were correct; the paired-mean estimates used for the level-level rule are unchanged. A separate direction-aware summary was generated from the saved per-image rows, and `PHASEC_robustness_summary_corrected.csv` is the canonical combined summary. The conservative direction-level check identifies two additional failing comparisons (saturation `0.40`, brightness `0.50`).

Inference emitted PyTorch's read-only NumPy-array warning for transformed images. The analysis source was updated to copy inference inputs before conversion to tensors. This did not change image values, model weights, metric definitions, thresholds, or success rules. A synthetic read-only input check confirmed exact equality of the tensor and logits. The independent three-metric verification had already matched exactly; this maintenance edit is listed in `PHASEC_INTEGRITY_CHECK.md`.
