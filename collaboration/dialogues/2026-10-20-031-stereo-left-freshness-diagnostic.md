# 左右图像新鲜度隔离诊断 #257

## 任务摘要

承接 #256 的开阔短目标前置门失败。用户要求继续推进 GOAL；本轮先直接观察双目图像源戳、墙钟接收间隔、接收时 `/clock` 年龄，并比较定位状态。

## 约束与决定

- 保留 PROVISIONAL 定位健康阈值，不改项目源码、配置或 canonical launch。
- 探针只读订阅左右红外图像、`/clock` 和定位状态；不发布目标、控制或 PX4 setpoint。
- 用 run-local 力激励脚本按仿真时钟发 Gazebo wrench，不订阅模型真值或 IMU。
- 为降低负载隔离传感器与 VINS/定位链，本轮不启动 EGO、mapping、地图探针或 goal probe。

## 确认结果

#257 左／右图像分别收到1487／1486帧，双目3 ms内配对1485组；源戳最大间隔66 ms，接收时源龄最大181／192 ms。定位进入TRACKING并保持约41秒，随后由 `normalized_cost_exceeded` 锁定，没有观察到 `left_stale`。raw VINS输出有限，truth样本为0。此结果支持低负载下图像链持续新鲜，但不能证明适配器逐帧收到每条图像，也不能定位 #256 全栈 `left_stale` 的根因。

## 下一步

保留定位与MapStatus健康前置门，重试0.7 m开阔目标；启动 mapper/EGO，移除额外地图点云采样器，等待稳定定位、有效MapStatus和非空占据后只发布一个目标。无控制器、PX4或在线真值。

证据：[p2-stereo-image-freshness-20261020-257.json](../../progress/evidence/p2-stereo-image-freshness-20261020-257.json)。
