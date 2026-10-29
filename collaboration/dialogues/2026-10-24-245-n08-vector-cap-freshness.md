# N08 #245 对话摘要：PX4 时间域和定位 freshness

## 用户约束

- 继续用户已指定的 N08 Goal 完成模式。
- PX4 时间对齐验收按用户明确要求不要求跨运行连续；已通过的 N07 证据不复测。
- 不降低 N08 原有安全／制动门限；未有同 run stop-corridor certificate 前不执行 XY。

## 本轮决定

- 使用正确的 `n08_low_speed_vector_cap.json` 尝试同 run compute-only 证书。
- #245 PX4 HRT/ROS 时间域全样本有效，拒绝来自 Localization `telemetry_stale`，与 PX4 时间参考问题分开处理。
- 未修改健康阈值；下一项先定位 raw VINS 与 adapter 接收／回调时序。

## 待决

- 为什么 observer 后续看到 raw telemetry 推进，而 adapter 在 telemetry source age 超限时锁存且没有接收该推进样本，仍需用 callback/QoS/executor 时序验证。
- N08 的实际低速 XY、响应延迟、减速度、停止距离与三次同版本目标重复仍未完成。
