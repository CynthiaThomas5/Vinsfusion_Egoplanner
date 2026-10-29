# 对话摘要：N07 PX4 时间参考修复

- 用户要求先处理 PX4 时间戳与 ROS 时钟不对齐，并明确 N07 验收次数无需连续、已通过项不再复测。
- #198、#200、#204 已按相同固定 runtime 与 contract 审计通过，N07 累计为 3/3；保留证据，不复测。
- #203 首次 `px4_telemetry_stale` 时 ROS `/clock` 回调落后 PX4 HRT 196 ms；旧逻辑把新鲜遥测判为未来。桥接器已切换为 PX4 HRT／映射 `/clock` 较新值作为时间参考，门限不变。
- ROS 构建、源码语法检查及四次历史轨迹的离线复算通过。
- #206 在线集成验证被 N05 支架扫描 `normalized_cost_exceeded` 挡住（7/12 阶段）；没有飞行。已确认落地、disarmed、支架脱离和移除，容器 exit 0。
- #203 另有 VIO odometry 停顿及 `external_odometry_stale`，与 PX4 clock 错判分开记录。
- 后续仅需在 N05 正向准入后做一次有针对性的在线时间参考验证；不能重跑 #198/#200/#204。
