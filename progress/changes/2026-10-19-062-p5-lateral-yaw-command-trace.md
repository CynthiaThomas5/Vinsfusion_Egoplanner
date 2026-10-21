# P5 横移／偏航目标诊断与 EGO→PX4 命令链追踪

## 改动

- 新增 #177 run-local SITL 目标，要求相对起点横移0.5 m并改变 yaw +45°；使用单独的 ROS domain、Gazebo partition 和 PX4 SITL build 副本。
- #178 沿用相同目标，并扩展仅用于该 run 的 flight probe，将目标匹配的 EGO `PositionCommand` 与 bridge `/fmu/in/trajectory_setpoint` 原始字段和 wall 时间写入运行报告。canonical ROS 包源码未修改。
- 新增 [#177 横移／偏航证据](../evidence/p5-vio-truth-error-lateral-yaw-20261019-177.json) 和 [#178 命令链证据](../evidence/p5-vio-truth-error-command-trace-20261019-178.json)；更新 CURRENT、README、evidence index、P5 milestone、GOAL B/H evidence list。

## 结果

- 两轮 goal 均在稳定门后派发；首次 `normalized_cost_exceeded` 分别在派发后1.373秒和0.769秒，随后 action 中止。PX4 两次都安全降落并解除武装，failsafe=false。
- #177 的271组 flight-window 配对位姿位置 RMSE/P95/最大为0.1815/0.4999/0.5351 m；normalized_cost/位置误差 r=0.725，long-track/误差 r=+0.465。真值横移跨度约0.048 m，yaw 最远到−21.24°，没有完成+45°目标。
- #178 记录75条匹配 goal/epoch READY `PositionCommand`；EGO 早期 path yaw 为−0.289至−0.216 rad，横向位置指令仍约在起点，目标 yaw 为+0.785 rad。PX4 setpoint yaw 与对应 ENU→NED command 映射后呈约0.041 rad近常量偏差，不能据此宣称坐标转换缺陷；运行在 terminal yaw 段前被取消。
- #178 位置 RMSE/P95/最大为0.1367/0.3942/0.4165 m；cost/误差 r=0.624，long-track/误差 r≈0。long-track 相关在近竖直 run 为负、横移/yaw未完成 run 为正或近零，不能作为稳定误差代理。
- 位置质量门和 future 容差均未变；P5仍 `in_progress`，GOAL A–H 仍未完成。

## 验证

- 固定 Jazzy 容器 `tools/test_px4_bridge_frames.py`：19 tests PASS。
- 固定 Jazzy 容器 `tools/test_trajectory_server.py`：PASS，验证 yaw spline、frame、cancel。
- 固定 Jazzy 容器 `tools/test_navigation_adapter.py --project-root /workspace`：PASS。
- 固定 Jazzy 容器 `tools/test_navigation_task_state.py`：10 tests PASS。
- 两个 run-local shell `bash -n`、#178 run-local probe `py_compile`：PASS。
- 两轮离线 evaluator 分别匹配271与287组位姿，PASS。
- `git diff --check` 与 `python3 tools/project_status.py`：PASS；结构检查不代表阶段通过。

## 局限与下一步

两轮质量门都在产生实质横向位移或到达终端 yaw 前中止。#178 保存的 PX4 yaw 输入输出能确认设定点响应了早期 EGO command，但没有保存完整成功任务的 terminal yaw。下一步分析 `normalized_cost` 趋势与 VINS 输入时间线，再以相同门限验证完整任务；不能通过旁路或静默放宽门限来构造成功结果。

## 对话摘要

[P5 横移／偏航目标诊断与 EGO→PX4 命令链追踪](../../collaboration/dialogues/2026-10-19-062-p5-lateral-yaw-command-trace.md)
