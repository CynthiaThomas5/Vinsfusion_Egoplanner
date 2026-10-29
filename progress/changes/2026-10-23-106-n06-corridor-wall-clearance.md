# #106 N06 corridor wall collision and holdpoint iteration

对话摘要：[N06 r31 wall-clearance diagnosis](../../collaboration/dialogues/2026-10-23-106-n06-corridor-wall-clearance.md)

## Changes

- `tools/run_sensor_motion.py`: support finite, positive explicit phase durations while retaining the existing `phase_seconds` path; tolerate floating-point phase-end rounding and reject profiles whose `stop_seconds` omits a phase.
- `tools/test_motion_tools.py`: verify unequal-duration rest-to-rest motion, phase-count validation, and raw unknown rejection in sphere and continuous-sweep queries.
- `tools/probe_n06_live_layout.py`: add a fail-closed optional gate requiring three fresh same-identity archived snapshots with exact fused-source camera poses; all archived and live body, sweep and terminal-hold predicates must be raw free before the planner-only goal can publish.
- `tools/run_n04_map_layout_container.sh`: keep the input recorder alive through all three snapshots, then run the profile-selected target through the optional snapshot gate.
- `config/components/simulation/n06_x_holdpoint_slow.json`: r31 one-axis profile, source recorder duration and certificate-gated `(0,+0.25,0)m` target.

## Verification and run

- `bash tools/project.sh test` — PASS, 251 unit tests and navigation-adapter integration.
- In-memory Python compilation, `bash -n tools/run_n04_map_layout.sh tools/run_n04_map_layout_container.sh`, JSON parse, and profile ideal integration — PASS; predicted x=−0.800000 m, terminal velocity 0, peak speed 0.120000 m/s.
- Run command: `bash tools/run_n04_map_layout.sh n06-20261023-corridor-r31 corridor_box_column 94 motion_n06 config/components/simulation/n06_x_holdpoint_slow.json`.
- r31 did not reach a snapshot: fixture truth contacted the generated back wall at x=−2.987523 m; localization then became invalid (`normalized_cost_exceeded` at 149.755 s), and snapshot-01 timed out with `map_reset_acknowledged`. The runner never invoked the gated probe; no EGO goal was sent.
- Structure check, final diff checks and worktree status are recorded after the r32 run in the current task report.

Artifacts: [#106 evidence](../evidence/n06-corridor-wall-clearance-20261023-106.md), [r31 run directory](../../artifacts/runs/n06-20261023-corridor-r31/).

## Limits and continuation

The failed run does not pass N06.8 or N06/S4. The back-wall collision is confirmed by matching the measured fixture center to the generated wall face plus the D435i housing half-length; no map or unknown-space behavior is implicated. N06.9 / r32 changes only the excursion endpoint from −3.2 m to −2.6 m, keeping the same final holdpoint and certificate gate. Continue with the original N06 exits after this bounded iteration; do not advance `next_goal`.
