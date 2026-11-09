# TELEM2 DDS连接检查前置

用户报告新增TELEM2至Nano线缆、已配置DDS，要求连接查看消息，不更改参数或发送控制。SSH直接地址与ssh jetson两次返回No route to host；别名当前指向192.168.31.186。本机192.168.31.144/24，邻居186 FAILED；nano.local/jetson.local无解析。没有连上Nano，不能报告DDS接通或失败。等待当前Nano IP或网络恢复。对应collaboration/dialogues/2026-11-05-001-telem2-dds-check.md。CURRENT更新现场事实，HW10仍未通过；未运行FC进程/无代码或参数变更。

## 开机后实际检查

用户确认此前Nano未开机；再次ssh jetson成功，新增CH340/dev/ttyUSB0。无Agent/其他串口占用。按项目旧值921600启动Agent和独立环境只读观察器20s，观察器退出0、DDS计数空，已TERM Agent释放串口。用户不知道实际波特率；被动扫描9个常见值和约1M细分，出现数据但未取得完整有效XRCE帧，禁止把单个7e前缀当有效握手。无FC参数/重启/EV/控制。当前已发提示保留TELEM2并USB接PC，读取实际配置，再判波特率或接线/电平；等待外部接线。全部原始采样artifacts/runs/telem2-dds-20261105-01。结构/diff检查通过仅结构状态。

用户确认USB接运行Codex本机；实际本机lsusb/sysfs/serial无PX4，journalctl最近仅3-2断开。Nano无FC USB。已请求只重插本机USB口并保留TELEM2，等待枚举再读实际参数；不会把USB不枚举当DDS参数故障。原始host-usb/kernel.txt保存。

## 最终实测结论

USB枚举成功后完整只读probe退出0，1101参数、固件和NSH启动日志证实TELEM2@921600 DDS102、MAV1已关、USB2，extras不存在。DDS status disconnected，UART Agent20s遥测0并有错误字节。新USB正常状态取代历史旧故障。详见progress/evidence/telem2-dds-20261105.md。只读子项完成，DDS未通过，后续单变量降速/接线电平排查；未改参数/重启/控制。
