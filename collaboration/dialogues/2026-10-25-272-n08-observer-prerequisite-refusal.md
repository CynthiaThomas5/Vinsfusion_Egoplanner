#272 对话摘要

- 保留用户返航要求：原地转头约180°，确认机头方向后沿机头前向由EGO重新规划；不倒飞。本轮未飞行。
- #272 新cold start 初始raw-map因地面occupied证据不足拒绝；支架扫描可运行，但10/15阶段VINS `accel_bias_norm_exceeded`，最大0.15522m/s²，高于原0.15门限，normalized cost为0.572。N05 gate与健康门未放宽。
- 支架已脱离并由Gazebo确认删除。直接ROS读回bridge DISABLED/control0/armed=false/landed=true，PX4 disarmed，LandDetector landed/at_rest；stop exit0、容器exit0。
- 没有释放后准入、preflight、runner、enable或EGO目标，所以 #272 的PointCloud2 observer负载假设仍未测试。
- #273将对同一固定支架profile做一次新epoch判别；再次同因失败后停止重复扫描并分析轨迹段；成功则在同一fresh run继续目标observer实验。
