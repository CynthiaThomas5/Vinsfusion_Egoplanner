# P5 VIO 质量与只读真值轨迹关联诊断

## 改动

- `tools/probe_vins.py` 增加显式诊断参数 `--truth-topic /debug_truth/base_odometry` 与 `--imu-topic /sensors/d435i/imu`。只有同时传入两项才建立只读真值/IMU订阅；默认采集路径不订阅真值。诊断输出增加 truth 与 IMU 样本计数，并写出 `truth-motion.json`。
- 新增 `tools/evaluate_vio_quality_alignment.py`：按 PX4 飞行探针状态时间窗选取 VIO 源样本，与真值做时间插值；以首次配对姿态构造一次固定 SE(3) 变换，尺度固定为1，无分段重对齐；把 VINS quality telemetry 与位姿误差按源 stamp 匹配。
- 新增 `tools/test_vio_quality_alignment.py`，检查竖直轨迹初始位姿对齐、漂移误差可见、quality 样本关联和非单调 stamp 拒绝。
- 更新 `docs/acceptance.md`、README、CURRENT、evidence index、P5 milestone 和 Goal checklist。`progress/evidence/p5-vio-truth-error-diagnostic-20261019-172-175.json` 记录 #172–#175 状态及 #175 源文件哈希。

## 运行结果

- #172/#173 在真值桥 publisher 发现阶段排除；#174 因 run-local `run_vio_ego_flight.py` 缺失而在 goal 前退出。失败日志均保留，不计为导航运行。
- #175 复用固定 Jazzy install/`vio_closed_loop` launch，独立启动单向只读 Gazebo truth bridge 和 VINS probe。ROS graph 活动检查显示 `/debug_truth/base_odometry` 由 `ros_gz_bridge` 发布，仅 `raw_vins_readonly_probe` 订阅；`uav_px4_bridge` 无 debug_truth 订阅。采集窗口90秒，获得2,940条 truth、11,657条 IMU、882条 raw optimized VIO；flight report window内有269组可配对样本。
- VIO 一次固定 SE(3) 对齐，位置 RMSE/P95/最大0.3758/1.0532/1.3578 m，姿态 RMSE/最大0.3695°/0.7479°。normalized_cost 与位置误差 Pearson r=0.5604；long-track 数量 r=−0.8130、accel/gyro bias 范数 r=0.7881/0.8458、原始输入特征数 r=−0.0238。首次 health gate source stamp 35.460 s 与代价样本35.412 s相差48 ms；代价1.1460447时对齐误差约0.0110 m。位置误差首次越过0.30 m在37.920 s，约2.51仿真秒后；运行结束前最大误差1.3578 m。这些相关系数仅描述单轮。
- Navigate action 以 `localization_normalized_cost_exceeded` 中止；bridge `LANDED`、未解锁、`landed_and_disarmed=true`、PX4末态`failsafe=false`。目标不成功，P5未通过。
- 未修改 `max_normalized_cost=1.0`，未修改65 ms VIO future 容差。单轮相关性不等于预测器校准，不能支撑阈值变更或正式验收。

## 验证

- `python3 tools/test_vio_quality_alignment.py`：2 tests，PASS。
- `python3 tools/test_vins_alignment.py`：3 tests，PASS。
- `python3 -m py_compile tools/probe_vins.py tools/evaluate_vio_quality_alignment.py tools/test_vio_quality_alignment.py`：PASS。
- `bash -n artifacts/runs/p5-px4-vio-ego-flight-20261019-175/run-px4-vio-ego-flight.sh`：PASS。
- `python3 tools/project_status.py`：结构检查，不代表阶段通过。
- `git diff --check` 与新增文件尾随空白检查：PASS。

## 局限与下一步

诊断 run 有只读真值 observer，因此不是最终无真值验收组合；采集只覆盖一次短目标动作与安全降落，姿态/位移分布有限。后续增加多次冷启动和不同方向/高度/yaw运动段，并核查VINS特征、重投影残差、bias及质量门的时序；保持健康门不变。之后继续无真值目标到达、障碍净空、地图快照、故障和长时测试。

## 对话摘要

[P5 VIO 质量与只读真值轨迹关联诊断](../../collaboration/dialogues/2026-10-19-060-p5-vio-truth-error-correlation.md)
