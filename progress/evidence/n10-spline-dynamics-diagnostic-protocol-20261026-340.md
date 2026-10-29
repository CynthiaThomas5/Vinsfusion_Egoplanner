# #340 N10.3 最终样条动力学只读诊断协议

状态：**执行前协议固定。** #337（horizon=5 m）与 #339（horizon=2 m）均由 EGO 的最终 spline velocity/acceleration feasibility gate 拒绝；两个运行都没有逐轴超限值，因此暂时不能依据证据挑选新速度或加速度值。

## 唯一变化与假设

- 唯一变化：启用 diagnostics-only EGO 补丁 0050，输出每次 final-spline 检查的逐轴最大绝对速度、逐轴最大绝对加速度、configured limits、容差、velocity ratio、acceleration ratio、overall ratio 以及 refinement 序号。
- 算法、动态阈值、规划配置、任务和停止规则固定为 #339：16 m 单程、+0.1 m 高度、+0.2 rad yaw、native dwell 3 sim-s、max velocity 0.10 m/s/axis、max acceleration 0.25 m/s²/axis、planning horizon 2.0 m、official_ego 与单 D435i。
- 假设：诊断输出能确定最终曲线是被逐轴速度约束、加速度约束，还是二者共同主导而拒绝。该运行只测根因，不校准或放宽任何阈值。

## 判据与运行边界

1. 先在当前运行镜像重建受影响 ROS 包；构建与 source manifest/patch hash 校验通过后才启动 PX4/SITL。采样日志必须出现实际的 EGO 最终样条检查记录，且保留每个 refine attempt。
2. 目标拒绝时须通过逐轴最大值与原始限值、容差、独立 velocity/acceleration ratio 判定主导项；结合 EGO 当次状态记录，不能只从总 ratio 猜测。
3. 若任务意外通过，按原协议完成完整 16 m 独立真值到达评估，并仅在目标通过后开始 600 sim-s ACTIVE hold；保留原有定位、地图、freshness、tracking、contact 与 PX4 landed/disarmed 条件。
4. 任一定位／遥测失效、clock 回退或停顿、规划拒绝、超时、碰撞观察失败，均按当前 bridge-owned landing 结束。失败运行不重试、不改门限；先根据已记录的新数据确定有依据的下一个单变量实验。
5. 成功的 diagnostic log 不是飞行资格，也不能替代 N10.3 对长程定位、地图、净空、重规划和时效支持范围的独立校准。

## 输入与产物

- 运行 ID：`n10-20261026-340-spline-dynamics-diagnostics`
- Goal profile：`config/components/navigation/n10_long_range_vio_calibration_goal.json`
- Planner profile：`config/components/mapping/n10_horizon2_calibration.json`
- EGO patch：`dependencies/patches/ego/0050-n10-spline-feasibility-diagnostics.patch`
- 运行产物：原始 planner/ROS 日志、flight/preflight/arrival/contact/freshness/odometry 评估与 manifest，放入 `artifacts/runs/<run_id>/`；本协议与轻量结论放入 `progress/evidence/`。
- 参考：[#339 horizon 对照](n10-horizon2-calibration-20261026-339.md)、[N08 低速测量](n08-final-completion-20261026-327.md)、[N09 official_ego 资格](n09-official-policy-qualification-20261026-332.md)。
