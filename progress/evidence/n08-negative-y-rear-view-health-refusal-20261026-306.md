# N08 后向观察返回期间定位健康门拒绝（#306）

状态：未通过。后向 yaw=−π 观察已到达，但在经−π/2回中时 VINS cost=1.0311887 越过原1.0门限；未回中到yaw0、未完成支架回收，故没有释放后N05或mission。

## 结果

- 新profile共17阶段，完成12阶段；此前远端路线和返程健康有效。后向观察目标已到达，进入回中阶段时触发`normalized_cost_exceeded`。健康门和任何地图／空间预算均未修改。
- 初始N05因raw ground-plane候选不足拒绝；扫描中止后没有post-release/current-area admission、goal、enable或飞行。
- cleanup确认fixture detached、Gazebo模型不存在、landed；独立4秒PX4读回bridge `DISABLED`、disarmed/landed、控制0。项目容器停止Exit(0)。

## 下一步

#306未能留下扫描后的地图，无法评估rear view是否清除了x≈−1.05m unknown。下一子项#307只把 rear facing 的12秒固定hold缩短到4秒，其余turn、回中、路线和原健康门均不变；假设减少额外后向驻留可在回中前保留定位健康。仍需完整释放后fresh N05以及N08走廊/保持门通过，方能尝试mission。

机器可读摘要和文件哈希见此JSON；原始运行位于`artifacts/runs/n08-cancel-highspeed-prescan-20261026-306/`。
