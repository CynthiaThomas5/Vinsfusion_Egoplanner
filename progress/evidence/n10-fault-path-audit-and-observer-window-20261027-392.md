# N10.3/#392 故障结束路径与观察器终止条件审计

## 结论

静态审计确认 EGO 深度/里程计超时与 planner 进程退出都会向当前 `goal_id/epoch` 发布任务 abort；navigation 清理转发目标；PX4 bridge 通过匹配的 abort 进入 LANDING，并委托 PX4 原生着陆状态机。原版本只发一次 `NAV_LAND`，且没有把 LAND ACK 与当前请求关联，无法据此确认命令已被接收。最小修复加入有界重发、ACK/原生状态读回，并在尝试用尽后继续保持 LANDING，等待 `landed && !armed`；没有增加项目自定义拒飞、停飞、强制 disarm 或运行健康门。

本轮也修正了一个真实调用错误：`REQUEST_ARM` 的 Offboard 丢失分支仍使用旧 `_begin_landing` 签名，可能抛异常；现在传入当前快照和 wall time，并新增回归测试。

观察器原先可能把 `flight.json` 存在误当安全终止。#391 证明失败任务可在 bridge `LANDING`、armed、未 landed 时产生 `flight.json`，资源观察随后被中断。现在统一要求已验证的原生 safe-to-stop、明确记录的紧急收尾，或成功且 bridge 终态一致的 flight 记录；资源观察在安全终态后再采 3 秒。观察器只读，超时/缺数据仍记录为不足，不影响起飞、取消、降落或 PX4 控制。

## #391 状态记录校正

冻结 PX4 `VehicleStatus.msg` 中 `nav_state=18` 为 `AUTO_LAND`，`12` 为 `DESCEND`，`14` 为 `OFFBOARD`。#391 的 `vehicle_status_history` 先于 273.916 s（flight wall elapsed 139.887 s）记录 AUTO_LAND；278.032 s（wall elapsed 144.261 s）转为 failsafe DESCEND。紧急命令前的独立读回仍为 DESCEND/armed/not-landed。紧急 disarm 后读回为 OFFBOARD 状态码，但已 disarmed、LandDetected=true、bridge LANDED/control-disabled、零控制。原始消息与历史保持不变；派生分析报告现列出状态转移。归档没有可关联到 NAV_LAND 请求的 ACK，因此不推断 ACK 成功，也不把紧急关闭算成原生故障降落。

## 代码路径

| 阶段 | 已审计行为 | 边界 |
| --- | --- | --- |
| EGO 深度/odom 超时 | `0055` 调用 `stopForSafety`；该函数发布带活动 goal/epoch 的 `MODE_ABORT`、锁存安全状态、清除目标并回到 `WAIT_TARGET` | EGO 消息本身不证明 PX4 命令、着陆或 disarm 已完成 |
| Navigation | 仅处理仍转发且 epoch 一致的故障；abort active action，再清除转发目标 | 这是 action 终止路径，不是物理安全终态 |
| EGO 进程退出 | bridge 在 VIO closed-loop active goal 期间按 PID+进程启动 tick 监视；消失或进程身份不唯一时发布匹配 abort | 只在 active goal 期间监视；未经 SITL 不能宣称完整链路通过 |
| PX4 bridge | 仅匹配当前 airborne goal/epoch 的 abort 生效；进入 LANDING，重发未确认 `NAV_LAND`；读到原生 DESCEND/AUTO_LAND/PRECLAND 或接受 ACK 后停止发命令，持续等 PX4 landed 且 disarmed | 重试次数耗尽或 PX4 未给 terminal 时 phase 保持 LANDING；不会伪报 LANDED 或强制 disarm |

ACK 处理按时间域区分：`UXRCE_DDS_SYNCT=0` 时将 PX4 HRT ACK 时间与 HRT 命令时间比较；启用同步时改用本机 monotonic 接收先后，不比较 Agent 与 PX4 两个不兼容时钟域。`VehicleCommandAck` 本身没有原命令事务 ID，所以这仍是 command-id 加时间/接收序的关联，不等于可唯一标识任意多个并发同类命令。

## 验证与限制

- `bash tools/project.sh build ros`：17 个 ROS 包构建通过。
- `bash tools/project.sh test`：471 个工具单测通过；navigation adapter integration 与 official EGO policy probe 通过。
- 额外离线命令：`python3 tools/debug_truth/evaluate_n10_hold_divergence.py --run-dir artifacts/runs/n10-20261027-391-integrated-calibration-retry --output artifacts/runs/n10-20261027-391-integrated-calibration-retry/n10-hold-state-divergence.json`。报告复列 `AUTO_LAND → DESCEND`、紧急 precheck 和紧急 terminal 读回；未修改归档原始输入。
- `git diff --check` 通过。

上述是源码、构建、单测和归档复算，不是 EGO 真断流或 planner 退出的端到端 SITL 通过证据。#391 的接触先于定位锁存与 planner timeout；初因未识别，且故障保持期间缺少连续图像/双目接收历史。PX4 最终 landing/disarm 仍需在修复且冻结的新运行中逐类校准。N10.3 与 N10 保持未完成，#391 不计 N15/N16 正式次数。

下一项先把 #381/#385/#391 的实测跟踪/漂移误差对应到机体尺寸、路径净空和通道几何，建立可解释的离线误差预算；同步固定下次综合运行的完整 observer/readback 顺序。只有出现具体、可验证的输入或实现修复并冻结运行身份后，再启动受影响校准。
