# uav_mapping

当前实现包括两部分：

- `depth_health_monitor` 检查模型约定的 frame、编码、尺寸、步长和数据长度，并按稳态墙钟检测输入超时；状态以可靠 transient-local QoS 发布在 `/mapping/depth_health`。新鲜度阈值为 config 中 PROVISIONAL 的 1.0 秒稳态墙钟；时间戳回退会锁定本次监视进程。
- `mapping_input_adapter` 只向 EGO 已有 `plan_env::GridMap` 转发输入。它使用 `/localization/optimized_imu_odom` 在深度源 stamp 两侧作有界位置／姿态插值，按 SDF 几何组合 IMU 到 depth optical frame 的外参；只有定位、深度健康和 plan_env reset 服务都就绪时才发布同 stamp 深度与 `PoseStamped`。输入状态无效、源时间不递增或 epoch 变化会关闭输入并请求重置 map_id。

`plan_env` 是唯一占据更新器。本项目补丁让它跳过零／无效深度像素（保持 unknown），提供 `/mapping/reset_map` 清空占据、膨胀与射线缓存并切换 epoch frame，并给 occupancy PointCloud2 写入仿真 ROS clock 的发布时间戳。合成 ROS smoke 验证了同 stamp 输入和定位失效后清图；动态 D435i/VINS run #08 观察到 TRACKING、233 组同 stamp 深度／位姿和最多 1,787 个占据点。单次单墙探索对照的可见墙面残差中位数为 3.63 cm、P95 7.31 cm；点云 stamp 为 19.838 s 仿真时间，距最近优化位姿 4 ms。该测量未冻结验收阈值，也未评估重影、覆盖、unknown/free 分类、膨胀、间距、规划响应、PX4 或快照回读。EGO 目前停在 INIT，日志显示没有规划里程计输入。插值界限、状态年龄和有效像素采样检查仍为 PROVISIONAL。证据见 `progress/evidence/p2-ego-map-input.json`、`progress/evidence/p2-ego-map-live.json` 和 `progress/evidence/p2-map-geometry.json`；参数见 `config/components/mapping/ego_input.json`。

同一适配器提供 `/mapping/get_map_status` 与 `/mapping/status`，报告当前 epoch/map_id、门状态、最近转发深度时间、收到的 EGO occupied-cloud 点数和配置哈希；free／unknown 计数没有来源，故不暴露。它还以不超过 1 Hz 的速率发布 `/mapping/rgbd_keyframes`：RGB 与深度 stamp 差必须在配置界限内，位姿分别按各自图像源 stamp 插值，消息保留 CameraInfo、epoch、map_id 和 SDF 标定哈希。关键帧受与 EGO 深度输入相同的定位、深度健康和 map-reset 门控。集成验收见 `progress/evidence/p6-handoff-interfaces.json`。


`MapStatus` 仍不报告 free／unknown 体素，因为 mapping adapter 只消费 EGO occupied cloud。规范 EGO 依赖链现包含 patch 0021：`/mapping/get_occupancy_snapshot` 由 `plan_env` 只读返回 raw unknown/free/occupied 与独立 inflation mask；请求必须绑定当前 epoch/map_id，且受融合深度、位姿、timeout 与更新时间门控。`python3 tools/fetch_dependencies.py --source ego_planner` 按锁定清单重建包含此补丁的唯一 `src/vendor/ego_planner` 来源。#292–#296 隔离运行验证了服务回读、时序增长与同布局重复，但已知体素仍不足配置地图的1%，墙面约一格的摆动和首帧离群点原因未解；覆盖、几何完整性、重影、unknown 安全和规划用途仍未验收。服务重建与全包构建见 `progress/evidence/p0-ego-snapshot-canonical-build-20261020-297.json`；运行证据见对应的 #292–#296 报告。

#293 将体素快照延迟到运动开始后采集，配置地图已知体素约0.450%；离线固定尺度单 SE(3) 对齐后，1,319个raw occupied体素中心到场景SDF表面的距离中位数4.28 cm、P95 7.06 cm。箱体／圆柱样本分别仅64／41个；单快照不能检验地图完整性、重影、free-space准确性或规划安全。

#294 在同一epoch/map_id/frame内捕获三份快照，known voxel从13,688增长至19,878和20,283；raw occupied集合相邻Jaccard为0.702/0.885，几何残差均小于一个0.1 m体素。该指标只描述单次单场景快照，不能证明完整性、无重影或规划安全。EGO无目标且出现36条 odom/depth lost告警，planner readiness未验证。详见 `progress/evidence/p2-map-snapshot-temporal-growth-20261020-294.json`。

#295 的第二布局快照显示known voxel增至21,983；raw occupied集合重合和墙面中位体素位置变化约7 cm仍属单轮描述。EGO没有输入timeout，但运行没有导航目标，不能据此评价规划或避障。须在同布局新epoch复测并定义ROI指标。详见 `progress/evidence/p2-map-snapshot-temporal-growth-20261020-295.json`。

#296 在新epoch重复#295障碍布局时，墙面中位体素位置的一个栅格级摆动复现；首帧还有72个占据中心超过10 cm的SDF距离，后续两帧分别2/5个；首帧离群点都分配给大墙且在当前中心采样窗之外，该诊断窗不是验收ROI。墙面前表面x=3.0 m正落在名义地图x栅格边界index150；离线对齐后的边界距离支持单栅格side-selection假设，但不证实成因。应按capture phase与有界可见ROI分析原始深度、格点选择及大墙边缘72个首帧离群点，再讨论ghosting或覆盖标准。当前没有规划目标测试。详见 `progress/evidence/p2-map-snapshot-temporal-repeat-20261020-296.json`。
