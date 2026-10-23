# N01：原始 VIO 全状态误差与漂移基线

**状态：通过。** 三个不同 VINS fresh epoch 在相同冻结协议／runtime contract 下完成所需测量，并按同点坐标评估。这个结论只覆盖本报告列出的低速未武装支架运动；不表示最终定位门限或飞行验收通过。

## 测量方法

- Gazebo truth `d435i_link` 与仿真 IMU 原点重合，VINS body frame 是 IMU。truth 与 raw VINS 直接比较；`base_link` 安装杆臂只用于 `v_imu = v_base + ω×r` 一致性核对。
- 只用一次初始 SE(3) 对齐，尺度固定为 1，不拟合全轨迹或时间偏移，不在返回段重对齐。速度比较 raw VINS 的 world-frame `twist.linear` 与独立 truth 位置的 0.2s 中心差分。
- 三个 epoch 的语义 protocol hash 为 `8e8c6ae6…baf433`，runtime contract hash 为 `4e2b88bd…354478e`。计划文件 SHA-256 为 `9d20de4d…b4d8900`。统一使用带 2ns 表示舍入容差的最终离线 evaluator；该修正未改原始采集或协议。

## 三个 fresh epoch 汇总

下表为三个 epoch 的 **min / median / max**，不是把所有帧混为一个样本。

| 指标 | min / median / max |
|---|---:|
| 位置 ATE RMSE | 0.0303 / 0.0346 / 0.0370 m |
| 位置 ATE P95 | 0.0490 / 0.0608 / 0.0623 m |
| 位置最大误差 | 0.0640 / 0.0642 / 0.0672 m |
| 姿态测地 RMSE | 0.3511 / 0.3745 / 0.4325° |
| roll RMSE | 0.0265 / 0.0305 / 0.0401° |
| pitch RMSE | 0.0361 / 0.0413 / 0.0435° |
| yaw RMSE | 0.3479 / 0.3701 / 0.4295° |
| 速度向量误差 RMSE | 0.01850 / 0.01860 / 0.01991 m/s |
| 源龄 P95 | 0.292 / 0.296 / 0.296 s |
| raw 最大 source gap | 0.200 / 0.200 / 0.264 s |
| raw callback 最大 wall gap | 0.214 / 0.221 / 0.225 s |
| truth 配对位置覆盖 | 1.00000 / 1.00000 / 1.00000 |
| truth 配对速度覆盖 | 0.99954 / 1.00000 / 1.00000 |
| 超出 0.2s 插值支持上限的 raw 间隔数 | 0 / 0 / 1 |

### 相对位姿误差（RPE）

| 窗口 | 平移 RMSE min / median / max | 旋转 RMSE min / median / max | 各 epoch 支持数／拒绝数 |
|---|---:|---:|---|
| 1s | 0.00271 / 0.00278 / 0.00285 m | 0.0264 / 0.0266 / 0.0279° | 2153/2169 (16 拒绝), 2108/2117 (9 拒绝), 2077/2088 (11 拒绝) |
| 5s | 0.00877 / 0.00884 / 0.00937 m | 0.0550 / 0.0571 / 0.0630° | 2117/2169 (52 拒绝), 2084/2117 (33 拒绝), 2054/2088 (34 拒绝) |
| 10s | 0.01325 / 0.01339 / 0.01374 m | 0.0718 / 0.0751 / 0.0832° | 2085/2169 (84 拒绝), 2053/2117 (64 拒绝), 2022/2088 (66 拒绝) |

### 逐次返回漂移

| 返回 | 位置漂移 min / median / max | yaw 漂移 min / median / max |
|---|---:|---:|
| 1 | 0.0213 / 0.0239 / 0.0286 m | 0.290 / 0.293 / 0.315° |
| 2 | 0.0356 / 0.0373 / 0.0416 m | 0.371 / 0.443 / 0.488° |
| 3 | 0.0460 / 0.0579 / 0.0607 m | 0.499 / 0.575 / 0.727° |

## 独立 epoch 与完成依据

