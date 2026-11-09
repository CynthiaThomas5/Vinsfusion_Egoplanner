# GS02.3 静止 RViz 控件与生命周期验证

## 目标

趁用户离开时完成无需物理移动的界面交互和停止归属检查，为GS02.3补足重复启动、viewer停止及计算会话正常关闭证据。

## 改动与产物

- 归档 Debian + Nano run hw10-groundstation-20261106T092711Z，包含viewer状态样本、视觉收件事件、VINS/localization日志、生成会话和姿态记录；补充groundstation/rviz-control-metrics.json。不保留临时相机截图。
- RUN-SHA256SUMS有27个条目，SHA256 92fbca54a20704ddeb753cff4ce334924d3495908703d813618047a2c7f69eef。
- 更新progress/CURRENT.md、progress/milestones.json、本任务书和对话/变化记录；GS02.3仍为in_progress。

## 验证结果

- MoveCamera左旋、中平移、滚轮缩放后，3D视口相邻帧ROI像素差>3比例分别2.42%、4.95%、6.15%。
- 活动run内第二次启动返回1并被拒绝，未建立第二session。
- stop-view停止Debian viewer并保留Nano perception session；两个relay异步退出。随后experiment-stop正常收尾。
- Debian及Nano均报告无统一硬件会话；VINS/localization/relay相关进程为空；rmem_max=212992。Nano microxrce-agent.service仍active于CH340/TELEM1。PX4 outputs=not_started。
- run记录1552个位姿，记录器268.097s，首尾估计位移0.50mm；本轮没有实物移动，不计入动态绕圈出口。

## 验证命令与限制

- Debian：./tools/groundstation.sh status → No unified hardware session；docker ps --filter name=d435i-gs-view为空。
- Nano：bash tools/hardware.sh status → No unified hardware session；ps -eo pid,args | grep -E 'd435i|vins|localization|visuals-|realsense'无匹配；sysctl -n net.core.rmem_max → 212992；systemctl is-active microxrce-agent.service → active。
- 详细像素、重复启动和停止时序见[证据报告](../evidence/gs02-rviz-controls-lifecycle-20261107.md)及raw run。该静止检查不解释此前动态13–20秒reader滞后，不证明运动期真实屏幕连续性；后续仍需用户移动并观察。
- Debian同步复核：release 380项SHA及overlay zstd通过；目标project_status显示PASS，groundstation check/status通过，容器镜像SHA未变。旧overlay、manifest、SHA三件文件已备份到backups/gs02-overlay-before-20261107-004/。
- 上下文审计发现Debian接续页仍写“RViz实际paint未测”，与静止paint证据矛盾；已更新GROUNDSTATION_CONTEXT.md与docs/groundstation-debian.md，区分静止绘制基线和待测动态连续性。
