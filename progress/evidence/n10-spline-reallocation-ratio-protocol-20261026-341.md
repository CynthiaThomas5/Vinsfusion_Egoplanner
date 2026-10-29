# #341 N10.3 时间重分配 ratio 修正验证协议

状态：**执行前固定。** #340 的 40 条最终 spline 诊断行显示 X 轴导数控制点速度越限；没有加速度越限，但原算法令 `max_acc=-1` 后仍计算 `sqrt(abs(-1)/0.25)=2`。因此第一次 time reallocation 使用 2.0，而速度越限要求的 ratio 是 1.90426。

## 唯一代码变量与假设

- 唯一行为变化：若当前候选样条没有任何违反加速度限值的导数控制点，`acceleration_ratio` 设为 0，不再把 `max_acc=-1` 哨兵绝对值当作实际加速度。存在加速度违反时仍沿用原 `sqrt(max_acc/limit_acc)`；velocity ratio、最终检查、限值、容差与最大 3 次 refine 完全不变。
- 唯一变量为上述“未触发加速度项对 time-reallocation ratio 的贡献”从错误的正值改为 0；planner profile、map、camera、goal、PX4 参数、健康门与任务 runner 都同 #340。
- 假设：首次时间重分配将只按实际违反的速度项进行，减少错误 sentinel 造成的过度时间伸缩；随后最终 spline 仍必须通过原速度／加速度检查。若后续优化再次放大 X 轴速度，本假设即被否定。

## 判据与终止

1. `bash tools/project.sh build ros` 必须通过；run manifest 必须显示 #341 patch/source 与 2 m horizon、0.10 m/s、0.25 m/s² 输入身份。
2. planner log 需证明无加速度违反时 `acceleration_ratio=0`，同时最终 feasibility gate 保留原限值和拒绝行为。
3. 若原 16 m action 通过，则完成 3 sim-s dwell、固定 SE(3) 独立到达评估与完整 600 sim-s ACTIVE hold；地图/freshness/localization/tracking/contact/PX4 末态条件不变。
4. 若 action 被拒或任一 gate 失效，依原桥控流程安全降落。单次结果记录后停止，不用相同假设重试，也不把失败改称通过。

## 固定输入与产物

- run：`n10-20261026-341-spline-reallocation-ratio`
- 同 #340：`config/components/navigation/n10_long_range_vio_calibration_goal.json`、`config/components/mapping/n10_horizon2_calibration.json`、官方 EGO 策略、单 D435i、PX4 唯一控制者 `uav_px4_bridge`、真值只读。
- 新补丁：`dependencies/patches/ego/0051-n10-spline-reallocation-ratio-sentinel.patch`，按 0050 之后重放。
- 运行原始数据进入 `artifacts/runs/<run_id>/`；报告进入本目录，保留 #340 的失败对照。
