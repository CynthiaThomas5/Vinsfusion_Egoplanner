# P5 VINS Ceres 分组代价诊断与 SITL 复测

## 改动与行为

- 将可选诊断补丁 `dependencies/patches/vins/0005-diagnostic-cost-components.patch` 纳入 VINS 补丁顺序。默认关闭；启用 `VINS_DIAGNOSTIC_COST_GROUPS=1` 后，只在每个 VINS 进程首次 `normalized_cost >= 1.0` 时评估边缘化先验、IMU、视觉三组 Ceres robust cost，不改求解器参数、定位健康门或控制行为。
- 在固定 Jazzy 镜像中构建 `camera_models` 与 `vins` 两包，安装到独立 overlay；PX4 SITL 使用由 P0 干净构建复制出的 run-local build。
- #179 的 ROS domain 234 触发 Fast DDS 端口范围错误并在 PX4 DDS 状态门退出，作为无效启动保留。#180 改用 domain 231、独立 Gazebo partition，成功建立 ROS graph 并完成只读真值采集。
- 新增运行证据，更新 VINS 来源审计、P5 证据目录、里程碑证据引用和 CURRENT。P4/P5 仍进行中，P6 未开始。

## 结果

#180 首个质量门越线样本位于仿真戳34.256 s，`normalized_cost=1.0370628`。该样本中视觉、边缘化先验、IMU 的 robust cost 分别为884.2412、113.5596、0.2625，占总 `final_cost=998.0633` 的88.60%、11.38%、0.03%；分组和与 `final_cost` 的差为−1.7053e−12，分组残差维数1856与总维数一致。诊断字段只在这895条遥测中的首次越线样本出现。

目标因现有 `normalized_cost_exceeded` 门控中止，车辆已落地并解除武装，failsafe=false；只读真值采集完成且无解析错误。该结果说明这一帧聚合目标函数由视觉残差组主导，但没有识别图像、特征、标定或运动来源，无法校准通用门限，也不是目标完成或 P5 通过证据。`solve_seconds` 在分组评估前记录，故本轮未量化额外诊断耗时。

## 验证

- `git apply --check` 针对 0004 后的固定 VINS 源码应用 0005：PASS；补丁与 VINS 源 SHA256 见 `progress/evidence/p0-source-audit.json`。
- Docker `d435i-vins:dev` 中 colcon 独立构建 `camera_models`、`vins`：2/2包通过；#180运行时 `ros2 pkg prefix vins` 指向诊断 overlay。
- #180 SITL：PX4 DDS session建立，导航派发目标；首个 quality gate 触发后 action ABORT，bridge `LANDED`、disarmed；真值采集 exit 0。`truth-input-graph-check.txt` 与 topic graph 确认唯一真值订阅者为 `raw_vins_readonly_probe`，PX4 bridge 无 debug_truth subscription。
- `python3 tools/project_status.py`：PASS（结构检查，不代表 SITL 或阶段验收）。
- `python3 tools/test_vio_quality_alignment.py`：3 tests PASS；`python3 tools/test_localization_health.py`：11 tests PASS；`python3 tools/test_fetch_vins.py`：1 test PASS。
- 分组诊断构建：Jazzy `camera_models`、`vins` 2/2 packages finished；证据中的16个运行／源码SHA256全部匹配。
- 构建命令（`d435i-vins:dev` 容器内）：`source /opt/ros/jazzy/setup.bash && colcon build --base-paths src/vendor/vins_fusion/camera_models src/vendor/vins_fusion/vins --build-base artifacts/runs/p5-vio-cost-component-build-20261019-01/build --install-base artifacts/runs/p5-vio-cost-component-build-20261019-01/install --merge-install --parallel-workers 1`；SITL 命令：`bash artifacts/runs/p5-px4-vio-ego-flight-20261019-180/launch-diagnostic-run.sh`。
- `git diff --check`：PASS；另对10个新增／改动的文本与 JSON 文件检查尾随空格和制表符，0项。

## 局限与下一步

- 只有一次运动目标样本；未运行匹配悬停对照，未保存图像／逐特征残差时间线。
- Ceres 的 solve 时间字段不含额外分组评估；该评估只运行一次，但真实额外耗时未测。
- 保持质量门1.0与 fail-closed 行为。下一步做同配置悬停基线、图像／特征时间对齐和评估耗时测量，再继续 P5 目标完成及障碍验收。

## 对话摘要

[P5 VINS Ceres 分组代价诊断](../../collaboration/dialogues/2026-10-19-064-p5-vio-cost-components.md)
