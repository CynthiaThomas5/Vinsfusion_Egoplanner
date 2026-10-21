# 修改与验证记录

- 任务 ID／日期：#042 / 2026-10-21
- 对话摘要：[任务摘要](../../collaboration/dialogues/2026-10-21-042-ego-world-import.md)
- 修改文件：新增 simulation/worlds/ego.sdf、dependencies/patches/simulation/0001-ego-harmonic-static-world.patch 及说明；修改 tools/prepare_px4_vio_bootstrap_world.py、对应测试、dependencies/sources.json、README、simulation/README、src/own/uav_sim/README、补丁索引和 CURRENT；新增轻量证据。模型、外参、飞控及健康参数未改。
- 行为变化：默认 PX4/VIO 场景生成器由单标定墙切换到用户指定的约 20×20 m 围墙／19 根柱子环境。沿用启动器 world ID vio_initialization；保留 PX4 基础物理和传感器系统，不复制上游控制器或地图。sensors.launch.py 仍是独立标定入口。
- 来源：固定提交 fdbe8743897b04dd0b8d412f60592d4299b69ef3；上游文件哈希 92f04e5674bf46fbc7c8fe4fe9cc6b76004305e2877a176c404083fa752250a3。记录保存状态到静态位姿、16 个碰撞修复及材质／Harmonic 变更；原版和完整差异在导入报告及补丁，许可 NOT_DECLARED，不擅自改标。当前目标／补丁／脚本哈希见证据。
- 验证类型：静态、单元、Gazebo 场景／原始传感器 smoke。不是 PX4 固件联调、VINS、地图、规划或飞行验收。
- 命令／结果：`python3 tools/test_px4_vio_bootstrap_world.py` 3项通过；`python3 tools/test_sim_geometry.py` 3项通过；`python3 tools/test_motion_tools.py` 3项通过；运行脚本 bash -n 与 Python 编译检查通过；最终两份 `gz sdf -k` 均 Valid；原文件按补丁重建与目标逐字节一致。
- 运行结果：固定 d435i-vins:dev 镜像中加载生成世界并生成 x500_d435i，15秒采样收到左目／RGB／深度各342帧，IMU 2255条，静置加速度范数约9.8。最终日志无 custom plugin 加载失败；没有启动 PX4 固件、桥、控制或目标节点，容器已退出。前两次 smoke 保留，因早期材质／检查脚本插件路径差异不代替最终系统加载证据。
- 证据：[报告](../evidence/ego-world-import-20261021-01.json)；原版、来源清单、生成世界、检查脚本和日志保存在 artifacts/runs/ego-world-import-20261021-01，报告含哈希。`python3 tools/project_status.py` 和 `git diff --check` 通过。
- 未验证与 PROVISIONAL：砖纹没有保留为纹理；新房间内 VINS 特征／误差、持续地图、EGO 净空、飞行均待验证。上游许可未声明。历史阶段通过属于此前场景；本轮不升级任何 P0–P6、S1–S6 或 A–H 状态。
- 下一步：按用户指导，在新房间先验证静置传感器与 VINS／地图，再推进 Goal v2 的稳定飞行基线；不运行旧 artifact 的单墙预览冒充新默认环境。
