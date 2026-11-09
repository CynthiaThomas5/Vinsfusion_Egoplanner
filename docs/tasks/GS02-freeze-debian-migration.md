# GS02：冻结当前版本，迁移 Debian 地面站与项目上下文
状态：passed（GS02.1–GS02.4按本任务范围完成）。冻结包、Debian迁移/上下文接续、地面站纯VINS启动停止及安全边界已验证。追加动态run `hw10-groundstation-20261106T104050Z`中，用户报告全程无卡顿；Nano定位27/27条TRACKING，Debian五路reader最大接收间隔≤0.806s、发送到接收最大≤0.372s；RViz窗口5Hz采样覆盖运动段，双目及3D视图各143对相邻帧均有变化。早先run的13.2–20.6s reader滞后本次未复现，根因和触发条件仍未定位；将其作为历史间歇观察保留，不声称已修复或改动固件/门限。原始运行数据已归档并校验；迁移overlay、release清单和目标机入口复核在本轮收尾后更新。

## 目标与目标机

把当前 PC 项目和 Nano 实际部署冻结为可校验、可回退的地面实验基线，迁移到 `work@192.168.31.223`，使用户后续在 Debian 上独立接续本项目，并启动刚才的 VINS 双目、稀疏特征、机体与细轨迹绕圈实验。后续无人机控制启动也从该地面站进入，按 HW08/HW10 剩余出口单独验收。

已核实：目标机 Debian 13.7 / x86_64、Docker 可用、125 GB可用；镜像 `uav-groundstation:jazzy-20261104` ID `sha256:119e6564bce3d322bd85da2f65dddd2e5b5dfab91c58444e35a0ea3d8de5880a`；`DISPLAY=:0`、Xauthority可读、renderD128存在，地面站 launcher 已安装。旧项目566文件、无Git仓库，已备份至 `backups/pre-gs02-project-20261106.tar.gz`，SHA256 `93d6750eec12b253759159098617aa3da7af0e964dbdc95487b3295dd61c33a4`。Nano当前在线但已重启；其无Git metadata，安装检查通过，16个定位/桥接Python安装文件与源码一致。密码只用于SSH认证，不写入任务或归档。

Nano 保持 `jetson@192.168.31.186`、工作区 `/home/jetson/D435i-VINS-EGO-ROS2-hardware`，承担相机、VINS、定位、后续建图及控制计算；Debian 承担 SSH、RViz、QGC、记录和项目协作。复用 [Debian 地面站入口](../groundstation-debian.md)、`tools/groundstation.sh` 和 `config/groundstation/debian.env`，不重装 Nano 系统，不默认迁移算法到 Debian。

## 冻结时必须保留的现状

- 当前源码有大量已修改和未跟踪文件，不能只复制 HEAD，也不能将已有修改回滚或未经要求全部提交。冻结范围包含任务所需自维护源码、配置、工具、补丁、第三方固定来源及上下文文件。
- 飞控采用 HW10-SYNC-023 最小同步先发修复；原门限保留。024 修复 EV-only 退出；027 高度基准对照完成且临时参数已恢复。高度功能在当前测试板上经用户接受，装机后仍需复测。HW08/HW10 总体验收尚未完成，主线未完成项为 HW10-EV-028 及后续控制/接管等出口。
- 最近实验为 HW10-VIEW-032：perception + 原生 VINS 可视化，轨迹宽 0.005 m，无膨胀地图、规划、EV 或控制。032 运行数据是会话证据，不能作为新启动时要恢复的运行状态。
- 已发现电脑显示路径约 16.166 s 空窗，左右目图也暂停；Nano 记录的优化定位最大间隔约 0.330 s、左右目约 0.206 s、初始化后健康无失效。显示链路具体原因仍未定位，冻结必须保留该未解项，不能标记为已修复或迁移后实时性通过。详见 [032 初查](../../progress/evidence/hw10-view-pause-20261105-032.md)。
- 地图体积与膨胀范围仍带 PROVISIONAL 资格，当前用户已取消地图视图。迁移默认实验不得自动开启地图或修改健康/RTT 门限。

## 顺序、交付物与通过标准

### GS02.1：生成不可变冻结包

1. 读取 AGENTS、README、GOAL、CURRENT、milestones 和相关硬件证据；核验源 PC、Nano、Debian 当前会话及归属。先保存 032 圈记录、原始日志和最终状态；如仍在运行，按当前会话状态安全交接，不能为打包盲目重启或强杀。控制状态不明时保留监护，不因迁移拆控制链。
2. 记录 Git HEAD、分支、tracked diff 与 untracked 清单、逐文件 SHA256、权限和符号链接；对纳入范围做明确 allowlist。保存固定基准 Git 历史或 bundle 与工作树内容，不能仅导出 patch 而遗漏未跟踪实现。
3. 分别核实并记录 Nano 源码/实际 install 身份、相机/VINS 配置、软件及系统依赖、Agent 服务配置与启动参数、飞控固件 manifest/固定镜像及回退镜像、当前参数基线、相机外参与 rig 资格。PC 源和 Nano 部署有差异时逐项列出，不能默认为相同。
4. 冻结上下文：AGENTS.md、README.md、GOAL.md、docs、dependencies、progress/CURRENT.md、milestones、相关 evidence/changes、脱敏的 collaboration/dialogues 任务摘要。选取 023/024/026/027/029–032 必要证据；大日志在单独证据包记录哈希和位置，不能只留不可访问的源机绝对路径。
5. 冻结可重建地面站依赖；固定实际 Docker 镜像身份并保存可导入包或可验证构建来源。Nano ARM 二进制保留为 ARM 部署/回退材料，不能在 Debian x86 上冒充可运行环境。
6. 不打包 `.ssh`、密码、Token、Cookie、私人原文聊天、宿主凭据、活进程 PID、`.runtime` owner 文件及 ROS daemon 缓存。只保存脱敏的会话状态证据，目标机运行状态重新生成。

