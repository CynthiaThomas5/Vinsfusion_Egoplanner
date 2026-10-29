# N10.6/#463 干净重建回归与图契约拒绝

## 回归结果

在 #462 的隔离 clean install 上，项目全套 596 项单测通过，导航适配器集成与官方 EGO unknown 语义探针通过。第一次回归因 code-only export 没带历史几何测试夹具而有 3 项 `FileNotFoundError`；从 #398 归档拷入只读 SDF 夹具并核对 SHA-256 `eb22ce222e701372ff0e87066ea9fa63a6ce660904ea759dc3b80bac1c3e0d94` 后，596 项全部通过。夹具仅在 candidate 的 `artifacts/runs/` 下供离线测试使用，不属于源码、构建或 SITL 输入；两次完整日志均保留在 `artifacts/runs/n10-20261028-462-clean-rebuild/`。

## PX4 任务入口结果

#463 在全新 PX4 SITL/ROS 安装启动后，确认了唯一 `uav_navigation` publisher、EGO planner 与 `uav_px4_bridge` 两个接收端。起飞前状态检查通过；`tools/n09_runtime.sh` 随后因错误地要求 subscriber 数为 1，以 exit 14 拒绝继续。未提交导航目标，无 `flight.json`、无 offboard enable、无解锁或起飞。

独立停机前读回：bridge `DISABLED`, `control_enabled=false`, `armed=false`, `landed=true`；PX4 `arming_state=1`（disarmed）、land detection `landed=true`。预检查时 `pre_flight_checks_pass=false` 是当前未解锁 POSCTL 模式的状态；PX4 启动后已记录 mode-specific takeoff check 的 `Ready for takeoff!`。本次任务未进入预送 setpoint 阶段，因此这个状态既不是任务拒绝原因，也未绕过 PX4 原生 preflight。SITL 容器经项目 stop 命令受控退出（exit 0），没有使用紧急 disarm。

图拒绝和末态原始输出见 `artifacts/runs/n10-20261028-462-clean-rebuild/n10.6-flight-driver.log`、`n10.6-refusal-final-readback.txt`、候选原始目录 `n10-20261028-463-clean-build-regression/` 及 `n10.6-refusal-closeout.json`。

## 修正与范围

N10 冻结协议中的图契约及此次 live graph 均要求一个 supervisor publisher 和两个接收端。已将 `tools/n09_runtime.sh` 与 `tools/run_n10_cancel_calibration.sh` 的静态检查改为精确要求两个已知接收节点（planner、PX4 bridge），保留 publisher、节点身份与图不完整即拒绝的原有检查。`bash -n`、`git diff --check`、`python3 tools/project_status.py` 通过；此修改尚未在最终候选上做项目全回归和完整 PX4 任务。

由于 shell runner 属于运行身份，#462 的干净构建只适用于修复前源码快照，不能用作最终 N10.5 候选。下一步重新导出修复后源码并完成全新 ROS/PX4 构建，再对该安装复跑全回归和代表性 PX4 任务。该报告不计 N09 正式次数或 N11–N16 次数；N10 故障校准仍按 #434 排除。
