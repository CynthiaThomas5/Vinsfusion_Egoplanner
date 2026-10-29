# N07 #197：悬停被定位状态新鲜度保护提前中止

## 结果

**FAIL_SAFETY_ABORT；本次不计为 N07 合格冷启动，连续计数保持 0/3。** Run：`artifacts/runs/n07-20261024-197-01/`。同一 epoch 完成 N05 支架路径及释放后准入，但无目标悬停只持续 **2.16 仿真秒**，未达到每次至少 30 秒的出口。

## 固定条件与 N05 准入

镜像 `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`、runtime 配置 SHA-256 `1ddd6838ae2a678f89547ce90eea849582edcc29cddab341667bd2d1d9d3e360`、runtime-contract 文件 SHA-256 `856bf1f2222a5286493813c9702731f7e5166844eb2bfd98c6f525f3f36924eb`、spawn `-6.5,0,0.3,0,0,0`、`wall_box_column` 布局、`n06_full_airframe_retreat_240_oblique_separated_return` 支架路径及所有准入／健康／控制／验收阈值保持不变。

初始 N05 online/offline gate 一致因 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope` 拒绝。未武装支架扫描完成 12/12 阶段，N05 summary 为 **14/14**，post-release 和独立 current-area fresh online/offline gate 均在同一 epoch/map 上接受 `all_entry_phases_known_and_clear`。fixture helper 的 `outcome` 仍为 failed，错误为 `fresh DISARMED status is required for every fixture command`；错误未隐藏。helper 记录 attached→detached、`fixture_removed=true`、`fixture_may_remain_attached=false`，但 remove service ack 为 false。独立 Gazebo model list 确认 fixture 不存在；支架释放安全读回确认 vehicle DISARMED/landed、bridge DISABLED 且无控制。

## 悬停结果和时序证据

未经修改的 no-goal runner 到达 `ACTIVE`，起飞后开始 hold，没有发送导航 goal。悬停从 wall elapsed `28.1252s` 到 `30.9141s`，共 **2.16 仿真秒／2.789 墙钟秒**，随后 runner 请求 disable 并完成正常 landed/disarmed。flight runner 返回 `SAFETY_ABORT`、exit 1；独立 evaluator **10/11** 检查通过，唯一失败为 `hover_completed_at_requested_sim_duration`。

最有证据支持的立即触发是定位状态的接收新鲜度超限：runner 对 localization status 使用 **0.2s** 最大接收年龄；hold 结束时最近一条 valid/TRACKING 状态在 wall elapsed `30.5611s` 收到，年龄约 **0.3530s**，下一条 valid 状态在 `30.9147s` 才收到，晚于记录的 hold 结束时刻。depth、camera pose、occupancy cloud 和 optimized odometry 也在同一时段记录到约 **0.338–0.385s** 接收间隔。hold 结束时记录到的 bridge 状态仍为 ACTIVE/armed，clock 没有停滞或倒退，VINS 状态样本全为 valid。runner 未记录显式 loop-break reason，因此将这个新鲜度原因标为基于时间戳的推断；系统调度或传输暂停的根因尚未分离。

`flight.json.failure=px4_preflight_failed` 来自落地后的 bridge readiness 状态。该字符串在起飞前 DISABLED 状态已出现；#194/#195 也有相同起始状态并完成 30 秒 hold，因此不能据此认定它是本次 hold 中止原因。

## ULog、ROS graph 与安全停止

PX4 ULog 分析 **12/12** 通过：`EKF2_EV_CTRL=15`、`EKF2_GPS_CTRL=0`、`SIM_GZ_EN_ODOM=0`，记录到 airborne EV position/yaw fusion，GNSS flags 未激活，最终 PX4 disarmed 且 landed。ULog SHA-256：`088fb95e2fc3a2b426bc68ddac91ff43478b05103795e3503c6b25942b3c9b18`。只读 graph gate 在 0.410s 内发现 ACTIVE+armed 和四个唯一 bridge control publishers；`active_discovery_ready`、`airborne_active`、`flight_result_written` 三个快照均无 ROS truth topic/node 且唯一控制发布者为 bridge。

飞行后 bridge 独立读回 `LANDED / control_enabled=false / armed=false`，PX4 `arming_state=1`，LandDetected `landed=true`，fixture 已移除，flight/observer 进程已结束。`bash tools/project.sh stop n07-20261024-197-01` 退出 0；容器 `Exited (0)`，活动项目容器为 0。安全读回文件写入后，host 显示脚本在打印摘要时抛出格式异常；随后重读已保存 JSON，六项 safety checks 全通过，且 stop 状态验证通过。

本次有短暂受控起飞，不代表 N07 飞行验收通过。没有地下飞行或地下目标。

## 下一步

失败的冷启动不计入三次连续成功；N07 仍为 `in_progress`、streak 0/3。#198 使用同一固定条件和门限开启新冷启动，观察同一 freshness 限制下是否能完成完整 30 秒 hold；不放宽 0.2s freshness 要求。若仍提前中止，将按记录的新时间窗口检查接收间隔是否重现。

原始时序推断和逐文件哈希见[JSON 报告](n07-no-goal-hover-failure-20261024-197.json)及运行档案 `artifacts/runs/n07-20261024-197-01/`。
