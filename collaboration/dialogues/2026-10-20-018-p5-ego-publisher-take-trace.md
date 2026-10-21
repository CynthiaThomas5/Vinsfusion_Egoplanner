# 任务对话摘要

- 日期与任务 ID：2026-10-20，018。
- 用户目标与约束：继续 P5 单 D435i、无真值 VINS→EGO→PX4 SITL 诊断；保持现有定位质量、安全、PX4 freshness 门及唯一控制发布者，不因单轮结果改阈值。
- 已确认的决定：在 #227 trace 基础上，#228 同时选择 EGO PID 909 与 /drone_0_camera_pose 发布端 mapping_input_adapter PID 908；新增 publisher init/publish tracepoint，沿用低负载 harness、同一横移/yaw 目标与 run-local EGO overlay。
- 结果：首 32.5 秒 trace 窗口有 575 次 camera-pose rmw_publish、548 次 EGO successful rmw_take。EGO 最大 take 空档为 2.521827 秒；该空档内发布端仍有 50 次 rmw_publish，最大间隔 0.122401 秒。相机位姿 reader 在该区间没有 RMW take 尝试，也没有 taken=0 记录。写端静默不能解释该空档；Fast DDS reader readiness 与 executor wait-set 选择尚未区分。目标因既有 localization_accel_bias_norm_exceeded 门中止，PX4 后续 AUTO_LAND、DESCEND/failsafe、touchdown、disarm。无真值，canonical 门控未改。
- 待决问题：publisher 的 RMW write 是否到达 EGO DataReader，以及数据已到达时 wait-set 是否将 pose subscription 标记为 ready。通用 executor tracepoint 没有 selected-entity 字段。
- 实施范围：新增双进程 run-local trace、publisher/take 时间对齐、ULog 汇总、轻量证据、状态与索引；没有修改自维护或第三方源码、canonical 参数、QoS 或 PX4 控制逻辑。P5 未通过。
- 下一步：先查固定 Jazzy/Fast DDS 环境是否能只读观察 EGO DataReader 的 data-available/readiness；以隔离 preflight 确认观测点低开销，再决定是否进行 #229。保持 QoS/阈值不变，不加图像或点云观察器。
- 对应改动记录：progress/changes/2026-10-20-018-p5-ego-publisher-take-trace.md
