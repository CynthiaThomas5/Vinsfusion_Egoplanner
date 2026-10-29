# N11 #491 offline estimator/RPE review

This read-only review uses the archived #491 raw VINS pose, truth, velocity, and native estimator telemetry with the frozen N11 evaluators. It does not modify runtime behavior, acceptance limits, or control inputs.

## Findings

- The aggregate goal-motion RPE failed at 0.106189 m. Its P95 was 0.112488 m in the first 10 seconds, then below 0.023 m in each complete later bin.
- In the high-RPE first bin, median tracked-input and continued-track counts were 103 and 79. In the following passing bin they were 106 and 78. Later counts increased while RPE remained low. The native solver was usable, state-finite, and current on all 808 goal frames; solve time P95 ranged from 11.1 to 15.9 ms and waiting features/span stayed at zero. These observations do not support feature starvation or queue backlog as the cause.
- Per-residual-family cost breakdown was absent for all captured frames. A healthy solver flag and feature count cannot establish that visual correspondences or the resulting pose increments were unbiased.
- Shifting truth timestamps by up to ±200 ms did not make the run pass. The best tested result was 0.078328 m at +200 ms. The best velocity-error shift changed its P95 only from 0.015555 to 0.015366 m/s.
- The pose-increment versus integrated-velocity comparison is not a root-cause discriminator: similar or larger mismatch appears in previous RPE-PASS runs. It is retained as an exploratory consistency result only.
- Fail intervals move between runs: #488 first 20 seconds, #490 20–30 seconds, and #491 first 10 seconds. No single repeated temporal pattern is established.

The next useful experiment is one exact revision9 formal attempt without the supplemental telemetry subscription. This checks whether the extra observer contributed to the higher resource use or receipt-ledger gap, while also providing the next independent cold start. The required GUI window listing must be written before goal dispatch. If RPE fails again under the uninstrumented baseline, retain all failures and pursue a specific estimator/input hypothesis before further repeats.

Reproducible scripts and numerical output are in [`artifacts/n11-prepared/n11-20261029-491-formal06`](../../artifacts/n11-prepared/n11-20261029-491-formal06); the compact evidence record is [n11-estimator-diagnostics-20261029-491.json](n11-estimator-diagnostics-20261029-491.json).
