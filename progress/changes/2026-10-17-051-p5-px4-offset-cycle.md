# P5 75秒 PX4 offset 重估与 stale 周期复核

对话摘要：[2026-10-17-051](../../collaboration/dialogues/2026-10-17-051-p5-px4-offset-cycle.md)。

## 结果

- #112 使用ROS domain 228、新 Gazebo partition 和独立 PX4 build 副本运行75秒被动 SITL。VIO送达PX4 473条；EKF2 EV position/yaw融合可见、GNSS flags全零、truth topic/订阅均不存在。控制输出为零、bridge保持DISABLED、车辆disarmed。
- 观测到两次 estimated_offset 重估：12.814–18.340秒和44.706–49.988秒，相隔31.892秒。两段各对应一簇 `px4_telemetry_stale` detail，共70/576条，时间区间为12.954–18.554和44.853–49.954秒。estimated_offset平台期间，每路高频遥测收包源龄恢复到毫秒级；末次重估后 attitude/local-position P95为4.771/8.951 ms。
- 两个平台期间 observed_offset继续漂移，其速率大小约0.5824秒/墙秒，而 `/clock` 约0.4176仿真秒/墙秒；速率绝对值之和约1。#112 在12.814066秒和44.705552秒都观察到 `estimated_offset=0`，下一条TimesyncStatus分别在0.48/0.38 ms后将估计值设为 observed_offset；这与 PX4 `Timesync::reset_filter()` 后由首个样本重建估计相符，属于滤波器实际重置的直接状态证据。PX4 v1.17源码还显示高偏差路径和 `deleteSession()` 都能重置滤波器；Agent日志只有一次会话建立、无重连记录，因此高偏差重置是目前最有力解释。PX4 debug 文本和内部计数器未捕获，故高偏差计数触发仍是有根据的推断，而非直接日志证明。
- 这说明当前桥接 freshness 门会在估计映射变更期间触发保护；它没有证明最终视觉闭环可容忍周期失效。readiness末端为0，原因仍是DISABLED下 `px4_preflight_failed`。

完整原始样本、运行参数、源码与产物哈希见[轻量证据](../evidence/p5-px4-offset-cycle-75s-20261017-112.json)。

## 验证

- 从归档 `TimesyncStatus` 样本离线复算，两次 `estimated_offset=0` 后紧随的首个估计均等于观测值；70条 stale detail 与36/34两簇之和一致。#109–#112每份报告列出的原始run artifact SHA-256均复核通过。
- `python3 tools/project_status.py`：PASS；`git diff --check` 与 `git diff --cached --check`：PASS。本次没有修改PX4第三方源码、桥接行为或健康阈值。

## 限制与下一步

- 75秒不是GOAL规定的10分钟最终负载运行；没有Offboard、解锁、飞行、轨迹或避障验收。
- 下一步量化Gazebo lockstep、`/clock` 与 Agent wall-clock 的时基关系，并评估仿真专用映射/失效行为；保持健康阈值不变，先做隔离复测，再继续P5视觉导航和P4/P6缺项。
