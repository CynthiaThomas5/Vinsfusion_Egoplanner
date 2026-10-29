# N07.12 #166：第二次独立冷启动无目标悬停尝试

## 范围

Goal 完成模式，用户指定 N07。计划按 #165 的固定镜像、runtime、spawn、wall 场景、支架 profile、准入门限和悬停流程做 fresh cold start；未授权门限或控制行为调整。

## 结果与决定

Run `n07-20261024-166-01` 的初始 N05 只读检查拒绝 `ground_plane_insufficient_raw_occupied_voxels`。支架扫描到第 7/12 阶段时加速度偏置达到 0.150655 m/s²，超过既有限值 0.15；无 prescan marker、附着／释放后 gate 或飞行。fixture 已移除，PX4 landed/disarmed，bridge disabled，容器安全退出。完整证据在 `progress/evidence/n07-retreat-observation-20261024-166.md`。

重新核对 N07 出口：“同一固定版本连续 3 次”且“失败修复后重新计算连续次数”。因此 #166 中断 #165 开始的序列；计数修正为0/3。#167 是下一次 fresh cold start，通过才计入新序列1/3。地面下体素排除规则、N05门限和控制行为均未调整。
