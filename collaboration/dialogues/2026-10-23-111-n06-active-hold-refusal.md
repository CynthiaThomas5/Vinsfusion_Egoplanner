# #111 N06.2.2 active and terminal-hold refusal

- **User constraint:** Resume Goal completion mode for N06; keep PX4, bridge, controller, trajectory execution and real flight out of scope until N06's original exits are supported.
- **Task:** Verify active-curve map-change and completed terminal-hold fail-closed behavior, wrong-map refusal, query classes and late-curve suppression.
- **Decision:** Use `tools/probe_ego_safety.py` with isolated EGO/plan_env and synthetic depth, then associate current adapter/resource regressions without presenting synthetic data as actual-layout evidence.
- **Result:** Active map change faulted on unknown before occupied in this run; #093 retains direct occupied-path evidence. Completed hold faulted on occupied. Both probes emitted no late curves. Wrong-map identity and raw query classes passed.
- **Limitation:** No actual-layout replanning/handoff or combined-runtime freshness/query injection was exercised here. N06 remains in progress.
- **Next:** N06.2.3 actual-layout, two-goal replanning handoff with source-matched archive and live map gates, followed by remaining refusal matrix.
