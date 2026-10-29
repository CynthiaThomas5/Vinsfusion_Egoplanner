# N08.2r #228：定位源时间线与停止区域复核

日期：2026-10-24。N08 保持 `in_progress`。本项解释 #227 的 stale 是否在同一链路窗口复现，并复核 compute-only 目标周围的同图几何；不构成制动或飞行通过证据。

## 运行结果

- Run：`n08-20261024-228-localization-timeline-01`。同一 epoch `7af4ed28ae2c42d2bf002304b848daf3` 内，observer 记录约 39.5 s、29,136 个事件；仿真时钟从 505.864 s 到 541.420 s，无倒退。
- 本次窗口没有复现 `telemetry_stale`：794/794 个 LocalizationStatus 样本均 `valid=true`、reason=`fresh_inputs_and_usable_solver`；174/174 个 MapStatus 样本均 `input_ready=true`、reason=`ready`，epoch/map_id 连续一致。
- raw VINS telemetry 与 optimized odometry 各 536 条，最大 source gap 均 68 ms；adapter optimized odometry 540 条，最大 source gap 68 ms、最大 source age 184 ms。raw propagated odometry 8,848 条，最大 source gap 4 ms；adapter propagated odometry 8,854 条，最大 source gap 220 ms。LocalizationStatus 最大 source gap 56 ms，MapStatus 最大 source gap 300 ms，`/clock` 最大 source gap 148 ms。时间线未复现 #227 的 stale，但不能据此解释 #227 的触发原因。
- 支架支持扫描完成 15/15 stages。fixture helper 自身仍以 `fresh DISARMED status is required for every fixture command` 记录 `outcome=failed`，不能将其写成 helper 全流程通过；独立证据显示支架已 detached、Gazebo 模型不存在、车辆 landed，且 post-release 与 mission-time N05 online/offline gate 均 `all_entry_phases_known_and_clear`。before gate 的 `ground_plane_insufficient_raw_occupied_voxels` 是扫描前拒绝，不是扫描后拒绝。
- compute-only runner 为 `PASS`：N05 current-area online/offline admission 通过；EGO 对同一目标产生一个 READY 样条，cancel 被接受并确认，bridge 在取消后保持 2.0 仿真秒，最终 landed/disarmed。专用评估 12 项通过。bridge 输入隔离有效；未执行 XY。

## 同图证书与边界

same epoch/map 的几何证书中，起点与终点 body sphere、终点 terminal-hold sphere 通过，连续扫掠 43/43 查询通过；起点半径 0.980618 m 的 hold sphere 有 71 个 raw unknown，故 `geometry_pass=false`，停止包络未证明，`n08_execute_authorized=false`。这不是地面以下可飞行性的判定；unknown 位于地面以上的后方水平空间，不能计作可用净空。

compute-only B-spline 的导数控制点速度上界为 0.099957 m/s，低于本证书向量上限 0.15 m/s。这个速度结果不提供 PX4 的最小制动减速度或响应延迟。本 run 读取到的 `MPC_ACC_HOR=3`、`MPC_ACC_HOR_MAX=5`、`MPC_JERK_AUTO=4`、`MPC_XY_VEL_MAX=12` 是最大限制，不能作为制动能力下界。没有实际水平运动，所以响应延迟、最小可用减速度、停止距离和运动跟踪误差仍无测量。

raw map snapshot 在仿真 804.780 s 获取，较 goal／样条生成时刻晚；它与运行保持相同 epoch/map_id，fusion age 为 28 ms、source age 为 104 ms。初次 snapshot 请求因 `no_fresh_fused_depth` 被拒；后续按已验证 goal、epoch、map_id 从独立 planner observation 恢复捕获并重试，未重建 MapStatus 原始服务响应。该快照可支持同一静态布局的几何查询，但不是与样条生成时刻同步的证据。恢复过程和 guard failure 均保存在 run artifact 中。

## 结论与下一项

#228 证明本次 compute-only 期间定位、地图状态和取消后桥保持正常；它没有复现 #227 的 telemetry stale，也没有得到起点 hold 球全 free 的证书。因此 N08 执行仍锁定，没有实际制动数据。

下一项 #229 只增加一个水平观察方向：保留 #228 的 overhead 支架扫描、场景与所有健康／N05 门限，加入 yaw=−π/2 观察并回中，不做 +π/2 第二侧扫描。假设是单侧后方视角足以覆盖起点 hold 球的剩余 unknown，且避免 #222/#223 中第二侧转向时出现的健康代价越线。判据为完整 detached 支架扫描、fresh post-release/current-area N05 online/offline 同身份接受、定位全程有效，并在该 run 的 raw map 上复算起点 hold 球及既定候选的 body／terminal-hold／连续路径查询。任何拒绝均保留；不放宽阈值，不执行 XY。

## 证据文件

原始产物位于 `artifacts/runs/n08-20261024-228-localization-timeline-01/`。

| 文件 | SHA-256 |
| --- | --- |
| `flight.json` | `02b652ff62c7e44b37534bfbbef69d7029feff679f0aaeac242bc7ee38a5e5d5` |
| `n08-compute-only-evaluation.json` | `5ae2cb0e9e875448d104af80a4db3bb58498df1eb7511e5bf8ca178268152a1c` |
| `n08-curve-certificate.json` | `2926f66908978df0c43733d2e4277be96098f6ad6ef725b25d2d8e400259cb86` |
| `n08-live-curve-map.json` | `304df7563532a92544e46e2eac7bb800acb5fb825c0328f2662313eb6584ab09` |
| `n08-live-curve-map.npz` | `d2e46be5cd21e9173c7897676e1f6a39dfbc6d5cb969a5101e0dfa74b08cb42e` |
| `n08-localization-source-timeline.json` | `00a0f9aea26251bfe8787bd0ffe7121028a2b67976a5347bb166de0b6d3b0e80` |
| `n05-run-summary.json` | `6eb7efa35828c69d28c6bff93d63d544cc709e0cd330212e218d01d6256404bd` |
| `fixture-result.json` | `5b4a0e65160bc78d36b1e0ccd3d62800962981f548002e5fa6af4f7b926b7e58` |

涉及 observer／运行链／捕获器／评估器代码的哈希登记在对应 `n05-run-inputs.json` 与 run manifest。静态检查已在 #228 change record 记录；`project_status.py` 是结构检查，不代替 ROS build 或 SITL。
