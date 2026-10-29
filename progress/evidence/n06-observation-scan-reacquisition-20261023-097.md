# N06.4 分段 yaw 与 health-lock 诊断

日期：2026-10-23。Goal 完成模式，范围 N06。父目标 N06/S4 均保持 `in_progress`，r22 不构成 N06 正向入口。

## r22 实际结果

r22 在固定位置、N06 textured surround 中按 24 个 15° rest-to-rest yaw 阶段运动，每阶段有 5 秒静止 hold，命令峰值约 0.05236 rad/s。首次 `n_pts size: 0` 在 sim 11.914 s、VINS 估计 yaw 0.92°。`normalized_cost_exceeded` gate 于 sim 12.970 s、VINS yaw 2.41° 关闭；第一条无效 localization status 是 sim 13.056 s，motion debug truth yaw 2.63°。因此 health lock 发生在第一段 15° 结束／hold 开始之前，停顿间隔对初始失效来得太晚。

其后部分静止段 VINS 的 `n_pts` 短暂恢复（例如第 6 段 hold 出现 5–43 个点且没有零计数），但 8,559 条 localization status 中，首个无效状态之后全部保持 `normalized_cost_exceeded`；MapStatus 结尾为 `input_ready=false`、`map_reset_acknowledged`，转发深度数 350、drop 数 12,067。由此可区分“偶尔有图像特征”与“健康门重新开放”：前者有局部证据，后者没有。

motion profile 排程了 360° 命令，但记录的 debug sensor-fixture truth 累计约 337.75°，末端 yaw 偏差约 -22.25°；24 次 step 的实际增量范围约 13.42°–15.22°。记录器覆盖 428.319 秒 wall time，但有效转发 depth/camera pose 只有 263 帧，最后 stamp 为 sim 12.871 s，早于 health lock；它不包含后续直接原始相机图像。MapStatus 无法恢复，snapshot-01 在 120 秒后以 `map_reset_acknowledged` 超时，未生成 snapshot；live EGO probe 未运行。完整文件及哈希见[机器报告](n06-observation-scan-reacquisition-20261023-097.json)与[运行目录](../../artifacts/runs/n06-20261023-wall-r22/)。

## r21、r22 的合并解释

r21 的四分之一角速率将 VINS health-lock 从 sim 13.564 s／估计 yaw 2.43° 延至 sim 45.574 s／估计 yaw 16.37°，但未完成 scan。r22 说明 15° 间隔静置无法保护进入最早 2.6° health-lock 门槛。低速连续运动与较快小步两者都未建立完整单目观测入口；地图 identity/reset、深度／位姿 freshness 门和 unknown 拒绝未放宽。

## N06.4 下一实验

下一步只做 8° pilot：八个 1° rest-to-rest yaw 步进，每步后静置约 5.16 秒；保留 r22 的角加速度、固定位置、同一 surround 和 sensor-only 控制边界。主要变量为最大不间断视角变化，从 15° 缩到 1°；峰值角速度随固定角加速度和短步长相应下降到约 0.01352 rad/s。判据是定位 health 能否跨过首个 2.6° 门槛并在八个 hold 期间保持有效，且地图输入继续 fresh。pilot 通过也不等于 360° 覆盖或 N06 通过。

profile：[n06_yaw_microstep_1deg_pilot.json](../../config/components/simulation/n06_yaw_microstep_1deg_pilot.json)。命令：

```bash
bash tools/run_n04_map_layout.sh n06-20261023-wall-r23 wall_box_column 86 motion_n06 config/components/simulation/n06_yaw_microstep_1deg_pilot.json
```

runner 中断处理已修正：background motion 与 input recorder 显式接收 SIGINT/SIGTERM 并保存 partial files；host wrapper stop grace 为 90 秒。若出现持久 health lock，在容器内向 `run_sensor_motion.py` 进程组发 SIGINT，让 runner 依序清理 motion、recorder 和 mapping。

## 验证与状态

- `bash tools/project.sh test`：243 tests 通过；navigation adapter integration 通过。
- profile 重建：24×15° 命令步进与 physical truth 337.75°，差值已如实保留。
- `python3 tools/project_status.py`、`bash -n`、Python compile 和 `git diff --check` 结果统一见 #097 changes。
- r22 无快照、无 EGO 曲线；N06.2 两布局全机扫掠、terminal/emergency hold 与 replan handoff 仍未通过。
