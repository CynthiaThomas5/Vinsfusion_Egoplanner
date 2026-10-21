# GOAL B/C 定位 telemetry 负载与 MapStatus 窗口诊断 #261–#266

关联对话：[2026-10-20-035](../../collaboration/dialogues/2026-10-20-035-localization-telemetry-load-isolation.md)。

在 #260 后给 run-local localization adapter 副本增加回调入口计数、最后源戳、最大callback间隔和锁定快照；原始健康策略、topic/QoS、回调顺序、单线程executor与控制发布集合未变。#261 在完整mapper/EGO加直接图像/IMU观察器时以`telemetry_stale`锁定：适配器最后接受的telemetry源龄329 ms（门限300 ms）、receipt age281 ms（门限500 ms），raw VINS独立订阅最大telemetry源戳间隔165 ms。

#262去掉mapper/EGO及直接传感器观察器后50秒未复现telemetry_stale，定位保持TRACKING至35.515秒，随后由`normalized_cost_exceeded`锁定；锁定时输入新鲜。#263保留mapper/EGO但不运行直接图像/IMU观察器，至38.693秒前仍TRACKING，EGO记录108条odom/depth timeout。#264同组合跟踪至39.492秒，timeout 139条；它的MapStatus CLI启动早于publisher，exit 2，没有地图状态样本。

#265/#266将MapStatus CLI订阅延迟到publisher发现后。#265观察到6条ready状态、902占据点及131→151条深度转发，随后在仿真9.373秒发生`telemetry_stale`（源龄/收包龄363/322 ms）并reset地图。#266观察到2条ready状态、902占据点及147条深度转发，随后在9.377秒以`imu_stale`（源龄/收包龄212/212 ms）锁定；telemetry与optimized源龄也达301 ms，地图reset。两轮锁定原因不同。

结果表明附加观察/调度负载与早期输入陈旧可能相关，但目前是小样本、单次运行间对照，且独立raw VINS订阅不能证明adapter接收同一消息。根因未定，不放宽任何健康门，不发布goal、不启动轨迹控制或PX4。MapStatus曾ready只说明输入门短暂打开，不构成规划或净空验收。

验证：#261–#266 run-local localization 包各1/1构建通过；最终运行容器均退出0，`gz sdf -k`有效（保留已有`gz_frame_id`警告）；shell/Python语法检查通过；无真值、goal、controller、PX4或setpoint；运行后容器清单为空。#262保留一次初始重复world前置检查失败和修正前日志；#264保留publisher未发现时退出的MapStatus观察器日志。最终清单审计将#266的instrumented source路径纠正到#266自身运行副本，并刷新对应报告SHA-256。运行清单及报告逐文件/目录SHA-256记录。该记录提出的publisher-side trace下一步已由#267/#268完成，结果及新的因果验证计划见[后续记录](2026-10-20-036-localization-telemetry-publisher-mapstatus-trace.md)。结构检查只表示骨架一致，P2阈值仍PROVISIONAL，GOAL B/C及整体目标未完成。

证据：[#261](../evidence/p2-localization-telemetry-callback-trace-20261020-261.json)、[#262](../evidence/p2-localization-telemetry-low-load-isolation-20261020-262.json)、[#263](../evidence/p2-localization-telemetry-ego-load-no-sensor-observer-20261020-263.json)、[#264](../evidence/p2-localization-telemetry-mapstatus-low-bandwidth-20261020-264.json)、[#265](../evidence/p2-localization-telemetry-mapstatus-ready-retry-20261020-265.json)、[#266](../evidence/p2-localization-telemetry-mapstatus-observer-repeat-20261020-266.json)。
