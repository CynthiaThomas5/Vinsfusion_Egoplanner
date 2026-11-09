# 飞控当前连接检查

用户确认当前仅USB供电，另告知此前使用过14V外接电源；接入接口、是否降压仍未知，不得认定过压或硬件损坏。

产物artifacts/runs/fc-condition-20261104-01。USB枚举26ac:0032、PX4 FMU v5.x应用设备，串口无其他占用。只读OS FD被动12.025s RX0；随后有write_timeout=1的MAVLink GCS心跳/身份请求8s无PX4心跳/版本，RX0，未发参数/重启/武装/模式命令。pymavlink输出Device is dead为通信库提示，不是硬件故障鉴定。诊断进程已退出。

结论：当前应用通信不可用，无法仅凭USB枚举和无心跳区分供电硬件损伤、固件/启动脚本挂起或USB数据路径问题。不能报告飞控已坏，也不能报告硬件正常。需确认14V实际接法及读取SD启动/故障日志。HW10/DDS修复仍未完成；原参数恢复状态仍待回读。

## 最新Nano仅USB供电复测

用户表示接的是POWER口，可能有降压模块但不确定，随后接回Nano。Nano应用USB路径1-2.4/26ac:0032正常枚举、无进程占口。pyserial有界测试：被动5s RX0，主动MAVLink GCS/身份请求发送被系统接受（heartbeat21B），再观察5s仍RX0；发送成功仅代表主机写操作成功，不能证明FC应用处理。DTR/RTS五阶段（00/11/10/01/11）各2s均RX0；最终状态11。只读直接控制台ver all11B发送，观察3s RX0。没有参数、重启、模式/武装命令；诊断已退出，fuser无占用。

产物artifacts/runs/fc-condition-nano-20261104-01，包含inventory/dmesg/serial-check/line-state/direct-console。当前USB回复路径失效，不能诊断为损坏或已恢复。与历史已验证正常相比存在后续启动脚本/参数改动，需要SD启动日志与撤销临时hook，不能把原因直接归给用户14V操作。后续需读卡器读取SD；缺该通道时不再重复重启或协议切换。
