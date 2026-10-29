# #405 N10.3 depth fault terminal calibration

- 对话摘要：[2026-10-28-405](../../collaboration/dialogues/2026-10-28-405-n10-depth-fault-terminal.md)
- 结果证据：[校准报告](../evidence/n10-depth-fault-terminal-calibration-20261028-405.md)、[机器可读报告](../evidence/n10-depth-fault-terminal-calibration-20261028-405.json)、[协议](../evidence/n10-depth-fault-terminal-protocol-20261028-405.md)
- 当前计划：[N10 剩余执行计划](../../docs/n10-completion-plan.md)

## 修改

- `tools/fault_relay.py`：为 goal source-stamp 深度注入增加 0.5 s 原子报告检查点；SIGINT/ROS executor shutdown 后仍写 finalized 丢帧和恢复计数。
- `tools/run_vio_ego_flight.py`：增加 opt-in `--expected-fault-abort-reason` 诊断模式。只在 action 按期望原生故障 abort 时等待桥接器自然 landing/landed；不发 operator-disable。普通 runner 行为不变。
- `tools/debug_truth/evaluate_n10_depth_fault_terminal.py`：从 ROS launch `vio.log` 读取 EGO 原生错误，而不是从只读 planner ROS 观察器日志读取；报告原生日志来源，要求 relay 报告 finalized。
- 增加 `tools/test_n10_fault_abort_runner.py` 测试，并扩展 `tools/test_n10_depth_fault_terminal.py` 的原生日志定位回归。
- 建立 run-local 协议、prelaunch identity 和 driver：`artifacts/n10-prepared/n10-20261028-405-depth-timeout-terminal/`。所有观察器只读；不增加运行时健康/拒飞门。

## 运行结果

- 首次 `n10-20261028-405-depth-timeout-terminal` 已观察 action 以 `planner_full_curve_depth_odom_timeout` abort、bridge 按相同故障进入 LANDING 并自然 landed/disarmed，独立末态读回安全；但 relay 收到 SIGINT 后抛 `ExternalShutdownException`，没有落盘注入计数。保留为 evidence-incomplete，不计 PASS。安全读回后通过项目入口停止容器。
- 修复 relay 的 shutdown/finalize 和检查点后，独立 SIGINT smoke 成功得到 `status=finalized`。
- `n10-20261028-405-depth-timeout-terminal-r02` 在相同协议变量下完成。目标后 2.0 sim s 开始仅丢 depth 3.0 source s，丢弃 91 帧；之前/之后转发 1,138/536 帧。窗口内 stereo-left/right/IMU 收据分别为 90/91/749。action 同 epoch/goal abort，bridge 因 `planner_fault:full_curve_depth_odom_timeout` 自然落地；窗口起点至 LANDING 为 0.608 sim s（描述量）。15 s 独立终态检查全部通过，零控制、无 operator-disable、无 emergency disarm。
- 首次离线重放发现 evaluator 误读 planner observer log；从 `vio.log` 复算后，10/10 判断项 PASS。飞行记录未改变。资源 53 点；sensor capture bag exit 0、三路无 source-stamp regression、错误 0。

## 验证

- `PYTHONPYCACHEPREFIX=/tmp/n10-pycache-20261028 python3 -m py_compile ...`：相关 relay、runner、evaluator、测试与 prelaunch 脚本通过。
- `bash -n tools/project.sh tools/sim_runtime.sh .../n10-runtime-driver.sh`：通过。
- ROS 2 Jazzy 环境下 `test_n10_fault_abort_runner.py`、`test_fault_relay.py`、`test_n10_depth_fault_route.py`、`test_n10_depth_fault_terminal.py`：14/14 通过。
- 真实 SIGINT relay smoke：finalized report 写入成功。
- 固定镜像归档重放 `evaluate_n10_depth_fault_terminal.py ...r02`：PASS，全部十项为 true。
- 首次和 r02 均在独立 landed/disarmed/control-disabled/zero-control 读回后运行 `bash tools/project.sh stop <run_id>`；当前无活动项目容器。

## 状态与边界

N10.3/#405 仅完成 depth-loss 故障类别的一次当前版本校准，不计入 N15。一次性 emergency-disarm 授权未在 #405 使用（授权已在 #391 消耗）；没有恢复用户要求移除的健康/速度/raw-known-free 门限。N10 总 acceptance 仍 `INSUFFICIENT`：#404 raw-map 分类 FAIL，跟踪净空预算与平台资源容量依据不足；其他故障类需要校准，N10.4 数值、N10.5 干净重建、N10.6 受影响回归、N10.7 冻结均未完成。下一子项转入 #404 离线分类、误差预算和资源依据复核，再按证据安排下一个缺证据故障类别。
