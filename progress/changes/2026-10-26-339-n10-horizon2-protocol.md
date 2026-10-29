# #339 N10.3 重新启动局部时域对照

沿用 #338 预先固定的 horizon=2 单变量校准。#338 因 `ros2 topic info /navigation/ego_goal` 首次发现延迟未启动 runner；本轮只增加了入口 graph-readiness retry，不改变运动参数、目标或判据。

正式飞行命令仍需通过 graph gate，完整成功条件包括原 16 m 到达与 600 sim-s active hold。

协议：[采样前记录](../evidence/n10-independent-calibration-protocol-20261026-339.md)。
