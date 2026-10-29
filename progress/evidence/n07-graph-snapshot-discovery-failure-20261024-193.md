# N07 #193：active-window graph 首快照未完成 DDS discovery

## 判定

**N07 本轮不通过，连续合格 cold start 归零为 0/3。** #193的12/12支架路线、N05 14/14、30.0仿真秒 no-goal hover、定位/遥测稳定、ULog 12/12和最终 landed/disarmed均通过；但ROS graph首快照在 recorder 尚未发现 bridge 状态或控制 publishers 时读到四个 PX4 控制 topic 均为0 publisher。后续 airborne 与 landed 快照都通过，严格全快照要求仍失败。运行档案：`artifacts/runs/n07-20261024-193-01/`。

## N05 与 hover

初始online/offline gate一致拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`；全机支架扫描完成12/12。attached、post-release、current-area gate均接受 `all_entry_phases_known_and_clear`，同epoch/map，summary 14/14全true。Fixture helper保留错误 `fresh DISARMED status is required for every fixture command`；独立检查确认detached/removed且不可能残留。

无目标 hover脚本PASS，完成30.0仿真秒（33.478墙钟秒），无导航目标，定位tracking及PX4 telemetry stability通过。最终 landed/disarmed为true。可选VIO freshness probe未运行；#191 telemetry stale未复现。PX4 ULog **12/12 PASS**：EV position/yaw融合实际出现，GNSS/GPS flags未激活；`EKF2_EV_CTRL=15`、`EKF2_GPS_CTRL=0`、`SIM_GZ_EN_ODOM=0`，最终landed/disarmed。ULog SHA-256：`6676b2d96835b85ec502c2616373d999dc78eff56b26b15821e1771bf23d659f`。

## Graph 与独立评估

Active-window waiter记录到 `/uav_px4_bridge/status` `ACTIVE && armed`，然后启动未更改的graph recorder。首个 `pre_enable_or_early_run` 快照中`bridge_status=null`，四个控制topic publisher count均为0；`airborne_active`和`flight_result_written`两个后续快照各topic均为唯一 `uav_px4_bridge` publisher，且无truth ROS node/topic。GID reconcile因首快照缺publisher失败。

独立N07 evaluator为 **10/11 FAIL**，唯一失败是 `read_only_ros_graph_unique_control_owner`。独立位置误差 p95 **0.0127 m**、最大 **0.0129 m**；yaw误差p95 **0.1020°**；Gazebo hold displacement最大 **0.0924 m**，PX4 local displacement最大 **0.0874 m**。这些数值仅报告测量，GOAL未为它们设定额外门限。

保留raw bridge timeline。重复同phase状态行由运行目录中的同一transition projection折叠后，未修改evaluator仍仅因graph check失败。raw graph、reconciled graph、trigger状态、评估报告与SHA均在证据JSON和run目录中。

## 安全收尾与下一步

`flight.json`及ULog确认landed/disarmed；场景模型回读不含支架fixture；容器`Exited (0)`，活动项目容器为0。helper状态错误原样保留。下一项#194保持飞行代码、N05、健康/控制阈值、无probe observer set和hover完全不变，仅让run-local只读graph recorder等待其自身DDS发现ACTIVE状态及四个唯一bridge control publishers后再采首快照；发现等待有界，超时则明确失败。
