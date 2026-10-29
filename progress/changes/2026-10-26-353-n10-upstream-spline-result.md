# Change record #353 — N10.3 upstream spline-flow result

- Removed active project-added EGO patch 0044 as requested; the additional multi-pass final-curve hard rejection is gone. Upstream's single check and one reallocation/refinement attempt remain.
- Fresh EGO source replay passed with 32 active patches; ROS build passed for 17 packages; project tests passed (407 unit tests and two navigation ROS integration probes).
- SITL emitted 26 B-splines and 1,071 READY commands; no custom final-spline rejection occurred. Observed actual peak speed was 0.859 m/s.
- Flight aborted after 9.4 simulated seconds on the project-owned localization health guard at normalized cost 1.007707962 > configured provisional 1.0. No arrival, dwell, 600 s hold, or controlled braking measurement. The health threshold was not changed.
- Fixed preflight-aligned READY command to truth-IMU tracking error: median 0.771 m, p95 0.942 m, max 0.946 m; retain as a measurement, not a final threshold.
- Independent terminal readback confirmed landed/disarmed, bridge disabled, zero control samples; the project container was stopped.
- Evidence: [#353 report](../evidence/n10-upstream-spline-speed120-open-speed-16m-20261026-353.md); run artifacts under artifacts/runs/n10-20261026-353-upstream-spline-speed120-open-speed-16m/.
- Next: #354 changes only EGO max velocity 1.2 to 0.8 m/s/axis on the same route/source; all health thresholds and safety/identity gates remain unchanged.
