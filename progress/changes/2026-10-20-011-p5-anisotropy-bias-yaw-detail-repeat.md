# P5 零偏移 bias 与 PX4 yaw 对齐诊断 #217

对话摘要：[2026-10-20-011](../../collaboration/dialogues/2026-10-20-011-p5-anisotropy-bias-yaw-detail-repeat.md)。轻量报告：[run #217](../evidence/p5-vins-anisotropy-filter-bias-yaw-detail-repeat-20261020-217.json)。

## 修改与行为

- `src/own/uav_px4_bridge/uav_px4_bridge/px4_bridge_node.py`在现有只读 bridge detail JSON 增加 `alignment_yaw_error_rad`，直接记录原本用于对齐健康检查的 yaw error。它不改变门限、fault 分支、Offboard 状态机或控制输出。
- #217继承run-local `0008`阈值0.01，使用经 SHA-256 确认的#207零偏移目标，关闭debug truth订阅与输入。
- 动作在估计器 accel-bias state 超过0.15 m/s²限值后中止。首个越限样本0.187455 m/s²，首次 localization invalid 时 normalized_cost为0.699565，低于未变更的1.0门限。
- 中止前最后一个新鲜 ACTIVE 配对yaw误差0.052709 rad，平移误差0.014649 m；未记录 `px4_frame_alignment_drift`。桥接进入LANDING后对齐样本变旧，不推断故障时yaw。
- PX4 ULog无dropout，有EV融合、GNSS aiding零、最终落地解除武装；触地后短暂DESCEND/failsafe。导航目标未完成，P5仍进行中。
- #217作为零偏移目标也触发bias门，撤回#214报告中“两个横移run与零偏移run形成bias关联”的表述。run之间的差异不证明横移、filter或单一运行状态是根因。#216 yaw分支解释仍未证实。
- 对#214–#217已保存VINS遥测作只读对比：#214/#215横移首次越限分别在派发后3.854677/4.040592秒，#217零偏移在1.762286秒；#216零偏移没有越限并在`long_tracks_insufficient`时失效。三次bias越限的normalized_cost均低于1.0，触发时track/视觉观测数不同，没有一致的质量变化签名。
- 四个run目录未保存ROS bag、MCAP、DB3或逐帧preintegration导出。PX4 ULog不是VINS实际IMU输入及preintegration因子的直接记录，无法由现有文件完成原始输入核对。

## 验证

- run-local colcon build：6个指定 ROS 包构建完成；构建日志保存在 `artifacts/runs/p5-px4-vio-ego-anisotropy-filter-yaw-detail-20261020-217/colcon-build.log`。
- `python3 tools/test_px4_bridge_frames.py`：19 passed。
- `python3 tools/test_px4_bridge_control.py`：11 passed。
- `python3 tools/test_px4_bridge_vio_profile.py`：7 passed。
- `python3 tools/test_px4_bridge_time_mapping.py`：20 passed。
- `PYTHONPYCACHEPREFIX=/tmp/p5-217-pycache python3 -m py_compile src/own/uav_px4_bridge/uav_px4_bridge/px4_bridge_node.py`：通过。
- SITL报告、ULog时间线、桥接detail、run-local输入隔离、残差/图像manifest及输出均列入SHA-256索引；12组双目原图、675个runtime overlay和42个离线标注文件校验通过。

## 局限与下一步

估计bias是VINS状态范数，不是传感器真值；独立初始化不是因果配对。可用的yaw观测没有覆盖#216故障瞬间；质量残差采集发生于定位锁定后，不能证明过滤器候选准入。下一轮仅在run-local harness旁增加只读 `/sensors/d435i/imu` 采集器，并按仿真源戳与现有VINS遥测对齐；不接入真值，不改健康门或控制，不新增canonical探针。保留 `0008` run-only。GOAL A–H与P5仍未完成。

该采集方案在#218中试运行，但SIGINT清理时rclpy默认signal handler先关闭context，导致observer未写入数据。故#218不能作为IMU时序/偏置根因证据；故障记录和直接yaw结果见[改动记录#012](2026-10-20-012-p5-anisotropy-yaw-alignment-repeat.md)。
