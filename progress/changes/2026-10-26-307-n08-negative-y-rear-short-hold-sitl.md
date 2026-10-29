# #307 N08 后向短保持profile SITL结果

- 新冷启动运行 `n08_overhead_free_sector_negative_y_rear_short_hold`；17阶段中完成14阶段，rear view与yaw0回中完成，回中后的fixture下降阶段 normalized cost 超过1.0，最终1.0098607。
- fixture cleanup确认已回初始pose、detached、Gazebo模型移除，PX4 LandDetector landed。独立ROS只读topic读回 bridge DISABLED、控制关闭、PX4 disarmed/landed；`project.sh stop`及容器exit均为0。没有释放后N05 admission、N08 mission、goal、enable或飞行。
- 初始N05 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`拒绝；失败后的只读snapshot helper因缺少optimized odometry超时，作为独立次级故障留档，不冒充准入结果。
- 由于#248已有慢下降同高度附近仍失败证据，#308不再只改下降速度；先用#305同身份存档地图审计球形查询与N05实际碰撞几何查询的差异，原unknown／margin／tracking／连续性阈值保持。

证据：[运行报告](../evidence/n08-negative-y-rear-short-hold-refusal-20261026-307.md)、[机器摘要](../evidence/n08-negative-y-rear-short-hold-refusal-20261026-307.json)。profile静态准备见[#307静态报告](../evidence/n08-negative-y-rear-short-hold-profile-20261026-307.md)。
