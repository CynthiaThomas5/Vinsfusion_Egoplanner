# HW02 历史 IMU 零帧恢复记录核查

更新：用户后续授权的一次当前设备SDK复位已恢复IMU并完成60秒采集/20秒正常重启复验，见[当前恢复测试](hw02-imu-reset-test-20261102.md)。本篇保留历史调查当时的约束与结论。

- 日期：2026-11-02
- 用途：只读复核 ROS_SEARCH 旧实验区中与当前 HW02 IMU=0 现象相近的证据；没有启动或重置当前相机。
- 来源：`/home/ac/codexworkspace/ROS_SEARCH/.artifact-work/vins-integration/internal_health/session_protocol/`
- 当前设备身份可比性：记录中的 API serial 为 `243622073269`、固件 `5.17.3.10`、SDK `2.58.1`，与 HW02 当前设备/SDK版本匹配。

## 零帧与恢复过程

`usb_reconnect_20261016_141634` 记录了相机重连后的零帧现象：

- `post_restart_stream_check.json` 采集约 30 秒，`/camera_b/imu` 与 `imu_corrected` 均为 0；IR/深度有帧。
- `post_restart_retry_stream_check.json` 再采约 30 秒，两个 IMU topic 仍为 0；IR/深度恢复到约 15 Hz。
- 随后的 `sdk_recovery_steps.json` 记录依次执行 `stop_camera_retry`、`sdk_reset`、`wait_enumeration`、`sdk_imu_8s`、`sdk_rgbd_imu_15s`。这组恢复发生在该 run 的一次物理 USB 拔插之后。
- 时间戳核查：`user_replugged.json` 为 `1792131718856948070`；相机启动/重试请求随后发生，两份零帧检查均在 SDK reset 之前；`sdk_reset` 为 `1792131847196788282`。因此，USB 重插后仍有零帧，恢复出样发生在 SDK reset 及后续直采阶段。不能将重插本身认定为修复，也没有证据证明必须再次重插。首个启动请求还因 PID 预检拒绝而未启动相机，不能把两份零帧检查说成两次成功相机重启实验。
- SDK 直采日志确认 Accel 100 Hz 得到 806 帧、Gyro 200 Hz 得到 1563 帧（8 秒，`bad=0`）；RGB-D+IMU 15 秒日志得到 Accel 1515、Gyro 2976 帧。SDK 日志仍出现 libusb `Resource temporarily unavailable`，深度流也有较大间隙。
- 之后 ROS 30 秒恢复检查得到 raw IMU 4304 帧（143.46 Hz，最大 header gap 95.05 ms），说明不再是零帧，但整项 stream check 未通过。后续低负载 20 秒检查 raw/corrected 各 3999 帧（约 199.93 Hz、最大 gap 5.01 ms）通过；VINS 运行中的受限联合 IMU 检查也约 200 Hz 通过。完整多图像 freshness 仍明确未通过。

因此，旧记录确实包含一次从 IMU 零帧恢复到可持续出样的经历，但证据支持的是**人工监督下的恢复路径**，不是自动恢复，也不代表当前传感器模块完整通过。保存的 `sdk_reset.log` 确认复位目标 serial/固件；具体 SDK reset 调用脚本没有保存在这组 artifact 中，不据此推断更细的底层调用。

## 后续 OS 重启记录的边界

相邻的 `os_reboot_20261016_143343` 记录了 USB 保持连接的一次系统 warm reboot。重启后 USB 树仍显示 5000M，文件哈希无变化；managed session 得到 IMU 15210 帧、header rate 199.89 Hz、最大 gap 10.00 ms，检查通过。但该实验发生在上述人工恢复之后，且其范围声明为“单次 warm reboot”；它只能说明该次重启后 IMU 正常工作，不能单独证明 OS reboot 能从当前的零帧状态恢复。

另一个 `imu_start_gap_fully_fixed_result.json` 是带有首秒 IMU 间隙的 VINS 回放：原始 IMU 仍有约 1707 条样本。它解决的是 VINS 启动窗口覆盖问题，不是设备/ROS 传感器零帧问题。

## 对 HW02 的处理

- 这些历史文件为当前零帧提供了相似设备的恢复线索，但根因仍未确定；当前 HW02 的 SDK 直读 0/0 证据仍有效。
- 已知恢复路径包含物理 USB 拔插及 SDK reset，与本轮约束“不重置 USB”冲突；本次只读调查没有重放该路径，也没有重启 Nano。
- 不更新 HW02 通过状态。后续需在约束经用户明确调整后才能重放恢复流程；若不调整约束，则需等待设备以允许方式自行恢复后复验。

## 关键 artifact SHA256

- `post_restart_stream_check.json`: `cc9e1103ca86cede9973f6cba8d1b632d494b76f47a446e935c24bbfa2c138da`
- `post_restart_retry_stream_check.json`: `98541749fc59249a4023d45b3cd62580b9c003ca1a3e73bdcdf1fb5645d2fd56`
- `sdk_reset.log`: `08dabfda018673ee995fa4a732cd88137ed438ed4a64bf4666e449f7db8850bb`
- `sdk_imu_8s.log`: `d6da9c4ccce64805ad9c37f48bfd54fbe6c3ebf8c27e59c4b2517123fc1fcfde`
- `sdk_rgbd_imu_15s.log`: `86cf6ab513c9fb3495157a2ce5da34b481b0037c092497b36fca793b5cc2dc0d`
- `post_sdk_recovery_stream_check.json`: `ed96188e0086816fffb7be2bbfa55e0eeee61521e4fede9c3d17859ae31a262b`
- `low_load_imu_check.json`: `02dbfa3c413999ce55f1b0f5c7d55a29e12c822fdd592a38a2dc9987f4d0a527`
- `joint_imu_check.json`: `85ef050d1d432c3ad5d227ca009ab7a803b56ecde67e67a652ffbadad8ec2687`
- `os_reboot_20261016_143343/post_boot_session_result.json`: `32df89e4024442179dee33aa38c76aa12ceb6dfb8669b02360847fb8148474db`
