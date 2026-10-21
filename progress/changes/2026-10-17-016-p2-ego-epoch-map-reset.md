# P2 EGO 跨 epoch 地图 reset 验证

日期：2026-10-17。对话摘要：[2026-10-17-016-p2-ego-epoch-map-reset.md](../../collaboration/dialogues/2026-10-17-016-p2-ego-epoch-map-reset.md)。

- 修改：新增 `tools/probe_mapping_epoch.py`，运行时检查旧 epoch 占据图清空、reset barrier 等待期间输出停止、新 epoch 输入恢复后只产生新 epoch frame；新增 run harness，单独使用 ROS domain 188。未修改生产节点、vendor 源码、配置、PX4 控制或物理仿真源。
- 观察：固定 Jazzy 容器中旧 epoch 先产生4个占据点；新 epoch 触发 adapter 与 plan_env reset；reset 后不发送传感器样本的等待期内深度／位姿输出保持5／8；之后新 epoch 获得7组配对 stamp，8条 pose 均使用 `odom_<new_epoch>`，map 再次产生4个点。probe exit 0。具体数据与 hash 见[证据报告](../evidence/p2-ego-map-epoch-switch.json)。
- 验证：epoch ROS 集成 probe 通过；mapping-input 4项、depth-gate 4项、localization-health 9项测试通过，后者包含 clock regression 锁存；Python 编译通过；`python3 tools/project_status.py` 报 PASS（仅结构／设计检查）。全量 colcon 未重跑：生产源码未改动，运行复用已有16包构建 overlay。[原始运行资料](../../artifacts/runs/p2-mapping-epoch-switch-20261017-01/)已记录 probe、adapter、EGO 日志及 SHA-256。首次 ROS setup 因 shell nounset 报错的 harness 失败也留档，修改 source 顺序后重跑通过。
- 局限：这是单次 synthetic epoch switch，不是 GOAL E 两次独立故障注入验收；没有回放 ROS `/clock` 倒退或实际 VINS 重启。probe synthetic odometry QoS 与 EGO 可靠 planner odometry reader 不匹配并记录 warning，本次不声称规划输入或规划响应通过。无真实地图几何、PX4 SITL／飞行证据。
- 下一步：在实际 localization/mapping 链路补做 ROS 时间回退与 VINS restart 的独立重复故障注入，验证目标／轨迹取消及 map reset；继续多场景几何与规划闭环。P0–P6 和 A–H 状态不变，GOAL.md 尚未通过。
- 未 stage、commit 或 push。
