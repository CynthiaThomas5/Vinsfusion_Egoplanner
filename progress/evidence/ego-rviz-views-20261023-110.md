# #110 EGO 导航视图验证

结论：可选 GUI 显示功能通过本轮构建、合成 ROS 消息与 RViz 配置加载验证。不代表飞行、N06 空间准入或目标机器 GPU 渲染验收。

- 固定镜像 `d435i-vins:dev`（`sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`）内 `colcon build --packages-select uav_navigation uav_px4_bridge --parallel-workers 1`：2 包通过。
- `python3 -m unittest tools.test_visualization_geometry tools.test_vio_ego_bringup_config -v`：13 项通过，包括实际 B 样条几何、样本限制和畸形输入。
- `tools/probe_navigation_visualization.py`：独立 ROS_DOMAIN_ID=183、无网络容器，曲线／历史／目标及调试坐标副本、其他 epoch 拒绝、取消及迟到轨迹、定位失效清除、仅显示发布者五组通过。
- Xvfb + 软件 OpenGL 实际启动 `rviz2 -d <run>/mapping.rviz`：进程存活、无插件加载错误、会话 Fixed Frame 正确、调试组默认关闭。
- Python 非写入语法编译、`bash -n tools/sim_runtime.sh` 通过。项目结构与 diff 检查见改动记录。

原始记录：`artifacts/runs/rviz-20261023-099/`。此 run id 中的 099 不对应 N06 的 #099 记录；本项任务编号为 #110。[机器可读结果与源码／日志哈希](ego-rviz-views-20261023-110.json)。

验证没有启动 Gazebo/PX4 或发布飞行设定点，没有重启已有 N06 会话。红色曲线来自真实 B 样条采样，青色路径为 VINS 估计；包络只是 provisional 显示。真实传感器飞行显示效果及目标 GPU 性能仍需在后续已授权会话中观察。
