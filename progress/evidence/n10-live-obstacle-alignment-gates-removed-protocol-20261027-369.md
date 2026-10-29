# N10.3/#369：移除项目本地 frame alignment 数值降落门后复测动态障碍

## 唯一变量

相对 #368，仅删除自维护 PX4 bridge 中将配对位置差超过 0.15 m 或 yaw 差超过 0.15 rad 锁存为 `px4_frame_alignment_drift` 的项目本地数值门。两项误差继续计算并发布为诊断数据。

保持 `clock_mapping_max_samples=128`、0.35 s 时间映射源龄、0.3 s 映射后里程计 receipt-age、有效变换、融合/配对条件、目标、起点、EGO planner、方箱、注入时刻、碰撞策略及观察器不变。

## 运行判据

相同场景下检查：PX4/bridge 是否继续工作且目标是否完成；D435i/EGO 是否观测箱体并生成几何避让轨迹；离线机体包络净空、接触、原始定位/时效诊断以及最终 landed/disarmed/control-disabled 读回。任何故障或到达失败均原样保留，不用新阈值将其判 PASS。该单次诊断不构成 N10/N12 正式资格。

## 冻结身份

- Run ID：`n10-20261027-369-alignment-gates-removed-live-obstacle`
- Runtime contract SHA-256：`5c3cbe4d4621e7c520d323e80911a2fc0ce09ae040c22adbf313c2fc21e45c01`（665项）
- Protocol SHA-256：`f53aa6ccbbc044024bee54a9d51c46de57d8d60864f896ad1b8f18f32bcd5ea1`
- Tool freeze：`artifacts/n10-prepared/n10-20261027-369-alignment-gates-removed-live-obstacle/n10-tool-freeze.json`
- Prelaunch identity：[JSON](n10-live-obstacle-alignment-gates-removed-prelaunch-20261027-369.json)
- 代码/配置回归与17包构建：[构建报告](n10-px4-alignment-gate-removal-build-20261027-369.md)

开始运行前 runtime contract、协议与run-local工具哈希必须匹配；Gazebo create 与 action-cancel 服务必须在发目标前可用。
