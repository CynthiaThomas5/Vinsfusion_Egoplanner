# P5 VIO 质量与只读真值轨迹关联独立复测

## 改动

- 为 run #176 复制独立 PX4 SITL build 和导航探针，隔离 ROS/Gazebo partition，并在 run-local shell 中等待 `/debug_truth/base_odometry` ROS graph 达到一个 publisher、一个 `raw_vins_readonly_probe` subscriber 后才派发目标。
- 运行固定 `vio_closed_loop` profile。真值 bridge 只服务独立只读 probe；导航栈、定位、建图和 PX4 bridge 不订阅真值。保留原始 VIO、quality telemetry、真值/IMU、PX4 report、ULog 与 topic graph。
- 新增 [复测证据](../evidence/p5-vio-truth-error-repeat-20261019-176.json)，记录运行参数、结果、源文件与 artifact 哈希；更新 CURRENT、evidence index、P5 milestone、GOAL B/H evidence list 和 README 状态。

## 结果

- #176 90秒采集含3,046 truth、12,017 IMU、910 optimized VIO 与12,005 propagated VIO；优化和传播速率约15.15 Hz/200 Hz，所有数值有限且无解析错误。
- 279组 flight-window 位姿经一次固定 SE(3)、尺度固定为1的对齐后，位置 RMSE/P95/最大为0.3144/0.8835/1.1643 m，姿态 RMSE为0.3150°。normalized_cost/位置误差 Pearson r=0.7136；long-track、accel bias、gyro bias 与误差 r=−0.7496、0.5545、0.7707。
- 健康遥测在仿真时间35.608 s以 cost=1.1965跨过门限，对齐位置误差约0.0181 m；首次位置误差超过0.30 m在38.184 s，距 status source stamp约2.532 s。与 #175 的门控后漂移顺序和 long-track/bias 相关方向一致；两轮样本均以近竖直运动为主，不能据此推断因果或普适阈值。
- 导航 action 因 `localization_normalized_cost_exceeded` 失败；前置稳定门通过并观察到起飞/活动阶段，最终 PX4 `LANDED`、未解锁、`failsafe=false`。`/position_cmd` 有142条 READY flag-1和1条 flag-4；四个 PX4 控制输入各只有一个发布者。
- `max_normalized_cost=1.0`、VIO future 容差0.065 s 均未修改；P5保持 `in_progress`，GOAL A–H 未完成。

## 验证

- `bash -n artifacts/runs/p5-px4-vio-ego-flight-20261019-176/run-px4-vio-ego-flight.sh`：PASS。
- 固定 Jazzy 容器运行 `tools/evaluate_vio_quality_alignment.py`：279组位姿匹配，PASS。
- `python3 tools/test_vio_quality_alignment.py`：2 tests PASS；`python3 tools/test_vins_alignment.py`：3 tests PASS。
- `python3 -m py_compile tools/probe_vins.py tools/evaluate_vio_quality_alignment.py tools/test_vio_quality_alignment.py`：PASS。
- `python3 tools/project_status.py`：结构检查；不代表导航或 P5 通过。
- `git diff --check`：PASS。

## 局限与下一步

run #176 是独立 observer 参与的诊断运行，不是最终无真值验收；短目标和近竖直运动范围不足以确认横移、转弯或偏航时的 VINS 质量表现。下一轮保持健康门不变，覆盖明确横移或偏航段；随后仍需完成无真值重复任务、障碍净空、地图快照、故障注入及长时验收。

## 对话摘要

[P5 VIO 质量与只读真值轨迹关联独立复测](../../collaboration/dialogues/2026-10-19-061-p5-vio-truth-error-repeat.md)
