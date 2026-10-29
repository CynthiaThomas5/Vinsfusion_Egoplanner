# 2026-10-23 #095 N06 observation coverage diagnostics

对话摘要：[N06 coverage diagnostics](../../collaboration/dialogues/2026-10-23-095-n06-coverage-diagnostics.md)

## 目标与状态

Goal 完成模式，范围 N06；完成 N06.3 入口 unknown 视场诊断并为 N06.4 建立一个单变量观测实验。N06 与 S4 保持 `in_progress`，`next_goal` 保持 N06。

## 改动

- 新增 `tools/analyze_n06_observation_coverage.py`，从真实 raw occupancy snapshot 与记录的 VINS/camera pose 计算 N05 body/hold 球闭格查询，投影 unknown cell center 到源时刻及本次采集的相机几何视场。
- 生成 `artifacts/runs/n06-observation-coverage-20261023-r01/report.json` 与[证据报告](../evidence/n06-observation-coverage-diagnostics-20261023-095.md)。两布局 body/hold raw query counts 与 #093 的 r04 一致；unknown cell center 在全部采集视场中为 0。此为几何覆盖证据，不证明射线清除或分类正确。
- N06 运行准备新增 `n06_yaw_360_very_slow.json`：同一 full-yaw 端点和固定平移，峰值速率约 0.052 rad/s（r20 的 1/4），角加速度为 1/16。runner 支持 profile 自选的 wall-time input capture horizon，r21 设为 308 秒，覆盖 300 秒 profile timeout 加 8 秒。
- 前序已加入的 N06 surround world、marker visual 偏移、可选 world generator 开关和 no-daemon EGO parameter readiness gate 保留；r20 证明直接参数服务 gate 可通过。普通 N04 motion/static world 生成路径不变。
- 更新 CURRENT、GOAL、remaining-small-goals、milestones 与既有 N06 报告，记入 N06.3 结论及唯一下一子项 N06.4；未改 N06 exit criteria 或状态。

## 验证

- `python3 tools/analyze_n06_observation_coverage.py --output artifacts/runs/n06-observation-coverage-20261023-r01/report.json`：成功。wall body/hold unknown 1,801/4,048，corridor 1,807/4,085；source 视场及覆盖到 source stamp 的所有采集 pose 均有 0 个 unknown cell center 投影到成像区域。
- `PYTHONPYCACHEPREFIX=/tmp/n06-python-cache python3 -m py_compile tools/analyze_n06_observation_coverage.py`：通过。
- 旧记录的 `bash tools/project.sh test` 有 243 项通过，但发生在最新 recorder-horizon shell 修改之前；需本轮 `bash -n` 检查该改动。
- r20 完成完整 360° motion 采集但没有 snapshot：`n_pts size: 0` sim 13.432 s，首个定位无效 sim 13.630 s（`normalized_cost_exceeded`，yaw 约 2.58°）；用于提出慢速 yaw 假设，不视作成功出口。

## 限制与下一步

投影按体素中心且不使用深度采样值，近裁剪、遮挡、ray traversal 和 occupancy classifier 的独立贡献仍未知。wall query 请求的 pending-pair 状态未记录；corridor probe 的 odometry timeout 与定位 health lock 相符。N06.4 下一步执行 r21 角速率单变量测试，保持 PX4／控制链关闭；完整通过后再继续快照与 live EGO，失败时保存输入并安全清理。
