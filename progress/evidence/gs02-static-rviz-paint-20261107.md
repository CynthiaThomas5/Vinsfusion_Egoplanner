# GS02.3 静止 RViz 绘制基线（2026-11-07）

## 范围

- 运行：`hw10-groundstation-20261106T085810Z`，从 Debian freeze01 固定入口 `uav-groundstation experiment-start` 启动，层级为 perception，epoch `946bac604df647dda6225ef7ebb0c4e3`。
- 设备保持静止；没有用户移动，不是绕圈。PX4 outputs=`not_started`，没有 map/planner/EV/control、模式操作、武装/起飞，也没有改飞控固件/参数。
- 在静止运行中，通过 X11 直接采集 RViz 客户窗口 30 秒、5Hz，共150帧；另保存单帧实际窗口截图。未保留30秒视频；测得摘要和源视频SHA留在原始运行目录。

## 结果

- Nano run记录285.767秒、1659个位姿，最大位姿接收间隔0.783秒；Debian状态采样282.982秒、1231条，最大采样间隔0.391秒。状态依次为：前44.1秒无状态191条、初始化20条、TRACKING有效1012条（约48.9–281.0秒），停止边界LOCKED/stale 8条。
- 所有1012条TRACKING状态均valid。运行中各可视通道decode error=0；相机、image、points、history、body的收件计数都增长。时钟偏移估计75,286,874.315秒，最大不确定度1.5毫秒。

| 通道 | 事件数 | Nano relay发送至Debian reader延迟 P95 / 最大 | reader接收间隔最大 / >1秒次数 |
|---|---:|---:|---:|
| body | 4191 | 156 / 710 ms | 0.752 s / 0 |
| camera | 1613 | 163 / 727 ms | 0.916 s / 0 |
| history | 436 | 170 / 506 ms | 1.061 s / 3 |
| image | 1012 | 220 / 865 ms | 1.058 s / 1 |
| points | 1604 | 166 / 724 ms | 0.917 s / 0 |

- 30秒窗口采样为1600×940、5Hz；解码150帧，150帧全窗口像素帧均不同、相邻完全相同帧0。主3D视图ROI在149个相邻对中均有像素变化；左右目ROI有14对在灰度差阈值3下未变化，其余样本变化。RViz窗口状态栏显示约15fps。该证据确认静止时所需视图确实绘制并持续更新，不等同于GPU每次present/显示器扫描时序。
- 截图可见左右目特征跟踪、稀疏特征点、机体坐标/姿态及细轨迹：[RViz静止截图](../../artifacts/runs/hw10-groundstation-20261106T085810Z/groundstation/rviz-static-screen.jpg)。绘制采样摘要：[rviz-paint-metrics.json](../../artifacts/runs/hw10-groundstation-20261106T085810Z/groundstation/rviz-paint-metrics.json)。
- viewer进程RSS峰值约193MB、容器内存峰值约306MB；cgroup OOM与CPU throttling计数均为0。静止链路没有复现此前动态run里13.2–20.6秒的send-to-reader滞后；history/image仍出现少数约1秒接收间隔，不能隐藏为“零间断”。
- Debian事后读取为`NTP=yes`、`NTPSynchronized=no`；与当前执行环境UTC比较约慢8小时。本轮没有校正系统时钟。run内间隔用monotonic，跨Nano/Debian延迟用样本记录的时钟偏移估计（最大不确定度1.5ms）；绝对run日期按Debian本机时钟理解。

## 停止与复核

- 使用 `uav-groundstation experiment-stop` 正常停止。Nano `hardware.sh status`显示无统一会话；VINS/localization/relay已退出；Debian viewer容器已停止。`rmem_max=212992`，Micro XRCE-DDS Agent保持active于CH340/TELEM1，Nano Wi-Fi省电保持on。
- 原始运行目录：`artifacts/runs/hw10-groundstation-20261106T085810Z/`，包含Debian状态/逐条收件事件、轨迹记录、Nano VINS与relay日志、session配置、截图及绘制摘要。`RUN-SHA256SUMS`共27项全部通过，清单SHA256：`37b7969fa9917d42cf2b5b08d76c9eec9790403c575b3610d86add6e22365eb3`。
- 目标机本轮只运行纯感知静止观察；没有改变持久配置。来源视频经分析后删除，只保留单帧截图和统计摘要。

## 限制与下一步

静止条件下的reader与窗口像素均连续，不能解释运动时才出现的长reader滞后，也不能证明运动期间图像、3D视点和轨迹持续绘制。该子项不能代替动态绕圈出口。用户回来后用现有采样器做短动态运行，同时观察屏幕并关联Nano relay、Debian reader、网络计数与资源；在原因得到有证据支持的处置前，GS02.3与父GS02保持`in_progress`。
