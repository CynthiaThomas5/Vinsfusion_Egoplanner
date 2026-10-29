# 2026-10-23 #097 N06 segmented yaw reacquisition

对话摘要：[N06 segmented yaw reacquisition](../../collaboration/dialogues/2026-10-23-097-n06-segmented-yaw-reacquisition.md)

## 改动与结果

- r22 完成分段 360° yaw 命令 profile；首次 map health gate 在 sim 12.970 s／VINS yaw 2.41°关闭，第一条无效 localization status 在 sim 13.056 s／truth yaw 2.63°。这早于第一个 15° segment 的 sim 20.117 s stop/hold。
- 首次 health lock 后，部分 hold 的 VINS 特征计数回升，但定位 status 始终无效、MapStatus 没有恢复；input_ready 结尾仍为 false。snapshot-01 120 秒 readiness wait 超时，未保存快照，也未运行 live EGO probe。
- profile 排程 360°，physics truth 只累计 337.75°；motion truth 写入36,501样本，IMU91,252样本。Input recorder 覆盖428.319 wall秒，但 EGO forwarded depth/camera pose 只有263帧，最后source stamp早于定位锁定；数据没有覆盖后续 raw camera 图像。
- r22 正常 runner 错误路径结束，没有 orphan container/process。
- 修复中断保存：`run_sensor_motion.py` 与 `record_n04_mapping_inputs.py` 增加显式 SIGINT/SIGTERM handler，使 background child 的 SIGINT 可触发 partial-save；`run_n04_map_layout.sh` 容器停止 grace 从15增至90秒。r22 当时已加载旧代码，因此它通过 natural profile completion/save，而不是靠新 handler。
- 新增8° pilot profile `n06_yaw_microstep_1deg_pilot.json`：八个1° rest-to-rest步进，每步约5.16秒静置；保留r22角加速度，最大不间断转角降至1°。这是下一子项，不代表正向入口通过。
- 更新 CURRENT、milestones、GOAL、remaining-small-goals 和 N06 主报告；N06/S4仍为`in_progress`，验收条件未变。

## 验证

- `bash tools/project.sh test`：243 tests 通过；navigation adapter integration 通过。
- r22 原始数据复算：首次 gate、truth yaw、分段角度和MapStatus如上；原始文件哈希在[机器报告](../evidence/n06-observation-scan-reacquisition-20261023-097.json)。
- 当前 Python handler compile、runner `bash -n`、project_status 和 diff check 需在本次最终检查完成后写回。
- N06 SITL 正向入口未通过；不把传感器仿真失败或结构检查算作成功导航。

## 限制与下一步

健康门在约2.6°时关闭。15° hold不能覆盖该门槛；特征数后来短暂增加没有让map输入门重新打开。下一步运行8×1° pilot，确认更早的停顿是否能让健康与mapping输入持续；若通过，再扩展完整 yaw coverage；若失败，保留 no-go 及具体单目入口限制。PX4/bridge/controller/flight均不启动。
