# N07 #187 对话摘要：early-view 支架扫描偏置健康失败

## 约束

- 按已授权的N07 Goal完成模式继续到三次连续冷启动出口通过。
- 不放宽0.15m/s² bias门限、N05门限或地下边界。健康失败时不得起飞。

## 结果与下一步

#187换用同一镜像/runtime历史成功的early-view支架profile，但第7/12阶段VINS accel bias于source 250.276s首次越过既有0.15，最终到0.187644，触发`accel_bias_norm_exceeded`；normalized cost仅0.531617。没有ready marker/attached gate/飞行。fixture安全移除，PX4 disarmed/landed，容器exit0；N07计数仍0/3。

数据见[失败报告](../../progress/evidence/n07-preflight-health-failure-20261024-187.md)。#188回到#180/#182用过并通过N07的separated-return路线；门限不变。
