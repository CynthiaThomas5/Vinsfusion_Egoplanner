# N10.3/#400 规划器退出校准尝试与故障链发现

对话摘要：[2026-10-27 #400](../../collaboration/dialogues/2026-10-27-400-n10-planner-exit-calibration-attempt.md)。

## 改动

- 从 #398 独立准备 planner-process-exit run-local 输入，固定 runtime、目标、planner、spawn、协议和 prelaunch 身份。
- 增加只读 ROS 订阅的进程退出注入器：要求目标/epoch、bridge、action status 和单一 PID/start ticks 身份匹配；保护逻辑 5 项单测通过。
- 增加 fault-run driver 和运行协议；末态 probe 显式携带 `flight.json` 中的 goal_id/epoch。
- 注入器未发信号。本次 incidental PX4 local-position invalid 触发 bridge landing，但对应 navigation action 仍 executing；已在 landed/disarmed/control-disabled 后精确取消该 action，并确认终态后 control stream 为零。
- 因 post-terminal 的同 goal/epoch READY 位置命令仍被观察到，fault terminal evidence 保持 insufficient。物理停止条件已另行核实后，按 `tools/project.sh stop` 正常停止容器。

## 验证

- `test_planner_exit_injector.py`：5 passed。
- injector/prepare prelaunch Python compile、runtime driver `bash -n`、协议 JSON parse、`git diff --check` 与 `python3 tools/project_status.py`：通过；结构检查不代表故障链通过。
- #400 SITL：起飞前检查和 goal submit 通过；planner SIGTERM 次数 0，因此不构成 process-exit calibration。桥于 sim 119.316 s 因 `px4_local_position_invalid` 转入 LANDING，并于 124.536 s 到达 LANDED；action 未随 bridge landing 结束，直到安全 closeout action cancel。
- 15 秒独立终态读回：LANDED/disarmed/land-detected/control-disabled 和 zero-control 通过；同身份 READY 命令 1,099 条，`no_old_epoch_goal_or_trajectory=false`，终态总结 `native_terminal_evidence_complete=false`。
- sensor capture 离线读取 PASS 不成立：payload/receipt 数据可读取，但完整终态、run identity 和 observer closeout 缺失，overall `INSUFFICIENT`。资源/真值/接触最终报告和净空结果不计通过。
- 项目容器在独立 physical-terminal readback 通过后，使用 `bash tools/project.sh stop n10-20261027-400-planner-process-exit-calibration` 正常停止，container exit 0；没有 emergency disarm。

完整数据和限制见[校准尝试报告](../evidence/n10-planner-exit-calibration-attempt-20261027-400.md)与对应 JSON。#400 不加入完成子项列表。下一子项 #401 修 bridge failure 到 navigation action 的身份匹配 abort，修 action-status QoS，并补运行收尾区分；完成构建和定向回归后再运行当前版本校准。N10 仍 `in_progress`，N15/N16 未启动。
