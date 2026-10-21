# P6 地图状态与 RGB-D 关键帧接口交接

日期：2026-10-19

## 本轮目标

按完整 GOAL A–H / P0–P6 继续推进，完成 GOAL G 后续算法接口的真实调用证据。范围限于单 D435i 仿真；独立探针不订阅真值、不发布 PX4 控制，也不请求 Offboard 或解锁。

## 已确认与决定

- 新增 `MapStatus`、`GetMapStatus` 和 `RGBDKeyframe` 接口。地图状态只报告 reset/输入门、map_id、最近深度和占据云时间、占据点数及配置哈希；plan_env 无 free/unknown 计数接口，因此不伪造。
- RGB-D 关键帧保留源图像及 CameraInfo 消息头，分别按 RGB 与 depth 源时间插值相机位姿，附 epoch、map_id、SDF 标定哈希，并受既有定位、深度和 map-reset 门控。
- 修复了 Python ROS Header 赋值的别名问题，避免写 pose frame 时改写深度图消息头。
- #05 以当前定位位姿作为 action 目标，查询当前地图并验证旧 epoch 查询被拒绝；实时收到带有限位姿的 RGB-D 关键帧，action 在 61 条 feedback 后返回成功。该零距离目标证明接口交接和终态反馈，不证明位移动作或飞行。
- PX4 bridge 日志为 `DISABLED/service_enable_required`；独立探针仅发布 `/parameter_events`、`/rosout`。topic 图没有 `/debug_truth`。
- GOAL G 三项现有文档/取消与 epoch 测试、地图门控证据和 #05 live probe 已齐，G 标记通过；P6 仍进行中，A–F/H 和完整验收仍未完成。

## 待办

- P6 仍需地图快照回读、几何覆盖、故障和负载场景以及最终验收；#05 占据云虽收到但点数为 0。
- 回到 P5，继续分析 #191 安全降落期间 PX4 failsafe / Offboard signal loss 与定位状态的时序，不能把时间相关性写成因果。
- 当前工作树初始已有用户修改；未 stage、commit 或 push。完整初始状态快照未保存，GOAL H 仍待补足。

证据：`progress/evidence/p6-handoff-interfaces.json`。改动记录：`progress/changes/2026-10-19-071-p6-map-status-rgbd-keyframe-interfaces.md`。
