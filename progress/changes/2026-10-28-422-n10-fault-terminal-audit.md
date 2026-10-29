# N10-20261028-422 — #415 fault-to-terminal audit

Dialogue summary: `collaboration/dialogues/2026-10-28-422-n10-fault-terminal-audit.md`.

Audited the #415 source/log chain and added current read-only PX4 and Gazebo-truth samples. The current bridge treats PX4 `DESCEND` as landing-active, suppresses another LAND request in that state, and waits indefinitely for `landed && !armed` before entering `LANDED`. #415 remains armed/failsafe DESCEND without land detection after the localization/EGO timeout sequence. The invalid propagated quaternion payload was not preserved, so its source is unknown and no code-level estimator fix is justified yet.

Artifacts: `n10-live-fault-state-probe-r11.json` (SHA-256 `17c9d57b1731128f2d31af0b349489136101f3e0d80a6e8622d3a8293212ca88`), `n10-live-gz-pose-probe-r11.json`, and final `n10-live-fault-state-probe-r12.json` (SHA-256 `7a6281f27d4abd18f61e424d6a63999e05d03df17ef58f26860772882fbecef6`). The pose probe observed near-ground altitude but does not prove contact or PX4 terminal state. The monitoring probes received no command-topic events and published none.

Validation: reviewed source paths in `control_state.py`, `px4_bridge_node.py`, `uav_navigation/node.py` and the #415 log extract; parsed r11/r12 and truth-probe JSON files and verified hashes. No source/config changes, control commands, tests, or flight actions were performed.
