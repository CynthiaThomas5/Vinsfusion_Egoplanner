# Debian 地面站使用

地面站 `work@192.168.31.223`，项目部署在 `/home/work/D435i-groundstation/project`。
Nano 为 `jetson@192.168.31.186`，别名 `uav-nano`，工作区 `/home/jetson/D435i-VINS-EGO-ROS2-hardware`。
两机需在可互通的局域网。地址变化时修改地面站 `~/.ssh/config` 中的 `Host uav-nano`。
项目参数位于 `config/groundstation/debian.env`；配置中不保存密码。

Nano运行相机、VINS、建图、EGO和导航；地面站运行RViz、QGroundControl、SSH和诊断。
Debian宿主保留原系统，ROS显示运行于项目专用Jazzy容器。Nano仍是Foxy。
本项目默认通过SSH传输显示数据、在Nano执行原生ROS操作，不依赖Foxy/Jazzy直接DDS互操作。
本地显示使用domain83，与Nano运行域隔离；不设置自动起飞或开机自动控制。

## 日常入口

应用菜单和桌面已安装定位视图、占据地图、运行状态、Nano终端、QGroundControl入口。
也可在地面站终端执行：

```bash
uav-groundstation check
uav-groundstation status
uav-groundstation nano-shell
```

`check`检查容器、SSH、库和消息接口；进程存在不代表定位有效。
`status`中各进程alive应为true，定位仍须核对有效状态和原因。
当前已知IMU未来戳问题未由本次部署修复，INVALID/LOCKED不得视作可导航。

## 启动Nano纯计算与显示

要复现最近的纯VINS绕圈视图，在地面站终端执行：

```bash
uav-groundstation experiment-start
```

此入口先在地面站启动RViz、左右目/几何两路只读relay和轨迹记录器，确认relay已连到Nano后，再启动新的Nano perception epoch。定位有效并收集20个位姿静止起点后，入口才提示可以移动。运行ID对应的PC轨迹数据写入 `artifacts/runs/<run_id>/groundstation/`。动态诊断还会在run根目录保存5Hz `viewer-status-samples.jsonl`与逐条`visual-receive-events.jsonl`：记录Nano/PC时钟偏移、VINS stream freshness、每种视觉数据的源时刻、relay发送、Debian接收和本地解码处理时刻，不保存视觉payload；状态样本还记录host/container资源和默认网卡计数。正常`experiment-stop`会把viewer容器console保存到`groundstation/viewer-console.log`。这些数据能测到Debian接收/处理，不等于GPU/RViz实际绘制帧时间；移动时仍需留意并报告屏幕是否冻结。实验停止用 `uav-groundstation experiment-stop`，它仅接受perception层并先正常停止Nano会话，再关闭本次viewer并保存终点/记录统计。此入口无地图、规划、EV、模式切换或武装。若入口中途报错，按提示检查 `status`，不要叠加启动第二个会话。

此前动态run曾记录Nano发送后到Debian reader最高20.627秒滞后；历史根因未定位。新动态run `hw10-groundstation-20261106T104050Z`覆盖运动段，用户现场报告无卡顿，Nano定位27/27条TRACKING，五路reader最大接收间隔≤0.806秒、发送到接收最大≤0.372秒；RViz窗口以5Hz采集174.8秒共874帧，运动段双目与3D视图143对相邻帧均变化。故冻结版当前动态展示连续性通过，但旧异常仅为未复现，不能称已修复。时延使用run内时钟偏移估计，持续时间使用monotonic；Debian NTP状态未同步，本轮未校时。完整细节见`progress/evidence/gs02-dynamic-rviz-20261107.md`，并参阅`progress/evidence/gs02-display-pipeline-20261106.md`、`progress/evidence/gs02-static-live-20261107.md`、`progress/evidence/gs02-static-rviz-paint-20261107.md`、`progress/evidence/gs02-network-baseline-20261107.md`和`progress/evidence/gs02-rviz-controls-lifecycle-20261107.md`。

已有会话先检查，不可叠加启动；确认旧会话可结束时使用正常stop。

```bash
uav-groundstation nano-stop
uav-groundstation nano-start plan
uav-groundstation view
```

`plan`一次启动传感器、定位、建图、EGO、traj_server和导航action；没有PX4桥，不发EV、模式或武装指令。
仅看定位可改用 `nano-start perception`。普通启动不自动发导航目标。
`view`默认仅读取已有定位日志，不增加Nano ROS订阅。机体轴和轨迹只有定位有效时更新；没有数据/失效显示INVALID。

