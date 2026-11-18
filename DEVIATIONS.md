# Deviations and Execution Log

This ledger records the known implementation changes, retries, and skipped work across the current project stages. It is not a claim that the procedures were deviation-free. Stage 1d events are reconstructed from its saved report and execution history; some historical before-edit hashes were not retained, as explicitly recorded below.

## Stage 1d confirmation

### D-001 — Download retry after interrupted transfer

- **Event:** The first transfer stopped after 13 of 24 authorized files following a connection reset. The downloader was changed to validate existing manifest entries, resume the remaining files, read response chunks with `read1`, and retry failed transfers. The same 24 catalogued files and URLs were used; no additional data types were fetched.
- **Outcome:** All 24 expression/spatial files completed. The final downloader SHA-256 recorded in the Stage 1d report is `e8bb41507af7b36b3b865ef9c5b552f57180a449020ad1e1bdd8bf7197e2aeb1`.
- **Before hash:** Not recorded at the time of the retry. This was an operational retry before confirmation model application.

### D-002 — Input-format compatibility fixes before frozen inference

- **Event:** The frozen confirmation loader was adjusted to recognize prefixed Matrix Market member names by their standard suffixes and to read the frozen feature-name list from the `features_in_order` JSON field. These changes addressed input representation only; they did not alter model, target, normalization, cohort, or decision rules.
- **Outcome:** Inference proceeded with the frozen artifacts. Final script SHA-256 recorded in the Stage 1d report: `ee11e4075c63b5de1d531feb6bf1e96c5a190f49a033ccfefefb92ce14f0dab9`.
- **Before hash:** Not recorded before these pre-inference fixes.

### D-003 — Fresh-process verifier serialization fix

- **Event:** The first fresh-process verification attempt failed while serializing a NumPy boolean. The value was converted to a native boolean, and verification/report finalization was rerun from saved predictions and metric outputs; model inference was not rerun or refit.
- **Outcome:** The saved predictions were independently checked; the Stage 1d report records a maximum absolute metric difference of `8.33e-17`.
- **Before/after hashes:** The intermediate pre-fix and post-fix script hashes were not preserved at the time. The final `run_frozen_confirmation.py` hash recorded in the report is `ee11e4075c63b5de1d531feb6bf1e96c5a190f49a033ccfefefb92ce14f0dab9`. This is a historical script-integrity logging gap, not evidence that the protocol was changed.

### D-004 — Post-result report/output corrections

- **Event:** After metrics had been generated, the report finalization code was corrected to provide a header for the empty exclusion CSV and to display the explicit `FAIL` decision label. The report was regenerated from existing outputs; primary metrics, bootstrap settings, and the decision rule were not changed.
- **Before/after hashes:** The exact intermediate hashes at the time of these edits were not retained. The final script hash recorded in the report is `ee11e4075c63b5de1d531feb6bf1e96c5a190f49a033ccfefefb92ce14f0dab9`. This is a historical P2 logging gap.

### D-005 — Bootstrap summary discrepancy and wording clarification

- **Event:** A fresh recomputation from `primary_participant_metrics.csv` using a different bootstrap implementation produced a different lower-bound value for the `mlp_spot - depth_only_ridge` comparison than the saved `primary_comparison_summary.csv`. The retained confirmation code in `stage1d_confirm/run_frozen_confirmation.py` uses a single `np.random.default_rng(BOOTSTRAP_SEED)` instance, reused sequentially across both comparisons, without reseeding between them. The summary file was reproduced exactly using that retained logic.
- **Outcome:** The discrepancy was resolved by matching the exact script logic rather than substituting a different RNG stream. No model parameters, metrics, or decision labels were changed. The phrase “preregistered Elastic Net” in the Stage 1d report was corrected to “exploratory Elastic Net” to reflect the preregistered distinction between required primary analyses and exploratory secondary analyses.

## Stage 2A

The preregistration was completed before the dataset audit; its SHA-256 and read-only state are recorded in `LAB_NOTEBOOK.md`.

### D-006 — Segmentation training skipped at Gate 2A-1 / licence blocker

- **Skipped:** No preprocessing, training, or evaluation was run. RENFAST's Mendeley licence field is blank, and the KPMP segmentation packages document network-generated outputs with pathologist QC rather than direct expert masks. The KPMP IFTA provenance is also contradictory.
- **Reason:** There is no dataset currently meeting both the expert-mask provenance and verified-use-terms requirements. Proceeding would require either assuming RENFAST reuse rights or misclassifying KPMP outputs as expert ground truth.
- **Outcome:** Stage 2A stops at the data audit. The options and evidence are recorded in `stage2A_audit/BLOCKER.md`. No data were downloaded, no package was installed, and the preregistration was not amended.

### D-007 — Stage 2C/2D analysis held before data access

- **Skipped:** No development-table construction, image embedding extraction, model fitting, permutation test, or power analysis has been run. `stage2C_redesign/TRIAL_LEDGER.csv` contains only its header.
- **Reason:** The locked Stage 2C preregistration selects Phikon-v2; its official model card states an Owkin non-commercial licence. Project eligibility/authorization is unconfirmed. P8 requires stopping when licence acceptance cannot be completed by the assistant.
- **Outcome:** No model weights or participant data were downloaded for this stage; no validation data were accessed. `stage2C_redesign/BLOCKER.md` records the issue. The Stage 2C preregistration was not changed.
