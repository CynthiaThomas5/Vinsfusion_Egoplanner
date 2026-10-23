# #083 持续 Goal：N01 原始 VIO 全状态误差与漂移基线

## 用户目标与约束

- 持续完成 N01：位置／姿态／速度／RPE／返回漂移／时序，至少 3 个 fresh epoch，并明确已测支持范围；不受普通任务的 30 分钟预算限制。
- 先复用既有项目证据；旧未提交修改都属于项目工作区，不回滚、不提交、不推送。
- 只使用单 D435i 仿真与未武装物理支架；真值仅供独立离线评估，不输入 VINS、地图、规划或控制。
- 不修改定位算法、健康门、控制链路，不启动解锁飞行；保留失败记录。

## 本轮决定

- 既有 #057／#069／#070／#072／#074 记录包含 raw VINS 位置、姿态与独立 Gazebo 真值，但原始采集未保存 raw VINS twist 速度，也没有回调接收时间；不能用 VINS 位置差分代替速度测量。
- 坐标审查发现 Gazebo 真值发布点 `d435i_link` 与仿真 IMU 原点重合；VINS 配置生成的 body frame 也是 IMU。此前评估又将 `base_link` 到 IMU 的杆臂加在 `d435i_link` 真值上，旧绝对误差数值需由正确坐标重新计算。
- 以 raw VINS 的 world-frame 线速度作为估计量；以独立真值位置的 0.2 秒中心差分作为 IMU 点速度参考；单一静止位姿作 SE(3) 对齐，尺度 1，不在返回段重新对齐。补报 `v_imu = v_base + ω×r` 的杆臂一致性核验。
- 固定运行前 protocol：已有 drift fixture 路径、3 次返回、0.1 秒半窗速度差分、40ms 真值括距、200ms raw 位姿插值上限、1／5／10 秒 RPE；报告源龄、单调墙钟回调间隔、coverage 与支持范围。
- GPU0 有无关 AirSim 验证进程；仿真限定使用空闲 GPU1，不触碰 GPU0 或无关容器。

## 完成与待办

- N01.1 证据字段／缺口盘点已完成。
- N01.2 只读数据采集、全状态离线评估器、protocol 与合成回归已完成；`bash tools/project.sh test` 通过 202 项和 ROS action 集成。
- N01.3 已完成：三个 fresh epoch、全状态／RPE／返回漂移／时序汇总和独立 cleanup 审计均记录在 [N01 证据报告](../../progress/evidence/vio-full-state-baseline-20261022-083.md)。
- N01 已标记为通过，下一项 N02；结果只覆盖低速未武装支架仿真，不构成最终精度门限或飞行资格。#02／#04 的失败尝试及 #03／#05 cleanup RPC 未确认均保留并披露。

详细实现、验证和限制：[progress/changes/2026-10-22-083-n01-full-state-baseline.md](../../progress/changes/2026-10-22-083-n01-full-state-baseline.md)。
