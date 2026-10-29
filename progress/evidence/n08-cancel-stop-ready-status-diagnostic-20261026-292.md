# N08 #292：取消后停止样条已生成，runner误等未发布的 COMPLETED

## 结论

本次完成了真实 motion-cancel 与独立制动测量，但 native runner 最终为 `FAIL`，因此不能作为 N08 通过或最终重复运行之一。停止样条通过速度与地图走廊证书，PX4 真值显示飞行器已停住；runner因等待不存在的 `PositionCommand.COMPLETED` 状态，超时后在终点降落检查前 operator-disable。

## 前置准入

- Run：`n08-cancel-translation-prescan-20261026-292`，epoch `a129f5addd294d78a61017c4ad7d9498`。
- N05 全机扫描6/6，夹具拆除，post-release online/offline准入接受且同 identity；摘要 `diagnostic_pass=true`。helper 留下通用 localization warning，但显式 post-release检查通过；保留警告。
- 40.0145 s 只读preflight通过，最大optimized-odometry receipt gap 0.3604 s（门限0.5 s）；mission current-area online/offline N05接受。
- MapStatus刷新修复有效：ground/airborne raw-map snapshot请求成功，capsule与起飞前 destination landing候选通过。

## 取消与停止轨迹

取消时 PX4 水平速度 `0.0400167 m/s`，EGO reference速度 `0.0578432 m/s`，进入既定触发窗口。action 取消确认；ROS结果三字段为 status=5、outcome=`canceled`、reason=`caller_cancel`、success=false。

原轨迹ID 1 被新停止轨迹ID 2替换。EGO日志记录最终动力学refine成功、16次fresh-map曲线查询均为free。独立实时曲线证书通过：停止样条vector速度导数界 `0.08712 m/s`（上限0.12），reference tube通过；无watchdog事件、无spline rejection。旧trajectory ID后续未恢复。

独立真值部分测量（结束于runner开始operator-disable，不是完整任务验收）：峰值水平速度 `0.08785 m/s`，source-curve braking start后行程 `0.19270 m`；cancel请求到停止的实际轨迹长度 `0.29850 m`，约 `4.552 s`；到持续减速的响应 `2.932 s`；真值最大采样间隔 `0.02 s`，reference跟踪最大误差 `0.09130 m`。独立曲线观测到速度持续低于水平0.03、垂直0.05 `1 s`，停住后位置最大偏移 `0.01217 m`。PX4 local-position样本也在速度门内持续约9.2仿真秒，直到runner启动operator-disable。

这些数据支持EGO实际停住，但不是完整N08 pass：runner没有写出规定的 `post_goal_hold_end_sim_ns`，没有确认完整3秒hold出口，没有执行stop后的destination landing admission/command。

## 根因

`run_motion_cancel_stop()` 等待 `PositionCommand.TRAJECTORY_STATUS_COMPLETED`。当前EGO `traj_server.cpp` 在样条时间结束后将参考位置设为终点、速度和加速度设为零，但发布路径仍设置 `TRAJECTORY_STATUS_READY`。新停止样条终端参考首次在source stamp `387.864 s`出现，末端位置约 `[0.30116, 0.00216, 0.88133] m`，导数为零；该轨迹2共记录2552条命令，全为READY。历史#260普通终点也呈现READY语义。

因此native runner在没有状态事件的情况下等待到18秒墙钟上限，随后operator-disable。不是EGO没生成停止样条，也不是地图或速度证书拒绝。

## 修复与安全收尾

#293修复为：用EGO B-spline knots有效时间域与source `/clock`确定轨迹终点；确认同一停止轨迹在终点后持续发布稳定末端位置和零速度/加速度，再核对PX4水平 `<=0.03 m/s`、垂直 `<=0.05 m/s` 连续3仿真秒且bridge保持ACTIVE。`READY`被记录为上游终端保持语义，不作为完成事件，也不降低任何速度、时间或安全门限。离线evaluator同时改为检查status=5、outcome=`canceled`、reason=`caller_cancel`各自的正确字段。

PX4独立最终读回：bridge `LANDED`、control disabled、disarmed、landed；control mode、trajectory setpoint、vehicle command消息均0。runner的operator-disable正常降落完成；项目容器已停止。

部分诊断原始结果：`artifacts/runs/n08-cancel-translation-prescan-20261026-292/diagnostics/pre-disable-cancel-stop-measurement.json`（SHA256 `3fd5b3fbee34392bbcef1dad8a373aec59261edaee30901e47441bf2cf8dba07`）。完整flight记录及PX4读回在同一run目录。native `flight.json` SHA256：`1c631015ef9cfec1aa5ec4ed08e67bf66759d510e79cb01bc385c47574288d79`。

## 下一步

新冷启动#293：重做当前epoch N05支架扫描与任务前门；确认MapStatus修复，再验证source-time stop-spline endpoint判据、实测3秒hold、stop后landing及独立evaluation。N08仍`in_progress`。
