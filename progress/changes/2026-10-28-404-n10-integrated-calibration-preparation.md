# N10.3/#404 综合校准准备与结果

关联对话：[2026-10-28 #404 综合校准准备](../../collaboration/dialogues/2026-10-28-404-n10-integrated-calibration-preparation.md)

## 产物与决定

- 从 #402 预备器复制出独立运行身份 `n10-20261028-404-speed040-integrated-calibration`，冻结 profile、planner、spawn、capture、observer、接受评估和 runtime 仍由 prelaunch 现场重算。
- 加入 #403 物理步净空 evaluator 的工具 SHA 检查和运行后离线回放；起飞前复制实际加载的 `simulation/models/x500_d435i/model.sdf` 到 run 目录并保存 SHA。
- 同一综合校准保留 #398 场景和 0.4 m/s profile；采集 source-covered snapshot、点查询、地图/重规划/真实净空、VIO/跟踪、资源/队列、MCAP、接触和终态。
- 读取 `config/components/simulation/d435i_bridge.yaml` 与 `vio_closed_loop_px4.launch.py` 后确认多路图像与 IMU 共用一个 parameter_bridge。停止该进程不能构成深度单流断流，因此 #404 不注入故障；另行准备深度单流隔离路径，再校准故障终态。
- 保持所有运行期控制逻辑和门限不变；离线统计不触发拒绝、取消或降落。一次性紧急 disarm 授权已在 #391 消耗。

## 执行结果

- 16 m action 成功；独立位置/yaw 联合达标 4.352 仿真秒。15 仿真秒 active hold 是诊断段，不是 N16 正式十分钟验收。
- raw/inflated 快照 source stamp 覆盖 ROI cloud watermark 0.960 s；箱体内部仍有 18 个八角完全位于实体内的 known-free 体素，raw 分类候选 FAIL。点查询 `/mapping/get_map_status` 不可用，0/26 查询。
- 26,005 个 4 ms solver 状态完整；25,187 个无接触区间的模型净空下界均为正，最小 0.162761 m；817 个滑橇接触区间另行处理，违规接触为 0。跟踪误差 P95 0.333776 m，逐点平移净空下界 434/9,381 个样本为负，尚不足以冻结误差预算。
- 资源采样 189.0 wall 秒；映射 pending-depth 高水位 8/8，VINS 内部队列容量未暴露，主机容量依据不足。完整 raw VIO 分段复算和 sensor capture 结果见 [#404 结果报告](../evidence/n10-integrated-calibration-result-20261028-404.md)。
- 整体 acceptance 为 `INSUFFICIENT`；action 成功，末态独立读回 landed/disarmed/control-disabled/zero-control。末态 `reason` 保留初始 disabled 字符串，时间线显示后来 `operator_disable` 进入落地，不把初始字符串归因为本次末态。
- 原 runtime driver 返回 1 是离线验收不足的结果；flight/action 和安全关闭本身成功。安全读回后只停止了本项目容器。未使用紧急 disarm。
- 修正离线 VIO evaluator 兼容当前 profile 的 `position_tolerance_m`，并将误标的 15 s 段改名为 `diagnostic_post_goal_active_hold`。3 项针对性单测通过，完整复算成功；无控制代码、运行门限或冻结阈值变更。

## 验证

- `PYTHONPYCACHEPREFIX=/tmp/n10-pycache-20261028 python3 -m py_compile tools/debug_truth/evaluate_n10_full_route_vio_metrics.py tools/test_n10_full_route_vio_metrics.py`：通过。
- `PYTHONPYCACHEPREFIX=/tmp/n10-pycache-20261028 python3 -m unittest tools.test_n10_full_route_vio_metrics`：3 项通过。
- `PYTHONPYCACHEPREFIX=/tmp/n10-pycache-20261028 python3 tools/debug_truth/evaluate_n10_full_route_vio_metrics.py artifacts/runs/n10-20261028-404-speed040-integrated-calibration`：通过，更新分段 JSON/log。
- `bash -n artifacts/n10-prepared/n10-20261028-404-speed040-integrated-calibration/n10-runtime-driver.sh` 和 prelaunch/evaluator `py_compile`：准备阶段通过。
- `bash tools/project.sh stop n10-20261028-404-speed040-integrated-calibration`：安全读回通过后退出 0；`docker ps --filter label=d435i.project=/home/huangxiaocheng/D435i-VINS-EGO-ROS2`：无运行容器。

## 下一步

N10 仍 `in_progress`。先实现并验证只影响深度输入的故障路径，再做对应当前版本的触发到自然 PX4 终态校准；继续处理 raw-map 分类 FAIL、跟踪误差预算不足和资源容量依据缺失。之后完成 N10.4–N10.7；N15/N16 正式测试仍在冻结之后。
