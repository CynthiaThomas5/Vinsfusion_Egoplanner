# #284 N08 trial refused by stale runtime-script fingerprint

Run: `n08-cancel-translation-prescan-20261026-284`. This was a pre-action refusal, not a flight attempt.

The 40.002 s read-only navigation preflight and fresh same-run N05 current-area online/offline admission passed. The movement runner then stopped before bridge enable because it compared `tools/run_n08_braking_trial.py` against the historical #276 compiled-build source list. That list records runner SHA `039478bbf28dac2ff40ddaf49ff447d5d5e55eaf910789b7a859841364eca344`; the valid #282 Python runner SHA was `c35b3adad8121c9548678e19e6402b467c2e303e4893ad2f3ce6cfe18e4bcc66`. This Python-only fix did not change compiled sources or installed binaries, whose #276 fingerprints remain unchanged.

The run produced no `n08-trial-pre-enable-admission.json`; the read-only planner observer saw 0 messages; no navigation goal, enable, or flight was sent. A fresh independent N05 readback still accepted the same epoch/map with bridge `DISABLED`, PX4 disarmed and landed, and localization valid. The project container was stopped. The wrapper's later odometry evaluator error on incomplete, non-monotonic source stamps is secondary and contains no flight data.

Correction: compiled sources remain checked against #276. The Python runner is authenticated against a hash captured in the cold-run runtime manifest; `tools/runtime_manifest.py` now records non-test Python and shell tools.

Machine-readable facts and hashes: [#284 report](n08-runtime-source-fingerprint-refusal-20261026-284.json).
