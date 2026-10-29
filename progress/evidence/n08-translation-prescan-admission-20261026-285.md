# #285 N08 translation-only N05 support scan and admission

Run `n08-cancel-translation-prescan-20261026-285` completed all 6/6 stages of the existing `n06_full_airframe_retreat_240_translation_only` support profile. The saved motion trace contains 10080 samples and zero invalid-localization samples. Peak accelerometer-bias norm was 0.09440 m/s², below the unchanged 0.15 m/s² gate.

Post-scan, post-release and an additional independent fresh online/offline N05 check accepted `all_entry_phases_known_and_clear` on the same epoch/map. The independent check read bridge `DISABLED`, PX4 disarmed and landed, localization valid, and fresh map/depth/fusion ages within 0.4 s. Both the scan runner and an independent Gazebo model-list query confirmed the fixture absent. The cold runtime manifest contains the current trial-runner hash, and the installed #276 binary fingerprints match. No control or goal was published.

The support helper still records a generic localization error during its final settling step after all profile stages and fixture removal. The trace itself has zero invalid-localization samples; post-release admission and an additional fresh N05 check passed. Preserve this warning; the N05 prerequisite diagnostic passed and the N08 motion trial may proceed. This report does not qualify any flight behavior.

See the [machine-readable report](n08-translation-prescan-admission-20261026-285.json) and run artifacts under `artifacts/runs/n08-cancel-translation-prescan-20261026-285/`.