| Run | Epoch | collector result | 完成依据 |
|---|---|---|---|
| [n01-vio-state-20261022-083-01](../../artifacts/runs/n01-vio-state-20261022-083-01/vio-full-state-report.json) | `78fe4157c79848a9bea64b8d44cbbadc` | `unarmed_support_drift_completed` | `probe_completed_and_acknowledged_fixture_removal` |
| [n01-vio-state-20261022-083-03](../../artifacts/runs/n01-vio-state-20261022-083-03/vio-full-state-report.json) | `bfe776476ee3404c9fc1148dab7b5200` | `failed` | `all_motion_stages_complete_and_postdetach_cleanup_independently_verified` |
| [n01-vio-state-20261022-083-05](../../artifacts/runs/n01-vio-state-20261022-083-05/vio-full-state-report.json) | `e3fa3cf74ebe4d0f83efcdbf47256b59` | `failed` | `all_motion_stages_complete_and_postdetach_cleanup_independently_verified` |

#03／#05 的采集 result 因 detach 后移除 RPC 未收到确认而保留 `failed`。独立 cleanup audit 对每轮均确认支架已 detached、Gazebo pose 中模型不存在、PX4 为 DISARMED 且 landed。汇总器只接受这一精确清理错误，并要求完整 23 阶段、三个返回、原始输入哈希和独立 audit；未改写失败 result。

Run05 有 1 个 raw source gap 为 0.264s，超过 0.2s RPE 插值支持上限。窗口级评估拒绝跨越不支持区间的 RPE 样本，并报告拒绝数；不跨该间隔插值。其余 raw 样本、ATE／速度真值配对覆盖与三次返回仍完整列入汇总。

## 未计入的尝试

- **#02**：第 11/23 阶段因 `normalized_cost_exceeded`，cost 1.20598，采集器依既有健康条件停止。支架随后通过独立 Gazebo 关节缓慢归位、确认 DISARMED 后拆除；保留 partial full-state 结果，不计入三轮。
- **#04**：0/23 运动阶段；导航日志记录 localization 状态接收龄 0.520s（guard 0.500s），optimized odometry 接收龄 0.599s。最后 VINS 状态仍 valid、cost 约 0.191。现场无支架运动；确认 landed／DISARMED 和支架移除后停止，不计入三轮。
- #03 首次容器启动因未预建输出目录在 Gazebo 启动前退出，无仿真、无 epoch；日志保留在 `artifacts/runs/n01-vio-state-20261022-083-03/startup-attempt-01.log`。同一 run id 的后续有效采集在目录预建后执行。

## 历史 #057／#069 同点更正

- **#057**：1290 对／85.144s；位置 RMSE 0.04796m、最大 0.08964m、末端 0.08669m；yaw RMSE 0.2943°、最大 0.5095°。无 raw 速度与回调接收时间，因此不计入三次全状态 epoch。
- **#069**：2365 对／344.388s；位置 RMSE 0.03548m、最大 0.07398m、末端 0.06624m；yaw RMSE 0.4161°、最大 0.7331°。三次新增返回位置漂移 0.01855／0.03732／0.05716m，yaw 漂移 0.2484／0.4242／0.6554°。同样不计入三次全状态 epoch。

## 已测支持范围与限制

三轮各覆盖约 342.7–344.8 仿真秒、truth path 8.37–8.40m；水平往返跨度约 1.2m、高度变化约 0.6m、yaw span 约 17.45–17.45°。速度峰值约 0.122–0.134m/s。roll 未激励，pitch 变化约 0.28°。

没有声明最终误差通过门限。该测量不能证明 roll／pitch 强激励、长距离、重复纹理、障碍物地图、EGO 规划、PX4 自主飞行、真实 D435i 时间同步、Jetson 负载或实机性能。独立 timing 观察另发现 optimized odometry 有 0.358s 间隔超过导航监督器 0.3s guard，作为 N02 时序风险保留。

机器可读交叉 epoch 汇总：[summary.json](../../artifacts/runs/n01-vio-state-20261022-083-checks/summary.json)。逐帧误差、RPE CSV、返回漂移、原始 odometry、truth、trace 和 cleanup audit 均在上表各 run 目录，并由报告记录 SHA-256。

完整更正与过程记录：[changes #083](../changes/2026-10-22-083-n01-full-state-baseline.md)。N01 完成后下一项为 N02；P4–P6 与总 GOAL 保持进行中。

## 验证

- `python3 -m unittest tools.test_vio_full_state_summary -v`：5 项通过。
- `bash tools/project.sh test`：208 项通过；ROS action／250Hz clock 集成通过。
- `python3 tools/project_status.py`：Structure/design check PASS；报告 80 个可选历史 artifact 链接缺失。该检查不代表 ROS build、SITL 或实机验收。
- `git diff --check`：通过。
