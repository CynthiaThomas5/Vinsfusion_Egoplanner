# 2026-10-27 N10 #361：移除项目定位门限后的复测

## 用户要求

继续完成 N10。凡会阻止运行的定位健康门限等保护措施，先审计源码；若由本项目自行添加，则删除该运行保护。

## 已确认与实施

- `uav_localization` 质量阈值、定位/优化里程计回执龄检查、初始化/连续合格帧门限均为本项目策略，已从运行逻辑移除；原始 cost、source age 仍采集。
- `uav_navigation` 不再按自定义 localization/odometry receipt-age 阈值拒绝或中止任务；此前仅 schema 检查的 `acceptance_calibration_limits` 配置字段和空检查也已清理。
- 时间戳单调、VINS epoch/发布者身份、消息/坐标完整性、地图身份与时效、PX4 bridge 控制约束及官方 EGO inflated-occupied 碰撞行为仍有效。
- 既有 17 包 ROS 构建仍适用（源码包未在本轮再变）；本轮 Python runner/config 清理后，`bash tools/project.sh test` 通过 413 项和 navigation/official EGO 两项集成。

## 决定与待办

使用与 #357 相同的速度参数、起点/目标、官方碰撞策略和 600 秒任务，创建新冷启动 #361。#357 的运行时旁路结果仍保留为历史诊断；#361 验证删掉运行门限后的实际流程和完整观测。#361 的测量只作诊断，不直接冻结安全预算。协议：`progress/evidence/n10-health-gates-removed-speed080-16m-protocol-20261027-361.md`。

## #361 运行结果

#361 通过 runtime 指纹核对与 40.004s 只读 preflight。目标 action 成功；独立位置/yaw驻留 3.0187s、最小三维位置误差0.0531m；600/600仿真秒ACTIVE保持完成。raw normalized cost p95/max=1.2547/3.2712，越过历史1.0参考后定位仍有效；无禁止接触。raw VIO位置p95/max=0.3142/0.3234m、yaw p95/max=5.691/5.854°；EGO跟踪p95/max=0.5016/1.0311m；map source/occupancy age max=0.160/0.112s。五个观察器确认覆盖终态，独立PX4/bridge读回LANDED/disarmed/control disabled/zero control，容器已安全停止。该运行没有障碍净空、重规划/故障注入或重复性证据，N10.3继续中。

首次 driver 在飞行前因运行快照文件名笔误退出，无目标或enable；3秒只读末态安全。修正driver并更新协议哈希后，同一未动作冷启动继续完成任务。详见 `progress/evidence/n10-health-gates-removed-speed080-16m-20261027-361.md`。
