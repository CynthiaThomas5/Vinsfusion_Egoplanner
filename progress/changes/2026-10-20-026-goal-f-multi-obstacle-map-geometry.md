# GOAL F 多几何在线地图采样

关联对话：[2026-10-20-026](../../collaboration/dialogues/2026-10-20-026-goal-f-multi-obstacle-map-geometry.md)。

在 `artifacts/runs/p2-map-multi-obstacle-geometry-20261020-247` 保存 run-local 箱体/圆柱世界、容器启动脚本、在线原始数据和离线 evaluator。项目源模型、PX4 上游、运行参数及控制代码没有因本次诊断而改变；运行使用 #246 已加入外壳碰撞的 D435i SDF。场景 world 仅在 artifact 中把墙体 collision 重命名以满足 standalone SDF 校验。

固定 Jazzy/Harmonic 容器中完成50.023秒观测，mapper/EGO plan_env 输出1264点地图；按诊断真值作一次固定尺度 SE(3) 对齐后，VINS 轨迹位置 RMSE 为8.14 mm。箱体区域30点的表面残差中位/P95为1.61/23.15 mm；圆柱区域34点为76.01/144.73 mm。地图时间戳落在仿真时钟内，距最近优化里程计为0秒。

该运行不能算定位健康通过：41.255秒定位适配器以 `normalized_cost_exceeded` 锁定；EGO日志仍为 `INIT/no odom`，未提交目标。地图样本和轨迹误差仅作诊断，不能说明规划器识别或绕开了障碍、最小机体间距、碰撞或 braking clearance。

验证命令：

- `python3 tools/prepare_motion_world.py --output <run>/scene-preflight-02.sdf` 与 `python3 <run>/add_obstacles.py --world <run>/scene-preflight-02.sdf`：场景生成通过。
- `gz sdf -k <run>/scene-preflight-02.sdf`：`Valid.`；生成世界在固定 Jazzy/Harmonic 容器中实际启动。
- `bash <run>/run-container.sh`：容器退出码0；Xvfb经 `xdpyinfo` readiness 检查并定向 SIGUSR1 后启动。原始传感器、VINS、定位、mapper、EGO 与探针日志全部保存在 run 目录。
- `python3 <run>/evaluate_multi_geometry.py ...`：离线多几何评估成功；初次调用的相对路径哈希错误已修复，保留评估脚本和最终输出。

下一步需要健康定位及 EGO 真实活动目标下的多场景复测，再量化同运行跟踪误差、机体最小间距、源数据年龄、重规划期限和制动/故障退出时间；未冻结 `config/acceptance.json`，D/E 正式运行尚未开始。完整局限和哈希见[证据报告](../evidence/p2-map-multi-obstacle-geometry-20261020-247.json)。
