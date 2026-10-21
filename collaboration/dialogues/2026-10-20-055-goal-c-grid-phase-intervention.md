# GOAL C 半体素墙面相位干预 #299–#303

## Task summary

Continue the GOAL C map-voxel investigation after the visible-frustum analysis #298. Test whether moving the calibration wall front face half a map voxel changes which wall-side cell EGO marks occupied, then compare the result at a source-time phase close to baseline #295/#296.

## User constraints and project rules

- Work only toward the single-D435i simulated P0–P6 project. Keep GOAL A–H and milestone status evidence-based; this exploratory work must not mark GOAL C passed.
- Use fixture truth/SDF only for offline diagnostics. Do not feed truth to localization, mapping, planning, or control, and do not use a truth subscription in the final navigation acceptance combination.
- No PX4/controller/control publisher in these mapping runs. Preserve `src/vendor` and the source world; generate run-local diagnostics from the project configuration.
- Preserve existing user changes and do not stage, commit, push, or clean them.

## Decisions and findings

- Baseline wall front face x=3.00 m aligns with a nominal 0.10 m grid boundary; the shifted x=3.05 m face lies at the adjacent cell center. Box/cylinder geometry and force acceleration commands remain unchanged.
- The shifted runs #299/#301/#302 all select local wall x=3.05 m across three snapshots. Only #302 has a phase close to baseline: offsets 1.748/4.157/6.863 s after first force, versus #295 1.683/4.257/6.930 s. #302 records zero occupied centers beyond the exploratory 0.10 m SDF distance.
- #299 is late relative to motion. #300 failed before motion due to a config path resolved relative to the run directory; it produced no snapshots. #301 snapshot 01 is pre-motion and later samples are earlier than baseline. Retain these artifacts but exclude them from matched-phase evidence.
- This strengthens the grid-side-selection plus full-run alignment explanation for #296's 72 first-snapshot >0.10 m wall points, but it does not establish a mapping root cause, prove map quality, or rule out other ghosting. The full-run transform is not independently calibrated; no voxel source timestamps, occlusion-aware ROI, coverage/ghosting criteria, planner goal, or trajectory acceptance exists yet.
- Evidence is [#303](../../progress/evidence/p2-map-grid-phase-shift-20261020-303.json); detailed analysis and artifacts are referenced in [change #055](../../progress/changes/2026-10-20-055-goal-c-grid-phase-intervention.md). GOAL C remains pending.

## Open questions

- What frozen navigation ROI and quantitative coverage, ghosting, unknown-space, and clearance criteria will be used across multiple layouts?
- Can an independent map-to-world calibration preserve the phase finding and quantify wall error without fitting the same short trajectory?
- Does the canonical EGO planner reliably generate safe obstacle-avoiding paths using only project localization/map inputs and with unknown space handled according to the frozen policy?
