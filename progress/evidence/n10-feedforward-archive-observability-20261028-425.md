# N10.3/#425：#412 前馈归档可观测性与 #415 安全读回

## 归档能证明什么

只读检查 #412 的 `flight.json`（SHA-256 `60cddc369542ac56ec01a47e9a7f89eb9519acbd0b8580064d925a73bde3934e`）发现，`position_command_history` 保留了 EGO 的位置、ENU 速度和加速度；`px4_trajectory_setpoint_observations` 只保留 PX4 输入的 position、yaw、yawspeed，没有 velocity 或 acceleration 字段。附属 MCAP（`d4fe2556829a62d802359b4b69fec03cac515ee9932f81e00fe6b39829cde612`）的 metadata 只列相机左右红外图和 IMU，共 50,522 条消息，没有 PX4 控制设定点话题。

这与 #424 的桥接源码审计相符：桥接器有计算出的 NED 速度，但当前实际发布将 velocity 置为 NaN。归档能证明输入速度存在、实际输出是 position-only，也证明同样本位置误差具有约 1 秒回看相关性；它没有记录实际 PX4 velocity/acceleration setpoint，因此**不能**用旧归档验证丢弃速度前馈是否导致滞后，也不能证明转发前馈会改善跟踪或净空。因果验证仍需在安全收尾后作单变量实现对照，保留同一阈值、航迹和评估方法。

## #415 当前安全状态

同域只读读回 `r15` 持续 6 秒，SHA-256 `b3338bfb0f5ea275d272f9dec53e1240d82508be50af3bd7cfb3ba5eee8f7308`：bridge 26、PX4 8、land-detection 3、local-position 187、attitude 376 个样本；没有 terminal 样本，也没有控制话题事件。读回仍为 bridge `LANDING`、control enabled、armed；PX4 armed/failsafe `DESCEND`，`land_detected=false`，EV position/yaw fusion false，local XY invalid。无效 local-position 报告数值为 NED `[206528.297, -32099.348, -1.502] m`、速度 `[24.010, 99.617, -0.110] m/s`；由于 `xy_valid=false`，这些值不能解释成真实机体轨迹或接触证明。PX4 与 bridge 控制发布端点仍存在，因此零事件只适用于这 6 秒采样窗口，不能证明控制已禁用。

r06–r15 共累计 104 秒分段同域读回，无一次观察到安全终态。#391 的一次性紧急 disarm 授权已经使用；当前仍不停止控制栈、不发控制命令、不开始新飞行、不改运行源码或参数。后续需要原生 landed/disarmed/control-disabled/zero-control 终态，或用户对当前 #415 明确新增一次紧急 disarm 与受控停止授权。

## 验证

- `PYTHONPATH=tools python3 -m unittest tools.test_n10_px4_tracking_lag tools.test_observer_window tools.test_n10_truth_observer -v`：12 项通过。
- `PYTHONPYCACHEPREFIX=/tmp/n10-20261028-pycache python3 -m py_compile tools/debug_truth/evaluate_n10_px4_tracking_lag.py tools/observer_window.py tools/debug_truth/record_truth.py tools/record_n09_contacts.py`：成功。默认仓库 `__pycache__` 首次因目录权限无法写入；将缓存放到 `/tmp` 后通过。
- `git diff --check`：通过。
- `python3 tools/project_status.py`：结构检查通过；报告 80 个可选历史 artifact 链接缺失。该检查不替代 ROS/PX4 构建或 SITL。
- 未修改运行代码、参数或验收阈值，未构建、未飞行。

证据文件：#412 flight `artifacts/runs/n10-20261028-412-speed040-yaw-lookahead-calibration/flight.json`、MCAP metadata `artifacts/runs/n10-20261028-412-speed040-yaw-lookahead-calibration/n10-sensor-payload/metadata.yaml`、MCAP `artifacts/runs/n10-20261028-412-speed040-yaw-lookahead-calibration/n10-sensor-payload/n10-sensor-payload_0.mcap`，以及 #415 live probe `artifacts/runs/n10-20261028-415-speed040-yawcap010-compacttrace-calibration/n10-live-fault-state-probe-r15.json`。
