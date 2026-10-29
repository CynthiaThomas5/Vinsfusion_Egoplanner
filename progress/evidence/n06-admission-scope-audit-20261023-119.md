# #119 N06.4 准入范围可行性审计

日期：2026-10-23。范围：只读审计 N06.4 全机支架释放后 fresh admission 是否能在当前 N06 执行范围内完成；未启动仿真、PX4、桥接、构建、测试或控制会话。

## 结论

**当前范围内没有合规的 N06.4 执行路径。** 恢复的 N06 子任务范围禁止启动 PX4、桥及控制链。N05 释放后在线复检要求 live bridge 状态；标准 runner 会启动 SITL，执行完整机体支架扫描，并在释放后重新运行在线准入。没有 PX4／bridge 状态链就不能取得条款要求的新鲜 DISARMED 状态，也不能形成有效释放后证据。

N06 父目标保持 `in_progress`，`execution_plan.next_goal=N06`；未开始 N07，未降低门限或替换入口条件。

## 可复核依据

- [N05 runner](../../tools/run_n05_preflight_layout.sh#L56) 调用 `tools/project.sh sim` 启动 SITL；后续通过 `tools/check_n05_entry_live.py` 执行扫描前、支架连接后及释放后的在线检查（[扫描与释放后调用](../../tools/run_n05_preflight_layout.sh#L94)）。
- [在线检查器](../../tools/check_n05_entry_live.py#L54) 订阅 `/uav_px4_bridge/status`；启动条件要求 localization、map、bridge、odom 和 clock 均已收到（[fresh state 集合](../../tools/check_n05_entry_live.py#L72)）。检查要求 bridge 未武装且 `phase=DISABLED`（[状态门](../../tools/check_n05_entry_live.py#L108)），捕获期间 bridge 状态收据不得超过 0.5 秒（[新鲜度门](../../tools/check_n05_entry_live.py#L166)）。
- [N05 入口报告](n05-entry-20261023.md)将当前结果判为 no-go；`wall-r05` 释放后 `transfer_gate_passed=false`。程序化检查 `progress/evidence/n05-entry-20261023.json` 和 `artifacts/runs/n05-20261023-wall-r05/n05-run-summary.json`，均未找到 `transfer_gate_passed=true`。
- 当前项目标签下没有运行中的 Docker 容器；未发现可直接复用的活动状态链。

## 决定与恢复条件

本轮不启动 runner，也不以历史状态、伪造 bridge 消息、debug sensor rig 或 planner-only 结果代替新鲜全机释放准入。需要先明确调整 N06.4 运行范围，允许 PX4 SITL 在 DISARMED、bridge control-disabled 状态下提供所需状态，并执行全机支架扫描、确认 fixture 已移除、完成释放后 fresh admission。该授权不隐含武装、Offboard、目标发布或轨迹执行。

若范围不变，N06.4 及 N06 父目标保持未完成，N07 不启动。恢复准入后，需检查新的 N05 入口结果，并复核受影响的 N06 双布局 planner 出口。

## 验证

只读命令：`git status --short --branch`、N06 文档／milestone 定向读取、`rg` 搜索现存 N05 admission 记录、`docker ps --filter label=d435i.project=/home/huangxiaocheng/D435i-VINS-EGO-ROS2`、读取 N05 runner 和 live checker。项目状态与本轮文档一致性验证见 [#119 改动记录](../changes/2026-10-23-119-n06-admission-scope-audit.md)。
