# #320 N08 current-geometry replay for a proven one-way scan route

## Result

Replayed #294's archived raw map using the current full-airframe forward-body corridor gate. The 0.6 m one-way target passed 25 sweep queries and both holds; the 0.5 m caller-cancel corridor passed 21 sweep queries and both holds. All queries returned zero unknown and occupied voxels; the reachable-center bound was 0.250778 m against 0.262500 m available.

#294 used the translation-only support scan, passed its same-run release/current-area N05 checks, and its native flight was a one-way `single_goal motion_cancel` with no return action. Because its runtime predates the current full-body gate, it is not counted among the current-version three repetitions. It provides evidence to reuse the simpler scan recipe and directly test today's live gate.

## Next

Cold-start #321 with `n06_full_airframe_retreat_240_translation_only`. Continue only if the same-run scan, release/current-area N05, read-only preflight, and current live full-body corridor all pass. Then run one-way `single_goal motion_cancel` in the previously supported 0.04–0.06 m/s PX4 window.

Machine report: [#294 current-geometry replay](../evidence/n08-294-current-geometry-replay-20261026-320.json). Prior one-way run: [#294 motion-cancel result](../evidence/n08-cancel-stop-qualified-replay-20261026-294.md).
