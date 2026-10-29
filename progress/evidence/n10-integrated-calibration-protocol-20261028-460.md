# N10.3/#460：修正物理步观察器后的完整正常导航校准

## 目的

#458 的综合正常任务总体为 `INSUFFICIENT`，其关键区间净空输入因没有物理步账本而不可判定。#459 已确认 PX4 通过 `PX4_GZ_MODELS/<model>/model.sdf` 直接选根模型，并在无飞行 SITL 中验证修正后的 run-local SDF 确实发布 4 ms 状态。本次复用 #458 的完整 16 m 路线、VINS `max_cnt=220`、动态箱体重规划、20 仿真秒保持、传感器采集和正常降落流程，只补整段物理步记录并按同一身份离线评估。

## 固定范围

- 唯一主要变化：`D435I_N10_KINEMATICS=1` 时 PX4 根模型选择本轮 observer overlay。路线、VINS、planner、spawn、箱体和控制配置与 #458 相同。
- 仅执行正常导航与正常降落；不做故障注入，也不计 N15/N16 正式次数。
- 记录 PX4 实际选中的 SDF 路径、SHA 和插件数；该报告仅供离线身份核对，不作为目标提交、起飞拒绝或降落分支条件。
- 使用修正后的 #436 归档复算作为跨运行上下文，不拼接 epoch 或轨迹样本。
- 运行结束须独立确认 `LANDED/disarmed/control-disabled/zero-control`，再受控停止项目容器。

## 判定

完整物理步覆盖要求使用同一次任务、严格递增的 Gazebo physics source stamps、匹配真值端点以及模型/observer/runtime 哈希；缺帧或身份不一致时保持 `INSUFFICIENT`。采样点的正净空不得表述为连续区间证明。跟踪误差、资源/队列容量及重规划量化依据继续按既有草案审查，不因本次记录自动通过，也不放宽数值或增加在线门。

## 运行身份

预期运行 ID：`n10-20261028-460-maxcnt220-kinematics-integrated`。详细环境、运行前冻结身份和实际运行命令记录在配套 JSON、prelaunch 报告及运行归档。
