# N06.4 慢速 yaw 诊断与分段扫描下一假设

日期：2026-10-23。Goal 完成模式，范围 N06。N06/S4 保持 `in_progress`，本次 r21 不建立 N06 正向入口。

## r21 对照结果

r21 在相同 textured surround、固定平移和相同 full-yaw 端点下，把 r20 的 yaw 峰值角速度降低四倍至约 0.052 rad/s，角加速度降为 1/16。VINS 日志中首次 `n_pts size: 0` 是 sim 17.194 s，估计 yaw 约 0.61°；其后健康门没有立即锁定。首个 `normalized_cost_exceeded` mapping gate closure 是 sim 45.574 s，前一条 VINS pose 的估计 yaw 约 16.37°，`n_pts` 为 4／3；随后 plan_env reset。r20 首个 mapping gate 在 sim 13.564 s、估计 yaw 约 2.43°，所以低速确实推迟了锁定，但仍远早于完成 360° 扫描。

r21 的 mapping log 一直保留到 sim 136.126 s（估计 yaw -160.84°），但 run 在完整 turn 和快照阶段之前停止。完整 `mapping-stack.log` 与 `run-inputs.json` 留在[运行目录](../../artifacts/runs/n06-20261023-wall-r21/)；日志 SHA-256 为 `3816cd8318de1c7dd3df1c9b9beeb678a5415f4b3776e65e6525441cc3f7b4e5`。15 秒 `docker stop` 宽限后容器 exit 137，`motion.json` 和 `inputs/mapping-inputs.json` 没有落盘；因此姿态是 VINS 估计输出，不是独立 truth，且没有 r21 raw 深度复核或 snapshot。结果详见[机器可读报告](n06-observation-scan-diagnostic-20261023-096.json)。

## 下一单变量假设

r21 在首次零特征帧后又继续约 28.38 仿真秒才关闭健康门，说明孤立 feature-count drop 与持续定位失效并不同步。下一次只改变扫描组织方式：24 个 15° rest-to-rest yaw 步进，每步后保持 5 秒，让相机视角固定以供特征重获；场景 surround、平移静止和峰值角速度约 0.052 rad/s 与 r21 保持。总命令转角为 360°，profile 及哈希见机器报告与 [分段 profile](../../config/components/simulation/n06_yaw_360_segmented_15deg.json)。

若某步触发持久 health lock，经 container 内 SIGINT sensor-motion 进程组，触发 runner 正常 cleanup 写下 partial motion/input 记录；host wrapper 的容器停止宽限已由 15 秒增至 90 秒。若完整扫过，保留匹配地图快照并继续 planner-only probe。命令：

```bash
bash tools/run_n04_map_layout.sh n06-20261023-wall-r22 wall_box_column 85 motion_n06 config/components/simulation/n06_yaw_360_segmented_15deg.json
```

## 状态与验证

- `python3 tools/project_status.py`：结构检查通过。
- `bash -n tools/run_n04_map_layout.sh tools/run_n04_map_layout_container.sh`：通过。
- 分段 profile 参数复算：72 个五秒角加／减／保持 phase，24 对 rest-to-rest 总计 360°、命令峰值 0.05236 rad/s；stop=365 sim s，record=428 wall s。
- 未运行项目测试；本报告不把 r21 判为通过，也不以结构检查代替 SITL。

下一步：继续 N06.4，运行 r22 分段慢速 yaw；若健康仍锁定，保留 no-go 和故障轨迹，评估单 D435i 的合法入口是否需要明确范围调整。N06.2 两布局曲线、hold 与 handoff 出口仍未完成。

**后续更新（#097）**：r22 已执行；15°首次停顿晚于约2.6° health lock。详见[分段 yaw 重获诊断](n06-observation-scan-reacquisition-20261023-097.md)。当前下一项改为八步1° pilot；显式SIGINT recorder handler与90秒 host stop grace也已补入。
