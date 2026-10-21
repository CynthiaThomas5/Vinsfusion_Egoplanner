# GOAL B/C EGO 开阔短目标重试 #258

## 任务摘要

用户继续推进 GOAL；承接 #256 前置门失败与 #257 低负载双目新鲜度观察，在保留 mapper/EGO 的情况下重试0.7 m开阔目标，并移除额外地图采样器。

## 约束与决定

- 定位健康策略保持原样；run-local EGO膨胀0.5 m、地图下界−0.05 m。
- 仅当定位有效、MapStatus input-ready、占据点至少500且地图持续非空0.5秒时才发布一次目标。
- 不启动轨迹服务器、控制器、PX4或setpoint发布者；不订阅真值。
- 使用按 `/clock` 驱动、无模型位姿订阅的run-local力激励脚本。

## 确认结果

健康门在目标探针可用时报告 `imu_stale`；建图适配器reset后 `input_ready=false`、占据0，goal未发送且无B-spline。40秒目标探针结束为 `timeout_before_ready`。65秒raw VINS只读观察仍有634条优化、8,359条传播和644条telemetry；传播输出最大源戳间隔135 ms、墙钟接收间隔332.5 ms。这些是下游输出，不能代替直接IMU输入接收记录，也不证明失效根因。容器正常退出0，未发布控制。

## 下一步

保持0.5 m膨胀的全栈设置，直接观察双目与IMU源龄／接收节奏，保留健康和MapStatus门；只有稳定就绪后才发一个短目标。无轨迹执行、PX4或真值输入。

证据：[p2-ego-clear-target-retry-20261020-258.json](../../progress/evidence/p2-ego-clear-target-retry-20261020-258.json)。
