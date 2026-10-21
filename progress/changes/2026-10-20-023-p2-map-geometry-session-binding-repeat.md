# P2 单墙地图几何独立复测 #243

对话摘要：[2026-10-20-023](../../collaboration/dialogues/2026-10-20-023-p2-map-geometry-session-binding-repeat.md)。证据：[独立动态复测与 raw VINS publisher 观测](../evidence/p2-map-geometry-repeat-20261020-243.json)。

## 结果

修正 run-local harness，从本轮生成的 `session/session.json` 读取 VINS namespace，并在启动前断言它与定位适配器预期 namespace 完全相同。使用 Jazzy 固定镜像、ROS domain 116、GPU/EGL 和容器内 Xvfb，未启动 PX4／控制节点；真值仅由 motion 工具离线记录。只读 raw VINS 探针观察到唯一 publisher 均为本 epoch 的 `vins_estimator`：62秒内 677 条优化里程计、8,926 条传播里程计、687条 telemetry，全部输出有限值且 initialized telemetry 为677条；未订阅真值或IMU诊断话题。

50.036秒 mapping probe 全程保持 TRACKING 和 depth READY，收到535条适配器优化里程计、1,014组同 stamp EGO 位姿／深度输出；地图最大1,924点。单 SE(3) 固定尺度轨迹对齐 RMSE/P95/最大位置误差为 0.02134/0.03699/0.04251 m，姿态 RMSE 1.133°。占据点距单墙可见面的最近残差中位数/P95/最大值为 0.02562/0.09049/0.13886 m，98.39% 在10 cm内；点云时间戳使用仿真时钟，距最近优化位姿1 ns。

与 #08 的同墙描述性结果相比，轨迹 RMSE 相近，地图残差有轮间变化。两轮只覆盖同一个墙面和运动 profile，不足以冻结地图几何误差或净空标准；点云最大快照也不度量未知／自由分类、膨胀、碰撞或规划反应。

## 复测判定与下一步

#232–#239 排除原因已由旧 session namespace 错误确认。#240 在容器 Xvfb 启动等待阶段中止；#241 namespace 修复后短暂 TRACKING，随后以 `telemetry_stale` 锁定，几何数据排除；#242 无 Xvfb 时 Ogre2 渲染初始化崩溃。只有 #243 进入完整有效观察窗并作为独立探索性地图样本。

不改变 P2 阶段通过状态、健康门、配置或验收阈值。GOAL F 仍未达到冻结条件：还缺多种障碍几何／覆盖、飞行跟踪误差、机体最小间距、最大数据年龄、重规划期限及故障检测／退出时延的规范场景基线；D/E 正式验收尚未开始。原始产物与 evaluator 报告的哈希见轻量证据 JSON。
