# N08 #315 profile

- #314 passed the single-axis pitch transition, then failed during low-height yaw with pitch held at −0.35 rad.
- #315 keeps pitch at 0 while yawing to rear and returning. Pitch moves to −0.35 rad and back only while stopped at rear yaw, with a 4 s rear-view hold.
- This is one timing variable change; all acceptance thresholds and the first 13 stages are preserved.
- The 20-stage, 490 simulated-second profile passes 46 static preflight-scan tests, structure/design, JSON, shell, joint-limit, and diff checks.
- Runtime #315 stopped during stage 14/20 with a localization health refusal. No post-release gate or goal followed. N08 remains in progress; the static result is not a flight or braking pass.
