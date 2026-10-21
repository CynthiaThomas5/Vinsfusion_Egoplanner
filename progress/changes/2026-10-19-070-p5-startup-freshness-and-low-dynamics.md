# 修改与验证记录

- 任务 ID／日期：#070／2026-10-19。
- 对话摘要：[P5 启动 freshness、preflight 与低动态复测](../../collaboration/dialogues/2026-10-19-070-p5-startup-freshness-and-low-dynamics.md)。
- 修改文件：新增 #191 run-local harness/launcher、启动权限记录、PX4 ULog 摘要及真值对齐评估；新增 [#188–#191 诊断报告](../evidence/p5-vio-startup-freshness-low-dynamics-20261019-188-191.json)，更新 CURRENT、证据索引和 P5 里程碑引用。canonical bridge、PX4 参数、默认规划配置和健康门限未修改。
- 行为变化及原因：run-local 启动稳定观察延长至5秒，确保 PX4 telemetry 与定位 freshness 连续稳定后才请求 prestream；按 canonical 状态机在切换 Offboard 后、arm 前检查 preflight。该次避免 #189 的起步时源戳 offset=0 短暂状态；不将 AUTO_LOITER 下的 preflight=false 当作 prestream 阻塞条件。
- 验证类型：离线分析、静态检查、SITL 与只读真值评估。`bash -n`（#191 两个 run-local shell）、`python3 -m py_compile`（run-local 探针）通过；`python3 tools/evaluate_vio_quality_alignment.py ...` 对322组配对完成固定 SE(3) 评估；PX4 ULog 由 pyulog 离线解析。`python3 tools/test_vio_ego_bringup_config.py` 6/6、`python3 tools/project_status.py` 结构检查，以及 `uav_px4_bridge` Jazzy 构建1/1，见 #069/#188 证据。
- 命令与环境：固定 Jazzy `d435i-vins:dev`，独立 PX4 SITL 副本、ROS domain 223、独立 Gazebo partition；运行 `bash artifacts/runs/p5-px4-vio-ego-hover-20261019-191/launch-diagnostic-run.sh`。
- 结果及证据位置：#191 通过5秒 freshness 稳定门，PRESTREAM→OFFBOARD→解锁→起飞；306条匹配 READY PositionCommand 后，小型3D+yaw action 因 `normalized_cost=1.15269` 中止，PX4 landed/disarmed。固定 SE(3) truth 对齐 RMSE/P95为5.63/13.43 cm；首次越线时视觉组占 robust cost 89.0%。PX4 ULog 有短暂 failsafe 与 Offboard signal loss；电池状态和电池 failsafe flags未报警，触发原因未确定。90秒只读 truth capture 完整，graph 检查确认 bridge 无 `debug_truth` 订阅。
- 未验证与 PROVISIONAL：低动态 profile 尚未完成导航目标；1.0 cost gate仍保持，P5未通过。视觉组占比和 cost/error 关联仅为诊断，不证明因果。降落阶段 failsafe 原因尚未定位；不称该轮 failsafe-free。
- 下一步：检查 #187/#191 的视觉残差、feature-track 和命令时间线；核对 landing command、Offboard signal loss、local-position invalid 与 failsafe 状态顺序，再选择下一次受控复测。
