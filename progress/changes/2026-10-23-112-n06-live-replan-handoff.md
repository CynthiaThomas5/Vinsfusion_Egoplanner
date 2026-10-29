# #112 N06.2.3 live EGO replan handoff

**Dialogue:** [#112 task summary](../../collaboration/dialogues/2026-10-23-112-n06-live-replan-handoff.md)
**Evidence:** [report](../evidence/n06-live-replan-handoff-20261023-112.md), [machine summary](../evidence/n06-live-replan-handoff-20261023-112.json)

## Changes

- Extended `tools/probe_n06_live_layout.py` to optionally certify and publish a replacement goal only after its own source-matched snapshot, live map identity/freshness, body, continuous sweep and terminal-hold gates pass.
- The probe records curve endpoints, goal/trajectory IDs and FSM replan transitions from the mapping-stack log. It requires an actual `EXEC_TRAJ -> REPLAN_TRAJ` transition and a changed trajectory ID for a passing handoff.
- Extended `tools/run_n04_map_layout_container.sh` to pass an optional handoff offset from the profile; added `config/components/simulation/n06_x_visibility_handoff_recorded_slow.json` with first target `+0.6 m y` and replacement target `+0.9 m y`.
- Added an explicit wait for same-epoch odometry within the existing 0.4 s freshness threshold. No freshness limit or occupancy policy changed.

## Validation

- Python AST parse, runner `bash -n`, and profile JSON parse: pass. `py_compile` could not write its bytecode into the workspace's existing `__pycache__`; the no-write AST parse was used instead.
- `bash tools/project.sh test`: pass, 251 unit tests and navigation-adapter integration.
- r35: fail-closed before publishing because the sampled odometry age was 0.566 s; all snapshot/raw route gates passed. VINS output continued in the mapping log, so root cause is not asserted.
- r36: pass. Three same-identity snapshots and both target raw predicates passed; live EGO emitted goal IDs `f241102f4f384c49869540924fea4cdb` / `60b1691690d84e8c9b34f20c42193dec` and trajectory IDs 1 / 2. The FSM log confirms active replanning; full-curve certificates were free, with no faults or control graph endpoints.
- Runtime command: `bash tools/run_n04_map_layout.sh n06-20261023-wall-r36 wall_box_column 100 motion_n06 config/components/simulation/n06_x_visibility_handoff_recorded_slow.json` — exit 0, cleanup confirmed.

## Limits and next step

Both curves were planner-only and were not executed. N06/S4 remain `in_progress`; emergency hold behavior and combined failure-matrix coverage remain open. Continue at N06.2.4.
