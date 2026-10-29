# N10.3 #377 run result and evidence-based retargeting

对话摘要：[2026-10-27 #377 result](../../collaboration/dialogues/2026-10-27-377-n10-speed070-cancel-result.md)

- SITL runtime identity, loaded planner/spawn/goal, read-only contact overlay and action graph matched the frozen candidate.
- Two run-local ROS setup failures occurred before flight; 6 s independent PX4/bridge readback showed DISABLED, landed, disarmed and zero control. A run-local wrapper-only `nounset` setup fix was frozen before the first goal; project source/install fingerprint stayed `b4707af345d1cd082dfb1cae3a24f24103134eedfce306205785b44342582ea7`.
- The 16 m EGO action completed before PX4 horizontal speed reached the `[0.70,0.80] m/s` trigger; measured PX4 horizontal peak was `0.647896 m/s` while EGO reference peak was `0.715213 m/s`. No cancel/brake sample exists.
- Contact evaluation passed with `0` prohibited contacts; independent final readback confirmed `LANDED`, landed/disarmed/control-disabled/zero-control. Project container was safely stopped.
- Offline as-of matching of PX4 local-position records to the latest same-goal/same-epoch READY EGO command found 0 candidates in the failed window and 110 in `[0.60,0.66] m/s`. This supports a new #378 measurement-only trigger window; no speed or acceptance threshold is changed.

Run report: [evidence](../evidence/n10-cancel-stop-speed070-20261027-377.md), [JSON](../evidence/n10-cancel-stop-speed070-20261027-377.json). No product source/configuration files changed in this result step. N10.3 remains in progress.