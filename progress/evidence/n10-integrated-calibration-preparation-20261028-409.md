# N10.3/#409 综合校准准备

状态：运行准备已完成，尚未启动本次 SITL；N10 父目标仍为 `in_progress`。

## 本次校准

复用 #381/#385 的长程原始 VINS 与真值数据，以及 #404 的 16 m 综合任务场景。#409 在同一目标 epoch/map 身份下安排目标后 8 仿真秒的 raw/inflated 地图快照、目标后 12 秒插入的障碍及一个 source-covered 后快照。离线比较单元类别变化、地图栅格几何和保存深度帧中央 ROI 的源时刻。运行同时记录 250 Hz 物理真值、样条/PositionCommand、定位/跟踪、接触、resource 和 VINS 队列 telemetry。

目标后诊断保持采用 20 仿真秒：覆盖 #391 目标结束后 +7.468 秒首次越过独立 0.30 m 位置界的时刻，并早于该运行首次禁止接触的 +49.088 秒。它仅为诊断观察窗；不是在线阈值、正式 N16 或安全保证。

## 运行决策

- 离线图栅格数组是 raw-map 比较主体；点查询是可选旁证。单独 point-query observer、26 查询完成等待及传感器观察器图订阅要求已从 #409 控制路径移除。
- 起飞前保留唯一 goal 发布者、EGO planner 与 `uav_px4_bridge` 两个控制消费者、原生 PX4/preflight 和 landed/unarmed/control-disabled 状态检查。传感器、资源、队列观察器在场与否只记为证据完整性，不新增起飞拒绝、取消或降落分支。
- 快照配对离线检查前快照的融合源时刻早于插入、后快照的融合源时刻晚于插入，并校验 epoch/map/frame/grid 身份。缺少任一快照或深度源覆盖时报告 `INSUFFICIENT`。
- 本次不注入故障；#401 planner-exit 与 #405 depth-only loss 各保留一份当前版本校准。N15 每类两次正式重复仍在 N10 冻结后。

## 准备验证

- `PYTHONPYCACHEPREFIX=/tmp/n10-409-pycache python3 -m unittest tools.test_n10_snapshot_pair tools.test_n10_acceptance tools.test_n10_full_route_vio_metrics`：26/26 通过。
- Python `py_compile`、JSON parse、`bash -n` 与本轮触及文件的 `git diff --check`：通过。
- 安装 VINS binary SHA 与 #408 build summary 一致；`strings` 可见 `acc_current_before_feature_dequeue`、`gyr_high_water`、`feature_high_water` telemetry 字段。
- 容器镜像 ID 与固定配置一致；目标 run path 不存在；GPU 有两张 RTX 4090。尚未启动 flight。

协议：`progress/evidence/n10-integrated-calibration-protocol-20261028-409.json`。本记录是准备证据，不代表运行或验收通过。
