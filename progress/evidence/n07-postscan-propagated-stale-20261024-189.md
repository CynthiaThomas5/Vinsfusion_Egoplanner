# N07 #189：N05释放准入通过，定位在hover前失效

**结果：FAIL_NO_FLIGHT；N07连续合格cold start保持0/3。** 运行目录：`artifacts/runs/n07-20261024-189-01/`。

## 固定条件与N05准入

使用新epoch `9f5cf153ed184864a7aa9b90806100ef`，map `9f5cf153ed184864a7aa9b90806100ef-33646b66932a493f854f17c90fff2dd3`。镜像、runtime contract、spawn `-6.5,0,0.3,0,0,0`、wall布局、`n06_full_airframe_retreat_240_oblique_separated_return` profile、hover程序及健康/N05门限均未改变。

初始N05 online/offline一致按预期拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。全机支架扫描12/12阶段完成，ready marker为attached、PX4 `vehicle_arming_state=1`、无truth输入、无控制或目标发布。等待2.000072925秒后attached N05在线检查接受；offline replay匹配，snapshot/source/fusion age为0.112/0.124/0.044秒。释放helper返回原始错误 `fresh DISARMED status is required for every fixture command` 并exit 1；它记录attached→detached、fixture已移除且场景中不存在支架。post-release与current-area online/offline均接受 `all_entry_phases_known_and_clear`，同一epoch/map；相应freshness为0.104/0.132/0.052秒和0.108/0.124/0.052秒。`n05-run-summary.json` 的14项检查全部true。

## 释放后时间线与停止原因

只读VIO freshness probe从ready marker后启动，在N05 release/current-area决策结束时停止，覆盖81.96墙钟秒、至仿真sim 480.992秒。窗口内LocalizationStatus一直`TRACKING/valid`；相机、IMU、VINS telemetry、raw/adapter odometry都产生连续事件。该探针被提前结束，没有覆盖后续hover前置等待。

`run_vio_no_goal_hover.py` 随后因 `vio_bridge_map_preconditions_not_ready` 失败：`preconditions_ready=false`、没有service call、导航goal、position command或takeoff。状态时间线记录sim 555.724秒 bridge `DISABLED/external_odometry_stale`，随后sim 556.208秒为`DISABLED/localization_not_tracking`；最终LocalizationStatus state 4、`valid=false`、reason `propagated_stale`，source stamp停在555.724秒，accepted optimized/propagated计数为8283/136650。失效的具体源龄或receipt龄越限条件没有被探针覆盖，不能推断根因。

PX4最终`arming_state=1`、LandDetected `landed=true`且at-rest；bridge DISABLED、armed=false、control_enabled=false。ROS graph捕获到唯一bridge控制publisher和无truth命名节点/话题，但未出现airborne snapshot，因此不构成N07 graph验收。没有悬停、空中ULog评估或11/11独立hover评估。记录器完成写盘后，`bash tools/project.sh stop n07-20261024-189-01`确认容器`exited 0`、无活动项目容器。

## 下一步

#190保持同一运行条件。唯一诊断变量是将只读freshness probe的结束标记延长到`flight.json`生成后，覆盖hover前置等待及结果；全部N05门禁和14/14汇总通过后立即启动no-goal hover，避免门禁结束到飞行前置之间的额外等待。只有tracking/freshness仍通过时才允许探针自身调用bridge enable；失效继续fail-closed。详细SHA见[JSON报告](n07-postscan-propagated-stale-20261024-189.json)。
