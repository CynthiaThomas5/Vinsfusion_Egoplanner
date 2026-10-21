# GOAL B/C publisher-side MapStatus trace repeat #267–#268

## 任务摘要

在 #265/#266 的 MapStatus CLI 观察条件下，定位分别于仿真 9.373/9.377 s 提前锁定；此前无有效 MapStatus reader 的 #263/#264 则跟踪到约 39 s。为观察发布端本身的状态而不增加 ROS reader，在 run-local `mapping_input_adapter` 副本中，于既有 `/mapping/status` publish 之后每秒最多记录一次结构化状态，并在 ready/reason/map_id 变化时补记。原项目源码、健康策略、topic/QoS、状态发布频率和输入回调顺序未变。

## 用户约束与执行边界

- 仅做单 D435i 仿真诊断，不修改项目源码或阈值；语义、信念和探索功能不进入本轮。
- mapper/EGO 保持运行；不启动 MapStatus CLI reader、图像/IMU观察器或占据云观察器。
- raw VINS observer 只读；不订阅真值，不发 goal，不启动轨迹服务器、控制器、PX4 或设定点发布者。
- run-local trace 记录发布端 MapStatus、定位/深度健康 receipt age、深度转发计数和 EGO occupied 状态；不改变接口输出。

## 结果与判断

- #267：50 s raw VINS 观察得到 533 条优化、7,029 条传播和 543 条 telemetry，最大 telemetry 源戳间隔 67 ms。定位从仿真 4.005 s 跟踪到 25.574 s，于 26.335 s 以 `normalized_cost_exceeded` 锁定；锁定时 telemetry/optimized/IMU 源龄为 231/297/195 ms，均未越健康 freshness 门。发布端 trace 共 47 条，其中 27 条 ready；地图由源戳 4.588 s ready 持续至 25.873 s，随后随锁定 reset。EGO 保持 `WAIT_TARGET`，没有输入 timeout 或 goal。
- #268：独立 50 s 重复得到 535 条优化、7,052 条传播、545 条 telemetry，最大源戳间隔 67 ms。定位在观测窗口内 TRACKING 至 38.479 s，没有锁定；46 条发布端 trace 中 42 条 ready，最近深度源戳到 38.413 s，occupied 点数最高 1,293，深度转发计数到 1,017。EGO 保持 `WAIT_TARGET`，记录 87 条 `odom or depth lost!`：7 条在 21.172–21.397 s，另 80 条在最后一次 EGO 同步 source stamp 38.710 s 后（仿真 `now` 到 43.769 s）；没有 goal 或样条。
- #267/#268 均未运行 MapStatus CLI reader。它们与 #265/#266 的早期 stale 结果不同，但跨 run 的质量代价和时序也不同；这只能说明 reader 负载可能相关，不能确定因果或具体 DDS/executor 根因。#268 的 EGO timeout 说明发布端 ready 仍不等于 EGO 持续消费正常。
- 健康阈值保持 PROVISIONAL；GOAL B/C、地图规划响应和轨迹执行均未通过。本轮没有 goal，不能推断避障或净空。

## 决定与待决问题

- 不调整健康门、话题、QoS 或发布频率；保留 run-local instrumentation。
- 若需要判定 CLI reader 是否导致额外调度负载，下一步采用同一 mapper/EGO workload 的成对重复，仅切换 MapStatus CLI reader，并继续保留 publisher-side trace。
- EGO `odom or depth lost!` 需要单独定位其 occupancy/reader 边界；当前没有目标，不能评价实际规划结果。
- #267 的 `xvfb-run` 在显示 :100 已通过 `xdpyinfo` 后仍等待 readiness signal；确认 X ready 后向 wrapper 发 SIGUSR1 才继续。#268 改为容器内直接启动 Xvfb 并通过 `xdpyinfo` 预检，完整运行退出 0。两轮第一次 overlay build 也各有脚本前置错误，均在启动仿真前修正并记录。

证据报告：[#267](../../progress/evidence/p2-localization-telemetry-mapstatus-publisher-trace-20261020-267.json)、[#268](../../progress/evidence/p2-localization-telemetry-mapstatus-publisher-trace-repeat-20261020-268.json)。原始日志与校验和在对应 `artifacts/runs/` 目录。
