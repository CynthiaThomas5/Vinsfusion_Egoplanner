# #115 N06.2.5 emergency-hold trigger diagnostic

**Scope:** Isolated EGO/plan_env component with synthetic depth and a synthetic peer trajectory. No Gazebo, VINS, PX4, bridge, world truth, controller, or flight.

## Result

The probe received the peer trajectory, but the fixture did not change occupancy on the active curve. EGO kept finding certified curves on the same route. During the three-second observation window the FSM logged 32 same-state EXEC_TRAJ to EXEC_TRAJ safety/replan transitions and 33 published curves. It observed neither EMERGENCY_STOP nor a constant-position hold spline. The report is therefore a failed trigger diagnostic, not a passing emergency-hold test.

This run did not show that the emergency path was unreachable for a map-blocked curve; it showed that a same-path peer is not a discriminating fixture for that condition. The next probe changed raw depth occupancy on the active path and separately covered a blocked stationary hold. Freshness, identity, unknown-space, and query gates stayed enabled.

## Verification and artifacts

- Probe command: python3 tools/probe_ego_safety.py --swarm-emergency
- Structured result: [result.json](../../artifacts/runs/n06-20261023-emergency-115/probe/result.json), SHA-256 725b3822e099d55d9b43e85c386a66da0aa9aa41d77f6cf624fc98118dd496d9.
- Planner log: [planner.log](../../artifacts/runs/n06-20261023-emergency-115/probe/planner.log), SHA-256 a90490c1919d676bfa5f96a5b3200d70b8103909f14aef5f6b749670e54736a6.
- The fixture returned acceptance_passed=false; no safety behavior is claimed from this run.

## Continuation

Use a changed active-path occupancy input to exercise the exact blocked-curve branch. Keep the hold certificate fail-closed, and distinguish a planner-published stationary spline from physical stopping.