交付路径：`artifacts/releases/gs02-20261106-freeze01/`，包含完整工作树压缩包、Git历史bundle、Nano ARM已安装运行时和PX4 Agent服务/二进制依赖归档、Debian旧项目备份、Nano部署manifest、过期owner安全恢复快照和选定HW10原始运行数据。冻结工作树在父分支HEAD `dbb724f...` 的当前dirty状态，不是干净提交；有33项已跟踪改动与1073项非忽略untracked路径。PX4子仓库commit `d6f12ad...`、clean。380项SHA清单本地与Debian均通过；后续任务状态/入口修复作为独立`migration-overlay.tar.zst`分层，最终封包仍须在收尾时重算。原PC工作树未回滚。

### GS02.2：迁移和上下文接续

1. 核验 Debian 已有部署和本地修改，先为其生成回退备份；将冻结包传入新的版本目录，校验后再切换入口，不覆盖唯一副本。
2. 建议版本目录 `/home/work/D435i-groundstation/releases/<freeze_id>/project`，既有 `/home/work/D435i-groundstation/project` 入口在确认兼容后受控切换；具体路径以现有安装器约定为准，并记录回退命令。
3. 配置 Debian → Nano 的 SSH 身份与别名、最小所需文件权限；密钥在目标机本地生成或复用，验证主机身份，不复制源 PC 私钥。
4. 使用已有 Jazzy 显示容器；核对 X11/Xwayland 凭据、GPU/渲染、字体、桌面入口、组权限和实际登录会话。不能把旧 PC 的显示号、Xauthority、NVIDIA 型号或 PID 写死到新机。
5. 提供仓库内接续说明，入口明确指向 AGENTS → README/GOAL → CURRENT/milestones → 当前证据；包含源 PC / Debian / Nano 职责、连接方式、启动/停止、当前已知问题、未验收项和恢复方法。在 Debian 的新会话中实际按这些文件复述现状和下一项，验证上下文可用；不依赖旧对话记忆。若目标机使用 Codex，单独核验其安装/登录状态，不迁移源机账户凭据。

通过标准：离开旧 PC 的文件路径依赖后，Debian 能读取完整任务上下文；源码和依赖身份可核验；能 SSH 到 Nano 并执行地面站 check/status；旧部署可回退。结构检查或库 import 通过不能替代下一阶段实测。

### GS02.3：从 Debian 复现刚才的实验

1. 确认旧 PC 完整 viewer/relay 已释放，设备静止且未武装，新 epoch 启动纯 perception 与所需 visuals 预热。复用 Nano 的 session owner，不启动第二套相机/VINS/relay。
2. 补齐并验证地面站入口对 `perception --visuals` 的完整支持：现有 `nano-start perception` 未显式透传 `--visuals`，必须核对预热顺序，不能直接沿用命令就声称与 032 同配置。
3. Debian 显示左右目跟踪、稀疏特征、相机视锥、机体姿态与 0.005 m 轨迹；默认 MoveCamera，可正常旋转、拖动与缩放。默认不打开膨胀地图。
4. 正式移动前固定静止起点；用户完成有限空间慢速绕圈并返回后保存完整轨迹、端点和静止段。没有独立真值时只报告返回偏差与连续性，不宣称绝对精度。
5. 单独记录采集、VINS 原始输出、Nano relay、Debian 接收及显示的时间/间隔，区分 PC 发布时间与 Nano 源时钟；以同一时段证据定位或排除 032 的显示停顿。记录运行时长、最大/P95间隔及资源情况；发生未解释的长停顿则保持该出口未通过，不以“最后轨迹没飘”代替实时性。
6. 验证 epoch 变化不拼接旧轨迹、重复启动被拒绝、显示停止能释放 relay、计算停止归属正确；确认无额外 EV/控制 publisher，未改飞控参数和同步门限。

通过标准：从 Debian 独立启动并完成上述完整实验与正常停止，证据对应冻结版本；032 显示停顿有判别数据及处置结论。若需修复产生新版本，保留原冻结包，对修复版另记 manifest 和受影响回归，不改写原基线。用户持续看图时记录 live 会话归属与停止入口。

### GS02.4：无人机启动入口和后续飞行验收交接

本任务内“启动”交付为地面站可启动/停止无人机上的感知计算、查看状态和已具备资格的诊断入口，不把启动程序绑定为自动武装/起飞。

