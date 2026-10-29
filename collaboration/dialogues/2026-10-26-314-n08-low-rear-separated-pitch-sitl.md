# N08 #314 SITL result

- User scope: complete N08 according to the existing plan; do not retest passed N07, alter thresholds, or add a return goal to a one-way task.
- #314 retained the same map, health, and spatial thresholds. The later sequence audit found stage 13 changed yaw and pitch simultaneously; it was not pitch-only.
- The support scan stopped during stage 14 of 19. The combined transition to yaw −π/2 and pitch −0.35 rad completed with max cost 0.880538; the following yaw continuation at fixed pitch crossed the existing 1.0 localization-health threshold at 1.002558. The initial N05 snapshot had refused for insufficient raw occupied ground-plane voxels.
- No same-identity post-release admission, read-only preflight, forward geometry gate, mission, or flight occurred.
- Fixture detachment/removal and landed state were confirmed. An independent six-second readback showed bridge DISABLED, disarmed/landed, and zero control-topic samples. Only run #314 was stopped.
- Next diagnostic #315 keeps yaw turns neutral-pitch, changes pitch only at a stationary rear-facing pose, and restores pitch before returning yaw. Passing this scan remains only a precondition for N05/preflight/geometry gates; it does not itself pass N08.
- N08 remains in progress; no thresholds changed.
