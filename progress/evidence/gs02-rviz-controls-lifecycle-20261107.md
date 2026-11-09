# GS02.3 静止 RViz 控件与生命周期验证（2026-11-07）

## 范围

- Debian 固定入口启动 run hw10-groundstation-20261106T092711Z，epoch 8aa5a7336be4488d983dd994623ec8c2，配置 config/rviz/hardware_live.rviz，RViz MoveCamera 工具。
- 这是不需要用户移动的静止感知/UI验证。本轮没有移动相机或机体；PX4 outputs=not_started，没有 map/planner/EV/control、模式操作、武装/起飞，也没有修改飞控固件、参数或同步门限。
- 原始 Debian 与 Nano run 内容归档在 [artifacts/runs/hw10-groundstation-20261106T092711Z/](../../artifacts/runs/hw10-groundstation-20261106T092711Z/)。RUN-SHA256SUMS覆盖27个数据文件，清单SHA256 92fbca54a20704ddeb753cff4ce334924d3495908703d813618047a2c7f69eef。

## RViz 视点操作

窗口为1600×940。屏幕工具栏/状态提示为MoveCamera：左键拖动旋转、中键拖动平移、滚轮缩放。通过 XTest 注入三类鼠标事件，每步保存一张临时截图；截图在计算像素指标后删除，只保留源帧哈希与测量摘要。比较相邻动作帧的灰度差，ROI为3D视口x=500..1599、y=80..879，阈值为灰度绝对差>3。实时画面本身可能改变像素，因此这些指标表示动作后视口有变化，不作为精确相机变换量。

| 操作 | 全窗灰度平均绝对差 | 3D视口平均绝对差 | ROI中差值>3的像素 |
|---|---:|---:|---:|
| 左键拖动旋转 | 1.0716 | 1.6114 | 21,286 / 880,000（2.42%）|
| 中键拖动平移 | 2.4694 | 3.9615 | 43,546 / 880,000（4.95%）|
| 滚轮缩放 | 3.0434 | 4.9726 | 54,156 / 880,000（6.15%）|

摘要与捕获来源哈希见 [rviz-control-metrics.json](../../artifacts/runs/hw10-groundstation-20261106T092711Z/groundstation/rviz-control-metrics.json)。临时相机画面未留在仓库。

## 重复启动与停止归属

- 运行中再次执行experiment-start返回1，错误为“A groundstation viewer already exists; inspect status and close its owner first.” 原会话epoch保持不变，没有创建第二个viewer/session。
- stop-view后Debian viewer容器停止，Nano感知会话继续；relay按异步退出。约3秒复查时geometry relay已退出而image relay仍存活；随后下一次hardware status时两个relay均已退出。
- 随后正常执行experiment-stop。Debian groundstation status与Nano bash tools/hardware.sh status均为“No unified hardware session.”；Nano没有VINS/localization/visual relay相关进程，rmem_max=212992。microxrce-agent.service为active，ExecStart使用/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0、1,000,000 baud，即CH340接PX4 TELEM1。Debian无d435i-gs-view容器。
- 运行记录器有1552个姿态、时长268.097s、最大接收间隔0.473s。首尾估计位移约0.50mm，距首姿态最大偏移约3.60mm，累计估计路径约0.17m；没有任何实物移动输入，这些数值只描述静止噪声，不算绕圈或精度验收。

## 结论与限制

Debian RViz视点的旋转、平移和缩放均产生对应操作后的视口变化；重复启动保护有效，显示停止与Nano计算停止的归属符合设计，两个relay最终释放。未改PX4或控制状态。

该run未复现动态长reader滞后，也没有动态移动期间的屏幕观察，不能关闭GS02.3。用户回来后仍需短时移动并同时观察真实RViz画面，结合已有Nano relay、Debian reader、资源和网络采样判别停顿。

## 迁移包与目标机复核

新增迁移overlay含196个唯一文件，目标端zstd完整性与release 380项SHA清单通过，overlay已解包到固定入口。Debian目标机执行python3 tools/project_status.py显示Structure/design check: PASS，groundstation check的镜像、aarch64和imports检查通过，groundstation status为No unified hardware session。镜像SHA保持119e6564bce3d322bd85da2f65dddd2e5b5dfab91c58444e35a0ea3d8de5880a。替换前的overlay/manifest/SHA三件文件已备份到目标机backups/gs02-overlay-before-20261107-004/。

## 上下文接续页

发现并修正了Debian接续页中“RViz paint未测”的过期概述。GROUNDSTATION_CONTEXT.md和docs/groundstation-debian.md现记录静止paint证据、MoveCamera/lifecycle结果和仍未通过的动态连续性出口；二者随最终overlay重新同步。
