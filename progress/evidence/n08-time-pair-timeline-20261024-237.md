# N08.2aa #237：PX4 时间源与定位锁存时间线

## 结论

本次没有复现 PX4 HRT 与 ROS `/clock` 的显著失配。它们在第二段时间线中保持在 −8 ms 至 +16 ms，PX4 时间域样本始终有效、没有 `/clock` 回退。

复现的是另一类配对差：N05 支架扫描返程时，LocalizationStatus 在 source/sim 474.180 s 从 valid 变为 `normalized_cost_exceeded`，normalized cost 从 0.95343 越过 1.0 到 1.013814。adapter optimized odometry 随后停在 source 474.048 s，adapter propagated 停在 474.148 s；VINS raw optimized/propagated 与 telemetry 仍继续到 515.364/515.432 s。PX4 local-position 继续前进后，bridge detail 的 PX4-local-position 与 adapter optimized-odometry source-pair gap 从失效前约 0.12 s 增至 41.376 s，bridge 原因为 `localization_not_tracking`。因此，本次观察到的大 gap 是定位健康锁存后的结果，不是 #206 所修复的 HRT/ROS 时钟年龄问题；gap 仍会使桥安全地 fail-closed。

这也说明后续任务确实可能被**单次**定位失效挡下，但 N07 的累计三次规则与这个失效无关，不能通过要求连续或重测已通过项来解决。

## 运行与准入

- Run：`n08-20261024-237-time-pair-timeline-01`；相同 22-stage rear-down 支架 profile，DISARMED；完成 16/22 阶段，实际到达 yaw=−π、pitch=+0.45 的新增下视段。返程 yaw 阶段触发原有 localization 健康门；N05 helper exit 1，外层 wrapper exit 12。
- scan 前 N05 online/offline 同 identity 均拒绝 `ground_plane_insufficient_raw_occupied_voxels`。因健康中止未得到 prescan-ready、after/post-release 或 current-area 准入；compute-only 不启动。
- 未发布 goal 或控制；PX4 arming-state 采样均为 1（`ARMING_STATE_DISARMED`），bridge DISABLED；车辆 landed，夹具 detach 已确认且 Gazebo 模型已移除。`bash tools/project.sh stop ...` 后容器 `Exited (0)`，无匹配项目进程。

## 时间线覆盖与限制

观察器先以全频率运行 50.42 秒，产生 25,487 条事件；为限制诊断数据量，通过 stop marker 正常落盘并安全退出。第二段使用 100 ms 源采样，持续 297.44 秒并记录 19,306 条事件，保留 LocalizationStatus/VINS 健康、MapStatus、bridge 状态变化和源戳回退。第二段覆盖仿真时钟 251.428–515.432 s，完整捕获定位失效和配对差增长。

两段之间仿真时钟 52.740–251.428 s 没有观察数据，所以本报告不声称全程连续。健康失效前后的关键因果顺序在第二段有直接读回；本次未解锁，没有验证任何 airborne timing/control gate。容器 CPU 同时读数约 632–695%，但没有建立宿主整体饱和或观察器导致健康失败的因果关系。

## 验证

- `python3 -m unittest tools.test_n08_timeline_helpers tools.test_n08_curve_certificate tools.test_n08_compute_only`：12 项通过。
- `bash -n tools/run_n05_preflight_layout.sh`、观察器/helper/test 的 AST parse、JSON parse、`python3 tools/project_status.py` 与 `git diff --check`：通过。结构检查提示 80 个可选历史 artifact link 缺失；不影响结构通过。
- 运行输入、观察器分段、fixture trace、VINS/raw odometry 与 N05 before gate 的 SHA-256 见 JSON 报告和 `artifacts/runs/n08-20261024-237-time-pair-timeline-01/`。

父目标 N08 保持 `in_progress`。下一步需处理返程运动时的定位代价越线，并取得 N05 释放后同身份入口准入；即使这些通过，仍需实际制动／响应延迟／减速度／停止距离证据和至少三次目标重复，才能关闭 N08。
