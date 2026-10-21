# 修改与验证记录

- 任务 ID／日期：GOAL C occupied map snapshot #269／2026-10-20
- 对话摘要：[037 对话摘要](../../collaboration/dialogues/2026-10-20-037-goal-c-map-snapshot-readback.md)
- 修改文件：`tools/export_occupancy_snapshot.py`、`docs/contracts.md`、GOAL C 证据报告、`progress/CURRENT.md`、`progress/evidence/README.md`、`progress/goal-checklist.json`。
- 行为变化及原因：新增离线 exporter，将一份已记录的 EGO occupied PointCloud2 采样打包为 PCD 与 sidecar 元数据。校验输入云的 epoch/frame、live map sample stamp/点数、此前 map reset 日志中的 map_id，并逐点验证 float32 PCD 回读。工具不启动 ROS 节点、不发布控制，不把 free/unknown 或跨 epoch 数据伪装成 occupied map。
- 验证类型：静态、离线实测回读；未新增或启动 SITL。
- 命令与环境：`python3 -m py_compile tools/export_occupancy_snapshot.py`；对运行 `p2-map-multi-obstacle-geometry-20261020-247` 执行 `python3 tools/export_occupancy_snapshot.py --run-report progress/evidence/p2-map-multi-obstacle-geometry-20261020-247.json --probe artifacts/runs/p2-map-multi-obstacle-geometry-20261020-247/probe.json --cloud artifacts/runs/p2-map-multi-obstacle-geometry-20261020-247/map-cloud.json --mapping-log artifacts/runs/p2-map-multi-obstacle-geometry-20261020-247/mapping-adapter.log --input-config config/components/mapping/ego_input.json --camera-model simulation/models/d435i/model.sdf --output-dir artifacts/runs/p2-map-multi-obstacle-geometry-20261020-247/map-snapshot`。
- 结果及证据位置：同 epoch `9568a1e570274064aa8325a93520fae9`、map_id `9568a1e570274064aa8325a93520fae9-af391e20c26b46cd8704d03905afe601`、frame `odom_<epoch>`、source stamp `23068000000 ns`；1264 个点与 live probe 同 stamp 样本计数一致，PCD 读回 1264 点且 float32 坐标逐点相同。轻量报告：[GOAL C snapshot report #269](../evidence/goal-c-occupied-map-snapshot-20261020-269.json)；原始 cloud、probe 与导出物在对应 `artifacts/runs/.../map-snapshot/`，SHA-256 见报告。
- 未验证与 PROVISIONAL：此为 run #247 的历史采样归档，不是新运行；采样属于后续 `normalized_cost_exceeded` 之前的同一 map_id。该云只表示一个时刻的 occupied 点，不包含 free/unknown；没有验证整场景覆盖、跨时刻地图持久化、地图几何阈值或避障。GOAL C、P4、整体 A–H 仍未通过。
- 下一步：在新的无真值建图诊断 run 中同钟保存 MapStatus 与 occupancy 快照，并验证移动过程的地图累计／更新；随后继续几何覆盖、规划和正式定量验收。

代码提交存在时记录实际 commit；未提交则以工作树状态和本记录引用的文件／产物哈希追溯，不虚构提交号。
