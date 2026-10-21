# 修改与验证记录

- 任务 ID／日期：GOAL C live MapStatus snapshot #270–#273／2026-10-20
- 对话摘要：[038 对话摘要](../../collaboration/dialogues/2026-10-20-038-goal-c-live-mapstatus-snapshot.md)
- 修改文件：`tools/probe_mapping_runtime.py`、新增 `tools/probe_map_snapshot.py`、`tools/export_occupancy_snapshot.py`、`docs/contracts.md`、`README.md`、`progress/CURRENT.md`、证据索引、GOAL checklist 与 milestone 证据引用。
- 行为变化及原因：运行探针可记录 MapStatus，并在消息到达时按 epoch/map_id/frame、最后占据点云源 stamp 和点数匹配同一份 cloud，立即锁存原始点。Exporter 对嵌入 MapStatus 做同 epoch、ready/reset、stamp、frame 和 count 校验，再写 PCD/sidecar 并逐点 float32 回读。匹配缓存过期问题由 #271 暴露并修正。
- 验证类型：静态、编译、真实 SITL 静态传感器／在线地图采样和归档回读；未运行飞行控制。
- 命令与环境：`python3 -m py_compile tools/probe_map_snapshot.py tools/probe_mapping_runtime.py tools/export_occupancy_snapshot.py`；`bash -n` 检查 #271–#273 运行脚本；固定 `d435i-vins:dev` 镜像下 `colcon --base-paths src/own --packages-up-to uav_localization uav_mapping ...`，4/4 包通过；#273 `probe_map_snapshot.py --seconds 35 --require-pair`；`export_occupancy_snapshot.py` 回读 #273 点云；`python3 tools/project_status.py`。
- 结果及证据位置：#270 clean overlay 4/4 构建，但定位 TRACKING 后约0.33 s因`telemetry_stale`锁定，208条MapStatus中0 ready、0占据点。#271只保留最近128云的实现报告3条ready和1381最大点数，run结束时无配对。#272同 stamp 得1354点，但节点未启用`use_sim_time`，不算同钟快照。#273 对所有自维护ROS节点显式启用仿真时间：35 s observer 收到141条 MapStatus，其中3条ready；在 epoch `83d71077c3914f46ba1d7554320bfbcf`、map_id `83d71077c3914f46ba1d7554320bfbcf-6c97e62b73a64990b424fabda351ef54`、frame `odom_<epoch>`、源 stamp 4.885 s 精确匹配1341点cloud。MapStatus头stamp 4.926 s，与云stamp相差41 ms；PCD回读1341点且float32坐标逐点一致。该快照比 propagated_from_future 锁定日志早143 ms。[证据报告 #273](../evidence/p2-mapstatus-occupancy-static-snapshot-20261020-273.json)，raw probe、cloud、run报告与PCD/元数据在 `artifacts/runs/p2-mapstatus-occupancy-static-snapshot-20261020-273/`。
- 未验证与 PROVISIONAL：#273快照后143 ms以`propagated_from_future`锁定；EGO未收到目标并保持INIT；后续核对发现该launch将`odometry_topic`设为`odom`，未接入适配器输出`/localization/optimized_imu_odom`，故INIT/no-goal及SIGINT teardown异常不作为planner readiness证据；MapStatus `input_ready`不代表EGO健康。静态场景没有地图移动、几何覆盖、free/unknown分类、障碍净空或避障。健康门与验收阈值未改，GOAL C、P4/P5及整体A–H仍未通过。#270–#272不用于同钟快照通过证据。
- 下一步：逐条关联 VINS propagated odometry stamp 与 `/clock`，确定 future-stamp 偏差来源；再以运动场景验证地图累计/覆盖及 EGO 输入健康，之后继续无真值目标飞行、故障和长时验收。

代码提交存在时记录实际 commit；本轮未提交，哈希与工作树状态见关联证据和最终状态检查。
