# N10.3 #378 caller-cancel result

对话摘要：[2026-10-27 #378 result](../../collaboration/dialogues/2026-10-27-378-n10-speed060-cancel-result.md)

- The frozen [0.60,0.66] m/s trigger was reached at `0.600867 m/s`. Caller cancellation, action result, replacement trajectory, 1.02 s PX4 stop band, bounded truth interval, full contact observation, zero prohibited contacts, and independent safe terminal readback all passed the sample-validity evaluator.
- Measured truth horizontal path to stop-band entry: `1.376716 m`; endpoint displacement `1.152746 m`; entry/confirmation `4.844/5.864` simulated seconds.
- Same run raw VINS comparison reported position RMSE/P95/max `0.0415/0.0658/0.0733 m`, yaw RMSE/P95/max `0.2399/0.4621/0.4926°`, with single fixed-scale SE(3) alignment. Diagnostic only.
- All input hashes named by the brake evaluator match the stored artifacts. Container stopped after `LANDED`, disarmed/control-disabled, zero-control readback.
- Report: [Markdown](../evidence/n10-cancel-stop-speed060-20261027-378.md), [JSON](../evidence/n10-cancel-stop-speed060-20261027-378.json). One sample does not establish repeatability or a general brake bound; N10.3 remains incomplete.
