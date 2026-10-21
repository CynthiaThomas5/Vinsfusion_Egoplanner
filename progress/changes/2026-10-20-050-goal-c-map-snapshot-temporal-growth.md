# GOAL C 同 epoch 多时刻地图快照 #294

对应对话摘要：[2026-10-20-050](../../collaboration/dialogues/2026-10-20-050-goal-c-map-snapshot-temporal-growth.md)

## 修改与行为

本轮没有改动源码或候选 patch。复用 #292 的隔离 EGO snapshot-service 安装，在同一力驱动 D435i 运动序列中完成三次只读 occupancy snapshot；每个快照按 epoch/map_id/frame、源龄、融合状态和 raw/inflated 分层校验并回读归档。单次固定尺度 SE(3) 对齐和同场景 SDF 对照离线计算地图表面距离与跨时刻占据体素变化。

三份快照保持相同 epoch/map_id/frame、240×240×60 栅格和0.1 m分辨率。known voxel数从13,688增至19,878、20,283；两段增长为+6,190和+405。occupied计数为1,290、1,184、1,200，非单调；相邻 raw occupied 集合 Jaccard 为0.702、0.885。三个快照内全部 occupied voxel中心距已知场景SDF表面不超过0.10 m；只作为本轮几何一致性描述。

VINS与独立 fixture truth 的372组成对样本经一个固定尺度 SE(3) 对齐，位置RMSE为8.31 mm、P95为15.23 mm。真值仅离线使用，ROS图内无truth/control topic，也无控制节点。EGO没有收到目标且保持 `WAIT_TARGET`；日志有36条 odom/depth lost 告警，分布在仿真时间4.811–5.671秒与28.705–29.041秒两段，最后一次伴随输入停止。该运行不作为planner readiness证据。

## 验证

- `bash artifacts/runs/p2-map-voxel-snapshot-service-20261020-294/run-container-01.sh`：exit 0；同 epoch 三次快照、错误 epoch/map_id拒绝和NPZ精确回读均通过，容器干净退出。
- `python3 artifacts/runs/p2-map-voxel-snapshot-service-20261020-294/analyze_temporal_maps.py`：对三份归档做shape/dtype/identity/count校验、时间差分、单一轨迹对齐及SDF比较；报告见 `temporal-map-analysis.json`。
- 三次快照服务响应为36.68–39.24 ms，源龄为99–141 ms；NPZ archive SHA-256分别为 `493c588b8815ce07899d88b854570f23379452820af381c4f93aefbd2285c5fd`、`b81a998c88a933d8d5e9e6affd5a2a5d42f8d045df7e6c3943909bb03370ab2a`、`d3bf58acc295596bc8b7e7c4a015b39579588ed78c48284df8aa77a7c86437d4`。
- 结构检查、脚本语法、证据和报告哈希及 `git diff --check` 在收尾阶段复核。

## 局限与下一步

这是一个障碍布局的一次运动序列；全配置地图仍约99.4% unknown。已知体素增长不等于地图完整，occupied Jaccard与墙面位置变化也没有冻结验收阈值，不能量化重影、free-space准确性、车辆净空或规划安全。候选 patch 0021 仍未进入 canonical 依赖链。下一步用第二种障碍布局重复快照和SDF分析，定义有界评估ROI与覆盖/时序门槛，再审查候选服务的正式依赖重建集成。GOAL C继续 pending。

轻量结果：[证据](../evidence/p2-map-snapshot-temporal-growth-20261020-294.json)；[运行报告](../../artifacts/runs/p2-map-voxel-snapshot-service-20261020-294/run-report.json)；[时序分析](../../artifacts/runs/p2-map-voxel-snapshot-service-20261020-294/temporal-map-analysis.json)。
