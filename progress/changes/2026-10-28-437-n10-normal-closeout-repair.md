# N10.3/#437：正常控制结束清理与只读记录收尾

- src/own/uav_navigation/uav_navigation/node.py：同epoch bridge进入既有LANDING/LANDED/DISABLED/LOCKED时，取消仍持有的forwarded参考；当前action如仍运行则结束。成功action在ACTIVE期间仍保留hold，正常disable后不再遗留READY。只跟随已有控制阶段，无新增拒飞或降落分支。
- tools/test_navigation_bridge_closeout.py：四案例覆盖保持、精确goal/epoch的一次取消、异epoch不污染、既有landing结束当前任务。
- tools/diagnostics/record_n10_sensor_streams.py：monitor关闭bag后用event通知main bounded spin_once循环，避免无消息时executor.spin无法完成收尾。r02真实ROS隔离中断测试alignment/planner/bridge/resources/capture五项均exit0、部分报告存在、safe=false。r01失败保留。
- tools/debug_truth/evaluate_n10_replan_geometry.py：point query文件变可选，缺失仍输出真实same-snapshot/轨迹/净空依据，不推断缺失查询成功；在#436归档无查询文件条件下完成复算。原始flight和map数组不改。
- config/components/navigation/vehicle_envelope.json：全测试先因既有source SHA陈旧出现2fail/8error；重新audit确认包络bounds、含桨radius、mount、resolution及所有预算完全一致，仅刷新advanced_param.launch.py的来源SHA。旧配置和新旧SHA/audit保存于prepared，未改数值。

验证：bash tools/project.sh build ros：17包通过（7.49s）。定向35项通过。bash tools/project.sh test复验：562项全部通过及两个ROS集成通过；初次失败日志保留。真实ROS中断r02五项通过。源码快照已与#436目标前hash核验，后续修复未倒算为该飞行版本。

局限：正常参考清理尚无修复后SITL；#436参考审计发现model origin/IMU/base_link混用，统一评估器尚未修完，旧连续界还涉及body-frame平滑twist处理，不作为最终保证。N10.3未完成。下一项#438优先只读统一参考和归档复算，再修预算不足的实现，不恢复已排除的故障校准。

产物：artifacts/n10-prepared/n10-20261028-436-normal-map-halo-calibration/checks；artifacts/runs/n10-20261028-436-observer-interrupt-smoke-r02/result.json；#436报告。对话：../../collaboration/dialogues/2026-10-28-437-n10-normal-closeout-repair.md。