实机 Offboard/起飞入口作为后续明确子任务：先核对安装后的 HW08、机型/执行器、EV 完整动态出口、唯一控制发布者、接管及退出；沿用 HW10 协议和现场条件实际验证后再开放。迁移本身不通过这些出口、不改 rig 拒绝条件。给出具体阻塞和对应证据，不能安装一个“起飞按钮”就声称无人机可飞。

通过标准：地面站的纯计算启动可用，飞控连接/状态与控制能力有清楚区分；后续 HW10 的任务入口、依赖和恢复步骤可接续。HW08/HW10 未完成状态保持真实。

## 执行与验收记录

普通“继续执行此任务”优先做 GS02.1，一个有界子项约 30 分钟；用户明确要求完成整个 GS02 时按 Goal 完成模式连续推进各出口，真实依赖阻塞除外。此文档不自动创建持续 /goal，也不触发实验或飞行。

按阶段记录实际命令和结果：`python3 tools/project_status.py`、`git diff --check`；修改入口时运行对应 groundstation/session 测试与 shell/Python 检查；目标机运行库检查、真实 GUI、Nano session、动态实验和停止验证分别留证。若修改算法或 bridge，补相应构建与专项验证，不能用结构通过替代实机。

完成后写回 CURRENT、changes、必要 milestones 和部署手册；只有对应出口实际通过才更新状态。回退应恢复 Debian 原版本入口与镜像，并按安全流程关闭本次拥有的显示/纯计算会话，不改飞控固件或参数来适配地面站。

历史动态run `hw10-groundstation-20261106T074153Z`曾记录Debian视觉计数停滞22.7–29.1s、路径最大接收空档8.302s、relay发送到reader最大滞后13.2–20.6s；Nano源端定位和relay发送未见对应长空档，接收后本地队列P95约0.05s。异常范围缩小到Nano发送后至Debian reader读取前，但根因未唯一确定，详见[第二圈链路证据](../../progress/evidence/gs02-display-pipeline-20261106.md)。本次新增动态run `hw10-groundstation-20261106T104050Z`期间用户报告无卡顿；运动窗口Nano定位27/27条TRACKING、五路reader最大接收间隔≤0.806s、发送到接收最大≤0.372s。RViz X11窗口5Hz采样174.8秒/874帧，覆盖运动段；双目与3D ROI各143对相邻帧均有变化。用户观察与采样证据支持本次冻结版动态展示连续性通过；旧长滞后未复现，保留为未定位的历史间歇异常，不据此声称根因已修复。细节见[动态连续性报告](../../progress/evidence/gs02-dynamic-rviz-20261107.md)，原始run含31项SHA校验清单。

在新资源/console采样上补做静止全链路run `hw10-groundstation-20261106T083700Z`：状态采样165.517秒、4479条视觉事件，VINS进入TRACKING；relay发送到reader延迟P95约26–74ms，最大约101–165ms，最长通道接收间隔0.753秒，无解码错误、CPU限流或OOM。未移动，不能算绕圈，也不能代表屏幕实际paint。另做Nano省电开/关及Debian反向的空闲ICMP基线：Nano→Debian RTT均值约52–56ms、最大121–139ms，关闭Nano省电没有改善，Debian iwlwifi省电参数关闭；未修改持久网络设置。详情见[静止全链路证据](../../progress/evidence/gs02-static-live-20261107.md)和[网络基线证据](../../progress/evidence/gs02-network-baseline-20261107.md)。

再通过Debian固定入口完成静止RViz绘制基线 `hw10-groundstation-20261106T085810Z`：运行285.767秒，记录1659个位姿，最大位姿接收间隔0.783秒；viewer状态样本282.982秒/1231条，1012条有效TRACKING。各可视通道send-to-reader延迟P95约156–220ms、最大约506–865ms；history/image出现4个约1.0–1.1秒接收间隔，未出现秒级以上reader滞后。RViz窗口30秒5Hz采集150帧、150帧不重复；静止截图显示左右目跟踪、稀疏特征点、机体及轨迹。解码错误0，viewer进程RSS峰值约193MB，容器内存约306MB，无OOM/CPU限流。用户未移动，本run不计绕圈。详情见[静止RViz绘制证据](../../progress/evidence/gs02-static-rviz-paint-20261107.md)。

宿主/cgroup/网卡采样和viewer console保存已在Debian固定镜像通过；静止UI/lifecycle run `hw10-groundstation-20261106T092711Z`确认MoveCamera三类操作、重复启动拒绝和停止归属，运行1552条姿态/268.097s且未实物移动，详见[静止UI与生命周期证据](../../progress/evidence/gs02-rviz-controls-lifecycle-20261107.md)。动态run和静止paint原始数据均归档并带SHA清单。Debian与Nano会话已正常停止，`rmem_max=212992`，microxrce-agent.service仍active于CH340/TELEM1；无PX4输出、EV/control、武装或飞行。本任务只验收冻结、迁移、纯VINS动态展示及上下文交接，不授予HW08/HW10飞行资格；后续硬件主线为 `HW10-EV-028` 及装机复测。
