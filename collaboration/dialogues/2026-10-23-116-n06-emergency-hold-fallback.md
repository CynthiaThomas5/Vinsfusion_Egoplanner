# #116 task summary: N06 emergency hold and current-version layout verification

- User scope: `codex resume --last` resumes Goal completion mode for N06. Preserve the N06 acceptance contract. Do not start PX4, bridge, controller, traj_server, navigation supervisor, control publisher, or execute planner curves.
- Existing evidence: #113 failed closed for stale depth and other identity/query/resource cases but did not observe an EMERGENCY_STOP hold spline.
- Decision: patch only the reachable map-obstruction branch. A stationary spline is publishable only after the existing current-map freshness, identity, body and terminal-hold gates pass. Stale and query failures stay fail-closed.
- Results: #116 emitted a certified hold after an active path obstacle; #118 refused a hold whose volume was unknown; #119 retained stale-map refusal; #120 emitted a certified hold for a newly blocked completed terminal. All had zero late curves.
- Current-build layout check: #121 rejected a +0.6 m corridor goal when full-body sweep encountered occupied cells. #122 passed both wall goals and the `EXEC_TRAJ -> REPLAN_TRAJ -> EXEC_TRAJ` handoff. #123 passed the previously qualified +0.25 m corridor goal. Every passing layout had three source-matched snapshots, raw-free body/sweep/hold checks, and no control graph endpoints.
- Conclusion: N06 original planner-level exits have evidence and the parent is marked passed. This says nothing about executed motion or dynamic braking; N08 owns stop-distance measurement. N05's no-go boundary remains in force. Next mainline goal is N07.
