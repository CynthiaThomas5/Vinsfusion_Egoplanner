# #113 N06.2.4 identity/freshness/query/resource matrix

- **User constraint:** Continue Goal completion mode for N06; preserve raw occupancy, map identity and 0.4 s evidence gates. No flight or controller execution in this planner-component probe.
- **Task:** Close current component/interface refusal coverage for identity, stale map, query classes and bounded work, then assess emergency-hold behavior.
- **Changes:** Added wrong-epoch and invalid-radius checks and a stale-depth-after-curve case to `tools/probe_ego_safety.py`; clock and odometry continue during depth loss.
- **Result:** Wrong epoch emitted no curve/fault; wrong map was refused before any occupancy query. Active unknown, completed terminal-hold occupied and stale occupancy each failed closed, with no late curves. Current-source tests covered query/sweep resource bounds and adapter stale/timeout/late/cancel/busy cases.
- **Open:** No `EMERGENCY_STOP` transition or emergency-hold B-spline occurred. The stale map gate refused first. N06 remains in progress.
- **Next:** N06.2.5 isolate emergency-stop/hold planner behavior without weakening freshness or occupancy gates.
