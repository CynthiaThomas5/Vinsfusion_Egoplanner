# N10.3 #378 speed060 caller-cancel protocol

对话摘要：[2026-10-27 #378 protocol](../../collaboration/dialogues/2026-10-27-378-n10-speed060-cancel-protocol.md)

- #377 on the unchanged runtime did not reach its `[0.70,0.80] m/s` trigger. PX4 horizontal peak was 0.6478956 m/s; EGO reference peak was 0.715213 m/s.
- As-of matching of valid PX4 position samples to the latest same-goal/same-epoch READY command found 110 candidates in `[0.60,0.66] m/s`, with the first at 0.601296 m/s. That evidence selected the new measurement window.
- #378 freezes the same runtime source/install hash, planner, spawn, one-leg +16m/+0.10m/+0.20rad goal, observers, and stop-band definition. The only measurement variable changed is the speed trigger window.
- Generated protocol/prelaunch and run-local driver under `progress/evidence/` and `artifacts/n10-prepared/n10-20261027-378-speed060-cancel-calibration/`. The driver inherits #377's ROS setup nounset fix. After SITL startup, the first identity check found that the current-run manifest had not yet been generated; it exited before preflight or goal. A 6 s independent readback confirmed the vehicle was still landed/disarmed/control-disabled with zero control samples. The driver now runs the already-frozen `runtime_manifest.py` to create that read-only manifest before identity comparison; an addendum and updated driver hash are frozen before retry.
- Validation: `bash -n` on the run-local driver; `python3 -m json.tool` on protocol, prelaunch, addendum and milestone JSON; `git diff --check`; `python3 tools/project_status.py`.
- No product source, planner configuration, acceptance threshold, or collision behavior changed. The #378 flight goal has not yet been sent. N10 remains `in_progress`.
