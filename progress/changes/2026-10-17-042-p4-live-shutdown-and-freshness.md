# P4 当前源码 live shutdown 与定位 freshness 门槛复核

对话摘要：[2026-10-17-042](../../collaboration/dialogues/2026-10-17-042-p4-live-shutdown-and-freshness.md)。

## 改动

- config/components/localization/health.json：将 propagated 的最大源年龄从0.05 s临时调整为0.12 s。#81旁路观测到源年龄在63 ms时超过旧门槛而锁存，但接收年龄估算约59 ms、低于0.2 s；原始流最大观测年龄108 ms。配置说明保留 PROVISIONAL，未放宽接收年龄或其他流门槛。
- 新增 progress/evidence/p2-health-guard-review.json，记录 #81/#82 的原始／接收年龄、决策和限制；新增 progress/evidence/p4-navigation-live-active-20261017-84.json，记录当前源码构建的 live action/停机结果。
- 更新 P4 shutdown 证据、里程碑、CURRENT 与 README。#83明确标为不具修复验收资格：它加载了旧 run-private Python 覆盖层，重引入锁内 accepted-goal INFO；#84从当前源文件生成诊断副本并复跑。

## 验证

- python3 tools/test_localization_health.py：9项通过。
- 直接状态机检查：健康进入 TRACKING 后，1.0 s propagated 断流仍以 propagated_stale 进入 LOST。
- 独立 Jazzy uav_navigation build #77 的1/1包构建、10项任务状态测试和 ROS action adapter（分别阻塞 odometry warning 与 accepted-goal INFO 的锁释放回归）通过，构建输出见 artifacts/runs/p4-navigation-lock-log-outside-20261017-77/。
- #84 canonical /clock live：定位状态33条均为有效 TRACKING；目标发送前1.0 s全部输入门通过；地图1,414点；观测到匹配 epoch/goal 的 B-spline、READY 与 ABORT；action reason navigation_node_shutdown；navigation/probe exit code均0。当前源码派生 trace 有628个executor ready和74组回调入／出事件，无超过5 ms的锁事件。未启动 controller、PX4 或控制发布节点。
- git diff --check、JSON解析和 python3 tools/project_status.py 在本轮末执行并记录。

## 限制与下一步

#81/#82暴露的回调／接收停顿仍未解释；#82因约0.211 s仿真时间的 IMU 接收年龄超过既有0.2 s而触发 imu_stale，该 fail-closed 行为保留。0.12 s propagated 门槛及所有正式 F 阈值仍为 PROVISIONAL。#84只验证短时目标规划与 shutdown 清轨迹，不是目标跟踪或到达测试。继续 P4的真实轨迹跟踪／到达、定位／地图故障响应、多场景地图快照和10分钟负载，再推进 P5/P6 与 A–H。

主要证据：progress/evidence/p4-navigation-live-active-20261017-84.json、progress/evidence/p2-health-guard-review.json。