需要相机视锥、当前/历史稀疏特征、双目预览时，先关闭其他PC拥有的完整可视化，再执行：

```bash
uav-groundstation stop-view
uav-groundstation view --visuals
```

已有relay时入口拒绝第二套完整显示。新显示会增加Nano订阅/编码负载，不能从旧PC/Humble显示证据推断新地面站完整负载已合格。
首次启动完整感知时，既有脚本会设置接收缓冲区，要求Nano现有的sudo权限可用；不要绕过失败检查。

另一终端查看占据地图与规划参考采样：

```bash
uav-groundstation map-view
```

仅在Nano运行plan且定位有效时有地图。图中蓝色是occupied、橙色是膨胀占据，粉色是最近一条轨迹的参考采样记录，**不是完整未来B样条曲线**。
地图/参考通过Nano原生订阅和SSH传输；epoch不符、定位失效或状态3秒未到则清除显示。
显示使用当前VINS世界坐标和接收时刻，不改原始消息，也不能作为定位精度/碰撞证据。
会话epoch变化后关闭并重开显示，不自动拼接地图。没有plan/定位已失效时空地图符合预期。

## ROS接口、目标与记录

地面站 `ros2` 已指向Nano原生ROS环境，例如：

```bash
ros2 topic list
ros2 interface show uav_interfaces/action/NavigateToPose
ros2 topic echo /localization/status --once --qos-durability transient_local
ros2 action list
```

这条路径不将Nano消息通过Jazzy DDS反序列化；导航目标仍由现有 `/navigation/navigate_to_pose` 接收。
目标的frame必须使用当前 `odom_<epoch>`，包含完整3D位置、yaw四元数、容差和超时；不在启动器中放固定目标或默认发目标。
可通过 `uav-groundstation nano-shell` 在Nano原生环境录包，按原有数据负载预算选择话题，不默认录高频全量数据。

本地RViz诊断使用隔离域：

```bash
uav-groundstation local-ros topic list --no-daemon
uav-groundstation local-ros topic echo /hardware_view/status --once
```

不要用跨Foxy/Jazzy的直接DDS收包是否成功替代本项目SSH路径验证。

## QGroundControl

安装的是官方v5.0.8 x86_64 AppImage，SHA256 `06969c67ef58ea063def0a8271447a1cc385438c4a7df36813315b4475146737`。
文件放在 `/home/work/D435i-groundstation/downloads`，不入Git。入口使用extract-and-run，不依赖FUSE挂载。

```bash
qgroundcontrol-uav
```

宿主work已加入dialout；直接USB访问需重新登录桌面使新组权限生效。未全局停止ModemManager，也未改飞控参数。
直接连接飞控USB或使用专用MAVLink数传时，按实际端口配置QGC。
目前未配置一条可与Nano DDS常驻链路并行的双向MAVLink物理链路，不据安装成功宣称飞控已连接。

仅需通过Nano已有USB看遥测，可在串口无人占用且为MAVLink模式时执行：

```bash
uav-groundstation telemetry
```

该路径只将Nano收到的字节发送到地面站localhost UDP14550。QGC回发命令和参数请求不转发；不支持远程调参/模式操作，不占用Agent正在使用的串口。
Ctrl+C结束遥测。QGC默认可能尝试请求参数，但本接收链不会送往飞控；需要完整参数操作须使用独立双向连接。
QGC日志保留语音后端加载警告，视觉界面可启动，语音告警未验收。

## 停止与路径

```bash
uav-groundstation stop-view  # 只停地面站显示
uav-groundstation nano-stop # 停Nano所属纯计算会话
```

有真实EV/control状态时，继续遵守项目落地上锁流程，不靠关地面站确认飞控安全。

- Nano原始日志：`artifacts/runs/<run_id>`。
- 地面站安装/运行检查：`/home/work/D435i-groundstation/logs`。
- 本地显示状态：`~/.local/state/d435i-groundstation/live-status.json`。
- ROS镜像：`uav-groundstation:jazzy-20261104`；可用仓库 `docker/groundstation.Dockerfile` 重建。
- 原ros2/rviz2脚本备份：`~/.local/bin/*.before-uav-20261104`。
- SSH私钥只在地面站 `~/.ssh`，不进入源码/证据归档。
