# #598 NavRL world只读选型评估

用户要求查看NavRL的ros1/uav_simulator/worlds，推荐适合EGO的room并判断能否直接切换。本轮只读评估完成，**未切换世界、未飞行**。来源固定于NavRL commit `3725bcc2e7c1be4ecf1455d922299ae85042603a`；[JSON](navrl-worlds-review-20261030-598.json)保存源SHA256/范围/判定。

优先推荐floorplan2/floorplan2_static.world：约20.15×20.15m碰撞边界、2.5m高墙，13个box碰撞体构成外围和内部隔墙；全部内嵌静态box，无外部mesh/include/sensor/plugin。适合作为当前20×20柱群后的隔墙/拐弯场景。floorplan4_static约20.15×20.15m，29个box碰撞体，迷宫更复杂，适合后续分段目标；EGO局部规划不能据此保证单一终点穿越任意复杂迷宫。

其它：floorplan1约40×20m需要重新核对odom地图边界；corridor为长走廊+箱体适合长距离重复绕障，但范围与障碍位置要检查；room_static外墙约14×14m，不能原样容纳当前水平直线16m，并含未显式static的人物mesh，不是最省事的纯静态迁移。building多层和tunnel mesh、dynamic场景不作为当前静态单D435i范围的第一项。

兼容性：floorplan2/4在固定容器执行`gz sdf -k`均返回`Valid.`/退出0，**仅是SDF解析，不是Harmonic加载/传感器/飞行通过**。NavRL ROS1入口使用gazebo_ros/URDF/其自身控制与真值话题；接入时只迁场景几何，保持现有250级模型/D435i/VINS/EGO/唯一PX4桥与Harmonic系统。原world的0.001s ODE物理参数不能覆盖本项目0.004s/250Hz IMU约定；Gazebo Classic脚本材质需转为Harmonic可渲染材质并检查VINS纹理。当前prepare_px4_vio_bootstrap_world.py硬编码ego.sdf，需要增加显式场景选择、来源记录，再校核出生点/目标/地图范围。旧16m任务不自动适用于新隔墙布局。

已按world内box碰撞体计算Z=1.2m截面平面图（不是Gazebo截图，room人物mesh未画）：`artifacts/runs/navrl-worlds-20261030-598-review/static-world-layouts.png`；详细投影边界在同目录geometry-summary.json。这里只读下载至/tmp，未将上游模型迁入运行源；根MIT及uav_simulator子包MIT已查，实际迁入仍须按模型资产逐项记录来源/许可。

停止原因：选型与兼容性评估完成。建议下一项为floorplan2的几何接入和可选world入口，保留旧room，再做真实Harmonic/D435i/VINS/导航验证；未自动开始该实施任务。
