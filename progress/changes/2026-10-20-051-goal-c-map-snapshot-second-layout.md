# GOAL C 第二障碍布局同 epoch 快照 #295

对应对话摘要：[2026-10-20-051](../../collaboration/dialogues/2026-10-20-051-goal-c-map-snapshot-second-layout.md)

## 修改与行为

本轮没有改动项目源码或候选 patch。以 #294 为基线，移动并调整 debug 场景箱体与圆柱，保留墙面、相机运动配置和快照门槛；在新 ROS domain/Gazebo partition 及新 VINS epoch 中复用 #292 隔离候选安装，捕获三个时间点的 raw occupancy 与 inflation mask。

三份快照共享 epoch/map_id/frame、原点、尺寸和0.1 m分辨率。known voxel数为17,478、21,677、21,983；增量+4,199、+306。raw occupied点数为2,153、2,307、1,778，集合Jaccard为0.601和0.683。固定尺度单 SE(3) 对齐后，每个快照的occupied体素中心距同场景SDF表面最大8.58 cm；单轮位置RMSE为3.80 mm。墙面区域中位体素中心在相邻快照间移动7.33/7.12 cm，接近一个0.1 m栅格；该变化可能受可见采样集合影响，未作为ghosting判定。

EGO保持 `WAIT_TARGET`，没有收到目标或控制；没有真值topic，独立fixture truth只用于离线对齐。本轮 EGO 未记录 odom/depth lost 告警，正常退出；无目标运行仍不构成planner验收。

## 验证

- `bash artifacts/runs/p2-map-voxel-snapshot-service-20261020-295/run-container-01.sh`：exit 0；三份快照身份、错误epoch/map_id拒绝和NPZ精确回读通过，运行后节点图无控制节点及truth/control topic。
- `python3 artifacts/runs/p2-map-voxel-snapshot-service-20261020-295/analyze_temporal_maps.py`：shape/dtype/计数和同一栅格校验通过，生成同一固定尺度轨迹对齐、SDF距离与占据集合差分报告。
- 快照服务响应38.40–42.99 ms，深度源龄66–125 ms；运行、快照、SDF、分析及派生源清单均在证据 JSON 中关联 SHA-256。
- `bash -n`、结构检查、JSON/哈希完整性、`git diff --check` 在收尾时复核。

## 局限与下一步

本轮是第二种布局的一次运动序列，不是相同布局独立重复。占据集合变化和约7 cm墙面中位位置变化不足以确认地图重影或稳定性；全配置volume仍超过99% unknown，尚无明确ROI覆盖率和完整度阈值。下一步用新epoch复测此布局，解释近一个体素的墙面中位位置变化，再冻结可重复的ROI几何覆盖／ghosting指标。之后继续审查patch 0021的canonical依赖集成。GOAL C仍 pending。

轻量结果：[证据](../evidence/p2-map-snapshot-temporal-growth-20261020-295.json)；[运行报告](../../artifacts/runs/p2-map-voxel-snapshot-service-20261020-295/run-report.json)；[时序分析](../../artifacts/runs/p2-map-voxel-snapshot-service-20261020-295/temporal-map-analysis.json)。
