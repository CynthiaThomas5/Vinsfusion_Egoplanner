# N08.2c #213：compute-only 目标准入拒绝

## 结论

本次 compute-only 未通过：fresh N05 current-area gate 通过、launch 运行图确认 bridge 已隔离 `/position_cmd`，但 20 秒内没有观察到任何 PositionCommand READY 曲线。EGO 持续处于 `WAIT_TARGET`，planner observer 没有收到 `/navigation/ego_goal`。bridge 在 runner 超时后走 `operator_disable` 并安全着陆；没有 EGO 曲线或横向运动，也没有制动数据。此结果保留为失败诊断，不算 compute-only 通过。

## 可直接确认的证据

- 一轮 12 阶段 N05 支撑扫描完成，夹具模型被确认从仿真场景移除，attachment 状态含 `detached`，所有已记录 PX4 状态均 DISARMED，最终 landed 为 true。但扫描器自身因“fixture command 前需要新鲜 DISARMED 状态”返回失败且最后 landed 回执年龄 4.07 秒；wrapper 因此保留容器供安全检查。随后 mission 的只读 readiness 和新鲜 N05 current-area gate 均通过，online/offline 一致，才启动 compute-only runner。
- bridge 隔离图正确：`/position_cmd` 由 `drone_0_traj_server` 发布、订阅数为 0；`/n08/compute_only_position_cmd` 的唯一订阅者是 `uav_px4_bridge`。`/navigation/ego_goal` 的 publisher/subscriber 端点存在，但运行期 planner observer 收到 0 条目标消息；`PositionCommand` 样本数为 0。
- runner 记录 action 请求被 ROS action server 接受，目标为当前位姿相对 ENU +Y 0.6 m；但没有 READY 样条。runner 报 `ego_ready_trajectory_not_observed`，随后 bridge `operator_disable`，最终 `LANDED`、armed=false、landed=true。容器已按流程停止。

## 目标查询分析（离线推断）

导航节点只在目标球 raw occupancy 查询接受后才发布 `/navigation/ego_goal`。按冻结的同轮 N05 raw occupancy snapshot 与当前 0.7306179 m 查询半径，复算 +Y 0.6 m 目标球得到 2,181 个相交体素：1,848 free、333 unknown、0 occupied；unknown 高度约 0.8–1.7 m，球体最低点约 0.214 m，高于地面。即使不偏移，当前中心附近也有 53 个 unknown。这个离线 map 早于起飞数十秒，真实 action query 返回值未被 runner 保存，因此“目标球 unknown 导致导航未转发”是符合代码路径和运行图的强推断，尚非直接记录的服务响应。

同一 frozen map 上固定 X/Z 与查询半径、只改变 Y 的离线扫描显示，0 至 +0.9 m 的球体均含 unknown，+Y 越远未知越多。粗网格只读候选检查在 ENU offset (0, -0.4, 0) 找到 2,200 个相交体素全部 free、无 occupied/unknown。该点只是下一轮 compute-only 候选，未通过实时查询、路径净空或停止距离认证；执行模式仍锁住。

## 下一步

保持 0.7306179 m 查询半径和所有未知拒绝条件。改进 compute-only runner，让它在 READY 等待期间也观察 action 终态、保存明确拒绝原因，并在失败路径先取消活动 action 再禁用 bridge、记录着陆状态。随后用新的冷启动对 (0, -0.4, 0) 候选重新执行 fresh N05 gate 和 compute-only；任何新鲜查询拒绝或缺少 READY 都继续保持不运动。

运行输入哈希、目标球计数和候选扫描摘要见 [JSON 记录](n08-compute-only-refusal-20261024-213.json)。
