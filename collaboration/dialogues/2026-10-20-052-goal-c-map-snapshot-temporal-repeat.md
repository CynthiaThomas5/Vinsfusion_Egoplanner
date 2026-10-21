# GOAL C 第二布局独立 epoch 复测 #296

日期：2026-10-20

## 任务摘要

用 #295 的箱体／圆柱位置、尺寸和完整 world SDF，在新ROS domain、Gazebo partition与新VINS epoch重复三时刻地图快照，检查 #295 观察到的墙面约一个栅格的位置变化是否重现。

## 约束与决定

- 仅运行相机、VINS、定位/深度健康与建图适配器及隔离 EGO `plan_env`；无 PX4、controller、traj_server、导航目标或控制。
- 重用#292候选安装，不改`src/vendor`或canonical依赖列表。
- fixture truth不进入在线ROS链，只用于每轮离线固定尺度轨迹对齐。
- 保留所有大于10 cm的SDF表面离群中心，不做事后筛除；重复现象不是验收阈值。

## 结果与后续

#295/#296的完整world SDF和障碍物清单SHA一致，epoch/map_id不同。两轮都出现墙面中位位置约3.03→2.96→3.03 m的变化；相邻位移为约67–73 mm，同一采样时刻的跨run中位位置差约0.6–3.5 mm。#296第一帧有72/2,067个occupied中心离最近SDF超过0.10 m，之后两帧为2和5；首帧72个点都分配给大墙且位于已有中心墙面采样窗之外，窗口目前只是诊断范围。EGO无输入timeout，但没有goal。

该重复模式与墙面前表面x=3.0 m恰落在地图名义x格线index150的事实相符；两个run中心面片距离线投影格线中位数8.3/11.9 mm、P95 16.3/25.7 mm，单栅格side-selection可能解释摆动，但仍未证明原因。下一步在matched capture phase和有界可见ROI内比较原始深度、地图表面偏差、格点选择与snapshot源龄，并解释大墙边缘首帧离群中心。权威数据和限制在progress/evidence及run artifacts，本摘要不是验收凭证。
