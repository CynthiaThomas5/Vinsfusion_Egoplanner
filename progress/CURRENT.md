# 当前状态

- 2026-11-09 REPO-PUBLISH-001：整理当前工作树用于 GitHub 发布，更新 README、忽略规则与[发布说明](../docs/github-publishing.md)，本地 origin 指向 `CynthiaThomas5/Vinsfusion_Egoplanner`。网络权限恢复后已读取并合并远程初始提交；现有 SSH 密钥被拒绝，正在通过 GitHub 官方设备流程登录，上传待完成；不改变 GS02、HW08/HW10 与硬件下一项。详见[发布记录](changes/2026-11-09-002-github-publishing.md)。

- 2026-11-08 SYSTEM-AUDIT-001：批次1状态/启动修复、批次2profile/设备身份收敛、批次3fresh安装入口与清单及批次4导航减负已改。43项可运行的本地定向回归通过，含假colcon成功/失败安装激活、安装后源码变化触发清单失效、启动故障注入、构建/启动互斥、停止无启动依赖、同设备记录身份匹配及安装launch/config核对；ROS深度率测试缺 `ament_index_python`、导航集成测试缺 `rclpy`，均在导入阶段退出。当前x86_64工作站无ROS Foxy，Nano SSH连接被本地网络沙箱拒绝，故Nano ARM/Foxy fresh build和地面链路尚未验证。工作树还混有大量本任务外改动，四批未形成独立 Git 提交，提交级单独回退未完成。GS02完成，HW08/HW10资格状态不变；硬件主线仍为HW10-EV-028。计划见[实施计划](../docs/tasks/SYSTEM-AUDIT-001-remediation-plan.md)，报告见[系统审查](../docs/reviews/system-audit-20261108.md)。Nano 2026-11-09 重连复核见[重试记录](changes/2026-11-09-001-nano-connectivity-retry.md)。

- 2026-11-07 文档补充：新增[中文使用指南](../docs/使用指南.md)，覆盖当前地面站启动、记录、停止及独立仿真入口；仅文档更新，GS02/HW08/HW10 状态和硬件下一项保持原记录。

## GS02：冻结当前版本并迁移 Debian（已完成；历史reader长延迟保留为未定位观察）

