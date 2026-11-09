# GS02冻结与Debian迁移执行摘要

用户启动任务GS02并要求完成完整冻结/迁移/接续/复现实验入口。Nano在重启后重新上线，032采集与定位均已退出，圈记录器按900秒上限保存5609姿态；用户没有确认回到起点。Nano旧owner PID均消失、rmem恢复212992、VINS/camera/relay已退出；Nano重启后systemd Micro XRCE-DDS Agent自动active，保持串口运行。项目正常stop拒绝了重启后PGID身份不符的owner记录；保留owner快照后，仅清除确认无对应进程的三个stale状态文件。

Nano workspace无Git metadata。Nano硬件安装校验通过，16个定位/桥接Python源/安装文件匹配；部署manifest记录OS/架构/配置与选定二进制哈希。飞控没有被连接查询或改写。

冻结ID gs02-20261106-freeze01：工作树快照（排除所有artifacts及构建缓存）、父Git bundle、选定023/024/026/027/029–032原始run目录和固件、Nano部署manifest与owner恢复证据。本轮新增Debian experiment-start/stop命令：显示先开两路视觉relay和RViz，再启动perception；stop拒绝EV/control。

目标Debian13.7/x86_64、Docker镜像校验通过、图形桌面/Xauthority/render设备存在。旧项目566文件、无Git仓库，已备份并记录SHA。迁移切换、真实GUI/绕圈未完成。

## 2026-11-06 迁移运行检查点

冻结包本地与Debian目标校验通过后，将Debian固定`project`入口切换为freeze01版本并安装“启动VINS绕圈实验”。两次早期启动暴露容器环境来源问题，修复后通过实际Debian GUI/ROS/Nano启动。当前活动run为`hw10-groundstation-20261106T062621Z`，Nano VINS与两路视觉relay、Debian RViz及20 pose静止baseline已就绪。

用户询问此时能否关闭Nano。告知：当前VINS采集与relay正在运行，不可关机/重启/断电；若只关闭Nano桌面窗口则不会终止Nano计算。接下来用户需在有限空间慢速绕圈并确认回到起点，之后由项目入口正常停止并分析轨迹/间隔。未启动EV/control或飞行。

后续检查时Nano与Debian viewer仍存活，累计5559条路径pose但位置范围约3.9mm、端点偏移3.3mm，确认用户尚未移动；29.81秒静止视觉状态采样120/120样本VINS valid、无decode error，各topic计数持续增长。该结果证明短静止窗口的链路在更新，不代表完整动态圈或032长停顿已排除。等待用户移动并确认回起点。


## 2026-11-06 静止运行收尾

检查显示连续运行期间轨迹只在毫米范围抖动，没有用户移动。为避免无人操作持续采集，通过Debian `experiment-stop`正常停止，保存Nano原始log与Debian轨迹/relay样本；owner清空、相关进程不在、rmem恢复，PX4 Agent仍active。告知Nano现在可关机，但断电会断开TELEM1 DDS；GS02.3仍需用户另选时间完成动态圈和回点确认。最终收尾将该run目录纳入迁移覆盖包同步到Debian，使后续会话可在项目内复核静止证据。

## 2026-11-06 首次动态圈

用户确认设备准备好后，从Debian启动新纯感知epoch `16192046bb9741c6918df886d84ba741`，run `hw10-groundstation-20261106T071542Z`。用户完成绕圈并确认回到起点；Debian按项目入口正常停止。记录901个姿态，VINS估计端点差约8.1cm、路径接收最大间隔1.599s；Nano运动窗口有142条有效TRACKING观察，停止后正常失效。未启动EV/控制/武装/飞行，PX4输出标记not_started；停止后owner清空、rmem恢复，Agent继续active。

首次动态证据显示未复现032的16.166s路径空窗，但只有终态视觉快照，无法分析运动期逐通道relay/PC接收间隔，也不能据此确认RViz实际显示未停。用户本轮未报告路径/图像是否在运动中停顿。决定先在现有viewer中加入低频状态时间线、每条视觉relay收包时刻与Nano/PC时钟偏移记录；目标Debian测试通过后再做带时序的短动态验证。原始数据与局限见`progress/evidence/gs02-dynamic-circle-20261106.md`。
