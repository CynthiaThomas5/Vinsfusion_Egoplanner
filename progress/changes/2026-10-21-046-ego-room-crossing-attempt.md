# 房间穿越尝试：起飞前检查失败

对应[对话](../../collaboration/dialogues/2026-10-21-046-ego-room-crossing-attempt.md)及[证据](../evidence/ego-room-crossing-20261021-01.json)。

文件：本记录、对话、轻量证据与CURRENT；运行入口、任务意图、构建、两轮检查、截图和完整日志在 `artifacts/runs/ego-room-crossing-20261021-01`。产品源码、场景、健康门与控制配置没有修改。P0–P6/S1–S6不升级。

启动：旧 `d435i-ego-room-mapping-20261021-01` 已停止，替换为 `d435i-ego-room-crossing-20261021-01`（ROS domain215，同一固定GPU镜像）。当前6个包构建24.1 s通过；PX4日志确认出生pose为 `-8 0 0.3 0 0 0`。原始IMU静止检查86样本、norm9.8后启动VINS，产生新epoch。任务意图对侧x=+8，尚未发目标。

第一轮 `preflight.py` 40墙钟秒：定位曾TRACKING、地图ready，最后733占据点；RTF0.2189、位姿接收最大间隔0.4277 s，超过导航0.3 s门。连续满足条件最多1.896 s，未达到5 s；PX4 EV融合和遥测持续性未保持。未调用任何控制服务。

第二轮 `preflight-headless.py` 40墙钟秒：临时SIGSTOP RViz进程组，EXIT trap自动CONT恢复；只是暂停进程，DDS订阅保留，并非完整无GUI消融。RTF0.2849，但定位已锁定 `accel_bias_norm_exceeded`（source约16.468仿真秒），地图被清空，桥DISABLED、localization_not_tracking、未解锁、landed。连续稳定0秒。两轮均未起飞／发导航目标。先后窗口和初始化状态不同，不能把RTF变化全归因GUI。

偏置记录限制：未记录首次越限的精确范数；稍后34.852秒遥测input_features36、stereo34、long_tracks34，solver usable，accel_bias_norm0.1374低于0.15门限，属于锁定后的后续样本，不能替代首次越线或自动解除锁定。不能仅据此归因场景纹理、视角或IMU模型。

验证：两轮同容器ROS探针完成；JSON回读断言两轮未通过、第二轮锁定原因、全采样armed/control_enabled=false通过；脚本bash/Python语法、`python3 tools/project_status.py` 和 `git diff --check`通过。大日志和截图在run目录并以哈希关联。第一次CLI遥测默认截断，不用于数值证据；随后使用 `--full-length`重新保存并回读完整JSON。

当前：Gazebo GUI已打开、RViz恢复，新仿真保持运行。没有从一端飞到另一端，不能称任务成功。

下一步：先定位新出生点下的偏置越限，隔离初始化／视觉／IMU原因并修复，同时改善RTF和时效；重新证明定位与PX4融合稳定后再执行悬停和有位移目标。实际穿越前还需核对16 m目标相对当前24 m odom地图的边界、unknown策略与完整机体净空；不得在线注入SDF世界真值替代视觉规划。
