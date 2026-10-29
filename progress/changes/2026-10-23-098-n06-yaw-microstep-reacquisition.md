# 2026-10-23 #098 N06 yaw microstep reacquisition

对话摘要：[N06 yaw microstep reacquisition](../../collaboration/dialogues/2026-10-23-098-n06-yaw-microstep-reacquisition.md)

## 结果与记录

- r23 的首个 1° step 后出现约 5.16 秒静态 hold；特征计数在 hold 后段恢复到约 111–113。
- 第二步开始后特征数再次降至个位数。mapping gate 于 sim 18.844 s／估计 yaw 1.961°关闭；首条无效 LocalizationStatus 于 sim 18.910 s／truth yaw 1.546°。MapStatus 此后保持 `map_reset_acknowledged`，无快照输出。
- r23 的 105.604 秒输入记录窗口结束；深度／精确位姿的采样帧仅覆盖到 sim 18.745 s。运行 truth 为 8.820°，profile 命令为 8°；online mapping 未使用 truth。
- 新增 [机器可读报告](../evidence/n06-yaw-microstep-reacquisition-20261023-098.json) 和[证据报告](../evidence/n06-yaw-microstep-reacquisition-20261023-098.md)。runner exit code 未随丢失的 host exec session 保留；已检查容器与匹配项目进程均停止。
- 新增 `n06_yaw_microstep_025deg_pilot.json`：8 个 0.25°步进，每步固定静置约 5.164 秒；角加速度与 r23 相同，pilot 命令总转角 2°。这只是下一实验 profile，尚未运行。
- CURRENT、GOAL、execution plan、milestones 和 N06 主证据报告更新为 r24 是唯一下一子项；N06/S4 保持 `in_progress`，原 N06 出口不变。

## 验证

- r23 原始 motion、mapping log、输入记录及 profile 均有 SHA-256，见 #098 JSON。
- 新 profile 几何复算：8×0.25°=2°；每步两个加减速 phase 与八个静止 phase；静置 5.16398 秒；角加速度保持 0.0104719755 rad/s²。
- 完成状态写回后运行 `python3 tools/project_status.py`、profile/static consistency check、`git diff --check` 和 `git status --short --branch`。结构检查不替代 build、SITL 或 N06 正向出口。

## 限制与下一步

本轮没有证明完整观测覆盖或 fresh map 下的 EGO 曲线。下一步运行 r24 2° pilot，检查健康门能否跨过 r23 的约 1.55° truth yaw 失效点；成功只授权继续 observation scan 研究，不关闭 N06。
