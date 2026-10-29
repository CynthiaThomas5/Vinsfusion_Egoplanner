# #281 Caller-cancel trial stopped by runner result-field mismatch

N05 support scan, post-release online/offline admission, map identity and the 40-second read-only mission preflight passed. The single forward EGO goal was sent. At the source-time sample nearest the cancel event, PX4 horizontal speed was **0.04323 m/s** and EGO reference vector speed was **0.06092 m/s**, inside the configured 0.04–0.06 m/s trigger window. The planner observer recorded a caller cancellation with `MODE_STOP_HOLD` (1).

The runner compared ROS action `outcome` with `caller_cancel`, although the action contract returns `outcome="canceled"` and `reason="caller_cancel"`. It failed before observing an EGO replacement spline and used its existing fail-closed Offboard-disable landing path. Only trajectory id 1 was recorded; no stop distance/response measurement was qualified. PX4 ended landed/disarmed, bridge LANDED, and the project container was stopped. This is a failed/incomplete motion-cancel attempt, not an N08 pass.

The JSON report records the run hashes and the reconstructed trigger sample. The action result itself was not persisted before the assertion, so the conclusion about its exact result fields is source-contract based and supported by the observed caller-cancel event; the next run now records the result before continuing.
