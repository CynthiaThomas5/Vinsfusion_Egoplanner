# N08.2aa #237：记录支架扫描期间 PX4/VINS 时间配对

## 问题与假设

#235 的 bridge detail 在定位失效时显示 `alignment_pair_gap_sim_s=100.392`、last validated pair age=111.949 s。源码确认 gap 衡量的是 PX4 local-position 与 adapter optimized odometry 的源戳差；它不是 HRT 与 `/clock` 的直接差，但超过时会使 bridge fail-closed。现有 #235 没保存完整事件时间线，不能判断该差是 PX4 时间域偏移、优化里程计停止输出还是失效后的结果。

## 唯一变量与范围

- 唯一主要变量：在 #235 相同 22-stage DISARMED N05 profile 前启动只读 source timeline observer，低频记录 `/clock`，记录 LocalizationStatus、VINS telemetry/raw odometry、adapter optimized/propagated odometry、MapStatus 和 PX4 bridge detail。
- 不改 profile、场景、PX4/HRT 逻辑、健康门、N05/N06 unknown/速度门限或任务目标；observer 只订阅，不发布控制/goal/truth，也不写地图。
- Run ID：`n08-20261024-237-time-pair-timeline-01`。如果 scan health 失败，保留事件转换并安全收尾；只有 after/post-release/current-area N05 online/offline 对同 identity 准入后才允许运行既有 bridge-isolated compute-only。没有 XY。

## 完成标准

- run manifest 记录 observer 源码哈希；时间线完整记录 observer 起止、`/clock` gap/regression、LocalizationStatus reason/cost、optimized odometry source-vs-clock age，以及 bridge `px4_ros_clock_gap_sim_s`、`alignment_pair_gap_sim_s` 和 last-pair age。
- 成功或失败均保存 run-local JSON 与哈希。任何诊断代码不能改变 bridge/control 输入或安全门；N05 拒绝仍不发 goal。
- 运行结束后确认 fixture detached/removed、DISARMED、landed 和项目进程已停止或按既有交接要求保留监护。

## 已实现

- 添加 `tools/diagnostics/record_n08_localization_sources.py`：只读订阅 ROS `/clock`、LocalizationStatus、VINS telemetry/raw 与 adapter optimized/propagated odometry、MapStatus、PX4 bridge detail；时钟按 100 ms 采样并始终记录回退，桥接 detail 仅保留 HRT/ROS 与 PX4-local-position/odometry source-pair 时间字段及 PX4 telemetry source stamp/age。
- `tools/run_n05_preflight_layout.sh` 支持 N08 专用 observer 启动、限定时长和输入哈希归档，不改 N05 或定位门限。观察器不发布任何 topic；scan 失败、准入拒绝或显式 stop marker 时写出事件与摘要。
- 定向验证：`python3 -m unittest tools.test_n08_timeline_helpers tools.test_n08_curve_certificate tools.test_n08_compute_only`（11 项通过）；`bash -n tools/run_n05_preflight_layout.sh`、三个 Python 文件 AST parse、`python3 tools/project_status.py`（结构通过，80 个可选历史链接缺失提示）及 `git diff --check` 均通过。
- #235 证据补录了当时已读到的 source-pair gap 与 age，并明确独立 HRT/ROS clock gap 未保存、无因果顺序；宿主读数修正为“不能证明全局饱和”，不改变旧 run 结果。

## 运行结果

- Run `n08-20261024-237-time-pair-timeline-01` 的 22-stage profile 完成 16 stages，已到达 yaw=−π、pitch=+0.45 下视段；stage16 返回 yaw 时 health cost 从 0.95343 越至 1.013814，触发 `normalized_cost_exceeded`。N05 helper 安全恢复并 verified detached/model absent/landed；外层 exit 12，无 prescan-ready。
- 初始 N05 online/offline 同 identity 拒绝 `ground_plane_insufficient_raw_occupied_voxels`。没有 after/post-release/current-area admission、goal、compute-only、控制或 XY。
- 时间线两段：首段全频率试采因约 25.5k events/50.4 wall-s 过大而 stop-marker 收尾；第二段 100 ms sampling 捕获 health lockout。HRT 对 `/clock` 为 −8…+16 ms、PX4 time domain 全有效；定位锁存后 adapter odometry 停在 474.048/474.148 s，而 raw streams 继续到 515.364/515.432 s，PX4 local-position/adapter optimized pair gap 后升至 41.376 s。bridge `localization_not_tracking`。这把 #235 的百秒级 pair-gap 解释为定位锁存后果，不能归因于 #206 的 HRT 修复。
- 12 项 N08 针对性测试、runner shell syntax、AST parse、JSON、`project_status.py` 和 `git diff --check` 通过。最终结果及每个原始分段哈希见 [evidence](../evidence/n08-time-pair-timeline-20261024-237.md)。

**判定**：#237 的时间来源诊断完成；PX4 HRT/ROS-clock 不对齐假设在本次观察中未成立。单次任务仍会被定位健康锁存和 N05 ground-plane gate 阻止，N08 父目标保持 `in_progress`。

对话摘要：[dialogue](../../collaboration/dialogues/2026-10-24-237-n08-time-pair-timeline.md)。
