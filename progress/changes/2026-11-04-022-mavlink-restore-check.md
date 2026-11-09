# MAVLink恢复复测

用户要求切回再测。实际未获得维护入口，不能执行FC参数/模块切换。115200/2000000有界MAVLink请求RX0，后者写超时，串口已关闭。恢复SD文件已准备并bash -n通过，未写FC。证据progress/evidence/mavlink-restore-check-20261104.md，原始结果artifacts/runs/mavlink-restore-check-20261104-01。无源码/参数/固件修改。当前恢复未完成，外部阻塞为microSD访问；需要读卡器，不能靠主机换程序代替FC协议切换。project_status/diff通过仅结构检查。

用户最新明确取消备份，后续恢复直接写入限定恢复文件，不再以备份为前提。microSD访问通道仍缺，飞控尚未恢复；此决定不授权全参数重置/刷机。
