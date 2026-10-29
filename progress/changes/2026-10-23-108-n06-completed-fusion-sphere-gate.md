# #108 N06.10 completed-fusion sphere gate

对话摘要：[N06.10 r33 completed-fusion sphere gate](../../collaboration/dialogues/2026-10-23-108-n06-completed-fusion-sphere-gate.md)

## Changes

- Added EGO patch `0042-query-last-completed-fusion.patch`. The read-only sphere endpoint now calls `queryReadiness(..., false)`, matching the existing full-curve certifier's last-completed-fusion behavior. Identity, frame, source/update age, pose health, raw unknown/occupied/outside, and query-failure checks stay enforced.
- Registered patch order, SHA-256, replay context, and final vendor file hash in `dependencies/sources.json`; documented the active EGO chain in both dependency READMEs.
- Added `config/components/simulation/n06_x_holdpoint_recorded_slow.json`. It keeps r32 motion and target unchanged and extends only recording from 150 to 160 wall seconds, covering the measured r32 source-pose gap.
- r33 passed all three archived snapshot certificates, live body/sweep/hold queries, and EGO's 22-query full-curve certificate, then generated one planner-only B-spline without faults or a control path.
- Updated N06 progress and evidence references. N06 remains in progress; this run does not complete the two-layout, handoff, or fault matrix.

## Verification

- `bash tools/project.sh build` — PASS, 17 packages; existing `ConstPtr` deprecation warnings only.
- `bash tools/project.sh test` — PASS, 251 tests plus navigation-adapter integration.
- `python3 tools/fetch_dependencies.py --source ego_planner --target /tmp/ego-planner-n06-r33-20261023` — PASS; fresh patch replay produced the locked `grid_map.cpp` hash.
- `bash tools/run_n04_map_layout.sh n06-20261023-corridor-r33 corridor_box_column 96 motion_n06 config/components/simulation/n06_x_holdpoint_recorded_slow.json` — exit 0; cleanup confirmed.
- Evidence: [#108 report](../evidence/n06-completed-fusion-sphere-gate-20261023-108.md), [machine report](../evidence/n06-completed-fusion-sphere-gate-20261023-108.json), [r33 artifacts](../../artifacts/runs/n06-20261023-corridor-r33/).
