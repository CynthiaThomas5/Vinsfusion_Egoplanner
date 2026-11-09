# HW03 执行摘要

## 用户要求

- 按 `docs/hardware-agent-workbook.md` 完成 HW03 全部出口；先读取 CURRENT 和已有证据后直接实施，只验证受影响部分并写回结果。
- 保护开始前工作树已有修改；旧 Jetson 实验目录保持只读。本轮不启动 VINS、PX4、Gazebo、SITL、控制或飞行。

## 已有证据与决定

- HW01/HW02 均已通过。复用 serial `243622073269` 的 HW02 实测 640×480 stereo/depth CameraInfo、depth 米制转换链、IMU gyro-stamp linear-interpolation 流和约 320 mm 近距数量级核对。
- 只读从 `/home/jetson/realsense_debug/vins_integration/config` 取得同 serial PROVISIONAL 候选及来源哈希，并只读查询该相机 EEPROM。候选基线与右 CameraInfo 基线一致；EEPROM 查询实际链接 SDK 2.50，未声称是 SDK 2.58.1。
- rig 保留 PROVISIONAL：标定板尺寸条件假设未独立确认；候选噪声不是实测；`td` 候选源于 `/camera_b/imu_corrected`，当前项目使用 wrapper `linear_interpolation`，两者等价性未验证；无留出路线。
- 当前用户已量约 320 mm，用于既有深度数量级核对，不用作标定板尺寸或精标定证据。
- camera-to-airframe SE(3) 和含桨包络保持未测且 control-ineligible。HW03 不补造零安装变换；HW08 前不允许进入硬件控制路径。

## 交付与结果

- 当前唯一 rig：`config/hardware/rig.json`；hardware VINS settings：`config/components/localization/vins_hardware.json`。
- generator、localization、mapping、planner/bridge 配置读取均接入统一 rig/session identity；默认 simulation SDF 路径保留并有回归。
- 最终接受的未使用 session：`artifacts/runs/hw03-20261102-real-rig/session-accepted/`，epoch `67e1b6fb7a684859a2cb904fe8ff55bc`。OpenCV FileStorage 读取三份 YAML、rig/settings/generated hashes、baseline、SE(3) 和光轴定向检查通过。
- 定向测试：硬件 rig 4 项、仿真几何 5 项、planner/bridge 配置回归 11 项通过；受影响 Python `py_compile` 和 `git diff --check` 通过。

完整产物、哈希、限制和下一步见 `progress/evidence/hw03-real-rig-20261102.md`。HW03 已完成；下一模块 HW04，届时再运行 VINS 与动态定位路径。
