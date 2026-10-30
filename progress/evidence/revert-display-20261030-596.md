# #596 撤回#595，恢复#594显示

结果：用户指定的最近一次显示变更已撤回。恢复青色历史层、深色背景、Orbit三维视角、默认局部膨胀碰撞层；恢复原始累计点云直接显示，地面不再被显示过滤。保留250级模型及#594缓存/身份隔离功能。

5个核心文件（observer、配置、RViz、只读记录器、ROS probe）SHA256与#594实际SITL运行`gui-20261030-115354-3418835/runtime-contract.json`逐项完全一致。删除仅#595引入的history_display.py及5项对应测试，并清除其已生成build/install副本；原始历史证据保留，不改写#595曾通过的历史结果，只注明不再启用。

验证：`bash tools/project.sh build ros`18包PASS；`bash tools/project.sh test`740单测、3套ROS集成PASS；`python3 tools/project_status.py`、`git diff --check`PASS。原始日志在`artifacts/runs/revert-display-20261030-596/`；[JSON](revert-display-20261030-596.json)记录核心匹配和日志哈希。

旧GUI确认正常落地上锁后`./start.sh stop`；`./start.sh`重开`gui-20261030-130612-3599388`，保持未武装，不执行新飞行。不把本轮构建/GUI启动算作新的SITL导航通过；#594原有运行证据仅在其版本范围内复用。

停止原因：请求撤回完成；无自动下一项，无提交/推送。GUI按查看需求保留，结束可`./start.sh stop`。缓存仍限当前会话，重启不恢复此前已探索地图。
