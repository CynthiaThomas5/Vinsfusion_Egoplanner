# N07.9 #163：俯仰段 health 事件复现

对话摘要：[pitch health 事件复现](../../collaboration/dialogues/2026-10-24-163-n07-pitch-cost-event-replay.md)

## 父目标与依据

执行模式：Goal 完成模式；用户指定范围 N07。父 N07=`in_progress`，子项 N07.9 #163。#162 在 pitch 转入阶段被锁存 `normalized_cost_exceeded=1.138230`，但探针结果只保留最终 LocalizationStatus；883 条原始 telemetry 的同公式峰值为 0.694196，不能定位触发样本。#158 的完整平移扫描让 HOLD 未知中心降到3个，但 TAKEOFF_CONTACT 仍有122个未知中心；0个低于 raw-ground plane，37个中心落在平面，其余85个高于平面。未知地下体素不在本子项处理范围。

## 假设、变量与判据

假设：pitch 转入期间存在短暂 health cost 越线，最终状态已锁存，但逐事件 LocalizationStatus 记录缺失，无法与 estimator telemetry 对齐。

唯一实验变量是增加一个只读 `/localization/status` 全消息记录器；fixture 路线、pitch 目标/时长、VINS/N05 配置、阈值、布局和冷启动流程完全复用 #162。目标是完成9/9阶段，并保留逐事件状态和 telemetry 对照。扫描完整后在同一 epoch 进行 attached、released 和 post-release N05 五阶段 live gate，离线重放必须逐项一致且全通过；只有这时才可在该容器继续 N07 的 EV / GNSS / publisher 审核与首个≥30仿真秒无目标悬停。

## 执行边界

只运行新 run `n07-20261024-163-01`。observer 写入本 run artifacts，不发布控制、目标或真值。任何 VINS 健康失效都按现有锁存清理；released gate 不通过则保持 DISABLED/DISARMED，不解锁，并确认 fixture 已移除、PX4 landed fresh。此子项不改代码、配置、N05 规则或定位阈值。

## 结果

run `n07-20261024-163-01` 初始 N05 online/offline 一致拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`；只读坐标审计确认 ground plane 以下的 whole-cell 已排除，接触阶段仍有436个未知中心（0个低于平面、52个在平面、384个高于平面），HOLD有566个未知中心且全在地面以上。

俯视 route 完成9/9，pitch观察和返程未复现 #162 的 cost锁存。11,220条 `/localization/status` 记录显示 8,040 TRACKING 后转为 `telemetry_stale`；首次锁存 sim=335.152s、cost=0.472924，整个事件记录最高cost=0.718690。VINS telemetry继续记录到sim=340.432s，轨迹质量字段未越当前门。attached checker等待120s后因 `missing=['odom']` 失败，未产生raw snapshot；未检查released gate。

安全清理确认fixture detached并从Gazebo移除，PX4 DISARMED、末条新鲜 LandDetected=true、bridge DISABLED/control disabled/armed false/landed true；容器Exited(0)。没有飞行，hover=0/3。详见[#163证据报告](../evidence/n07-retreat-observation-20261024-163.md)；status历史为5.1MB运行artifact并在报告中登记哈希。

## 下一子项

N07.10 #164 复用同一路线与阈值，用主机 marker-watcher 自动立即触发 attached 与 post-release N05 检查，降低人工调度延迟；检查使用短有界等待。仅保留低负载状态观测，不启用 keep-all history订阅。目标是取得有效post-scan地图快照，并尽可能在fresh health窗口内完成released N05五阶段比较。任何N05拒绝、定位锁存或最终landed未确认均不解锁。
