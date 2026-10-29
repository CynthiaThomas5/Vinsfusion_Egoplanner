# N16最终完成 #568（2026-10-29）

目标：用户授权完成N16全部出口；按#552连续至少300仿真秒，故障专项按#547排除。Goal完成模式。本轮停止原因：N16出口完成；不自动执行N17。

## 真实运行与结论

正式第三次尝试#566（n16-20261029-566-formal03）通过，合格累计1次。GUI可见Gazebo/RViz，唯一桥接器控制；在线导航未订阅真值或完整世界地图。连续导航从37.232至362.340仿真秒，同epoch同武装会话325.108秒，6段往返，实际IMU采样路径71.534893m。各段均有执行轨迹及地图更新，11个核心进程同PID/内核出生时间连续存活。零违规接触，正常降落上锁、控制关闭及控制归零，独立终态检查全部通过后停止项目容器。无紧急disarm。

独立0.3m/15度/3秒标准保持；6段同时满足的连续时长分别4.728、4.036、4.432、4.088、4.296、4.184仿真秒。raw VIO全飞行位置误差P95 0.086638m、最大0.089223m；yaw P95 0.150512度、最大0.165581度。当前理想仿真陀螺模型标定，不构成实机精度证明。

## 缺失参考点的透明恢复

初始评估INSUFFICIENT原样保留：观察器第一条raw位姿晚于PRESTREAM。相同运行VINS原生日志保留PRESTREAM前64ms的完整位姿；2715个重叠时间戳的XYZ/四元数每分量差异均≤0.5e-6，符合日志六位小数舍入。独立评估副本只补一个该同epoch原生参考点，不修改原始归档、时域、scale或对齐方法，不使用终点拟合。supplement记录原日志、观察报告、时间线和工具哈希。

采用保守对齐影响界0.0002m/0.001度，并额外用更严0.2998m/14.999度重算；6段连续时长仍为4.728、4.032、4.432、4.088、4.296、4.180秒，全部通过。原不足报告与原始观察文件保留，不伪称最初观察器字段齐全。

## 资源、地图与时序

CPU中位7.557核、P95 8.044核；RTF中位0.85754。native等待特征最大0、pending span最大0；native输入工作lag最大0.048秒；mapping pending depth最大3，未见持续队列增长。内存从约3.26GB增至约4.46GB（峰值4.54GB）；其中file/inactive_file缓存约增加0.802GB，anon约增加0.389GB。完整memory_stat、事件计数及复查见memory-review.json，不称无限期内存有界，不外推机载实时能力。

26张同run/hash地图快照，18张固定高度ROI有占据表面样本，另外8张该ROI无支持则保留空值；有支持时最近实际墙面距离最大0.057481m。该离线表面诊断不是完整分类认证，不恢复已取消数值门。

VIO源时间到独立观察输出的采样龄P95 0.068秒；6998个非静止READY指令经固定坐标/IMU杆臂转换与实际PX4设定点匹配，指令源至PX4输出采样龄P95 0.004秒、最大0.012秒。583个未匹配设定点保留，不补插值、不把静止重复当因果配对。时序为分段端到端观测，不声称严格逐帧相机至执行器因果延迟或全局最坏界。

## 实际改动与验证

0022补丁：默认关闭known_zero_gyro_bias，当前vins_sim按实际无噪声/偏置D435i模型启用；仅固定三个gyro自由度，速度/accel偏置仍自由。初始化、优化及边缘化切空间一致；保留GPL、上游72023bc5d2abb14faa4c02a5c040d84f996b587a、应用顺序和全部SHA。只读进程观察器改sensor_data Clock QoS；未新增健康/拒飞/取消/降落分支。

#559数学测试8项PASS，#560完整同输入91728IMU/11119双目两例均完整无丢弃；#564直接链接实际生产库的默认与gyro-only边缘化/自由度测试PASS。实际生产构建54.9s PASS。归并主工作区后真实colcon vins构建45.0s PASS，VINS二进制SHA与#566实飞版本完全相同。

31项N16相关单元测试PASS：PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -m unittest tools.test_n16_process_lifecycle tools.test_n16_continuity tools.test_flight_profile tools.test_n16_resource_evidence tools.test_n16_contact_scope tools.test_arrival_evaluator。python3 tools/project_status.py与git diff --check通过；结构检查不替代上述真实构建/GUI飞行。

## 产物和版本边界

- 原始运行：artifacts/runs/n16-20261029-566-formal03及同名-stack；raw-inventory.json含逐文件大小/SHA。
- 冻结运行：artifacts/runs/n16-20261029-565-release，身份1c300ba6d00ff7deb7c515081ece6437971dafae91efc796dcc685252da7bb9b。
- 完整独立评估：artifacts/reanalysis/n16-20261029-568-native-anchor/n16-20261029-566-formal03/n16-formal-evaluation.json（PASS），同目录native-anchor-restoration.json及n16-rounding-robustness-arrivals.json。
- 两张资源/队列/VIO曲线在同评估目录；补充地图/时序/RTF/指令至PX4输出曲线和诊断在artifacts/reanalysis/n16-20261029-567-final-diagnostics。
- 最终逐项审计：artifacts/runs/n16-20261029-568-completion/completion-audit.json（全部checks true），含原始归档/正式报告/补充参考/严格复算/诊断SHA。
- #555独立到达FAIL、#563 VINS移植崩溃FAIL及安全收尾保留，不能计为通过。#563三个遗漏边缘化尺寸点已在正确0022补丁修复，详见#563–565报告。

N16通过范围仅为本次冻结隔离走廊运行及五分钟理想仿真模型；不承诺十分钟或故障资格。主工作区已归并同源码/参数/二进制，但完整默认世界与隔离实飞身份不同，不能把N16算为未经运行的默认场景通过。历史N11–N14保留其原始版本证据，不静默重计为新gyro版本合格；N17需审计受变更影响的回归和交付身份。本次不提前关闭A–H/P0–P6/S6或整个GOAL。

下一步：N17 A–H回收与可重建交付（尚未执行）。

对话摘要：collaboration/dialogues/2026-10-29-568-n16-final-completion.md
