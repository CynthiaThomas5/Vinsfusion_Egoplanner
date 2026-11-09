# TELEM1 DDS 用户修复后只读复核

2026-11-05，ID：DDS-CHECK-003。范围：检查现有链路及汇报后续任务；不继续旧修复实验，不启动相机、EV、控制或飞行，不写飞控参数、不重启、不停止用户Agent。

用户随后纠正：实际使用TELEM1承载DDS，另一个TELEM口未使用。本次只读订阅验证Nano端通信，未回读飞控端口参数；端口身份采用用户现场确认，不沿用旧TELEM2接线记录。

## 实测结果

Nano 192.168.31.186 可达。用户已有PID7950运行 `/usr/local/bin/MicroXRCEAgent serial --dev /dev/serial/by-id/usb-1a86_USB_Serial-if00-port0 -b 115200 -v 4`，实际设备ttyUSB0。现有Agent源码目录为v2.4.3/73622810，运行二进制ldd解析至/usr/local的FastDDS2.14.7/FastCDR2.2.8；不同于仓库旧隔离前缀的2.14.0/2.2.0，本轮未重新构建或资格化该依赖组合。未通过USB读取当前固件/参数，不能沿用历史回读作为本次配置事实。Nano系统日历为2024-06-17 UTC，本轮不调整；持续时间使用monotonic，原始时间保留。

复用现有只读record_hw07_dds.py，BEST_EFFORT/VOLATILE/depth5，实际观察30.016秒：

| 话题 | 收包数 | 最大接收间隔 | 时间戳倒退 |
| --- | ---: | ---: | ---: |
| vehicle_status_v1 | 14 | 4.037s | 0 |
| vehicle_attitude | 502 | 1.002s | 0 |
| vehicle_local_position_v1 | 57 | 1.881s | 0 |
| timesync_status | 18 | 4.036s | 0 |
| estimator_status_flags | 18 | 2.662s | 0 |

合计609条，均为真实解码消息，非仅发现话题。38个fmu/in话题publisher均空；全部status样本arming_state=1。最后local_position：xy_valid=false、heading_good_for_control=false；最后EKF flags的EV位置/高度/yaw/速度融合均false。本轮不发EV，这些状态不用于诊断先前融合是否失败。

**结论：DDS遥测接收链路已接通，旧“完全无DDS消息”阻塞解除。当前链路尚不满足项目EV时效准入。** Timesync RTT实测81.165–134.729ms，现有px4_bridge_ev.json/control.json要求≤10000us；最大接收间隔4.036s也超过2.0s新鲜度预算。无EV发布时已存在这些现象，原因尚未定位，不能凭此直接定为带宽或驱动问题；没有放宽门限或再次降/升速。未验证上行EV/控制传输、长期稳定性、重启后自动恢复或飞行资格。

## 命令与证据

SSH均使用BatchMode、ConnectTimeout8、ConnectionAttempts1、StrictHostKeyChecking=yes。

```bash
# Nano，干净Foxy及px4_msgs环境；沿用用户现有Agent
source /opt/ros/foxy/setup.bash
source /home/jetson/D435i-VINS-EGO-ROS2-hardware/install/px4_msgs/share/px4_msgs/local_setup.bash
python3 /home/jetson/D435i-VINS-EGO-ROS2-hardware/tools/diagnostics/record_hw07_dds.py --seconds 30 --output /tmp/px4-dds-recheck-20261105-003
```

观察器退出0，结束进程检查无record_hw07_dds.py，Agent7950保持运行。早期topic inventory误写local_setup路径返回不存在，之后用上述实际share路径执行观察器成功；不把topic list当实测通过。

本地原始产物：`artifacts/runs/px4-dds-recheck-20261105-003/`。

- dds.jsonl：355781字节，SHA256 `ac2942ac751c48e71912bf7109ee3ffd4edcfca6ee7cda7d8a715f91ee715de5`。
- dds-summary.json：27294字节，SHA256 `6d3b1f1d6cc9ea2a1d0db5ccfb36a271d441abeee46133bf1c71d57e75bb1a74`。

## 任务位置与下一项

HW01–HW07、HW09已有各自限定地面出口；HW08严格刚性安装/含桨包络未通过，rig仍UNMEASURED/T_airframe_imu=null/control_usable=false。HW10已有历史静态EV融合及SDK时间候选证据、guarded NED代码与隔离检查；真实NED配准、运动方向/尺度、独立VINS断源、控制/人工接管/退出未闭合。无RC是上次已确认现场事实，本轮未重新询问或推断其变化。HW10保持in_progress。

唯一下一项：HW10当前TELEM1链路时效核对，先固定用户现有配置/版本和启动方式，定位RTT/消息空窗；通过现有时效门后再恢复未武装EV/NED配准及方向尺度验证。真实控制前补HW08装机及遥控接管条件。其后HW11首次悬停→HW12短距离目标→HW13静态障碍导航→HW14可重复启动交接，均未被本轮启动。

停止原因：本轮只读检查及状态汇报完成，不执行下一任务。
