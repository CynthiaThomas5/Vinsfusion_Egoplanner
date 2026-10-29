# N10.3/#369：移除项目本地 PX4 对齐误差降落门

关联：[构建/回归报告](../evidence/n10-px4-alignment-gate-removal-build-20261027-369.md)、[#369 冻结协议](../evidence/n10-live-obstacle-alignment-gates-removed-protocol-20261027-369.md)、[对话摘要](../../collaboration/dialogues/2026-10-27-369-n10-alignment-gates-removed.md)。

## 变更

- 审计 `src/own/uav_px4_bridge/uav_px4_bridge/px4_bridge_node.py` 确认 translation/yaw 最大差触发共用 `px4_frame_alignment_drift` 锁存故障的门由本项目自维护代码实现，不属于 EGO/PX4 上游规则。
- 删除 `alignment_max_drift_m=0.15` 和 `alignment_max_yaw_error_rad=0.15` 两项运行配置及其数值拒绝逻辑。配对位置差与 yaw 差仍计算并发布为诊断值。
- 保留配对时间新鲜性、PX4 EV position/yaw fusion、输入/变换有效性、时间与 epoch 完整性、桥接器控制发布权和其他原有控制状态机行为。
- 增加定向测试，构造数值上很大的位置/yaw差并确认不会形成数值门故障。该测试不表示该差值在物理上无害；真实误差需由后续 SITL 量测。

## 验证

- `bash tools/project.sh test`：415 项单测通过；navigation-adapter ROS integration 与 official EGO policy ROS integration 通过。
- `bash tools/project.sh build ros`：17 个 ROS 包通过，包含 `uav_px4_bridge`。
- Python 编译、冻结工具 `bash -n`/`py_compile`、协议 JSON 校验、`git diff --check`、`python3 tools/project_status.py` 通过。
- 新 runtime contract：`5c3cbe4d4621e7c520d323e80911a2fc0ce09ae040c22adbf313c2fc21e45c01`（665项）。桥接器安装模块 SHA-256：`bad90f0eea2f6e6336f555add1d7431e9aa1d8d65b1b4746e4bbad1af5926e9f`。

## 尚未验证

代码/构建通过不代表飞行闭环通过。当前只冻结同场景 #369；SITL 动态障碍任务、实际误差与时效、接触、净空和安全终态仍待运行测量。
