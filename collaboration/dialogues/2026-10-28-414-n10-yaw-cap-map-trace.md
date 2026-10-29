# N10.3/#414 校准准备

## 任务
按 N10 完成方案诊断 #412 raw-map voxel 来源与 yaw/RPE 现象；固定线路和其余控制/地图参数，仅改变 EGO 常规前视航向 cap。

## 决定
- #413 审计发现旧 observer 对 occupancy cloud 每十帧抽样，且仅保留注入后有限窗口；`no_roi_cloud_observed` 不能推出没有 ROI cloud/体素更新。#414 改为记录计划窗口内每个云，并按快照源戳冻结 watermark。
- 新增 0058 只读 ROI voxel update trace，含 fusion/source identity、相机位姿、hit/miss 投票及更新前后 raw class。流落盘 JSONL 以限制 observer 内存；有写盘/mapper 额外负载，资源结果仅作带追踪配置的实测值。
- 0057 单变量为常规轨迹航向 cap 0.10 rad/s；不会改末端 task-yaw spline、路线、速度、地图、碰撞或接受阈值。分析不预设通过，负结果保留。
- 当前定向测试与 patch replay 通过；build 和 SITL 尚未执行。N10 保持 `in_progress`。
