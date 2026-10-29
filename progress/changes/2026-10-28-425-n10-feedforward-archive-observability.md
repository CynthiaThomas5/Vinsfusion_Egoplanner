# N10.3/#425：前馈归档可观测性与 #415 读回更新

## 改动

- 新增 #425 离线证据，确认 #412 保存了 EGO 原始位置/速度/加速度，但 PX4 setpoint observer 仅存 position/yaw/yawspeed，附属 MCAP 只含两路红外图和 IMU，不含 PX4 控制话题。
- 结论限定为实现路径证据与待验证假设；旧归档无法验证 velocity feed-forward 的因果收益。
- #415 新增 r15 六秒同域只读状态采样：仍 armed/failsafe DESCEND、bridge LANDING/control enabled、无 land-detected/terminal；补录 r06–r15 累计 104 秒读回。
- 更新 `progress/CURRENT.md` 与 milestones 索引，父 N10 仍 `in_progress`。

## 验证

- `PYTHONPATH=tools python3 -m unittest tools.test_n10_px4_tracking_lag tools.test_observer_window tools.test_n10_truth_observer -v`：12/12 通过。
- py_compile 使用 `/tmp` 缓存后通过；仓库 `__pycache__` 目录默认不可写。
- `git diff --check`：通过。
- `python3 tools/project_status.py`：通过，80 个可选历史 artifact 链接不存在；不表示构建/SITL通过。
- 未运行 ROS/PX4 build 或飞行；未更改 runtime source/config、控制行为或验收阈值。

## 未解项与下一步

#415 仍不满足安全停止契约；#391 的一次性紧急 disarm 授权已用。等待原生 landed/disarmed/control-disabled/zero-control 或当前运行的新明确授权。关闭后再实施并验证单变量 feed-forward 修复，然后补缺失校准、冻结标准、干净重建、重建后回归与最终指纹冻结。
