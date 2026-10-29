# N08 #225：fresh map 与隔离 compute-only

**子项结果：通过。** 本报告只覆盖 same-run N05 准入与桥输入隔离的 EGO 计算、取消、hold 和落地，不代表任何水平运动或制动验收。

## 运行

- Run：`n08-20261024-225-camera-cone-compute-only-01`
- 场景：`n08_overhead_calibration`，复用 `wall_box_column` 加顶板；N05 `n08_overhead_free_sector_view` 完成 15/15 阶段。
- Release 后 N05 online/offline 均接受，mission-time current-area online/offline 也均接受；两个时点 epoch/map_id 相同：`024773bb488b4d53b6db8accb47ce6f4`／`024773bb488b4d53b6db8accb47ce6f4-018c28519743459f81cfeb18107eb189`。
- Post-release raw map SHA-256：`2d7fec586fa7d3873b36f2d2fa5611178b73b963ba7663c2f2b95183c1b29de1`。

Support helper 的结果仍为 `failed`，原因 `fresh DISARMED status is required for every fixture command`。这项工具失败原样保留。独立 N05 readback 与 run summary 确认车辆 landed/disarmed、fixture detached，Gazebo 中 fixture model absent；项目容器最终通过 `tools/project.sh stop` exit 0。

## 同图候选门

查询沿用 `tools/probe_n06_live_layout.py` 中的 `raw_sphere_query` 与 `raw_line_sweep` 实现，body radius 0.730618 m、terminal-hold radius 0.980618 m、速度上限 0.15 m/s。

- #224 的 `[+0.8,+0.3,0]m` 候选在这张新图上终点 hold 球有 2 个 unknown，因此拒绝该候选，没有对它发 goal。
- 重新筛选后选择 `[+0.5,+0.2,0]m` 用于 compute-only。位移 0.539 m，较当前 yaw 的相机方位 20.11°，87° 水平 FOV 边缘余量 23.39°。
- 起点／终点 body sphere 均为 2182 个 free cell、0 unknown／occupied；终点 hold sphere 为 4921 free、0 unknown／occupied；continuous line 22 次查询均 free，cover radius 0.742857 m。
- 顶板附近 ROI `[-0.85,4.15] × [-2.75,3.95] × [2.1,2.7]m` 有 891 raw occupied voxels。
- 起点额外 terminal-hold sphere 有 42 unknown，明确保留。该项用于隔离 planner 诊断，没有执行轨迹，不能把此候选视为停止距离证书。

## Compute-only 结果

`flight.json` runner 为 `PASS`；fresh current-area N05 与 post-release map 同身份；bridge 未订阅 `/position_cmd`，只订阅 `/n08/compute_only_position_cmd`。EGO 对当前 goal/epoch 产生 1 个 READY 样本；cancel 接受且 action 终态为 canceled；取消后桥在 hold 状态 2.0 仿真秒，无 clock 回退，最终 landed/disarmed。N08 专用 evaluator 的 12 项检查全部通过。EGO 轨迹输入与 PX4 bridge 隔离，没有 EGO 水平轨迹命令到达 PX4 bridge，也没有制动测量。

最初 `project.sh mission` 外层返回 1，原因是独立通用 `evaluate_odometry.py` 读取不存在的 `localization_quality_history` 字段并抛出 KeyError，发生在 compute-only runner 已写 `PASS` 之后。修复了后续记录链：compute-only runner 保存健康样本；缺少旧记录时通用 evaluator 把样本可用性标为 false、无效数记为 null；mission runtime 先写 N08 专项 evaluation。N08 evaluator 对原始 `flight.json` 全通过。通用 odometry evaluator 使用 run 输入逐字节相同的 scratch 副本重放成功，见 [`odometry 描述报告`](n08-compute-only-odometry-20261024-225.json)。本次旧 run 的定位健康 history 没归档，因此该项仍是明确的数据限制，不宣称健康事件计数为零。

## 证据位置

- 完整机器可读结果与输入哈希：[`n08-camera-cone-compute-only-20261024-225.json`](n08-camera-cone-compute-only-20261024-225.json)
- Run 原始产物：`artifacts/runs/n08-20261024-225-camera-cone-compute-only-01/`
- 最终候选配置：`config/components/navigation/n08_compute_only_fresh_map_goal.json`
- 对应修改：[change record](../changes/2026-10-24-225-n08-camera-cone-compute-only.md)

## 尚未满足的 N08 出口

没有执行水平轨迹，故未量得实际 response delay、可用减速度、实际停止距离或跟踪偏差；position／velocity／yaw 连续性和运动中的取消制动也未验收。仍需至少 3 次独立冷启动实际低速运动重复，并将量得的运动／停止预算回填 N05/N06。父 N08 维持 `in_progress`。
