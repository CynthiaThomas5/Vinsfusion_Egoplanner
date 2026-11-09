# HW02 执行摘要

- 最新用户授权：在提出“一次SDK设备复位，先检查原始IMU，再检查ROS”的方案后，用户要求“测试一下，看看能不能解决”。执行该单变量恢复实验及受影响采集，允许目标相机SDK复位/重新枚举；旧目录保持只读，不扩展到物理拔插、Nano重启或固件修改。

## 用户约束

- 按 `docs/hardware-agent-workbook.md` 完成 HW02 全部出口；读取 CURRENT 和已有证据后直接实施。
- 只验证受影响部分并写回结果；本轮范围停在 HW02，不进入 HW03。
- 仅在当前 D435i 上做地面传感器采集；不启动 PX4、Gazebo、SITL、VINS 或控制，不修改固件。此前不重置USB的限制针对本次单次目标SDK复位试验已由最新用户授权更新；不扩大到物理拔插或循环reset。
- 旧 `/home/jetson/realsense_debug` 和旧 ROS 工作区只读；保护当前工作树已有修改。

## 执行决定

- 锁定 API serial `243622073269`、ASIC/USB serial `243323065857`、Foxy wrapper 3.2.3、SDK 2.58.1 及已有 HID-hold 补丁；启动前核对占用，运行时核对实际加载库。
- 深度转换改用 C++ 订阅/发布，16UC1 毫米转 32FC1 米，保留零无效值和消息头；移除高负载 Python 图像转换路径。
- 合成 IMU 保留 `linear_interpolation`，按 gyro stamp 输出；没有 `imu_corrected` 第二路，不添加 IMU 修正。
- 本模块不采关键帧，因此传感器 launch 的 RGB 默认关闭；保留 `enable_color:=true` 作为将来需要关键帧时的入口。
- 一次受控对照只改变 RGB 开关，未能恢复 IMU；随后用只读的 SDK 2.58.1 IMU 探针独立确认当前零样本发生在 ROS wrapper 之前。未执行 USB reset 或固件改动。

## 现场姿态与量测结果

- 用户现提供静止摆放信息：相机在桌上，脚下有箱子，口述约35cm、离地约65cm、前桌约40cm；镜头水平向前。20秒样本的specific-force均值 `[0.046724,-9.863085,-0.190142]m/s²`，偏离预期光学`-Y`约1.137°，静止重力方向核对通过。
- 用户之后用尺复量同一目标，确认镜头到目标约32cm。对应采样中心ROI深度中位数324mm、有效率65.09%，与量距相差约4mm；旧的22cm为目测估值，用户提供的100mm仍不需要作为尺度真值。该数量级核对关闭HW02最后一项，细节见 `progress/evidence/hw02-imu-reset-test-20261102.md`。

## 历史零帧恢复证据补充

- 用户指向 `/home/ac/codexworkspace/ROS_SEARCH/.artifact-work`；只读找到 2026-10-16 同 serial/固件/SDK 的恢复记录。相机重启后两次 ROS IMU=0，后续一次人工 USB 拔插+SDK reset+枚举等待后 SDK 和 ROS IMU 恢复；完整多图像 freshness 仍未通过。
- 当前约束“不重置USB”继续有效，因此本轮没有重放该历史恢复流程、没有重启 Nano，也没有把历史结果记作 HW02 当前通过。详见 `progress/evidence/hw02-historical-imu-recovery-20261102.md`。

- 后续时间戳核查修正顺序：先 USB 重插，随后两份 ROS 检查仍为0；停止相机、SDK reset 后直采才恢复样本。不能认定 USB 重插本身解决问题，也未证明必须再次重插。当前优先怀疑 Motion Module 初始化/状态或 HID 采集路径，根因尚未锁定。

## 最新实测结论与HW02收尾

- 执行获授权的一次当前设备SDK复位，前后同8秒探针从0/0恢复为accel806/gyro1585。随后ROS60秒IMU11924帧/199.798Hz；停止/正常重启后不再reset，20秒IMU3919帧/199.327Hz，均全部有限且单调。当前零帧恢复，不承诺永久修复。
- 当前设备及会话均已释放，无物理拔插、Nano重启或固件修改。已知平面量距复核约320mm，中心ROI中位数324mm、有效率65.09%，通过HW02规定的深度数量级检查。旧22cm目测数据和100mm板规格歧义保留为历史，不再阻塞该出口。HW02全部出口已通过；HW03是依赖顺序的下一项，但未在本轮启动。

完整结果及证据链接见 `progress/evidence/hw02-d435i-20261102.md`；实现和验证记录见 `progress/changes/2026-11-02-hw02-d435i-sensors.md`。
