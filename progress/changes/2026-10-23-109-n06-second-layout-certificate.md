# #109 N06.2.1 wall-layout certificate

对话摘要：[N06.2.1 r34 second-layout certificate](../../collaboration/dialogues/2026-10-23-109-n06-second-layout-certificate.md)

## Changes

- Added `config/components/simulation/n06_x_visibility_recorded_slow.json`, reusing the r29 wall-layout sensor motion and `(0,+0.6,0)m` candidate while extending input recording to 160 wall seconds and enabling the strict snapshot/live goal certificate.
- Ran r34 in `wall_box_column`. All three source-matched snapshots and live body/sweep/terminal-hold predicates were raw free; EGO's 45-query full-curve certificate was free and generated one planner-only B-spline.
- Updated CURRENT and execution-plan summaries. The two-layout forward curve evidence now exists in r33 corridor and r34 wall. N06 remains in progress because hold/handoff and the fault-rejection matrix remain open.

## Verification

- `bash tools/run_n04_map_layout.sh n06-20261023-wall-r34 wall_box_column 97 motion_n06 config/components/simulation/n06_x_visibility_recorded_slow.json` — exit 0; cleanup confirmed.
- Build and 251-test regression remain the #108 results; #109 changed only a simulation profile and progress records.
- Evidence: [#109 report](../evidence/n06-second-layout-live-ego-certificate-20261023-109.md), [machine report](../evidence/n06-second-layout-live-ego-certificate-20261023-109.json), [r34 artifacts](../../artifacts/runs/n06-20261023-wall-r34/).
