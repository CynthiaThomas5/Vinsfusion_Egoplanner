# P6 地图状态、epoch 查询与 RGB-D 关键帧接口

对话摘要：[`collaboration/dialogues/2026-10-19-071-p6-map-status-rgbd-keyframe-interfaces.md`](../../collaboration/dialogues/2026-10-19-071-p6-map-status-rgbd-keyframe-interfaces.md)

## 修改

- `uav_interfaces` 新增 `MapStatus.msg`、`GetMapStatus.srv`、`RGBDKeyframe.msg`，并声明生成依赖。
- `mapping_input_adapter` 新增 `/mapping/status`、`/mapping/get_map_status` 与 `/mapping/rgbd_keyframes`。查询支持 `expected_epoch`，跨 epoch 返回拒绝；占据统计来自现有 EGO `PointCloud2`，不推断 free/unknown。
- RGB-D keyframe 仅在 localization、depth-health 与 map-reset 门均通过后发布，按图像源 stamp 分别插值相机位姿，并保留图像/CameraInfo header、epoch、map_id 和 SDF calibration hash。
- 新增最小 no-control live probe：读 localization/map/keyframe、尝试旧 epoch 查询、以观察位姿发导航 action、采集反馈与终态；补充接口 README 和契约表。
- 修复嵌套 ROS Header 对象赋值引发的 frame aliasing，使 keyframe depth image 的 optical frame 保持不变。
- GOAL G 标记通过；P6 仍为 `in_progress`，完整 GOAL A–H 未完成。

## 验证

- 固定 Jazzy 镜像 `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8` 新 build/install 路径内 4 包构建通过：`uav_interfaces`、`uav_sim`、`uav_mapping`、`uav_navigation`；日志位于 `artifacts/runs/p6-handoff-interfaces-build-20261019-02/build.log`，退出码 0。
- SITL #05（ROS domain 207）通过：当前 map query accepted/input_ready；旧 epoch 以 `epoch_mismatch` 拒绝；RGB 与 depth 源 stamp 差为 0、各自 pose stamp 匹配对应图像、位姿有限且位于当前 epoch frame；action 使用观测位姿，收到 61 条 feedback，终态 `succeeded/position_yaw_tolerance_held`。
- #05 probe publisher list 仅含 `/parameter_events` 与 `/rosout`，`/fmu/in/*` probe publisher 为空；bridge 日志为 `DISABLED/service_enable_required`；topic list 与 bridge subscription graph 不含 `debug_truth`。PX4 log 没有 arming transition；本轮未请求解锁或 Offboard。
- P4 ROS action 取消和旧 epoch goal 拒绝测试、P2 epoch map reset 与 clock rollback 证据支撑 G 的取消及失效拒绝范围。
- 保留失败／中间运行：#01 ROS domain 超范围；#02 世界生成产物冲突；#03 暴露 Header aliasing；#04 用偏移目标，只作为接口诊断。均不计 #05 通过证据。

## 局限与下一步

- #05 收到占据云时点数为 0；此轮只验证状态查询，不验证地图有实际障碍、覆盖、快照回读或 free/unknown 语义。
- action 的目标就是当前观测位姿，成功证明 goal/action handoff 和终态反馈，不证明平移、避障、轨迹跟踪或 PX4 行为。
- 后续继续 P6 完整场景；近期优先回到 P5，分析 #191 的降落和 failsafe/Offboard signal-loss 时序。
