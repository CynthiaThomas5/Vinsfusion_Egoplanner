# GOAL B/C 定位 telemetry 负载与 MapStatus 窗口诊断 #261–#266

## 任务摘要

沿用 #260 的故障边界，在 run-local 副本中给自维护定位适配器增加低频 callback/source-stamp 快照；保持原健康门、topic/QoS、回调顺序、单线程 executor 和控制所有权。随后以不同观察负载对照，并用低带宽 `/mapping/status` 订阅确认定位失效前地图状态。所有运行均无真值输入、goal、controller、PX4 或 setpoint。

## 已确认

- #261 在完整 mapper/EGO 加直接图像/IMU观察器时，于仿真 11.583 s 以 `telemetry_stale` 锁定。适配器最后接受 telemetry 源戳龄329 ms，超过300 ms源龄门；receipt age为281 ms，低于500 ms门。锁定前 callback entry约9 ms，callback最大墙钟间隔358 ms。独立 raw VINS订阅继续收到 initialized telemetry至48.841 s，最大源戳间隔165 ms；它不能证明适配器收到相同样本。
- #262 移除 mapper/EGO 和直接传感器观察器，50 s内定位从3.946 s保持TRACKING到35.515 s，随后以 `normalized_cost_exceeded` 锁定；锁定时 telemetry源龄51 ms、receipt age 0 ms。raw telemetry最大源戳间隔67 ms。
- #263 保留 mapper/EGO、移除直接图像/IMU观察器，定位在至少38.693 s前持续TRACKING，没有 telemetry_stale；EGO有108条 odom/depth timeout日志，但未发goal。#264重复该组合时定位持续TRACKING至39.492 s；EGO有139条timeout日志。#264的MapStatus CLI观察器先于publisher启动，以exit 2退出，因此不能据此判断地图门状态。
- #265 在等待publisher可见后订阅MapStatus，取得150条状态。锁定前地图门有6条 `input_ready=true`，占据点902，depth转发计数从131增到151，深度源戳从8.284推进至8.977 s；定位于9.373 s以 `telemetry_stale` 锁定，source/receipt age为363/322 ms，随后MapStatus报告地图reset。
- #266独立重复MapStatus观察条件，取得146条状态；锁定前有2条ready样本、902个占据点及147个转发深度。定位于9.377 s以 `imu_stale` 锁定，IMU source/receipt age为212/212 ms；telemetry与optimized source age也达到301 ms。地图随后reset。锁定原因与#265不同。

## 决定与限制

- 这些对照显示附加观察/调度负载可能与早期 freshness lock 相关，但事件不稳定且锁定原因变化；单轮观测和独立 VINS 订阅不足以确认因果，也不能定位 DDS、executor 或回调内部原因。
- 健康阈值保持 PROVISIONAL 且未修改；定位、地图、GOAL B/C/D/F仍未通过正式验收。MapStatus ready不代表EGO成功规划、轨迹执行或障碍净空。
- 下一步在 run-local `mapping_input_adapter` 副本内做低频 publisher-side MapStatus trace，避免独立 ROS CLI reader；关联每次健康锁定时各流年龄、深度转发和 EGO timeout。先不发goal、不接控制或PX4。

证据报告：[#261](../../progress/evidence/p2-localization-telemetry-callback-trace-20261020-261.json)、[#262](../../progress/evidence/p2-localization-telemetry-low-load-isolation-20261020-262.json)、[#263](../../progress/evidence/p2-localization-telemetry-ego-load-no-sensor-observer-20261020-263.json)、[#264](../../progress/evidence/p2-localization-telemetry-mapstatus-low-bandwidth-20261020-264.json)、[#265](../../progress/evidence/p2-localization-telemetry-mapstatus-ready-retry-20261020-265.json)、[#266](../../progress/evidence/p2-localization-telemetry-mapstatus-observer-repeat-20261020-266.json)。原始运行目录均在对应 `artifacts/runs/` 下。
