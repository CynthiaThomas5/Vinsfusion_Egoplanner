# #111 N06.2.2 active-map and completed-hold refusal

**Dialogue:** [#111 task summary](../../collaboration/dialogues/2026-10-23-111-n06-active-hold-refusal.md)
**Evidence:** [runtime report](../evidence/n06-active-obstacle-hold-refusal-20261023-111.md), [machine record](../evidence/n06-active-obstacle-hold-refusal-20261023-111.json)

## Result

Ran the current EGO/plan_env component probe in isolated ROS domain 98 with synthetic depth. Raw free, occupied, unknown, and outside query classes were observed; wrong-map admission rejected with zero map queries. The active-curve injection faulted closed on `full_curve_unknown` in this run, and the completed terminal-hold injection faulted on `full_curve_terminal_hold_occupied`. Both cases had zero late curves. The direct `full_curve_occupied` active-path result remains the earlier #093 evidence; this run is not described as an occupied classification.

The first container bootstrap exited before probing because ROS setup referenced an unset variable under `set -u`; retrying without nounset completed both probes. No project process or container remained after the run.

## Validation

- `tools/probe_ego_safety.py` active-map case: pass; one certified curve, fail-closed unknown response, subsequent planning refusal, zero late curves.
- `tools/probe_ego_safety.py --after-completion`: pass; occupied terminal hold refused, zero late curves.
- Current-source bounded query/sweep and navigation-adapter identity/stale/timeout/late-reply/pending-cancel regressions are linked from #108.

Raw outputs and hashes are in `artifacts/runs/n06-20261023-safety-111/`; the evidence report records their SHA-256 values.

## Limits and next step

This is isolated component evidence, not another actual-layout run. N06 remains `in_progress`. Next: gate and observe a second goal/replan handoff in the actual r34 wall layout, then close remaining combined-runtime identity, freshness, query-failure and resource refusal cases. PX4/control execution remains outside this subtask.
