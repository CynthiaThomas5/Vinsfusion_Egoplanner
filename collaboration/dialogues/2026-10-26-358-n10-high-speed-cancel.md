# 2026-10-26 #358 N10 高速取消制动

## 本轮范围

继续用户授权的 N10.3。#357 已完成同一 16 m 路线、600 仿真秒保持和完整观察；本轮只补当前缺失的高速度 caller-cancel 制动测量，并同步修复 CURRENT 中落后的 #357 状态。

## 用户约束

- 继续使用单 D435i、Gazebo/PX4 SITL 和唯一 `uav_px4_bridge` 控制出口。
- 定位质量/新鲜度旁路仅为运行诊断；不改 normalized-cost 原门限，不宣称健康资格。
- 使用官方 EGO inflated-occupied 规划；不让项目额外 raw-free 全曲线检查拒绝这次候选停止曲线。
- 不把真值送入控制；确认飞行器落地、上锁、控制关闭和零控制样本后再停止本次容器。

## 决定

在 #357 实测 PX4 峰值 0.636 m/s 和 N08 约 0.081 m/s 低速制动之间，预先固定 0.50–0.56 m/s 作为唯一取消触发窗口。停止定义复用 N08 水平 ≤0.03 m/s、垂向 ≤0.05 m/s 连续 1 仿真秒。具体测量协议先写入 #358 protocol，再实现官方任务入口的 run-scoped 诊断模式。

## 待决

- 取消到替代轨迹、减速、停止的测量值及重复性。
- 同一运行的最小机体净空能否从冻结场景几何和真值轨迹独立复算；如不能则保留未测。
- N10.3 标准能否收敛；若有数值仍缺独立依据则保持 provisional。

## #358 启动结果

首次 runner 使用了 bash nounset，ROS Jazzy setup 因可选环境变量未定义而退出；未进入 preflight，也没有 PX4 控制。独立 3 秒读回确认 DISABLED、landed、disarmed、控制关闭、控制样本0，随后项目容器 exit 0。已移除 runner 的 `-u`。详情见 [#358 启动失败记录](../../progress/evidence/n10-high-speed-cancel-stop-startup-failure-20261026-358.md)。接下来使用全新 run id #359，仍按原 0.50–0.56 m/s 窗口和原始 flight settings 测量。
