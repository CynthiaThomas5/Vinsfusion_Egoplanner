# N08 #320 current geometry replay

- Current full-airframe forward-body geometry replayed against #294's archived same-run raw map.
- The 0.6 m one-way goal corridor passed all 25 samples and both holds; the 0.5 m cancellation corridor passed all 21 samples and both holds. All queries had zero unknown/occupied. Reachable center bound 0.250778 m; available bound 0.262500 m.
- #294 used the translation-only support scan and completed a native one-way `single_goal motion_cancel` with no return action. Its same-run post-release/current-area N05 checks passed. It predates the current full-body runtime gate, so it is not counted as one of the final current-version three repeats.
- Next: fresh #321 with the same known scan recipe; require live current-version geometry and all fresh gates before any goal/enable. If accepted, continue the same run with `single_goal motion_cancel 0.04 0.06`; no return command.

Evidence: [#320 replay](../../progress/evidence/n08-294-current-geometry-replay-20261026-320.md), [#294 trial](../../progress/evidence/n08-cancel-stop-qualified-replay-20261026-294.md).
