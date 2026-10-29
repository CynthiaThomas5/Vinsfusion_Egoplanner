# #383 到达评估改为仿真时间

- **对话摘要**：[2026-10-27-383](../../collaboration/dialogues/2026-10-27-383-n10-arrival-simtime-evaluator.md)
- **原因**：#382发现 `evaluate_arrival.py` 把Gazebo真值源时间窗用wall秒累计。#381原记录3.055 wall s折合2.34 sim s，不能证明GOAL F的3.0 sim s驻留。
- **修改**：离线评估器以truth `stamp_ns`累计sim time，记录wall time为诊断；同位置+yaw联合窗口，采样gap>0.04 sim s即断开；严格递增时间戳；缺证据状态与真实FAIL区分；健康状态和日志不作为项目自定义拒绝门。支持输出新文件，归档旧arrival报告不覆盖。
- **验证**：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_arrival_evaluator -v` 6/6；内存语法编译通过。#361/#376/#381归档复算：3.0187/3.1136/3.0551 wall s对应2.260/2.780/2.340 sim s，均FAIL 3.0 sim s合同。输出见 [#383报告](../evidence/n10-arrival-sim-time-reclassification-20261027-383.md)。
- **未解/下一步**：当前native action success与独立真值驻留未同时证明3.0 sim s。保持GOAL不变，下一步把native goal dwell延长至足以支持独立真值3.0 sim s并用PX4 SITL确认，然后把目标验收值与执行停留值放入唯一草案配置。父N10仍`in_progress`。
