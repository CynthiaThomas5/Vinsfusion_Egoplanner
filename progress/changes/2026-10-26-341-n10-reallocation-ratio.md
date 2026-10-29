# N10 #341 spline reallocation ratio correction

对话摘要：[2026-10-26 N10 #341 ratio 修正](../../collaboration/dialogues/2026-10-26-341-n10-reallocation-ratio.md)。

## 假设与代码变化

根据 #340 实测，唯一改变是处理无加速度违反控制点时遗留的 `max_acc=-1` 哨兵：这种情况下该项对时间重分配 ratio 贡献 0。速度项、加速度违反项、threshold/tolerance、最终 feasibility 判定和 3 次 refine 限制不变。协议固定于[报告](../evidence/n10-spline-reallocation-ratio-protocol-20261026-341.md)。

## 验证与结果

- `patch --dry-run -R -d src/vendor/ego_planner -p1 < dependencies/patches/ego/0051-n10-spline-reallocation-ratio-sentinel.patch`：成功，确认补丁基于 0050。
- `bash tools/project.sh build ros`：17/17 ROS 包完成，15.7 秒；日志在 `artifacts/runs/n10-20261026-341-spline-reallocation-ratio/build-ros.log`。
- 同 #340 参数的新鲜 PX4/SITL runner 因 `planner_full_curve_planning_failed` exit 1。40 条逐轴检查中，max X 控制点导数为 0.305505 m/s > 0.1051 m/s 门；max 加速度 0.061277 m/s² < 0.2626 m/s² 门。无 READY 曲线或水平目标运动；ratio 行显示没有加速度越限时 `acceleration_ratio=0`。
- `python3 tools/debug_truth/evaluate_odometry.py artifacts/runs/n10-20261026-341-spline-reallocation-ratio`：exit 0；434 个配对样本、最大位置误差 0.01161 m、最大 yaw 误差 0.04246°，只覆盖 28.676 sim-s 起降。
- Contact 评估通过、违规接触 0、live refusal 通过；PX4 arming_state=1、bridge LANDED/disarmed；project stop exit 0，容器状态 `exited 0`。
- 完整数据与哈希见[#341](../evidence/n10-spline-reallocation-ratio-20261026-341.md)。该源码行为变化可能影响历史两次 refine 的 N09 成功；按 N10.6 影响审查复核 N08/N09，不能直接继承。

## 后续

#340/#341 观察到长程初始 spline 的 X 控制点导数约 `0.239–0.306 m/s`，而 `.10 m/s` per-axis 配置的有效门是 `.1051 m/s`。下一项只试验由这些数值推导的 `max_velocity=0.31 m/s/axis` 候选。由于通用 N10 runner 之前没有运行中速度保护，#342 将先接入基于同一目标配置 `acceptance_calibration_limits.max_actual_vector_speed_m_s=0.12` 的 EGO参考速度与 PX4 本地速度监视；超限立即取消当前 action，走已验证的 EGO STOP_HOLD／bridge-owned landing 流程。该监视器不提高 N10 速度阈值；若候选轨迹越过原 0.12 m/s 向量上限，#342 只作为受控诊断失败，不能据此宣称 16 m 支持范围通过。N10.3 还缺长距离/时长定位、地图、净空、重规划与时效的独立依据；#341 的补丁也可能影响历史 N09 两次 refine 成功，需在 N10.6 做影响回归。
