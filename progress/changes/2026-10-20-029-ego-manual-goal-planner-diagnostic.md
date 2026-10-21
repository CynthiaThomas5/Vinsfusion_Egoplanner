# GOAL B/C/D/F EGO 手动目标与首条 spline 诊断 #255

关联对话：[2026-10-20-029](../../collaboration/dialogues/2026-10-20-029-ego-manual-goal-planner-diagnostic.md)。

运行未改项目源码、配置、PX4 或 canonical launch 默认值。EGO用 `flight_type=1`，在 localization TRACKING 与 mapping MapStatus `input_ready`、907个占据点时，run-local probe向 `/move_base_simple/goal` 发布一次目标，frame为 `odom_c428be26dd8e4ebfb68dfbf980866434`、(x,y)=(3.0,1.7) m；EGO唯一 goal subscription匹配，probe收到相同epoch的三阶B-spline（15控制点、traj_id=1）。目标回调固定Z=1.0 m。

run-local evaluator以601个 de Boor 采样点和单次固定尺度SE(3)真值离线对齐，位置RMSE/P95/最大9.22/15.80/16.61 mm、姿态RMSE1.57°。首条 spline 至已知箱体表面的最小有符号距离1.045 m，对 #246 的0.48194 m名义球形包络余量0.563 m；至圆柱为2.114 m，包络余量1.632 m。该数字只描述首条规划曲线与理想SDF几何。

全run日志随后记录285次replan失败及285条“terminal point of the current trajectory is in obstacle”告警；EGO曾进入 `EXEC_TRAJ`，之后在sim time 20.461 s的depth/odom timeout转 `EMERGENCY_STOP`，最后同步点 `last_sync_in_map=1`。终端地图输入门至46.752墙秒才随 `normalized_cost_exceeded` 关闭。没有轨迹服务器、跟踪控制器、PX4、setpoint或真值订阅，规划曲线未执行；不能据此宣布避障、目标到达或实际净空。

运行期0.5 m膨胀云峰值18,211点，同戳原占据1,188点（15.33倍）。圆柱地图误差、持续输入新鲜度、物理支架／线缆、定位误差、制动距离和故障退出标准仍未解决。保持 GOAL B/C/D/F pending，P2阶段状态不变。详见[planner证据](../evidence/p2-ego-manual-goal-planner-20261020-255.json)。

验证：容器退出码0；场景通过 `gz sdf -k` 并报告 `Valid`（保留现有 `gz_frame_id` schema warning）；run-local shell/Python语法及离线 spline evaluator通过。收尾时 `python3 tools/project_status.py` 通过；相关7份证据JSON解析通过，来源与原始产物哈希431/431匹配，工作区与暂存区 `git diff --check` 通过。项目源码无变化，不重复 colcon 构建。

短目标对照#256因`left_stale`、#258因`imu_stale`在目标前被门控。#257低负载双目观察未复现stale；#258保留mapper/EGO并去掉地图采样器后仍未就绪，raw VINS输出继续。下一步保持0.5 m设置，直接观测双目与IMU源龄、墙钟接收节奏和定位状态；只在健康定位及ready非空地图稳定后发短目标。
