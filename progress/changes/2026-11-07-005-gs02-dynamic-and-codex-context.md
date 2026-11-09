# GS02：动态RViz连续性与Debian Codex接续

对话摘要：[2026-11-07-005](../../collaboration/dialogues/2026-11-07-005-gs02-dynamic-and-codex-context.md)。

## 本轮

- 用户确认可辅助测试后，先只读检查Debian固定镜像、ROS导入、地面站/Nano session、传感器session与Agent；随后从Debian固定入口启动仅`perception --visuals`的动态验证。PX4输出`not_started`，无EV/control/模式/武装/飞行。
- 用户在短时绕圈后报告全程无卡顿。采集Nano定位与relay、Debian状态/逐条reader事件、host/cgroup/NIC和5Hz RViz X11窗口视频；另用窗口ROI逐帧差异核对运动段的双目与3D绘制。
- 正常停止后核对Debian无viewer、Nano统一/传感器会话均为空、`rmem_max=212992`、Agent仍active于CH340/TELEM1。运动统计和原始文件见[动态证据](../evidence/gs02-dynamic-rviz-20261107.md)及run目录`artifacts/runs/hw10-groundstation-20261106T104050Z/`。
- 用户更正Codex CLI已安装；登录shell核对CLI版本与登录状态，并在Debian项目路径以ephemeral/read-only新会话读取上下文。结果见[Codex证据](../evidence/gs02-codex-context-20261107.md)。未迁移/读取凭据。

## 判定

- GS02.3动态视图在冻结版本上完成：运动段Nano本地状态27/27 TRACKING；Debian五路视觉reader最大间隔≤0.806秒、发送至接收最大≤0.372秒；X11采样运动窗143对双目/3D ROI每对均变化，用户现场报告无卡顿。
- 早先独立run的13.2–20.6秒reader滞后本次未复现，根因仍不明；保留为历史间歇观察，不称已修复。按任务范围，当前迁移版启动与动态显示出口通过；不据此宣称实机飞行实时资格。
- 没有源码、依赖、PX4固件或参数变更。目标机活动会话均安全清空。

## 验证

- Debian `uav-groundstation check`：PASS；镜像ID保持`119e6564…5880a`。
- Debian `uav-groundstation status`及Nano `hardware.sh status`、`hardware.sh sensors status`：停止后均无会话；Agent `active`；`rmem_max=212992`。
- 原始run视频SHA256：`f2d16bfb5edfb59cca790019c8da2388eeb54a2e4dc063b90a0e603211942ac7`；完整`RUN-SHA256SUMS`在run目录。
- 本地动态run的31项`RUN-SHA256SUMS`通过；run清单SHA256为`27d6b759e992d7179398b4f31d6bd6b6d84b76352a198e380e594a71486e024d`。release 380项`SHA256SUMS`与overlay zstd完整性通过，overlay现含动态run及更新状态。
- Debian原release overlay、manifest、SHA清单先备份到`/home/work/D435i-groundstation/backups/gs02-overlay-before-20261107-005/`；备份三文件哈希分别记录于目标机。更新后目标`python3 tools/project_status.py`为`Structure/design check: PASS`，`uav-groundstation check/status`通过且无统一会话，镜像ID保持`119e6564…5880a`；动态run31项SHA在目标机通过。
- 最新状态写回后，从Debian固定项目目录运行ephemeral/read-only Codex新会话。它准确复述GS02通过、本次无卡顿证据、旧reader长滞后未复现且根因未知、会话/Agent状态、HW10-EV-028下一步和无飞行资格边界。未操作设备或修改文件。
- 本地`python3 tools/project_status.py`显示`Structure/design check: PASS`；`git diff --check`和`python3 -m json.tool progress/milestones.json`通过。仅文档/证据/迁移包变化，无代码或固件测试要求。

## 交接

GS02完成，历史异常保留为未定位、非复现观察。后续硬件主线仍为HW10-EV-028及装机复测；本次不授予控制/飞行资格。若显示reader长停顿再次出现，再按动态证据报告中的同一时钟/reader/资源/paint方法采样。
