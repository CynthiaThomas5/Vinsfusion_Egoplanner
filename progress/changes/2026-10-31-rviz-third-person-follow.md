# RViz第三人称跟随

[对话](../../collaboration/dialogues/2026-10-31-rviz-third-person-follow.md)。

改动：mapping.rviz使用原生ThirdPersonFollower，距离6m、俯角0.6rad、后方yaw=pi；prepare_mapping_rviz绑定epoch跟随帧。现有可视化节点从有效VINS里程计发布显示专用位置+yaw TF，沿用身份和时间检查，避免roll/pitch带动镜头倾斜；package.xml声明tf2_ros_py依赖。更新包说明并加入ROS回归。

验证：独立clone执行project.sh build ros，18包通过；test_visualization_geometry.py四项PASS；tools/ros_tests/test_visualization_follow.py一项PASS（位移、航向、旧frame/无效定位拒绝）。GUI会话gui-20261031-011553-65331实际打开RViz，生成配置Target Frame正确，/tf真实回读到当前epoch跟随帧；OpenGL4.6，地图订阅正常。当前未解锁GUI按用户查看要求保留。

原始GUI日志：/tmp/d435i-vins-gui-standalone-20261030/artifacts/runs/gui-20261031-011553-65331。局限：未重新飞行；运动跟随用ROS回调测试验证，当前GUI为地面实时TF验证。无控制逻辑或地图算法变更，无提交推送。
