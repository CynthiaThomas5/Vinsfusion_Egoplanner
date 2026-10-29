# N10.3/#373 preflight result — stale removed-age-key reference

## Result

#373 loaded the correct frozen planner profile (`max_vel=0.8`, `max_acc=0.25`, horizon 5.0, `official_ego`) and matched runtime contract `ff7ccf032737fd31b77ccbc2015590ef846b159a5b320ef87b720a51ed86075c`. The preflight then crashed before producing `preflight.json`: `tools/check_navigation_ready.py` still accessed the removed `max_odometry_receipt_age_s` and `max_localization_receipt_age_s` values to compute a historical comparison field. The age gate had been removed from admission, but this stale report-only comparison still raised a `KeyError`.

No navigation goal or obstacle was sent, `flight.json` is absent, and flight observers were not started. This is a preflight software error, not a flight outcome or N10 pass.

## Safe stop

The independent readback recorded bridge `DISABLED`, landed, disarmed, control disabled, and zero control samples. The container was stopped after this confirmation. See [safe-to-stop readback](../../artifacts/runs/n10-20261027-373-gatefree-cylinder0-observation/preflight-failure-safe-to-stop.json).

## Fix and regression

Removed the stale comparison/reference fields from the read-only readiness report; raw odometry receipt gaps remain measured. `python3 -m py_compile tools/check_navigation_ready.py` passed. `bash tools/project.sh test` passed all 413 unit tests, navigation-adapter ROS integration, and the official_ego ROS probe. This source change changes the runtime fingerprint, so #373's frozen identity is not reused; #374 gets a new contract hash.

Machine-readable details: [JSON report](n10-preflight-stale-age-summary-reference-20261027-373.json).
