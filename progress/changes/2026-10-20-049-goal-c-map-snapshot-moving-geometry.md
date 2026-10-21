# GOAL C 运动后体素快照与 SDF 几何对照 #293

对话摘要：[2026-10-20-049](../../collaboration/dialogues/2026-10-20-049-goal-c-map-snapshot-moving-geometry.md)。

## 改动与结果

- 新建独立 run `p2-map-voxel-snapshot-service-20261020-293`，复用 #292 精确隔离候选 install 和二进制，不构建新版本。捕获客户端门槛从20提高到150组转发深度；ROS domain 142、独立 Gazebo partition，无 PX4、control、traj_server、action goal或控制话题。
- 快照在转发深度计数151→153时读取；source age 99 ms、服务响应44.50 ms。240×240×60地图中unknown/free/raw occupied/inflated为3,440,463/14,218/1,319/6,866，已知体素15,537，占0.4496%；相较#292的7,082个已知体素为2.19倍。#292捕获在首个force command之前，#293在首个force command后约1.85仿真秒，因此跨运行差异不能单独归因于运动。错epoch/map_id继续被拒绝，NPZ两数组精确回读。
- 在日志中提取370组成对VINS姿态，与分开记录的sensor-fixture truth按源时间戳做一次固定尺度SE(3)对齐：位置RMSE7.5 mm、P95 14.6 mm；不做自由缩放或分段重对齐。将1,319个raw occupied体素中心变换到场景坐标，并与本run生成的墙、箱体、圆柱及地面SDF表面比较：最近表面残差中位/P95/最大4.28/7.06/7.94 cm；最近邻分配为墙面1214、箱体64、圆柱41、地面0。所有体素中心在0.10 m内。
- 真值topic不在ROS graph中，fixture truth由只读记录器单独保存，仅在离线计算中用作一个全局刚体对齐。在线定位、建图没有真值输入。
- 轻量证据：[证据 JSON](../evidence/p2-map-voxel-snapshot-geometry-20261020-293.json)；[运行报告](../../artifacts/runs/p2-map-voxel-snapshot-service-20261020-293/run-report.json)；[可复算几何报告](../../artifacts/runs/p2-map-voxel-snapshot-service-20261020-293/snapshot-geometry-analysis.json)。

## 验证

- `bash artifacts/runs/p2-map-voxel-snapshot-service-20261020-293/run-container-01.sh`：exit 0；capture attempt 01满足阈值，服务读回与归档检查通过；运行结束容器退出。
- `python3 artifacts/runs/p2-map-voxel-snapshot-service-20261020-293/analyze_snapshot_geometry.py`：exit 0；断言NPZ数组dtype、shape、元数据计数一致；370组轨迹配对与SDF分析生成报告。
- 源于 #292 的 `ego_planner_node` / `libplan_env.so` SHA分别为`691471c8e6679bf9eb867f9724407cb4f23f09675367bd44353084e65fbe6530` / `c2f3c5d409fa3138c400feb0884750b2c3b64c1183989ef981c3f772dc9617b0`。运行使用派生镜像`sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`。
- 原始NPZ SHA-256：`c45de73d5d38e7bddd0296adaaa25dc0551570efd5e77863a03aeabdd63abdb5`；所有关键artifact路径与哈希记录在证据JSON和run-report。

## 局限与下一步

仅有一个成功快照，99.55%配置体素仍unknown；箱体和圆柱点数分别64和41，不能冻结单物体几何阈值。残差只检查表面邻近，不检查覆盖完整、free-space正确、膨胀净空或规划可用性；单时刻快照不可能量化时间重影或累计地图稳定性。下一步同一epoch持续运动期间分时捕获多个快照，度量已知/free/occupied增长、墙面／障碍重复表面位移和融合时延，再在错位多障碍场景复测；之后审查候选patch 0021进入标准依赖重建链的方式。P2/P6阶段状态和GOAL C标准均不因本轮变化。
