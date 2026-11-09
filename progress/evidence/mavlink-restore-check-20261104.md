# MAVLink恢复请求与只读复测

用户要求切回MAVLink再测。Nano端口独占，未启动Agent。已有USB维护通道没有有效回复，无法实际执行PX4端SYS_USB_AUTO2或停止DDS命令，因此切回未成功、未假报已完成。

有界MAVLink身份发现（GCS心跳与REQUEST_MESSAGE148，无控制/参数命令）：115200观察6s，RX0、无心跳/版本；2000000观察，RX0并write timeout。诊断已关闭串口，不启动EV/控制，不重启。

产物artifacts/runs/mavlink-restore-check-20261104-01/result.json。已备妥recovery/extras.txt：set+e、停止DDS后确认未运行、恢复SYS2/MAG5/CHECK0并save、启动USB MAVLink、删除自有hook。bash -n通过；没有写入FC，不能代表恢复通过。需要外部microSD读卡器，先断电取卡、备份自有extras/hw10t日志再写恢复文件；只移除本项目hook，不能清空参数/刷机替代恢复。后续必须实机回读和维护重启确认。
