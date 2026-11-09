# Debian 地面站接续入口

本文件供地面站上的用户或新 Codex 会话快速接续。完整项目约定仍以 [AGENTS.md](AGENTS.md)、[README](README.md)、[GOAL](GOAL.md)、[CURRENT](progress/CURRENT.md) 和 [milestones](progress/milestones.json) 为准。先读取这些文件，再按当前任务读取相关证据；不要依赖旧聊天窗口。

## 机器职责

- Debian 地面站：`work@192.168.31.223`，x86_64、Debian 13，运行 Jazzy/RViz/QGroundControl、存放项目上下文和实验记录。
- Nano：`jetson@192.168.31.186`，`/home/jetson/D435i-VINS-EGO-ROS2-hardware`，运行 Foxy、D435i、VINS和后续建图/规划。
- 飞控与唯一 `uav_px4_bridge` 控制出口由 Nano侧接入。任何控制或飞行必须遵守 HW08/HW10 当前准入状态。

## 当前冻结与状态

当前冻结ID：`gs02-20261106-freeze01`。冻结包在 `artifacts/releases/gs02-20261106-freeze01/`，包括当前源码/工作树快照、Git历史bundle、Nano部署manifest、安全恢复快照及选定HW10原始运行数据。迁移使用 `docs/tasks/GS02-freeze-debian-migration.md` 中登记的SHA清单和版本目录。

Nano重启后032纯感知会话已停止。当前systemd Micro XRCE-DDS Agent active，走CH340/TELEM1串口、1Mbps；这是PX4通信服务，保持运行，不让其它程序抢占此串口。

历史动态run `hw10-groundstation-20261106T074153Z`曾记录Nano发送后到Debian reader最大13.2–20.6s滞后和22.7–29.1s视觉计数停滞；Nano源端未见同幅度长空档，根因未区分网络/SSH流控与Debian调度，见`progress/evidence/gs02-display-pipeline-20261106.md`。随后新增动态run `hw10-groundstation-20261106T104050Z`覆盖运动期采样：用户报告全程无卡顿，Nano定位27/27条TRACKING，Debian五路reader最大接收间隔0.806s、发送至接收最大0.372s；RViz X11窗口5Hz采样174.8s/874帧，运动段双目和3D ROI各143对相邻帧均变化。当前冻结版动态展示连续性通过；旧异常未复现、根因未定位，不称已修复。详情见`progress/evidence/gs02-dynamic-rviz-20261107.md`。

宿主/cgroup/网卡资源采样和viewer console记录已经通过Debian动态验证；本次运动窗未见CPU throttling、OOM或网卡drop/error。静止网络、静止paint、UI/lifecycle证据仍保留用于对照：`progress/evidence/gs02-static-live-20261107.md`、`progress/evidence/gs02-static-rviz-paint-20261107.md`、`progress/evidence/gs02-network-baseline-20261107.md`、`progress/evidence/gs02-rviz-controls-lifecycle-20261107.md`。

为补资源数据，在Debian入口完成静止run `hw10-groundstation-20261106T083700Z`，165.5秒状态采样、4479条视觉事件；reader send-to-receive延迟P95约26–74ms、最大约101–165ms，最大通道接收间隔0.753s，无解码错误、cgroup CPU限流或OOM。未移动，不算绕圈，RViz实际paint未测。Nano→Debian空闲RTT均值52–56ms；临时关闭Nano Wi-Fi省电无改善，结束已恢复。Debian iwlwifi省电关闭。静止run与网络结果见`progress/evidence/gs02-static-live-20261107.md`和`progress/evidence/gs02-network-baseline-20261107.md`。该静止run、网络日志和更新上下文已同步至freeze01 overlay；目标端release、run清单、结构及入口状态检查均通过。
随后完成静止RViz绘制基线run hw10-groundstation-20261106T085810Z：窗口30秒5Hz采集150帧，150帧全不同，截图确认左右目特征、稀疏点、机体和轨迹；reader send-to-receive P95约156–220ms，最大约506–865ms，未重现动态长reader滞后。该证据只覆盖静止paint，不覆盖运动期连续性，报告见progress/evidence/gs02-static-rviz-paint-20261107.md。
最新静止UI/lifecycle run hw10-groundstation-20261106T092711Z验证MoveCamera左旋、中键平移、滚轮缩放、重复启动拒绝、stop-view释放relay和experiment-stop归属；记录1552姿态但没有实物移动。Debian和Nano均无统一会话，VINS/localization/relay已停止，rmem_max=212992；microxrce-agent.service仍active于CH340/TELEM1。PX4 outputs=not_started。27项RUN-SHA已通过，报告见progress/evidence/gs02-rviz-controls-lifecycle-20261107.md。
GS02.1–GS02.4已按任务范围完成：freeze01保留、Debian固定入口和Codex上下文验证通过；动态RViz连续性有用户观察与窗口/reader证据。原先20.6s reader异常只在旧run出现，本run未复现且根因未定位，按历史间歇观察保留。

