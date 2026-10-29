# #115 N06.2.5 emergency-hold trigger diagnostic

**Dialogue:** [task summary](../../collaboration/dialogues/2026-10-23-115-n06-emergency-hold-diagnostic.md)
**Evidence:** [report](../evidence/n06-emergency-hold-reachability-20261023-115.md), [machine summary](../evidence/n06-emergency-hold-reachability-20261023-115.json)

## Changes

- Added a peer-trajectory diagnostic mode to tools/probe_ego_safety.py and corrected its timestamps to use the shared ROS simulation clock.
- The mode exposed a weak fixture: the peer did not alter raw occupancy on the active curve, so EGO emitted repeated certified curves instead of entering emergency stop.

## Validation

- python3 tools/probe_ego_safety.py --swarm-emergency — completed; acceptance_passed=false, no emergency stop or stationary hold spline, 32 same-state EXEC_TRAJ transitions and 33 curves.
- This run is retained as a diagnostic and was not counted as a safety pass.

## Limits and next step

The run did not exercise the map-blocked active-curve branch. N06 remains open here. Inject a raw depth obstacle on the active route, certify any stationary hold against the same freshness/identity/raw-map gates, and record blocked-hold refusal separately.
