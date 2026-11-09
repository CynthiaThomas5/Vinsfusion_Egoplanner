# HW10 飞控USB维护恢复 2026-11-04

结论：限定恢复出口通过，HW10整体验收仍in_progress。用户本轮要求先恢复飞控；第二线不存在，双串口改造延期。没有继续EV或实际控制。

## 实机恢复证据

目录：`artifacts/runs/hw10-fc-recovery-20261104-01`。汇总`result.json`，关键文件哈希`sha256.json`。

- 初始PC/Nano均无FC端口；Nano内核有USB枚举错误。用户直连PC后识别26ac:0032、FMUv5 USB。QGC占口，正常TERM退出释放；被动/主动发现先无PX4心跳，但有疑似DDS帧。
- 保持连接，仅被动观察。`passive-recovery-result.json`：687.300s观察后收到实际PX4心跳，base_mode29（未武装），共33219RX字节。此时无需写SD恢复文件，既有会话已切回MAVLink。
- `probe_hw07_px4.py`第一次恢复回读通过：system1/component1、PX4 1.17.0 d6f12ad1...、完整1106/1106公开参数；SYS_USB_AUTO=2、EKF2_MAG_TYPE=5、EKF2_MAG_CHECK=0。
- `hw07_usb_session.py verify --session-label hw10n`通过：`/fs/microsd/etc/extras.txt`不存在，`uxrce_dds_client` not running，USB MAVLink onboard运行，原生备份下载成功。完整命令/回显见`restored-usb/verify-shell.txt`。
- `reboot_unarmed_px4.py`：fresh PX4未武装心跳后仅发一次维护重启，command246/ACK0；未武装/未模式切换。
- 重启18s后重新执行probe与verify均退出0；同一固件身份、未武装、三参数仍2/5/0，hook仍不存在、DDS仍停止。日志在`after-reboot/`、`after-reboot-usb/`。
- 原始`original-native-before.bson`、恢复后以及重启后两份`native-after.bson`均2575字节、逐字节一致，SHA256均`88f277bbf3d5c9d010f33dac7b52ff3c3ff13c983448d2cba34ee2339f42bdc5`。没有全参数重置或固件刷写。
- 重启前公开参数1106、重启后1098。最初按集合完全相等断言失败；差异仅8个未再公开的UXRCE参数（DOM_ID/KEY/NS_IDX/PTCFG/RX_TO/SYNCC/SYNCT/TX_TO），共同参数值/类型无变化，无新增参数，完整原生存储字节一致。未将数量变化冒充参数丢失；详见`reboot-parameter-comparison.json`。
- Nano最终无Agent/桥/相机/VINS匹配进程，.runtime空，rmem212992。最初远程rg不可用，改为Python读取ps确认；不把失败管道当清理通过。所有本轮串口诊断已退出。QGC重新打开PID44416并占用/dev/ttyACM0；这里只确认程序与串口已打开，没有声称已人工验看QGC各页面。

## 本地受影响检查

`python3 tools/test_hw10_boot_restore.py`两项通过：临时参数恢复顺序，以及logger/DDS失败时set+e继续恢复。本地生成器补丁来自上一轮；没有重新上传或执行DDS脚本。本次未证实旧脚本提前退出，先前Nano无通信的具体原因仍未完全定位；不能将潜在脚本缺陷当作本次已证实故障。

最初15s发现日志因BAD_DATA bytearray不能直接JSON序列化未保存成功；后续6s发现记录正常保存。该诊断记录失败没有写飞控参数。

结构与diff检查结果见[改动记录](../changes/2026-11-04-016-fc-recovery.md)。没有扩大到算法/SITL/飞行验证。

## 未解与停止

停止原因：用户限定的通信/原参数恢复完成。HW10运动方向尺度、真实NED配准、控制/接管及HW08装机资格不由本次通过替代；无RC和未测rig限制保留。下一步是后续HW10余项；双串口待第二线及端口接线核对，本轮不自动重启DDS/EV。

## 用户接回Nano后的只读确认

- 范围：HW10恢复维护的回接确认，复用已有探针，未切换DDS、未启动EV/控制、未写参数或重启飞控。
- Nano和本机probe源码SHA256同为43cba75ad277c6978a4437e6649fe00336c83bc352bcf5eec7cd1f2d623a7b0a。
- 在Nano工作区执行`PYTHONPATH=$PWD/artifacts/runs/hw07-usb-20261103-01/python python3 tools/diagnostics/probe_hw07_px4.py --device /dev/serial/by-id/usb-3D_Robotics_PX4_FMU_v5.x_0-if00 --output artifacts/runs/hw10-fc-nano-return-20261104-01/probe`，退出0。
- 实际system1/component1 PX4未武装心跳，1098/1098参数完整；SYS_USB_AUTO2、EKF2_MAG_TYPE5、EKF2_MAG_CHECK0；与PC重启后1098项值/类型全部一致，参数名集合也完全一致；DDS not running。
- 诊断退出后Nano串口无占用，Agent/桥/相机/VINS匹配进程空，.runtime空，rmem212992。PC QGC保持打开，但本根USB已经离开PC，当前不直接连接FC。
- 产物：`artifacts/runs/hw10-fc-nano-return-20261104-01/{result.json,probe/,cleanup.json,sha256.json}`。只确认当前连接/参数，未增加持续运行或飞行资格。
