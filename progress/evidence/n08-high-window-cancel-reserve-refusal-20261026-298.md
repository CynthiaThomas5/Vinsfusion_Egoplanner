# N08 高窗口取消前置拒绝（#298）

状态：保留为失败；没有产生 motion-cancel 停车测量。

本次新冷启动 N05 支架扫描 6/6，夹具脱离／移除；post-release 与 mission 当前区域在线／离线 N05 均通过，40.01 秒只读 preflight 通过。解锁前与起飞后的 0.6 m 前向走廊、单独 0.50 m 取消候选走廊、目标区预降落候选均通过。

EGO goal 已发送并在 0.07–0.09 m/s 触发窗监测期间飞行；runner 在发 caller-cancel 前报告 `motion_cancel_stopping_envelope_not_available`，因为新增逻辑要求到原 goal endpoint 仍至少有 0.50 m。该位置关系不等于从当前速度产生的新停止路径长度，故门过严并阻止了原定高窗口取消测量。没有 caller-cancel action/result、替代停止样条或有效制动距离。runner 发起 operator-disable 并实际 landed/disarmed。4 秒独立 readback 再确认 bridge LANDED/control disabled、PX4 disarmed/landed、控制消息0；容器停止 Exit(0)。

## 修正

移除“到原 goal 尚须剩余 0.50 m”的取消触发拒绝，保留该剩余路程作为诊断值。0.50 m 仍由唯一 N08 profile 驱动解锁前与空中 raw-map 前向走廊 admission，并由离线 evaluator 对取消请求到实际停止的**测得路径长度**判定。发往 PX4 前，EGO 对新替代 B 样条作同 epoch/map 的 fresh raw occupancy 完整曲线和 terminal-hold 查询；地图 freshness、身份或任意查询失败时不发布该曲线。相关检查位于 `ego_replan_fsm.cpp::certifyLocalCurve` 和 `grid_map.cpp::GridMap::certifyCurve`。

`bash tools/project.sh test` 通过 362 项及 navigation-adapter integration。新增回归确认：余留到原目标小于 0.50 m 时，只要独立测得的取消停车距离满足候选包络，评估器不作错误拒绝。下一项 #299 使用全新冷启动重试高窗口取消，不能复用 #298 的飞行段。

详细记录见[机器可读证据](n08-high-window-cancel-reserve-refusal-20261026-298.json)与[运行产物](../../artifacts/runs/n08-cancel-highspeed-prescan-20261026-298)。
