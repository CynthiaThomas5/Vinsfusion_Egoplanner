# N10.3/#405 深度断流到 PX4 自然终态校准

## 结论

在 `n10-20261028-405-depth-timeout-terminal-r02` 中，隔离 depth 入口按活动 goal source stamp 后 2.0 s 开始丢弃 3.0 s，随后恢复转发。断流期间左右图像和 camera IMU 继续到达；EGO 原生 `full_curve_depth_odom_timeout` 触发后，action 以匹配故障原因 abort，bridge 自然 LANDING 并达到 LANDED/disarmed。独立 15 s PX4/bridge 读回确认控制关闭、终态后零控制、无旧 goal/epoch 轨迹；没有 operator-disable 或 emergency disarm。

本次离线评估为 **PASS**，只关闭“当前版本 depth 单流超时到自然 PX4 终态”的一次 N10.3 校准。它不是 N15 正式重复次数，不建立延迟门限，也不使 N10 总验收通过。

## 观测结果

- Depth relay 在窗口前转发 **1,138** 帧，3.000 sim s 窗口内丢弃 **91** 帧，窗口后恢复转发 **536** 帧。注入 goal ID 和 VINS epoch 与飞行记录完全相同。
- 故障窗口内收到 stereo-left **90**、stereo-right **91**、camera IMU **749** 条只读源戳回执；整段采集无源戳回退、MCAP bag exit 0、采集错误 0。
- EGO 原生日志记录 `Depth Lost! aborting active navigation task` 和 `depth_odom_timeout`。Action 结果为 `aborted / planner_full_curve_depth_odom_timeout`。
- Bridge 以 `planner_fault:full_curve_depth_odom_timeout` 进入 LANDING。故障窗口起点至 LANDING 的观测间隔 **0.608 sim s**，仅作描述，不是通过阈值；之后自然进入 LANDED，armed=false、control_enabled=false。
- 独立末态检查：PX4 disarmed/landed、bridge LANDED/disarmed/control-disabled、零终态后控制样本、无旧 epoch goal/trajectory，terminal violation 0。`safe-to-stop.json` 与独立读回均完整。
- 资源观察器采样 53 点，并在安全终态后 3 s 收尾；真值、bridge、planner、contact 与完整传感器观察均按同一 run 归档。

## 首次尝试与评估修复

原 run `n10-20261028-405-depth-timeout-terminal` 同样观察到 action 因深度超时 abort、bridge 自然 landed/disarmed、独立安全读回通过；但 fault relay 的 ROS 2 SIGINT 收尾抛出 `ExternalShutdownException`，没有保存转发/丢弃计数，因此保留为 **evidence-incomplete**，不计本项 PASS。修复 relay 以原子检查点保存状态并捕获 executor shutdown 后，在新 run `r02` 完整复验。

`r02` 首次离线报告因判断器读了 planner 观察器日志而显示 `INSUFFICIENT`；native EGO 事件在 run 的 `vio.log`。判断器已改为读取 ROS launch 原生日志并补两项日志源回归；用冻结镜像重放归档后，10 项判据全部 PASS。飞行与原始记录未变，判断器没有控制效果。

## 验证

- `python3 -m py_compile`：relay、飞行运行器、终态评估器、定向测试和 run-local prelaunch 脚本通过。
- `bash -n`：`project.sh`、`sim_runtime.sh`、#405 runtime driver 通过。
- ROS 环境下 relay、路由、fault evaluator 和 native-abort runner 定向测试 **14/14 通过**。
- relay SIGINT 独立 smoke：提前中断仍写出 `status=finalized` 报告。
- 固定镜像离线重放：`tools/debug_truth/evaluate_n10_depth_fault_terminal.py artifacts/runs/n10-20261028-405-depth-timeout-terminal-r02`，**PASS / 10 checks true**。
- 两次运行均在独立 readback 确认安全终态后，通过 `bash tools/project.sh stop <run_id>` 关闭；当前无活动项目容器。

## 身份与限制

Run-local runtime contract SHA-256：`773dd222f637fc79b3686ea488f3cac5af4b7b9ec6dfee93f4098bcce25c8981`。最终评估 JSON SHA-256：`a934c1809e7572a91990d7d4b1a5daac9cf58c2265e6540ae2747fb26354b780`。其他关键文件哈希见[机器可读证据](n10-depth-fault-terminal-calibration-20261028-405.json)。原始运行记录位于 [`#405 r02`](../../artifacts/runs/n10-20261028-405-depth-timeout-terminal-r02)；首次不完整尝试单独保留在 [`#405 首次尝试`](../../artifacts/runs/n10-20261028-405-depth-timeout-terminal)。

本结果只证明当前模拟配置下此一类深度输入故障的单次自然退出路径。其余故障类别、地图分类、定位/跟踪净空预算、资源容量依据及验收数值仍未完成；N10.4 仍为草案，N10.5–N10.7 未开始。N15 六类各两次正式故障测试与 N16 十分钟正式任务仍在 N10 冻结之后。
