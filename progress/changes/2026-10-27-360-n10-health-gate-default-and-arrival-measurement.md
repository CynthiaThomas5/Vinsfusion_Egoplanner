# #360 N10：默认旁路定位质量策略门并补充联合到达量测

对话摘要：[2026-10-27 #360 N10 health gate default](../../collaboration/dialogues/2026-10-27-360-n10-health-gate-default.md)。

## 修改

- `tools/project.sh sim` 默认将 `D435I_DIAGNOSTIC_BYPASS_HEALTH_GATES` 设为 `1`；仍可显式传 `0`复测原定位质量策略。
- `docs/running.md` 说明默认旁路的策略范围和仍有效的消息、时间、PX4桥、地图身份及 EGO 碰撞处理。
- 新增 `tools/n10_arrival_metrics.py`、`tools/debug_truth/evaluate_n10_arrival.py` 和定向测试，联合量测到达位置与 yaw，并同时报告 Gazebo 仿真时钟和墙钟驻留。
- 离线复算 #357 得到联合达标持续 243.28 仿真秒／319.06 墙钟秒；没有改动 GOAL F 阈值。
- 新增 [N10.3 证据汇总](../evidence/n10-calibration-synthesis-20261027-360.md)；N10.3 仍为 in_progress。

## 验证

- 隔离 Docker mock 启动 `tools/project.sh sim`：未设置变量时确认容器收到 `D435I_DIAGNOSTIC_BYPASS_HEALTH_GATES=1`；显式设为 `0` 时确认传入值为 `0`。mock 未启动仿真或 PX4。
- `python3 tools/debug_truth/evaluate_n10_arrival.py artifacts/runs/n10-20261026-357-upstream-spline-speed080-health-bypass-16m`：诊断检查通过，输出位置/yaw联合窗口及双时钟持续时间。
- `PYTHONPATH=tools python3 -m unittest tools.test_n10_arrival_metrics tools.test_localization_health tools.test_n10_motion_cancel`：25 tests passed。
- `bash -n tools/project.sh`、`bash -n tools/run_n10_cancel_calibration.sh`：通过。
- 三个新增 Python 文件 `ast.parse`：通过；`git diff --check`：通过。
- `py_compile` 尝试写入仓库既有 `tools/__pycache__` 时因权限拒绝失败；未改动该目录，改以 AST parse 和实际单元测试验证语法与行为。

## 局限和下一步

本轮只改变主仿真入口的 VINS 质量／源龄策略门默认值，不改 `health.json` 原始数值，也没有更改 PX4 bridge 或 EGO 碰撞规则。#357/#359 的净空调整使用观测到的相邻样本位移，不能作连续动力学证书。#359 仍是一个高速制动样本；补足重复性并冻结余下验收依据后再进入 N10.4。
