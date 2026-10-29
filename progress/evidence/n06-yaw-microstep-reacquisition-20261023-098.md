# N06.4 r23 1° microstep pilot

日期：2026-10-23。Goal 完成模式，范围 N06。父目标 N06/S4 保持 `in_progress`。

## r23 结果

r23 使用固定位置与 wall textured surround，命令 8 个 1° rest-to-rest yaw 步进，每步后静置约 5.16 秒，保留 r22 角加速度。VINS 首次 `n_pts size: 0` 出现在 sim 11.452 s／估计 yaw 约 0.557°／sensor-fixture truth yaw 0.616°。首步停止于 sim 12.576 s；静置阶段后半段特征恢复到约 111–113，并保持到第二步开始。

第二步从 sim 17.747 s 开始。特征随后从约 114 降至个位数；mapping health gate 于 sim 18.844 s、估计 yaw 1.961°关闭，首条无效 LocalizationStatus 于 sim 18.910 s，原因 `normalized_cost_exceeded`，此时 debug truth yaw 1.546°。其后 MapStatus 在 sim 19.115 s 转为 `input_ready=false`／`map_reset_acknowledged`；录制窗口最后状态仍未恢复。首次静态 hold 确实伴随 feature recovery，但没有维持第二步期间的定位健康。

因此 r23 支持“停稳可短暂重获图像特征”，不支持“1°间隔可跨过定位失效门槛”。profile 命令总角度 8°，debug truth 实际累计 8.820°；该 truth 只用于离线诊断，没有输入 mapping。

Input recorder 完整运行 105.604 秒，包含 2,649 条原始深度 header、4,712 条 depth health、2,095 条 LocalizationStatus、459 条 MapStatus 与完整 fusion trace；采样保存的 forwarded depth 和精确 camera pose 各 441 帧、优化 odometry 221 条，最后转发深度 stamp 为 sim 18.745 s。因此它不是跨 health lock 的原始相机图像录制。snapshot-01 没有生成输出，MapStatus 没有回到 ready；容器和匹配项目进程最终均已停止，但 host exec session 丢失后没有保留 runner exit code。完整哈希和结构化数据见[机器报告](n06-yaw-microstep-reacquisition-20261023-098.json)与[运行目录](../../artifacts/runs/n06-20261023-wall-r23/)。

## 下一项：r24 0.25° pilot

主要变量是最大连续 yaw 增量从 1°降至 0.25°；角加速度、每次约 5.164 秒静止重获、位置和 wall surround 不变。r23 在第二步约半程／truth yaw 1.546°时失效，因此 r24 用 8×0.25° 的 2° pilot 检查更频繁的暂停能否跨过该失效点。profile 为 [n06_yaw_microstep_025deg_pilot.json](../../config/components/simulation/n06_yaw_microstep_025deg_pilot.json)。

```bash
bash tools/run_n04_map_layout.sh n06-20261023-wall-r24 wall_box_column 87 motion_n06 config/components/simulation/n06_yaw_microstep_025deg_pilot.json
```

成功标准仅为：达到至少 2°实际 truth yaw 时 LocalizationStatus 仍有效，MapStatus 保持相同 epoch/map identity 且输入新鲜，并能取得匹配快照。即使通过，也只支持继续扩展 observation scan，不代表全周覆盖或 N06 通过。N06.2 两布局整曲线、terminal/emergency hold、handoff 和故障拒绝出口仍未满足。