- 执行模式：Goal完成模式；范围为GS02.1–GS02.4冻结、迁移、VINS动态实验和安全交接，不授予武装/起飞资格。冻结ID `gs02-20261106-freeze01`；原PC工作树未回滚。
- 冻结包本地及Debian目标校验通过：380项SHA256清单、zstd完整性和Git bundle验证。Debian固定入口 `/home/work/D435i-groundstation/project` 指向freeze01版本；旧566文件目录和压缩备份保留。镜像身份未变，桌面“启动VINS绕圈实验”入口已安装。
- Debian Codex CLI 已实机核验：`/home/work/.local/bin/codex`，`codex-cli 0.166.0`，ChatGPT登录有效；在冻结项目目录运行ephemeral/read-only新会话，能按AGENTS、CURRENT、milestones、接续页与GS02证据复述状态/边界。未读取或迁移认证凭据，见[Codex接续证据](evidence/gs02-codex-context-20261107.md)。
- Debian `uav-groundstation check/status`通过；真实ROS/RViz/GPU/X11启动通过；`python3 tools/project_status.py`结构检查PASS，groundstation边界测试4/4。实验入口遗漏ROS/venv来源及`nounset`冲突已修复并通过目标机重测。
- 首次动态run `hw10-groundstation-20261106T071542Z` 由用户绕圈并确认回点；901姿态、端点估计差8.05cm、累计路径21.98m，路径最大/P95接收间隔1.599/0.437s。Nano运动期142条有效TRACKING观察；因当时只有终态视觉快照，首圈不能判显示实时性通过。
- 5Hz状态采样和逐条视觉relay接收事件已部署并通过Debian固定镜像测试。第二次动态run `hw10-groundstation-20261106T074153Z` 已停止归档：1176姿态，回点估计差12.79cm，路径最大/P95接收间隔8.302/0.275s。Nano 175/178条健康观察有效，relay发送无>1s相邻空档；Debian通道读取最大间隔7.2–10.1s，send-to-reader最大滞后13.2–20.6s，接收后的本地排队P95约0.05s。同一窗口视觉计数停滞22.7–29.1s、VINS显示新鲜度短暂转stale。数据将停顿缩小到Nano发送后至Debian读取前，仍未区分网络/SSH流控与Debian线程/资源调度，也未测RViz paint。见[第二圈链路证据](evidence/gs02-display-pipeline-20261106.md)。
- 新增host/container/网卡资源采样和停止时保存viewer console日志；Debian固定镜像测试、`project_status.py`及`uav-groundstation check/status`通过。最终migration overlay、release 380项SHA和第二圈26项RUN-SHA均已在本地/Debian校验。
- 静止run `hw10-groundstation-20261106T062621Z` 已归档并纳入迁移覆盖包；24项校验通过，用户没有移动，不能算绕圈。
- 新增静止全链路run `hw10-groundstation-20261106T083700Z`：状态采样165.517s、717条，视觉收件4479条，TRACKING 506条；reader延迟P95约26–74ms、最大约101–165ms，各通道最大接收间隔≤0.753s，decode error=0，cgroup无CPU限流/OOM。运行静止、不是绕圈，也未测屏幕实际paint；原始run 25项SHA通过。见[evidence](evidence/gs02-static-live-20261107.md)。
- 新增静止RViz窗口绘制基线run `hw10-groundstation-20261106T085810Z`：状态采样282.982s、1231条，其中1012条有效TRACKING；静止5通道send-to-reader延迟P95约156–220ms、最大约506–865ms，最长reader接收间隔1.061s（history 3次、image 1次超过1s），未复现动态长滞后。X11直接采集RViz窗口30s/5Hz共150帧，150帧全不相同，截图能看到左右目特征、稀疏点、机体与轨迹；这补上静止paint证据，不证明动态连续性。未移动，不能算绕圈。见[evidence](evidence/gs02-static-rviz-paint-20261107.md)。
- 最新静止UI/lifecycle run hw10-groundstation-20261106T092711Z（epoch 8aa5a7336be4488d983dd994623ec8c2）验证MoveCamera左键旋转、中键平移、滚轮缩放；各动作后3D视口相邻帧灰度差>3像素占2.42%、4.95%、6.15%。重复启动被拒绝，旧epoch保持；stop-view后计算会话继续、两个relay异步退出，随后experiment-stop安全结束。Nano无统一会话/定位进程，rmem_max=212992；microxrce-agent.service active于CH340/TELEM1。未安排实物移动，PX4 outputs=not_started。见[UI与生命周期证据](evidence/gs02-rviz-controls-lifecycle-20261107.md)，run SHA清单27项，SHA256 92fbca54a20704ddeb753cff4ce334924d3495908703d813618047a2c7f69eef。本项只补交互与停止归属，不能替代运动期屏幕连续性。
- 收尾迁移overlay更新为232个唯一文件，含本次动态run与GS02完成状态。同步Debian固定入口后release 380项SHA、zstd、目标机`project_status`及groundstation check/status通过；旧overlay、manifest和SHA清单备份到`/home/work/D435i-groundstation/backups/gs02-overlay-before-20261107-005/`。Jazzy镜像身份保持`sha256:119e6564…5880a`。
- 空闲网络对照：Nano→Debian RTT均值52–56ms、最大121–139ms，Nano Wi-Fi省电开/关无改善，随后恢复开启；Debian iwlwifi `power_save=N`。ping无丢包。Nano系统时钟仍为2024-06-18且NTP未启用；run内时钟偏移探针已用于接收延迟计算，本轮未更改时钟。结论不解释动态长滞后、不修改网络配置，见[网络证据](evidence/gs02-network-baseline-20261107.md)。
- 收尾复核：Nano unified session为空，VINS/localization/relay进程不存在，`rmem_max=212992`；Micro XRCE-DDS Agent仍active于CH340/TELEM1。Debian无`d435i-gs-view`容器。两次动态run均为纯perception，无map/planner/EV/control、未武装/起飞、未改飞控固件/参数。
- 新增动态run `hw10-groundstation-20261106T104050Z`：用户报告无卡顿；运动窗位姿估计128.2–152.6s，VINS有效TRACKING、最大pose接收间隔0.526s；五路reader最大间隔≤0.806s，发送至接收最大≤0.372s。X11窗口5Hz/174.8s共874帧全不同，运动段双目与3D ROI的143对采样每对均变化。当前freeze01动态演示出口通过；旧run 13.2–20.6s滞后本轮未复现，确切触发条件仍未知，保留为历史未定位观察，不称已修复。原始run含31项`RUN-SHA256SUMS`且本地校验通过；停止后Nano/Debian会话均空、`rmem_max=212992`、Agent仍active。详见[动态RViz证据](evidence/gs02-dynamic-rviz-20261107.md)及run原始数据。
- GS02.1–GS02.4按本任务范围完成；结论只覆盖冻结/迁移、Codex上下文接续和Debian纯VINS动态展示。HW08/HW10飞行资格未通过，下一条硬件主线仍是HW10-EV-028及装机复测。冻结记录：[GS02证据](evidence/gs02-freeze-20261106.md)，历史异常：[链路证据](evidence/gs02-display-pipeline-20261106.md)，本次执行：[change记录](changes/2026-11-07-005-gs02-dynamic-and-codex-context.md)，任务书：[GS02](../docs/tasks/GS02-freeze-debian-migration.md)。

## 历史记录

历史硬件交接内容已移至[归档](history/CURRENT-history-through-2026-11-07.md)。以往运行状态须查各自 evidence；当前设备状态须重新读取。
