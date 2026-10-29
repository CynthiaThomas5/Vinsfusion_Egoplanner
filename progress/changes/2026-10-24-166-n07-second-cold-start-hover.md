# N07.12 #166：第二次独立冷启动无目标悬停尝试

## 执行模式与范围

Goal 完成模式；用户指定 N07。复用 #165 镜像、runtime、spawn、wall 布局、全机支架 profile、N05 门限、EKF2 参数和无目标悬停流程，不改控制行为或健康阈值。目标是取得 N07 三次连续冷启动序列中的下一次完整通过。

## 结果

Run `n07-20261024-166-01` 的初始只读 N05 online/offline 检查一致拒绝 `ground_plane_insufficient_raw_occupied_voxels`。随后全机支架 route 在 12 阶段中的第 7 阶段触发原有 `accel_bias_norm_exceeded`：sim 292.348 s 首次越过 0.15 m/s² 限值（0.150655 m/s²），最后记录最大 0.168070 m/s²。没有 prescan marker、attached/released gate、起飞或悬停。初始拒绝与健康故障均保留，不改门限、不跳过门禁。

安全收尾确认 fixture 脱离且场景中不存在，LandDetected 为 true，PX4 DISARMED，bridge DISABLED，项目容器退出码 0。完整数值与原始文件哈希见[失败证据](../evidence/n07-retreat-observation-20261024-166.md)及`artifacts/runs/n07-20261024-166-01/`。

N07 明确要求同版本“连续3次”并规定失败后重新计算次数；故当前连续计数从 #165 的 1/3 重置为 0/3。#165 的单次正向证据仍保留，但不计入 #166 之后的新连续序列。下一个 #167 使用同一固定配置和同一 profile fresh cold start；通过才计为新序列 1/3。
