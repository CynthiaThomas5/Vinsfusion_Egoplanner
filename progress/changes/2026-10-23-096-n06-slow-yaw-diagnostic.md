# 2026-10-23 #096 N06 slow-yaw diagnostic

对话摘要：[N06 slow-yaw diagnostic](../../collaboration/dialogues/2026-10-23-096-n06-slow-yaw-diagnostic.md)

## 改动与结果

- r21 使用 r20 相同的 wall layout、N06 textured surround、固定平移及 360° yaw 端点，峰值速率降四倍。`mapping-stack.log` 记录首个 zero-feature 时刻 sim 17.194 s／估计 yaw 0.61°，首个 `normalized_cost_exceeded` gate closure sim 45.574 s／估计 yaw 16.37°。它比 r20 晚锁定，但未持续健康至完成转向。
- 在仿真时钟 sim 136.126 s、估计 yaw -160.84° 时由 `docker stop --timeout 15` 停止。完整 map log 保留，但容器 exit 137，motion 与 input recorder 最终文件未落盘；此证据缺 independent truth 与 raw input。
- 将外层 N04 runner cleanup 的容器宽限从 15 秒增加到 90 秒，让中断时的输入压缩和 motion recorder 有时间完成。
- 新增 `config/components/simulation/n06_yaw_360_segmented_15deg.json`：24 个 15° rest-to-rest yaw 步进，每步固定 5 秒，保持与 r21 相同的峰值角速度并在各步之间静置 5 秒；当前下一项仍为 N06.4。
- 新增[诊断证据](../evidence/n06-observation-scan-diagnostic-20261023-096.md)，更新当前状态／milestones／N06 报告。验收门槛及 N06/S4 状态不变。

## 验证

- `bash -n tools/run_n04_map_layout.sh tools/run_n04_map_layout_container.sh`：通过。
- `python3 tools/project_status.py`：Structure/design check PASS；该检查不代表 ROS build/SITL。
- profile 几何复算：72 个 phase、24 次 15° rest-to-rest、总角度 360°、峰值 0.05236 rad/s。
- 未运行 tests；r22 未运行。

## 限制与下一步

r21 的实际 fixture truth 与独立输入记录未保存；只能使用 VINS log 位姿和健康 gate 时间。#096 不通过任何 N06 出口。下一步使用容器内对 motion 子进程发 SIGINT 的方式触发 runner cleanup，执行 r22 并保留可用 partial artifacts。
