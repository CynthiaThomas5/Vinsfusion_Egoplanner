# 当前USB直接DDS检查

用户明确要求MAVLink无回复时直接尝试DDS。保持FC当前配置与Nano接线，不改参数、不重启、不启动VINS/EV/控制。串口fuser无占用。

运行已安装MicroXRCEAgent serial --dev /dev/ttyACM0 -b921600 -v6，加strace -yy：30s内端口TCSETS B921600成功，但没有该USB FD的read/write调用（仅5条配置ioctl），未收到客户端串行数据。Agent已TERM正常释放。

第一次观察器误用Agent LD_LIBRARY_PATH，ROS spdlog符号冲突退出1；该轮counts空不能作为遥测验收。已将Agent/ROS环境分离再做15s：观察器定时器正常落盘、退出0，DDS计数空，Agent没有会话建立日志；两进程退出，fuser无占用。库冲突为本轮诊断启动方式问题，不能追溯归因于此前失败。

产物artifacts/runs/dds-direct-20261104-01，含agent.strace、原失败日志，以及retry/正确环境的实际观察。结论：当前直接DDS也未连通，不能仅解释为用MAVLink误读一个正常DDS流；不代表飞控硬件已损坏或当前真实模块状态已读回。保持未修复，仍需板端启动日志/恢复通道。结构检查通过仅代表结构一致。
