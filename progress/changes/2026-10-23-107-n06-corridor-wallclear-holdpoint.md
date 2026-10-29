# #107 N06 corridor wall-clear motion and source-gate result

对话摘要：[N06 r32 wall-clear holdpoint](../../collaboration/dialogues/2026-10-23-107-n06-corridor-wallclear-holdpoint.md)

## Result

- Added r32 profile `config/components/simulation/n06_x_holdpoint_wallclear_slow.json`, changing only the maximum observation retreat versus r31. Fixture truth reached x=−2.600431m and ended x=−0.803939m, without contacting the x=−3.0m wall. Localization and depth health remained valid in the captured run.
- The optional archived/live fail-closed goal gate ran. Snapshot-01 and -02 each had exact fused-source camera poses and all three raw predicates free. Snapshot-03 was fresh and same identity, but its source stamp was 4.191s beyond the last recorded camera pose.
- The live MapStatus remained ready/fresh, but body, first sweep and hold sphere requests returned `no_fresh_fused_depth`. Status showed 2 pending depth pairs; source inspection identifies the likely strict-pending precondition in the read-only sphere service. This is a supported inference, not direct request-time proof.
- No EGO goal was published; graph had no control nodes/topics. N06 remains in progress.

## Verification

- `bash tools/run_n04_map_layout.sh n06-20261023-corridor-r32 corridor_box_column 95 motion_n06 config/components/simulation/n06_x_holdpoint_wallclear_slow.json` — exit 0; snapshots and gate report produced; cleanup confirmed.
- Profile integral: endpoint −0.800000m, terminal speed 0, peak 0.108167m/s.
- Existing `bash tools/project.sh test` result remains PASS (251 tests plus navigation-adapter integration); no source code changed in r32.

Artifacts: [#107 evidence](../evidence/n06-corridor-wallclear-holdpoint-20261023-107.md), [machine report](../evidence/n06-corridor-wallclear-holdpoint-20261023-107.json), [r32 run](../../artifacts/runs/n06-20261023-corridor-r32/).

## Continuation

N06.10 adds a third-party patch after 0041 so the read-only raw-sphere endpoint reads the last completed fusion while new input is pending, consistent with the existing full-curve checker. Source-age, occupancy-age, epoch/map/frame, pose-timeout and raw unknown/occupied/outside checks stay in force. The recorder window increases to 160 wall seconds to cover the measured snapshot-03 pose gap. Then rerun the same sensor route and planner-only goal.
