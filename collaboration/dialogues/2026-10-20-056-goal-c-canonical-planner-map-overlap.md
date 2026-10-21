# GOAL C canonical EGO 绕障规划与地图单元对照 #304–#305

## Task summary

Continue GOAL C after the wall grid-phase intervention. Reuse the canonical reconstructed EGO install to send a planner-only target whose direct chord is blocked by a box, measure each emitted B-spline against the generated SDF, then correlate the route samples with same-epoch occupancy snapshots.

## User constraints and project rules

- Continue the single-D435i simulated P0–P6 system. Do not mark GOAL C or overall GOAL A–H complete without acceptance evidence.
- Use only one canonical EGO implementation. Keep third-party fixes in ordered `dependencies/patches`; do not alter a vendor source in place.
- Unknown, invalid-depth, and out-of-view space may not be treated as free. Any online truth input is restricted to `debug_truth`; truth in this run was not a ROS topic and was used only for offline frame comparison.
- No control setpoint publisher outside `uav_px4_bridge`; these runs had no PX4 bridge, trajectory server, or controller. Existing worktree changes remain user-owned; do not stage, commit, push, or clean.

## Findings and decisions

- Runs #304 and #305 reused the clean #297 canonical reconstructed EGO install and each published a manual planner goal at `(2.5, 1.4, 1.0)` in the new localization epoch. The direct line has a diagnostic nominal sphere clearance of roughly −0.435 m to the calibration box.
- Each run emitted two B-splines. The first path detours around the box and leaves roughly 13.3–13.5 cm nominal sphere clearance to it. The later path retains positive box clearance but has −2.4 to −2.8 cm nominal sphere clearance to the wall; it does not guarantee the 0.482 m nominal body sphere. The configured planner inflation remains 0.099 m and provisional.
- #305 captured a same-epoch occupancy snapshot after the probe emitted the goal. Its last fused depth stamp lagged the goal by 1.145 s because the service took 1.043 s to copy the full grid; the camera/world remained physically static until the first force command at 15.617 s. This is close diagnostic context, not an exact same-stamp snapshot.
- In that post-goal grid, the first and second B-spline centerlines had 422/1201 and 655/1201 samples in unknown cells, with no centerline sample in occupied or inflated cells. The same unknown pattern persisted in later snapshots before sensor motion. This is consistent with unknown space being traversable in the baseline planner, but voxel observation timestamps are absent and no path was executed.
- Both runs had an empty runtime list of control nodes, control topics, and truth topics. They do not prove collision avoidance during motion, unknown-space safety, or final GOAL C/D/E/F acceptance. Evidence is linked from [progress record #056](../../progress/changes/2026-10-20-056-goal-c-canonical-planner-map-overlap.md).

## Open questions

- Does the exact current canonical planner code still use the baseline unknown-as-free rule, and can the existing candidate patch be safely rebased after canonical snapshot patch 0021?
- What provisional planner inflation is needed to respect the nominal body envelope, and what additional map, tracking, and braking margins must GOAL F use before formal runs?
- Can the same target be replanned after applying unknown-as-obstacle policy and a larger provisional inflation, with an epoch-matched snapshot captured close to goal publication?
