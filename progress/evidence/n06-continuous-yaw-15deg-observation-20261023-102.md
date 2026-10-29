# N06.4 r27 continuous 15° yaw pilot

日期：2026-10-23。Goal 完成模式，范围 N06。父目标 N06/S4 保持 `in_progress`。

## r27 结果

r27 保留 r26 的 wall 位置、纹理 surround、单次加速／匀速／减速、角加速度 `0.0026179939 rad/s²` 和峰值角速度，仅把名义连续转角扩展到 15°。起始 readiness 通过，epoch 为 `227afbf2ee324531be882b325745fb62`；profile 命令完成后，debug fixture truth 实测累计 yaw `14.730994°`，比名义值少 `0.269006°`。

VINS mapping health gate 在仿真 `62.404 s` 以 `normalized_cost_exceeded` 关闭；相邻 VINS log 中 `n_pts=2`，四元数 yaw 估计约 `10.161°`。在线读取的锁存 LocalizationStatus normalized cost 为 `1.34155098`（阈值仍为 1.0）。Input recorder 的首条 invalid LocalizationStatus 为 `sim 62.478 s`，紧邻前一条 valid 状态 `sim 62.432 s`；按 fixture truth 插值，首条 invalid 时 truth yaw 约 `9.854°`。MapStatus 随后在 `sim 62.569 s` 变为 `input_ready=false`／`map_reset_acknowledged` 并换 map_id。该结果说明连续低角速度转动可将健康维持到约 9.85°，但不能满足 15° pilot 门槛。

Recorder 完成 150 秒请求窗口（实际 `152.519 s`），记录 1,762 组深度帧／相机位姿和 881 条优化里程计。最后一组已转发深度／相机位姿 source stamp 为 `sim 62.338 s`；reset 后没有恢复 MapStatus。三张 snapshot 未生成；snapshot-01 readiness wait 在 120 秒后以 `map_reset_acknowledged` 超时。没有 live EGO probe，因此本轮没有 body／hold 球的新 raw 分类、快照身份或规划曲线证据。Runner exit 1；确认容器和匹配项目进程已停止。

机器摘要：[n06-continuous-yaw-15deg-observation-20261023-102.json](n06-continuous-yaw-15deg-observation-20261023-102.json)。完整原始记录和哈希见[运行目录](../../artifacts/runs/n06-20261023-wall-r27/)；关键 SHA-256：mapping input `01ea90236e53421b4ccec3b5efe92a2c6d65f3d4b77bcc5063af1a39c37eed31`，motion truth `0b0e4c7ecae856b94ca5b2a1922f0c393dc454bd4d75fb7c9379b545be8040ba`，mapping log `030dd31ed5715829970651f708ab007357c228a7ed068dc79f13c2ce001edfc1`。

## 下一项：r28 单轴平移观察

r26 证明连续 2° yaw 可维持健康与 fresh map，但 body 球仍有 1,809 个 unknown；r27 将 yaw 扩展后在约 9.85° truth 锁存健康门。N06.3 视场诊断此前发现 unknown 多位于后向半球／近裁剪区。下一次保持 wall 布局和同一纹理 surround，只改用已有慢速单轴 X 平移 profile：从原点后退 2.4 m，再沿同一路径返回原点，全程无 yaw／Y／Z 分量。主要假设是后退后正向相机可从原点后方向前观察原起点 body sphere，并由平移视差提供与纯 yaw 不同的 VIO 约束。

profile：[n06_x_visibility_slow.json](../../config/components/simulation/n06_x_visibility_slow.json)，SHA-256 `653733f873234da35fb38af4f80771707190bd21df595372c88fa2924234988f`。之前 r14／r16 使用同一 profile 但未包含 N06 textured surround，均在 `input_features_insufficient` 时锁存；r28 在 r27 所用纹理 surround 中复核此单轴流程，场景／world 保持不变。通过判据：整段运动 LocalizationStatus 持续有效、MapStatus identity 单一且 depth fresh；回到原点后取得三张匹配 snapshot，再测 VINS body／hold 球、错误 identity 拒绝及 planner-only EGO。若健康或 map freshness 失败，保留 fail-closed 结果，不继续请求未满足 readiness 的曲线。

```bash
bash tools/run_n04_map_layout.sh n06-20261023-wall-r28 wall_box_column 91 motion_n06 config/components/simulation/n06_x_visibility_slow.json
```

r28 仅为未武装、sensor-only Gazebo/VINS/EGO mapping diagnostic；不启动 PX4、bridge、controller、setpoint 或 flight，不改 unknown policy、N05 包络／预算或 N06 原出口。即使取得 free body query，也只支持相应仿真入口诊断，不单独关闭 N06。
