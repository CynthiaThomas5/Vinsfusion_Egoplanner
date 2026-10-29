# #113 N06.2.4 identity/freshness/query/resource refusal matrix

**Dialogue:** [#113 task summary](../../collaboration/dialogues/2026-10-23-113-n06-failure-matrix.md)
**Evidence:** [report](../evidence/n06-freshness-identity-resource-refusal-20261023-113.md), [machine summary](../evidence/n06-freshness-identity-resource-refusal-20261023-113.json)

## Changes

- Extended `tools/probe_ego_safety.py` with wrong-epoch rejection, invalid-radius query classification, and a stale-map-after-curve scenario that stops depth while continuing simulated clock and odometry.
- The report now captures FSM transitions, emergency-stop observation and number of curves associated with the active goal.
- No production safety threshold, map policy or planner behavior was changed.

## Validation

- `python3` AST parse of `tools/probe_ego_safety.py`: pass.
- `bash tools/project.sh test`: pass, 251 tests plus navigation-adapter integration, including raw sphere and swept-curve bounded-work probes.
- Three isolated component cases in ROS domain 102: active-map unknown rejection; completed terminal-hold occupied rejection; stale-map refusal. Each passed, with zero late curves. The wrong-epoch command produced no curve/fault; wrong-map produced `full_curve_map_id_mismatch` with zero map queries.
- Depth interruption produced `full_curve_occupancy_update_stale`, then `full_curve_depth_pose_gate_closed` for a later goal. No emergency-stop transition or hold B-spline was observed.
- Container cleanup confirmed; unrelated service containers were preserved.

## Limits and next step

Component evidence does not prove a real-layout or actuator response. Emergency-stop/hold remains open. Next: isolate the emergency planner path with existing interfaces while keeping freshness and collision policy unchanged.
