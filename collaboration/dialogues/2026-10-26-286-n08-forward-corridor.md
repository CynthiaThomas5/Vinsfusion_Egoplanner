# N08 前向单目标走廊门恢复

## 本轮目标与约束

用户要求按 #274 测试计划完成 N08。普通 EGO 单目标到达并停车后结束；返航属于另一条显式命令。N07 已通过项不复测，#260、#267、#273 的有效单次制动数据保留，但不同 runner／goal 指纹不能组成同版本三次验收。所有 N08 速度、健康、时间、unknown、0.15 m 跟踪 watchdog、5 cm 曲线管道和 0.25 m 试验 margin 保持。

## #285 现场结果

纯平移 N05 支架扫描、释放后准入、任务前 full symmetric corridor、preflight 和 runtime 指纹通过。起飞后地图同一身份、时间新鲜，但对称前向 corridor 首球遇到机尾侧 32 个 unknown、0 occupied；runner 未发送 `NavigateToPose`，随即落地上锁。该次不算 EGO／制动验收。

## #286 方向证书决定

只对无偏航、前向普通单目标启用 directional swept-volume 证书：完整 `body + 0.25 m` 查询半径保留，采样球沿前向平移 0.075 m，曲线 x 必须不倒退，横／垂向 5 cm 管道、实际 0.15 m tracking watchdog、速度和健康门不变；起点 hold 仍检查，终点用中心不平移的全向 `body + 0.25 m` 球。显式返航和转向保持原对称检查。

在 #285 实际空中快照上，旧规则可复现 32 unknown 拒绝；新规则 25 个采样全部 raw free、起点与终点 hold 均通过，reachable bound 0.24014 m 小于 `0.25 m + 0.0125 m` 的可用界，保留 0.02236 m 几何余量。该离线结果只支持几何实现继续验证，不替代飞行。#286 计划以全新冷启动重做同一 N05 前置流程并执行 0.04–0.06 m/s `motion_cancel`。
