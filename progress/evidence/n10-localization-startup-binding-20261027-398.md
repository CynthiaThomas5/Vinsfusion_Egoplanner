# N10.3/#397–#398 定位流启动绑定与综合校准重试

## 结论

#397 的 0.4 m/s 综合校准在 PX4 原生预检阶段停止，没有提交导航目标、没有武装，也没有产生飞行校准数据。现场日志定位到 adapter 首次绑定 propagated 发布者的启动次序竞态。已修复并完成 8 项定向测试、17 包 ROS 构建；#398 使用修复后的新 runtime identity 重试。此报告暂不把 #398 计为通过。

## #397 原始证据

- 预检观察约 40.000 s；结果 `passed=false`，reason 为 `px4_local_position_invalid`，累计 379 次缺 odometry、377 次 bridge 本地位置无效及 377 次 PX4 external vision 未融合。PX4 EV position/yaw fused 均为 0。
- `vio.log` 在仿真 8.548 s 记录 VINS `Initialization finish!`；约 8.616 s，adapter 以 `propagated_publisher_missing_or_changed` 锁存。完整 `localization_integrity_fault_snapshot` 有 IMU、左右图像、optimized odometry 和 telemetry 样本，但没有 propagated 样本；normalized cost 为 0.0971446。该时刻 GID 尚未由 propagated 消息回调绑定。
- 传感器输入仍有持续收据：IMU 21,357 条、左右图各 2,588 条，来源时间范围分别覆盖 7.856–93.280 s、7.856–93.228 s；未观察到足以解释 EV 未融合的传感器断流。
- 只读末态记录确认车辆始终 disarmed/landed、bridge `DISABLED`、零控制；`bash tools/project.sh stop n10-20261027-397-speed040-integrated-calibration` 正常结束，随后没有本项目 Gazebo/PX4/ROS 进程或运行容器。无紧急 disarm。

## 修复内容与验证

- 尚未由首条消息绑定的流跳过定时 endpoint 查询。首条消息仍必须解析唯一 publisher、校验与已识别 VINS 节点一致并绑定 GID；后续变化、缺失或多 publisher 仍按完整性故障锁存。
- `python3 tools/test_localization_health.py`：8 项通过。
- `PYTHONPYCACHEPREFIX=/tmp/n10-398-pycache python3 -m py_compile src/own/uav_localization/uav_localization/health.py src/own/uav_localization/uav_localization/node.py tools/test_localization_health.py`：通过。
- `bash tools/project.sh build ros`：17 个 ROS 包构建通过。
- `git diff --check`：通过。

## 当前状态

N10 保持 `in_progress`。#397 是预检失败，不是 0.4 m/s 实验结果；#398 运行完成前，本项综合校准仍未完成。净空的连续区间界、完整当前版本故障终态校准、资源/队列接受依据以及 N10.4–N10.7 仍未关闭。N15/N16 正式次数仍须在 N10 冻结后执行。

## 关联日志

- [#397 run](../../artifacts/runs/n10-20261027-397-speed040-integrated-calibration/)
- [#397 independent preflight-abort readback](../../artifacts/runs/n10-20261027-397-speed040-integrated-calibration/terminal-preflight-abort-readback.json)
- [#397 run-local preflight](../../artifacts/runs/n10-20261027-397-speed040-integrated-calibration/preflight.json)
- [#397 adapter/VINS log](../../artifacts/runs/n10-20261027-397-speed040-integrated-calibration/vio.log)
- [#398 prepared run tools](../../artifacts/n10-prepared/n10-20261027-398-speed040-integrated-calibration/)
