# P2 动态地图几何独立复测前置条件失败 #232–#239

对话摘要：[2026-10-20-022](../../collaboration/dialogues/2026-10-20-022-p2-map-geometry-repeat-preflight.md)。证据：[复测前置条件与 GOAL F readiness](../evidence/p2-map-geometry-repeat-preflight-20261020-232-239.json)。

## 结果

原 #08 单墙几何探索只有一轮描述性样本。#232、#233、#234、#236、#238、#239 六次动态复测均没有产生当前 session 的优化里程计、EGO 位姿／深度输出或地图点，全部排除在几何误差统计之外。核对 run-local 启动脚本后发现共同错误：VINS 的 ROS namespace 仍从 #08 的旧 session 读取，而定位适配器按每轮新生成的 session manifest 订阅新 epoch namespace。VINS 日志每轮都包含 `Initialization finish!` 并持续运行 solver，因此失败发生在新 session 的 VINS→适配器话题绑定，不能归因为相机无特征或 VINS 算法初始化失败。

静态 GPU/EGL/Xvfb 预检 #237 的 31 项传感器检查全部通过，但它不覆盖 VINS session namespace。#239 改回 #08 使用的 ROS domain 116 仍失败，是因为脚本 namespace 错误未修复。六轮运动 SDF 与 #08 哈希相同；当前结论是复测 harness defect。

## GOAL F 决策

地图几何仍只有一次探索性墙面样本，缺少独立有效复测；飞行跟踪误差、机体最小间距、数据年龄、重规划期限及故障检测／退出时延也没有足够的规范场景测量。暂不写入或冻结 `config/acceptance.json`，D/E 正式验收尚未开始。P2 阶段表状态不因这些无效复测改变；本记录只保存排除原因。

未改配置、健康门、验收阈值、里程碑或 canonical 源码。原始日志、motion/probe 数据、session manifest 与 run script 的 SHA-256 均列于轻量证据报告，run 产物保留在各自 `artifacts/runs` 目录。
