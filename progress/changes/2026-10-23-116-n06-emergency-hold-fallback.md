# #116 N06.2.5 emergency hold fallback and N06.2.6 layout revalidation

**Dialogue:** [task summary](../../collaboration/dialogues/2026-10-23-116-n06-emergency-hold-fallback.md)
**Evidence:** [report](../evidence/n06-emergency-hold-fallback-20261023-116.md), [machine summary](../evidence/n06-emergency-hold-fallback-20261023-116.json), [#115 diagnostic](../evidence/n06-emergency-hold-reachability-20261023-115.md)

## Changes

- Added patch 0043 under the pinned EGO source to enter EMERGENCY_STOP on raw map obstruction of an active curve and attempt a stationary hold only through the existing freshness, identity, body and terminal-hold certificate. Stale, identity, query and resource failures retain fail-closed behavior.
- Registered patch order/hash and included the new patch in actual-layout run input hashes.
- Extended tools/probe_ego_safety.py with active-obstacle, blocked-hold, completed-hold and stale-map result reporting.
- Revalidated the patched binary on the previously qualified +0.25 m corridor route and on the wall two-goal handoff. The +0.6 m corridor route remains refused when its continuous body sweep intersects occupied map cells.

## Validation

- python3 tools/fetch_dependencies.py --source ego_planner --target /tmp/ego-planner-n06-0043-replay — pass; locked upstream and ordered patches reconstructed with verified source hashes.
- colcon build --base-paths src/vendor/ego_planner/planner --packages-select ego_planner --cmake-clean-cache --cmake-args -DCMAKE_BUILD_TYPE=Release — pass.
- bash tools/project.sh test — pass: 251 tests plus navigation-adapter integration.
- EGO component cases #116/#118/#119/#120: certified emergency hold, blocked hold refusal, stale-map fail-closed, and completed-curve terminal hold; zero late curves.
- Actual layouts #122 wall and #123 corridor: three source-matched raw occupancy snapshots each; full body sweep and terminal hold free; current EGO full-curve certificates free. #122 logs the active replan handoff.
- Actual corridor #121: +0.6 m sweep intersects occupied cells; no goal curve published.
- python3 tools/project_status.py, shell/JSON/AST checks, docker cleanup and git diff --check are recorded in the completion turn.

## Limits and next step

Planner publication is not trajectory execution. N06 is complete at its planner-integration exits; P6/S4, N05 takeoff/landing qualification, dynamic braking under N08, and final A-H acceptance remain open. The next mainline dependency is N07, whose first action must preserve the N05 no-go boundary.
