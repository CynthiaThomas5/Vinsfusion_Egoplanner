# P5 run-local anisotropy filter bias gate 对照 #214–#216

对话摘要：[2026-10-20-010](../../collaboration/dialogues/2026-10-20-010-p5-anisotropy-filter-bias-repeat.md)。轻量证据：[横移bias复测 #214](../evidence/p5-vins-anisotropy-filter-010-horizontal-bias-repeat-20261020-214.json)、[横移独立重复 #215](../evidence/p5-vins-anisotropy-filter-010-horizontal-repeat-20261020-215.json)、[经配置哈希确认的零偏移控制 #216](../evidence/p5-vins-anisotropy-filter-zero-offset-bias-control-20261020-216.json)。

## 变更

- #214在#211的0.01 run-local filter横移/+30°场景中，令run-local flight harness保存现有VINS telemetry JSON的`accel_bias_norm`和`gyro_bias_norm`。
- #215准备时意图使用#207零偏移目标，但路径替换遗漏了`$PROJECT`形式；运行后的目标 JSON显示实际仍为#192的0.30 m横移/+30°目标。保留原始运行文件，修正来源清单和解释，将其归类为#214的横移独立重复。
- #216将启动脚本明确改为复制#207零偏移目标，并在运行目录预置、运行后再次核验目标文件SHA-256。运行结束后发现复用脚本把`zero_offset_goal_config`写成0；根据实际配置哈希将派生事实更正为1，并在来源清单记录模板缺陷。该更正没有改变仿真输入。
- 三轮均只使用run-local observer/harness；没有改健康策略、canonical VINS源码、PX4参数、桥接或控制发布者。残差、图片、PX4 ULog离线解析结果及SHA索引均保留。

## 结果

- #214/#215均通过前置门、起飞并派发0.30 m横移/+30° yaw目标，随后因`localization_accel_bias_norm_exceeded`中止。首次超限的估计器`norm(Bas[frame_count])`分别为0.155665/0.161031 m/s²，健康限值0.15；首次invalid时normalized_cost分别为0.512546/0.514982，低于未变更的1.0 cost门。超限约在目标派发后3.85/4.04墙钟秒出现。估计器bias state不是传感器偏置真值。
- #216使用0平移、0 yaw偏移；action因`position_yaw_tolerance_held`成功。893条raw telemetry的accel-bias峰值0.138114 m/s²，未越限。PX4 bridge先在27.176秒因`px4_frame_alignment_drift`进入LANDING；该时平移对齐误差0.0101 m，小于0.15 m门限，时间配对新鲜，源码逻辑指向yaw误差门（0.15 rad），但yaw误差本身未记录。定位随后在28.076秒因`long_tracks_insufficient`失效；normalized_cost首次达到1.153525时已锁定。flight report未观察到最终disarm，PX4 ULog则确认AUTO_LAND、touchdown与最终disarm；touchdown后短暂DESCEND/failsafe。零偏移action成功不等于P5导航通过。
- #214/#215视觉残差快照分别为537/536 blocks，其中106/59个>1.5 px；#216为313个blocks、62个>1.5 px。快照在各自quality事件时获取，部分发生在action/定位已经失效后，不能直接证明当前左图候选如何通过run-local filter。
- 三份PX4 ULog均记录EV融合、GNSS aiding flags为0、0 dropout、touchdown和最终disarm；均在触地后短暂记录DESCEND/failsafe。三轮无运行时truth输入。

## 验证

- #214–#216的run-local wrapper执行`bash -n`；#214/#216启动前确认0.01 filter env和唯一Gazebo partition，#216实际目标文件哈希匹配#207零偏移配置。#215实际目标文件与#192横移配置哈希一致，并按此纠正证据分类。
- 各轮在固定Jazzy容器内完成6个自维护ROS包的隔离overlay构建；所有flight harness返回值按各自任务结果记录，外层容器运行正常收尾。
- 图像/残差分析无缺图，逐观测Huber cost可重算；原始双目图、runtime overlays、离线annotation和关键run artifacts均通过SHA-256复核。
- PX4 ULog离线解析确认EV/GNSS、dropout、landed/disarmed、DESCEND/failsafe时间线。`python3 tools/project_status.py`结构检查通过；`git diff --check`通过。结构检查与诊断run均不代表GOAL通过。

## 局限与下一步

两个横移run和一个零偏移run的结果只能形成待查线索。后续零偏移复测#217也触发accel-bias门，因此“bias门与横移相关”的小样本表述已被撤回；独立run仍不能证明filter导致bias增长。#216的yaw分支判断仍是源码逻辑下的推断：#217最后一个中止前新鲜ACTIVE yaw误差为0.052709 rad，未复现对齐故障，故未验证#216故障时的yaw值。后续细节见[改动记录#011](2026-10-20-011-p5-anisotropy-bias-yaw-detail-repeat.md)及[#217证据](../evidence/p5-vins-anisotropy-filter-bias-yaw-detail-repeat-20261020-217.json)。保持`0008` run-only并保留所有门限。P5和GOAL A–H仍未通过。
