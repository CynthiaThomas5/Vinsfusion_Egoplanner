# N10.3/#387 方箱坐标与实际命令净空复核

**结论：坐标修正解释不了全部差异；#385 有单次实际轨迹避开箱体的采样证据，但没有地图驱动重规划证据。** 本轮只对归档做只读取证，没有运行仿真或修改控制参数。

## 复核方法

用 #385 独立到达报告中的固定 prestream SE(3) 将协议使用的 EGO-odom 箱体中心、SDF 世界中心、整条 B 样条几何和逐时间戳 READY `PositionCommand` 都变换到同一 Gazebo world 坐标，再计算与同一个 0.8×0.8×2.8 m 方箱的距离。另核查注入后的同 identity raw-map query 和 ROI 关联。

## 结果

- 协议假设 odom 箱心 `[8, 0, 1.10] m` 经固定变换后落在 world `[0.122, -0.001, 1.166] m`；SDF 箱心为 `[0, 0, 1.4] m`，两者相差 **0.264 m**。反算 SDF 箱心的 odom 坐标为 `[7.878, 0.001, 1.334] m`。
- 使用实际 SDF world pose 后，注入前和注入后的首条完整 B 样条几何都出现零中心线距离；但逐时间戳 READY `PositionCommand` 的实际中心线距箱体至少 **1.463 m**。轨迹 ID 22 的整条几何样本不等于它活跃时间窗内实际输出的命令路径，不能把整曲线最近点当作已飞行轨迹。
- 真实机体包络按 Gazebo 真值采样，扣除观测到的最大样本间包络位移后为 **1.131 m** 正下界；这只覆盖该次离线采样，不是连续动力学证书。该 run 禁止接触数为 0。
- 注入后 0.5 与 1.25 仿真秒的 raw-map query 请求中心，经固定变换落在实际 SDF 箱体内部；两次返回 `free=true`、`unknown=0`、`free=160`、`occupied=0`。这是同 identity 查询观察，原因仍需查；单凭它不能断言在线 EGO 的最终碰撞策略，也不能声称地图已把方箱写成 occupied。
- 之前的 occupied-cloud ROI 是独立静态圆柱接近观察，记录没有与方箱对应的点坐标。深度/彩色快照也未提供足以将 ROI 点逐一绑定到方箱的坐标证据。

因此，固定 SE(3) 小幅修正不是零中心线结果的根因；更直接的差异是整条 B 样条几何与时间戳对齐的活跃命令序列不是同一数据。#385 的飞机确实有正净空的单次实际轨迹采样，但目前不能证明改道由方箱 occupied 输入触发。动态重规划的因果与地图更新仍未支持。

机器报告：[JSON](n10-obstacle-alignment-forensics-20261027-387.json)。离线复算：[JSON 产物](../../artifacts/runs/n10-20261027-385-arrival-dwell4-retry/n10-obstacle-alignment-forensics.json)，[复算脚本](../../tools/debug_truth/evaluate_n10_obstacle_alignment.py)。

**下一步 #388**：只读审计 occupancy query 的采样与地图更新语义，准备不改控制的观测记录：分别请求方箱迎机表面与内部、记录实际 frame/pose/source time/map identity，并把 occupancy 点坐标保存下来。若源审计/离线证据已能解释 free 结果，先复用，不盲目重飞。
