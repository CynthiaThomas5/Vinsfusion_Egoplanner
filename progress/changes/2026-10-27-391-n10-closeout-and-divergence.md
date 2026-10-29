# #391 安全收尾与保持漂移证据

对话摘要：[一次性紧急关闭授权和后续分析范围](../../collaboration/dialogues/2026-10-27-391-n10-closeout-and-divergence.md)。

按用户的一次性授权对 #391 执行 force-disarm 并受控停止。新增[收尾与漂移报告](../evidence/n10-integrated-calibration-closeout-and-divergence-20261027-391.md)，保留原先 run report 的同时态读数和原始文件。新增只读固定对齐分析 `tools/debug_truth/evaluate_n10_hold_divergence.py` 及其输出 `artifacts/runs/n10-20261027-391-integrated-calibration-retry/n10-hold-state-divergence.json`，比较 PX4 local/setpoint、raw VINS、独立真值与 feature telemetry。结论限定为 estimator/measurement 与真值在 hold 中分离，起因未唯一识别。

验证：`evaluate_n10_hold_divergence.py --run-dir artifacts/runs/n10-20261027-391-integrated-calibration-retry --output artifacts/runs/n10-20261027-391-integrated-calibration-retry/n10-hold-state-divergence.json` 已对只读归档执行；终态摘要记录 3 s 独立 readback 的 landed/disarmed/control-disabled/zero-control 与项目容器 stop 退出结果。该紧急收尾不计为原生 fault landing 通过，也不计 N15/N16 正式次数。未启动新 SITL。
