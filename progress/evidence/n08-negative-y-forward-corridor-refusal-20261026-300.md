# N08 负 Y 侧向 raw unknown 阻止前向走廊（#300）

状态：N05 post-release 和 mission current-area 正向准入通过；N08 取消停车任务在 goal／enable 前被独立 trial corridor gate 拒绝，没有飞行或制动测量。

## N05 支架与入口结果

`n08_overhead_free_sector_view` 完成 15/15 阶段；夹具 detach/remove 且 Gazebo model list 确认 fixture 不存在。helper 留有 `localization changed or became invalid during physical scan` 状态错误（最终 localization 仍有效，cost 0.7434），所以原 warning 保留；run summary 的结构和身份检查 `diagnostic_pass=true`。post-release 与 mission current-area raw-map 检查在同 epoch/map 下 online/offline 一致准入：TAKEOFF_CONTACT、ASCENT、HOLD、DESCENT、LANDING_CONTACT 均无 unknown 或 occupied 拒绝。只读 preflight 40.002 秒通过。

## N08 入口拒绝

运动开始前 raw map 被 0.6 m 目标 capsule 和 0.5 m 候选取消停止走廊共同拒绝。首个前向体积查询含 66 个 unknown；start／terminal hold 查询各含 58 个 unknown，均在 N08 原有机体＋跟踪半径内，故不改门限或将其按未知空间豁免。独立读取同一 raw occupancy 的 cell centers 后发现这些 unknown 集中在 map ODOM `y=−1.05 m` 的薄层，约为起始机体 `−Y` 一侧；因此 #301 采用已有 `n08_overhead_negative_side_view`，唯一改变观察朝向，尝试填充这个侧向观察缺口。

本次 `single_goal motion_cancel` 没有 action goal、服务调用、PositionCommand 或 PX4 TrajectorySetpoint，PX4 未解锁且 landed，bridge DISABLED/control disabled。4 秒独立 readback 的控制消息为 0；项目容器经 `tools/project.sh stop` 停止，exit 0。运行后 evaluator 缺少完整 PRESTREAM-to-LANDED flight，报错没有制动测量含义。

## 下一个子项

#301 新冷启动使用既有 `n08_overhead_negative_side_view`（15 段主观察路线后增加 yaw −π/2 侧向视角），保持布局、N05/N08 包络和 unknown 判据、速度与停车门限完全不变。只有 post-release 与 mission current-area N05 通过，且 fresh N08 forward-corridor/start-hold/terminal-hold 查询全 free 后，才重新执行 0.07–0.09 m/s motion-cancel。

机器可读证据与 SHA 在此报告的 JSON；原始产物位于 `artifacts/runs/n08-cancel-highspeed-prescan-20261026-300/`。
