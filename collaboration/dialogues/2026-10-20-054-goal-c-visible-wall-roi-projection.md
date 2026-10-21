# GOAL C visible wall ROI and voxel-side diagnostic #298

## Task summary

Continue GOAL C analysis after canonical EGO snapshot-service reconstruction and the same-layout map snapshots #295/#296. Bound the wall sample region by the depth camera view at each fused source timestamp, then inspect the alternating wall voxel center and the first-snapshot SDF outliers.

## Constraints

- Keep GOAL C and the full GOAL A–H status unchanged until formal acceptance evidence exists.
- Use fixture truth only for offline evaluation; do not feed it into localization, mapping, planning, or control.
- Preserve `src/vendor`, avoid changing the simulation source world, and label this as exploratory evidence.
- Existing user worktree modifications remain untouched; no staging or commit.

## Findings and decision

- The camera source-time ROI used the recorded `last_fused_depth_source_stamp_ns`, the session pinhole intrinsics/extrinsics, and the fixed SE(3) alignment already used by #295/#296. In both epochs the median inverse-aligned map x center is 3.05, 2.95, 3.05 m across the three snapshots.
- In #296, all 72 first-snapshot wall outliers are map-frame x=2.95 m centers. The full-run alignment shifts these points by −50 to −61 mm in x, enough for nearest-wall SDF distance to cross the exploratory 0.10 m threshold. This is a plausible quantization/alignment explanation, not proof that the map has no ghosting or that alignment is accurate.
- The frustum ROI bounds and occupied-center summary are recorded in `progress/evidence/p2-visible-wall-roi-projection-20261020-298.json`; detailed source-hash-backed results are under the #296 run artifacts.

## Open questions

- Snapshots do not retain per-voxel observation timestamps, and this ROI does not model missing depth returns or occlusion. A repeat with a shifted wall/grid phase or independent map-to-world calibration is needed to distinguish cell quantization, pose alignment, and depth error.
- GOAL C coverage, ghosting, unknown-space safety, clearance, and planning acceptance remain pending.
