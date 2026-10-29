# #349 N10.3 open-speed 16 m protocol freeze

This record freezes the first post-#348 calibration run. Compared with #347, the only planned factor change is the user-authorized removal of extra numerical speed cancellation/admission guards. The planner profile, spawn, goal, official_ego policy, remaining freshness/identity/collision checks and control owner remain fixed.

The task is the original +16 m / +0.10 m / +0.20 rad single goal, independent truth arrival and dwell, then 600 simulated seconds in ACTIVE, with read-only speed, VIO, map, tracking, contact and PX4 observations. Candidate acceptance values in the profile are not yet executable checks and will be calibrated before N10.4.

The frozen runtime snapshot is 655 files with SHA-256 `9fc811d5b318e392d62d0254ab55c7524a13494ca9c78a23f13c9853ce99d7ac`, from fixed image `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`. The complete protocol and per-file hashes are in [the protocol report](../evidence/n10-open-speed-16m-protocol-20261026-349.md) and its JSON companion.

Validation before execution: runtime snapshot generated read-only inside the fixed image; selected profile and source hashes recorded; unused run ID confirmed. No structural status check or flight result is claimed by this protocol freeze.
