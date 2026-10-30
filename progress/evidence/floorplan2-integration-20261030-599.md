# #599 NavRL floorplan2可选场景接入

限定接入与一条16m任务 **PASS**。实际结果、源/运行文件SHA256见[JSON](floorplan2-integration-20261030-599.json)。不代表任意隔墙/全部房间/多次冷启动或原N17资格。

## 实现与来源

- `simulation/worlds/navrl/floorplan2_static.world`原字节来自NavRL commit `3725bcc2e7c1be4ecf1455d922299ae85042603a`的`ros1/uav_simulator/worlds/floorplan2/floorplan2_static.world`；源diff为空。上下游文件SHA256一致，子包MIT许可位于`dependencies/licenses/NavRL-uav_simulator-MIT.txt`；来源登记在sources.json。
- `scenes.json`与`scene_config.py`绑定几何/出生/目标；新增floorplan2_spawn.json与floorplan2_16m_goal.json。入口为`./start.sh start floorplan2`、`./start.sh fly floorplan2`，原room可用`./start.sh start room`。无场景参数复用活动场景，无活动会话默认room。显式切换前检查任务/落地终态；飞行中拒绝切换。
- `prepare_px4_vio_bootstrap_world.py`按选择合成场景，`resolve_sim_spawn.py`按同一scene默认出生；`project.sh mission`从实际run/world.json选择默认任务。保留显式GOAL_CONFIG/出生配置覆盖入口。
- 只复制静态模型/光照与场景设置，保留PX4/Harmonic系统、地理/重力与0.004s物理步长，250Hz相机IMU匹配。source的Classic材质脚本在运行合成中转换为现有项目PBR纹理，所有collision元素原样保留。没有引入额外ROS包、机器人、NavRL策略、控制、真值话题或预建PCD。

## 验证

| 层次 | 命令/检查 | 结果 |
|---|---|---|
| 构建 | `bash tools/project.sh build ros` | 18ROS包PASS |
| 单元/ROS | `bash tools/project.sh test` | 749单测、3套ROS集成PASS |
| 场景身份/合成 | test_scene_config.py | 来源/许可哈希、路径拒绝、出生/目标绑定、collision完全保留、PX4物理步长/PBR通过；显式room与旧合成输出字节一致 |
| 启动器 | test_start_launcher.py | 新增安全场景切换、未确认飞行拒绝、活动场景复用、未知scene不停止现有GUI等通过 |
| 实际GUI加载 | `./start.sh start floorplan2` | world.json为floorplan2，只有ground_plane/floorplan2静态模型；源哈希正确；相机图像/在线地图/VINS输出均实际观测 |
| 物理/传感器 | check_imu_physics.py | 0.004s×250Hz=1；保留原桥、安装和传感器配置 |
| 实际导航 | `bash tools/project.sh mission gui-20261030-150047-3805409` | 使用floorplan2_16m_goal.json；qualification全部7项PASS |
| 结构/格式 | `python3 tools/project_status.py`、`git diff --check` | PASS；不替代运行 |

任务从世界(-8,-8)到(+8,-8)，native0.1m/5s、独立0.30m/15°/3sim秒标准保持。实际独立驻留 **5.252sim秒**，最小真实目标位置误差 **0.04290m**，违规接触 **0**，正常落地上锁/控制关闭、核心身份和唯一发布者全部通过。

离线相机点轨迹范围：X=-7.993→8.052m，Y=-8.037→-5.860m，Z=1.109–1.327m。经过下侧隔墙X≈0.268m时，实际Y≈-5.952m；墙高2.5m，实际轨迹证明侧向绕墙约2.1m，非从墙顶越过。该诊断来自只读真值离线变换，未向在线控制回馈。

原始产物位于`artifacts/runs/gui-20261030-150047-3805409/`：world.json、spawn-pose.json、imu-physics-contract.json、qualification.json、safe-to-stop.json、scene-route-diagnostic.json；实际截图scene-gazebo.png/scene-rviz.png。日志位于`artifacts/runs/floorplan2-20261030-599-checks/`。

对比#597冻结输入，所有自维护运行Python、机体模型、定位配置、主要规划/桥接参数及原ego.sdf均保持；具体文件数和检查在JSON。旧room生成字节一致，由单元验证，不把它称为本轮新room飞行。

## 范围与收尾

一个场景/任务配置候选，一次实际飞行通过，无阈值放宽或算法调参。地图仍来自在线D435i深度；NavRL world只作为仿真物理场景。墙面外观使用本项目纹理，未复现NavRL原材质；单路线通过不保证EGO单终点穿越所有迷宫，复杂路线可能需分段目标。

停止原因：本轮有界接入完成。当前floorplan2 GUI `gui-20261030-150047-3805409`已正常落地上锁并保留供查看。查看后可`./start.sh stop`；无自动下一任务，无提交/推送。
