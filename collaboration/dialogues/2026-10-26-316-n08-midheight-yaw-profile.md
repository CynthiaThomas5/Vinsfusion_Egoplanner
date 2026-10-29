# N08 #316 profile

- #312 completed rear yaw at z=1 m but failed later while descending. #313–#315 failed during low-height rear turning.
- #316 retains #315's yaw/pitch order and all limits but moves the turn to z=0.5 m, a level already traversed at neutral yaw. It descends to z=0 after the turn and view hold.
- The profile has 23 stages and 519 simulated seconds.
- Static validation: 47 scan-profile tests, project structure/design, JSON, shell, joint limits, and diff check passed.
- SITL aborted before stage 0 on an unattributed localization gate; it did not test the altitude variable. #317 will report the failed predicate without weakening it, then rerun the same profile. N08 remains in progress.
