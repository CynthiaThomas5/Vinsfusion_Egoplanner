# #598 NavRL场景评估

用户提供https://github.com/Zhefan-Xu/NavRL/tree/main/ros1/uav_simulator/worlds，要求查看适用场景与直接切换可能性。本轮按只读选型处理，优先推荐floorplan2_static，floorplan4作为后续复杂场景；原ROS1 launch不直接替代本项目ROS2/Harmonic/PX4。检查源码/几何、固定容器SDF解析，并生成离线平面预览；没有改运行场景或新增飞行。实现建议与边界见progress/evidence/navrl-worlds-review-20261030-598.md，摘要不是测试通过证据。
