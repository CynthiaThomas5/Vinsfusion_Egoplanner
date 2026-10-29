# N08 #315 SITL result

- #315 kept yaw neutral-pitch through both rear-turn stages and used pitch only at the rear-facing stationary pose; no thresholds changed.
- It completed 14/20 stages, then exceeded the existing localization health threshold during the second low-height yaw segment. Last trace: yaw −2.0613 rad, pitch≈0, cost 0.896595; maximum stage trace cost 0.931764; terminal health monitor cost 1.065024. The crossing pose was not captured.
- The initial same-run N05 check agreed online/offline but refused `ground_plane_insufficient_raw_occupied_voxels`. No fixture-release admission, preflight, geometry, goal, or flight followed.
- Fixture detached/removed; independent readback showed bridge DISABLED, PX4 disarmed/landed, and zero control samples. Only #315 was stopped.
- Since #314 also failed during the second low-height yaw segment with pitch held down, pitch alone is not a sufficient explanation. Next #316 moves the identical turn to the existing z=0.5 m intermediate height to test altitude dependence.
- N08 remains in progress.