Nano系统时钟记录为2024-06-18、NTP未启用；Debian NTP=yes但NTPSynchronized=no。动态reader跨机时延使用本run时钟偏移估计，窗口持续时间使用monotonic；本次未校时。Nano当前无VINS/localization/relay统一会话，`rmem_max=212992`；Debian无viewer容器，`microxrce-agent.service`仍active于CH340/TELEM1。没有PX4输出、EV/control、武装/起飞或固件/参数改动。

HW10-SYNC-023同步先发固件仅为已接受的**未武装地面基线**，不是飞行资格；HW10-EV-024退出修复、027台架高度功能已取证，完整HW08/HW10未通过。主线下一项为 HW10-EV-028。当前板上高度功能用户接受，最终装机后仍需检查。

032最近一次纯VINS显示在Nano重启后已停止，圈记录器保存5609姿态但用户未确认回到起点，因此该圈不算完成。显示同时停顿的记录空窗约16.166秒，Nano累计左右目/VINS接收数据连续，具体显示链路原因未查清。相关证据为 `progress/evidence/hw10-view-pause-20261105-032.md` 和冻结包中的032数据。

## 地面站命令

进入迁移后的项目根目录，或直接使用桌面“启动VINS绕圈实验”入口。命令行入口：

```bash
uav-groundstation check
uav-groundstation status
uav-groundstation experiment-start
uav-groundstation experiment-stop
```

`experiment-start`启用Nano上的纯感知/VINS和Debian上的双目、稀疏特征、相机视锥、机体和细轨迹RViz显示；自动先启动显示relay再启动新epoch。定位有效并捕获20个基线姿态后，它才提示用户移动。逐姿态轨迹和圈首尾写入`artifacts/runs/<run_id>/groundstation/`。5Hz `viewer-status-samples.jsonl`与逐条`visual-receive-events.jsonl`记录Nano/PC时钟及source/sent/PC-received时间，不保存视觉payload；状态样本还会记录host/container资源和默认网卡计数。正常`experiment-stop`会把viewer容器日志保存为`groundstation/viewer-console.log`。这些字段可以测到Debian接收/处理，不等于GPU/RViz实际绘制帧时间；用户仍需留意并报告屏幕是否冻结。实验不启动地图/规划/EV，不改PX4模式、不武装或起飞。用户在空间允许的范围内慢速绕圈并返回后，用`experiment-stop`完成落盘。如果已有运行会话，先status核验归属，禁止叠加启动。

该入口已按GS02在Debian固定镜像完成真实GUI、Nano运行和用户动态绕圈验收。若SSH、Xauthority、GPU、relay或定位检查失败，保留失败日志并按状态入口处理；不要绕过健康门限。再次移动时仍应由现场人员观察屏幕并在出现卡顿时记下大致时段。

## 启动其他无人机功能

`nano-start plan`只启动感知、建图、EGO和导航任务入口，不自动发目标；它不是PX4控制或起飞命令。真实EV/控制目前仍被rig测量资格及HW08/HW10剩余出口限制。未完成明确验收前不要增加控制启动项或声称可以实飞。
