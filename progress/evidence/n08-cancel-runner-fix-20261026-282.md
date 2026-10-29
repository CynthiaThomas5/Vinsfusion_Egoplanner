# #282 N08 cancel-result classification fix

The runner now validates the ROS action fields independently: terminal status `STATUS_CANCELED`, result `outcome="canceled"`, and result `reason="caller_cancel"`. It preserves the trigger speed sample and action result in `flight.json` if a later stop/hold check fails. Added regression coverage for valid caller cancel, wrong outcome, wrong terminal status, and wrong reason.

Verification: `bash tools/project.sh test` passed all 336 unit tests and the navigation-adapter integration; Python compilation, shell syntax checks and `git diff --check` passed. No compiled source changed, so #276 remains the EGO/interface build record. This does not qualify the EGO replacement stop spline; a fresh SITL run is still required.
