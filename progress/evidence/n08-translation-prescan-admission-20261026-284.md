# #284 N08 translation-only N05 support scan and fresh admission

Run: `n08-cancel-translation-prescan-20261026-284`. This is only an N05 prerequisite scan; it is not an N08 flight pass.

The existing `n06_full_airframe_retreat_240_translation_only` recipe completed all 6/6 stages in the same `n08_overhead_calibration` geometry. All 10131 recorded scan-trace samples were localization-valid; the peak accelerometer-bias norm was 0.11483 m/s², below the unchanged 0.15 m/s² gate. The support fixture detached and Gazebo confirmed its model absent.

The initial pre-scan N05 refusal was expected before the support scan (`TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`). After the scan, post-scan and post-release online/offline checks accepted all N05 phases. An additional independent fresh online/offline check accepted `all_entry_phases_known_and_clear` on the same epoch/map; it read back bridge `DISABLED`, PX4 disarmed and landed, localization valid, with current map/source/fusion ages within the 0.4 s limit. A separate `gz model --list` query confirmed the scan fixture absent. No goal or control was published.

The scan helper exited with code 2 and reported a generic localization error during its final settle step after all six stages and detach/removal. Its saved motion trace contains zero invalid-localization samples, its last status recovered as valid, and the independent post-release N05 checks passed. This warning is preserved rather than reported as a scan runner success; the N05 diagnostic criteria nevertheless passed. It does not establish flight safety or N08 motion behavior.

Artifacts and hashes are in the [machine-readable report](n08-translation-prescan-admission-20261026-284.json) and under `artifacts/runs/n08-cancel-translation-prescan-20261026-284/`.
