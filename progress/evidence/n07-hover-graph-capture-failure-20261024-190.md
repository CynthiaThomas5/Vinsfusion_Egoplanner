# N07 #190：完整 freshness 窗口与 no-goal hover 通过，graph 前置快照未通过

**结果：本次 no-goal hover 与 ULog 通过，但严格 N07 独立评估为 FAIL；连续计数仍为 0/3。** 运行目录：`artifacts/runs/n07-20261024-190-01/`。逐项结果、运行哈希和原始证据索引见[JSON 报告](n07-hover-graph-capture-failure-20261024-190.json)。

## 固定条件与 N05

本次使用固定镜像 `sha256:099ab9afecd28b7354f6d6494944b1db30c7c67c973e9b93b03f87aca7ad6f8`、固定 runtime contract、spawn `-6.5,0,0.3,0,0,0`、`wall_box_column` 和 `n06_full_airframe_retreat_240_oblique_separated_return`。未修改源码、控制参数、健康阈值或 N05 阈值。

初始 online/offline gate 按预期一致拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。支架扫描记录 12/12 阶段，epoch `0662b6c2bcaf44acb2cb9b5a15e965c5`、map id `0662b6c2bcaf44acb2cb9b5a15e965c5-d7c48924ec5c4a23b169a6731c2784d2`。attached、post-release 和 current-area 三组 online/offline gate 均接受 `all_entry_phases_known_and_clear`，identity 一致；三组的最大深度源龄分别为 0.116、0.160、0.144 秒，限值均为 0.4 秒。N05 汇总 `diagnostic_pass=true`，14/14 项为 true。

Fixture helper 仍将本次结果标为 failed，错误是 `localization changed or became invalid during physical scan`。其记录显示阶段数 12、最终 localization 回到 valid（normalized cost 0.464）、attachment 为 attached→detached、fixture 已删除且场景模型不存在、PX4 状态样本均 DISARMED、最终 landed。这个 helper 错误被保留，不从 N05 summary 的 14 项结果中抹去。

## 延长的定位窗口与 hover

只读 freshness probe 在 ready marker 后启动，以 `flight.json` 为结束标记，收到结束文件后继续采样 2.039 秒，覆盖 178.646 秒墙钟时间并写入 10,736 条事件。窗口内状态仅出现 `TRACKING / valid / fresh_inputs_and_usable_solver`；相机、IMU、VINS telemetry、raw 与优化里程计均继续更新。这个结果说明本次释放到 hover 的窗口没有复现 #189 的 stale 锁存；由于本次同时取消了 #189 gate 后的长时间分析间隔，不能单独断言 #189 根因只由探针结束时刻造成。

`run_vio_no_goal_hover.py` 的前置条件通过，桥接 enable 与 disable 均接受，无导航目标；空中保持 30.0 仿真秒，记录器确认曾进入 ACTIVE/armed，随后 `landed_and_disarmed=true`。PX4 ULog 分析 12/12 项通过：EV position/yaw 融合实际出现，GNSS aiding 全程未激活，EKF2_EV_CTRL=15、EKF2_GPS_CTRL=0、SIM_GZ_EN_ODOM=0，最终 landed/disarmed。独立定位误差与保持漂移均成功测得；N07 未规定数值精度门槛，故仅报告测量值。

## 未计入三连的原因

ROS graph 无真值 ROS 节点／话题。空中 `airborne_active` 和结束 `flight_result_written` 两张快照均显示四个 PX4 控制话题各有且仅有一个 `uav_px4_bridge` publisher。但第一张 `pre_enable_or_early_run` 快照四个话题全为 0 publisher，因此原始检查和既有全快照 reconcile 均失败；N07 hover evaluator 的 `read_only_ros_graph_unique_control_owner` 为唯一 false 项，最终评估 10/11、`result=FAIL`。空中快照通过不替代既有严格评估，因此不增加连续通过数。

结束时 flight 与 ULog 均记录已落地并解除武装；`bash tools/project.sh stop n07-20261024-190-01` 后容器 `exited 0`，无活动项目容器。额外的一次 `ros2 topic echo --once` 只读检查未能解析话题类型；安全结论依据 hover 报告、图中最终 bridge 状态及 ULog，而不依据该次 CLI 检查。

## 下一步

N07.37 #191 保持相同 runtime、profile、门限与 30 秒 no-goal hover，只调整 graph 记录开始时刻：由 run-local 只读等待器观察到 bridge `ACTIVE` 且 armed 后，再启动未修改的 `capture_n07_ros_graph.py`，使 graph 快照覆盖空中与最终 landed 状态，不采集一个尚未建立控制 publisher 的 pre-enable 图。其余 N05、freshness、真值、alignment、bridge 和 ULog 记录保持不变。
