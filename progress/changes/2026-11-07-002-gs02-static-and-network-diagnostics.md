# GS02.3静止全链路与网络基线诊断

关联对话摘要：[2026-11-07-002](../../collaboration/dialogues/2026-11-07-002-gs02-static-and-network-diagnostics.md)。证据：[静止全链路](../evidence/gs02-static-live-20261107.md)、[网络基线](../evidence/gs02-network-baseline-20261107.md)。

## 本轮子项与范围

- 子项：`GS02.3-static-and-network-diagnostic`；父目标GS02；Goal完成模式，范围GS02.1–GS02.4，不含武装/飞行。
- 具体缺口：已有运动run出现Nano发送后至Debian reader接收的长停顿；新资源/console采样还没有真实运行数据，不能判断静止viewer负载下是否也会停顿。
- 允许范围：只读静态网络测量、短暂且可恢复的Nano Wi-Fi省电A/B、Debian入口的静止纯perception/VINS/视觉运行；禁止移动、map/planner/EV/control、飞控模式/参数/固件变化。
- 完成标准：取得真实reader/资源/console时序；正常停止并确认Nano恢复、无活动viewer；保存脱敏数据与校验清单。该子项不替代动态绕圈出口。

## 实际结果

- Nano→Debian空闲ICMP平均RTT约56.5ms、P95 103ms、最大121ms，无丢包；到路由器平均3.7ms。Nano省电临时关闭后Nano→Debian P95 107ms、最大139ms，没有改善，结束恢复原设置。Debian→Nano平均6.5ms；Debian iwlwifi `power_save=N`。不据此改网络配置。
- 从Debian启动run `hw10-groundstation-20261106T083700Z`，静止运行；165.517秒状态采样、4479条视觉收件事件。TRACKING期间send-to-reader延迟P95约26–74ms，最大约101–165ms；每通道最大接收间隔不超过0.753秒，解码错误0。Viewer没有cgroup CPU限流或OOM，宿主可用内存充足。
- `experiment-stop`正常停止并落盘。Debian `status`和Nano `hardware.sh status`均为无统一会话；`rmem_max=212992`；Nano Agent仍active于CH340/TELEM1。PX4输出未启动，无EV、控制、武装/起飞。
- 新增静止run与网络原始日志、报告及校验清单。未改产品代码、Nano持久设置、PX4固件/参数或冻结基包。
- 最新migration overlay以134个唯一文件路径重建并同步至Debian原freeze01版本目录。目标端release `SHA256SUMS` 380项、静止run 25项、网络日志5项均通过；解包后`python3 tools/project_status.py` PASS，`uav-groundstation check/status`通过且无活动会话。固定镜像身份保持`sha256:119e6564...5880a`。

## 验证、局限与下一步

- 两个新证据包的SHA清单分别为25项和5项，全部通过；日志中SSID/AP/MAC已脱敏。
- 静止显示链路正常不证明动态图像paint连续，也未解释此前运动时20.627秒reader延迟。目标机时钟探针在静止run校准了Nano/PC时差；Nano主机时钟显示2024-06-18且NTP未启用，本轮未修改。
- 下一子项：用户回来后，结合其实际屏幕观察做一段短动态采样；对齐已有5Hz资源、Nano relay、Debian reader与网络计数。只有拿到动态证据才能判断要修网络/reader或RViz绘制路径。GS02.3及GS02保持`in_progress`。

本地验证命令：`sha256sum -c artifacts/runs/hw10-groundstation-20261106T083700Z/RUN-SHA256SUMS`、`sha256sum -c artifacts/runs/gs02-network-baseline-20261107/SHA256SUMS`。目标机run通过现有`uav-groundstation experiment-start/experiment-stop`入口启动和正常停止；未新增测试或代码。
