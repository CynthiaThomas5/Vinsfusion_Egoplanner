# N08 负侧观察短驻留变体在侧视前触发定位健康门（#304）

状态：未通过；本轮未到达负 Y 侧视，未取得 post-release N05 或 N08 任务结果。

## 结果

- 新冷启动使用 `n08_overhead_free_sector_negative_side_short_dwell`，仅把原侧视到位后的静止观察由18秒缩为8秒。扫描在第5阶段姿态运动期间（已完成4/18阶段）因 `normalized_cost=1.1430264109` 超过既有1.0健康门而停止；未进入正／负侧视段。
- 初始 raw-map N05 检查在线／离线一致拒绝 `ground_plane_insufficient_raw_occupied_voxels`。健康锁存后没有 post-release检查、mission、目标、解锁或飞行。
- cleanup确认fixture detached且Gazebo模型已移除，fresh land detector landed。独立4秒PX4读回为bridge `DISABLED`、PX4 disarmed/landed、控制输出0；项目容器安全停止，Exit(0)。

## 判读与下一步

该轮没有触及短驻留变量对应的侧视阶段，不能据此判定8秒观察不足，也不能解读成路线长度导致本次健康失败。前四阶段含远端俯视段；同形基础路线 #300 曾完成扫描并通过post-release N05，但后续仅缺负 Y 方向图面。因此下一子项 #305 复用 #300 已通过路线及原有侧视时长，只把既有正 Y 侧向观察窗口改为负 Y、水平观察，再按同一N05／N08门控检查。这避免在成功基线路线末尾额外叠加侧视驻留。所有门限保持不变。

机器可读摘要和原始文件SHA见此JSON；原始运行位于 `artifacts/runs/n08-cancel-highspeed-prescan-20261026-304/`。
