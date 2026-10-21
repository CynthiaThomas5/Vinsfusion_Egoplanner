# GOAL B/C publisher-side MapStatus trace repeat #267–#268

关联对话：[2026-10-20-036](../../collaboration/dialogues/2026-10-20-036-localization-telemetry-publisher-mapstatus-trace.md)。

在 #265/#266 的 MapStatus CLI reader 条件下定位约 9.37 s 提前以输入 stale 锁定，而 #263/#264 无有效 reader 时跟踪约 39 s。为观察发布端状态并避免新增 ROS reader，建立 #267/#268 两份 run-local `uav_mapping` overlay：在原有 `MapStatus` publish 之后最多每秒记录一次结构化状态，并在 ready/reason/map_id 转换时补记。没有改项目源码、健康策略、topic/QoS、发布节奏、输入回调顺序或控制接口。

#267 在 50 s raw VINS 窗口内记录 533 优化、7,029 传播和 543 条 telemetry，最大源戳间隔 67 ms。定位 TRACKING 至仿真 25.574 s，在 26.335 s 以 `normalized_cost_exceeded` 锁定；锁定时 telemetry/optimized/IMU 源龄为 231/297/195 ms，低于各自 freshness 门。47 条 publisher trace 中 27 条 ready，MapStatus 从深度源戳 4.588 s ready 到 25.873 s，随后地图 reset。EGO 保持 `WAIT_TARGET`，无 goal。

#268 独立重复同配置：535 优化、7,052 传播、545 条 telemetry，最大源戳间隔 67 ms；定位在窗口内 TRACKING 至 38.479 s、未锁定。46 条 publisher trace 中 42 条 ready，深度源戳到 38.413 s，occupied 点最高 1,293、转发深度计数 1,017。EGO 有 87 条 `odom or depth lost!` 日志，其中 7 条在 21.172–21.397 s，80 条在最后一次EGO同步source stamp 38.710 s之后（仿真时钟继续到43.769 s）；仍在 `WAIT_TARGET`，无目标或样条。

两轮都没有独立 MapStatus CLI reader、图像/IMU观察器、truth、goal、轨迹服务器、控制器、PX4 或 setpoint publisher。不同 run 的锁定行为表明额外 reader 负载可能相关，但本组跨 run 对照不是成对随机实验，不能推断因果；publisher-side logger 自身也增加少量文件输出。阈值保持 PROVISIONAL，GOAL B/C 和地图规划/轨迹执行未通过。

验证：两轮 run-local `uav_mapping` 各 1/1 构建通过，shell 脚本 `bash -n` 与 Python 内存编译通过；容器命令退出 0、SDF 检查为 Valid（保留已有 `gz_frame_id` warning），运行后 `docker ps` 为空。证据报告与六个 run-local source/build/install/log/capture/session 目录逐文件/目录 SHA-256 核对通过，所有运行文件均有覆盖。#267 记录了 Xvfb readiness signal workaround；#268 的直接 Xvfb/`xdpyinfo` 预检通过。初始 overlay wrapper 错误和修正均保留在 startup event 记录中。

下一步：若需要判断 MapStatus CLI reader 对调度的因果影响，做同 workload 成对重复、仅切换该 reader，并继续保留 publisher trace；另以只读 EGO occupancy reader trace 定位 `odom or depth lost!`。

证据：[#267](../evidence/p2-localization-telemetry-mapstatus-publisher-trace-20261020-267.json)、[#268](../evidence/p2-localization-telemetry-mapstatus-publisher-trace-repeat-20261020-268.json)。
