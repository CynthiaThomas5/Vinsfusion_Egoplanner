# #155 N07 远后视角诊断

对话摘要：[N07 远后视角诊断](../../collaboration/dialogues/2026-10-23-155-n07-retreat-observation.md)

## 范围

N07 Goal 子项；本轮仅做 DISARMED 全机支架观测和 fresh N05 gate，不构成悬停或飞行资格。

## 依据与计划

#154 双向平移后 HOLD 尚有 422 unknown。新增逐格审计确认未知格中心 z=0.55–1.25m，raw ground plane z=−0.35m，地面以下 unknown=0；故障点为地面以上的未知，不是地下体素。#154 的 `spawn=-8m` 使向后静态全机走廊受西墙限制在 0.8m。既有 #146 已使用 `spawn=-6.5m` 和 2.4m 后退路径，完成 12/12 阶段，并在支架释放后获得一致的 N05 五阶段 online/offline 接受。

主要假设：同一相机朝向下将后视平移距离由 0.8m 增至 2.4m，可把之前太靠近相机的 HOLD 包络未知格纳入有效深度视场。主要变量为后视观测距离；yaw/pitch 保持 0，N05 判据和全机安全半径不改。通过判据为定位与 epoch/map 连续、支架确认脱离、PX4 DISARMED、bridge DISABLED，且 fresh N05 online/offline 五阶段均接受。

## 本轮执行记录

- 先以 `bash tools/project.sh stop n07-20261023-154-03` 停止旧诊断容器，确认 `exited 0`；未停止其他容器。
- `config/runtime.json` 的 spawn 从 `-8,0,0.3,0,0,0` 改为 `-6.5,0,0.3,0,0,0`；改前 SHA-256 为 `a862e521dd738dba71d960cda95458509336f1e2cd845228b46311fd57928221`。
- 候选运行：`n07-20261023-155-01`，wall N05 layout，复用 `n06_full_airframe_retreat_240_translation_only` profile；运行产物计划位于 `artifacts/runs/n07-20261023-155-01/`。
- N07 悬停合格次数仍为 0/3。

## 结果与验证

待本轮 SITL 与 fresh N05 检查完成后填写：实际阶段、VINS/身份连续性、online/offline 结果、PX4/bridge 最终状态、SHA-256 和对应命令。

## 后续

只有 fresh N05 五阶段 online/offline 一致接受后，才启动 N07 三次独立冷启动无目标悬停。若仍拒绝，N07 保持 `in_progress`，继续按拒绝体素的新位置分布寻找可安全补充的视角；不放宽地面或 unknown 规则。

## 独立冷启动复核

后续 #156 在同一 spawn、profile 和距离下，于返程末段触发 `accel_bias_norm_exceeded`；其首个 telemetry bias=0.150071 m/s²，峰值0.159841 m/s²，map reset，未获得 release gate。#155 的 2.4m 路线因此不能视作跨冷启动稳定通过。#156 的清理确认 fixture 已删除且 PX4 DISARMED。详细对比见[#156 证据](../evidence/n07-retreat-health-failure-20261023-156.md)。下一项改用1.5m同轴观察，不放宽health门或N05。
