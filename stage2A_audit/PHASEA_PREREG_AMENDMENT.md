# Phase A Preregistration Amendment

**Registered:** 2026-11-16 16:05 +05:30  
**Status:** registered before any new Phase A comparison  
**Applies to:** [PHASEA_PREREG_A.md](./PHASEA_PREREG_A.md)

The audit grouping unit is filename families, not verified patient or slide IDs.

The preregistration's reproduction hypothesis used an incorrect precision
criterion by comparing a full-precision mean to the rounded report value
`0.9153` at `1e-12`. The already-saved report and `test_metrics.json` show the
reported value is rounded to four decimal places, while its saved full-
precision value is `0.9153306335833998`.

The reproduction criterion is therefore:

- The recomputed 50-image macro Dice must match the saved full-precision
  `test_metrics.json` value within absolute tolerance `1e-12`.
- The recomputed value, rounded to four decimal places, must equal `0.9153`.
- Report the signed difference from the literal rounded value `0.9153`.

No test comparison or new evaluation was run before this amendment.
