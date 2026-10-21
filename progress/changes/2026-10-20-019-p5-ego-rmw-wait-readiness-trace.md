# P5 RMW reader-readiness trace #229

对话摘要：[2026-10-20-019](../../collaboration/dialogues/2026-10-20-019-p5-ego-rmw-wait-readiness-trace.md)。证据：[RMW readiness、EGO take、publisher 与 PX4 ULog](../evidence/p5-ego-rmw-wait-readiness-trace-20261020-229.json)。

## 范围与配置

#229 在 #228 的低负载无真值 VINS/EGO/PX4 SITL 组合上，给 EGO `ego_planner_node` 单独加载 run-local `LD_PRELOAD` 探针。探针在固定 Jazzy/RMW Fast DDS 8.4.4 / Fast DDS 2.14.6 环境中记录 `__rmw_wait` 返回后的目标 camera-pose reader readiness；它与 ROS publisher、successful take、callback 和 executor 事件共用 LTTng 时钟。固定镜像内先完成 800 条 reliable 合成收发测试：基线与插桩各 800/800、零间隙，pass7 CTF 的805条目标 reader 事件序号连续。另以启动参数检查验证 run-local launch overlay；Babeltrace2 仅装在一次性分析容器。

沿用 #228 的目标（ENU +0.30 m、yaw +30°）、run-local anisotropy filter 0.01、EGO 补丁 0012→0013→0015、低速 MapStatus harness 和当前安全门。探针只通过 EGO Node 的 `additional_env` 加载，并检查可执行文件名及 topic substring；没有改 QoS、定位阈值、规划参数、PX4 参数、控制 ownership 或 canonical 源码。没有 debug_truth 或高带宽图像／点云观察器。具体来源和哈希见 run-local [probe-launch-provenance.json](../../artifacts/runs/p5-px4-vio-ego-pose-receipt-rmw-ready-trace-20261020-229/probe-launch-provenance.json)。

## RMW readiness 与 take 对齐

首32.5秒窗口内，mapping_input_adapter 对 `/drone_0_camera_pose` 记录582次 `rmw_publish`，EGO成功 `rmw_take` 563次；EGO最大 take 间隔为2.323925秒。该区间内写端仍有43次 publish、最大间隔0.160376秒。探针在目标 reader 上记录626次 wait 返回，其中625次 `ready=0`；唯一 `ready=1` 事件出现在下一次成功 take 前13.766微秒。该空档内没有 probe 序号缺口。

同一窗口的563次 `ready=1` 与563次成功 take 一一对应；ready 到下一次 take 的延迟中位数9.277微秒、P95 24.566微秒、最大3.895毫秒。EGO没有与该长间隔同量级的 callback 执行；事件证据将这次停顿定位在 RMW 报告目标 reader ready 之前，executor 选取或 pose callback 执行不能解释这段间隔。

这还不能证明具体 RTPS 网络传输或 Fast DDS history 根因：`rmw_publish` 只证明发布调用到达 RMW tracepoint，#229 未采样 DataReader `sample_lost`／`sample_rejected` 或 DataWriter acknowledgement 状态。全 trace 的 28,511 条 readiness 记录中，序号1008–1010有一个缺口，发生在 trace-selection marker 之前约20毫秒；32.5秒分析窗和最大 take gap 内均无缺口。完整33文件 trace 的逐文件 SHA-256 清单在 run artifacts 中。

## 飞行结果与限制

导航 action 以 `position_yaw_tolerance_held` 成功；目标误差位置范数0.0611米。PX4 ULog覆盖32.556仿真秒、dropout为零，EV position/yaw/velocity各有30/43个融合状态样本，GNSS aiding为零；PX4记录 AUTO_LAND、touchdown 与 disarm。最终 localization snapshot 为 `normalized_cost_exceeded`，因此该轮只是成功任务与安全着陆的诊断证据，不是长时定位健康或正式验收。

验证：合成 preflight 构建与 800/800 paired exchange、CTF 分析、`ros2 launch --show-args`、#229 SITL action/landing、Babeltrace readiness/publisher/take/callback 分析、pyulog ULog 汇总及 trace 逐文件哈希。所有输出位于 `artifacts/runs/p5-px4-vio-ego-pose-receipt-rmw-ready-trace-20261020-229`。P5/P6 和 GOAL A–H 仍未完成；F 定量标准尚未冻结，D/E 正式验收未开始。

## 下一步

做一次 run-local Fast DDS status probe，在最大 wait gap 周围只读采样 reader 的 matched、sample-lost、sample-rejected 累计状态，确认 reader 是否失配或发生历史资源拒绝；沿用同一无真值低负载任务，不改 QoS、健康门、PX4 参数或控制 ownership。随后先依据 P1/P2 校准完成 F 的标准冻结，再启动 D/E 正式场景与故障重复。
