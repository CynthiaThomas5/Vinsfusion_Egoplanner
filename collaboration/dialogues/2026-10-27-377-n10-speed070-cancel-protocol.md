# N10.3/#377 速度峰值附近制动量测

#376 同一 profile 测得 PX4 水平速度峰值 0.7418 m/s；在 `[0.70,0.80] m/s` 量测窗内有 98 个有效样本。本轮选该窗，在飞行曲线达到这段实测速度时 caller-cancel，记录 PX4 停止时间、真值停止路径和 contact/末态。速度窗只决定何时取样，不限速、不拒绝轨迹，也不是验收阈值。

固定项：单 D435i PX4 SITL、-8 m spawn、单程 +16 m/+0.10 m/+0.20 rad 目标、horizon5、max_vel0.8、max_acc0.25、official_ego 碰撞、read-only contacts。保留 PX4 原生 preflight/EV 融合和桥接停止控制。协议和 prelaunch 已冻结，尚未启动 SITL；实际加载 identity 不符时不发送目标。结束后必须独立确认 landed/disarmed/control-disabled/zero-control 才停止容器。
