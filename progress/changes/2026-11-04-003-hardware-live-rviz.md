# 真实硬件只读RViz

对话：[摘要](../../collaboration/dialogues/2026-11-04-003-hardware-live-rviz.md)。

新增tools/diagnostics/hardware_live_rviz.py与config/rviz/hardware_live.rviz：工作站Humble读取Nano既有1Hz定位日志，发布仅显示用途的Path/Pose/MarkerArray；epoch变化清轨迹，健康失效/日志中断提示失效。USB通过已有轻量串口relay传输，PC解码，不在Nano新增ROS订阅。relay新增显式可选GCS discovery heartbeat，无参数/EV/模式/武装指令。两局部坐标未配准，PX4显示偏置+3m且明确标注，不可比较位置误差。

当前会话Nano /home/jetson/D435i-VINS-EGO-ROS2-hardware：`bash tools/hardware.sh start perception --run-id hw09-live-view-20261104`；PC `source /opt/ros/humble/setup.bash; python3 tools/diagnostics/hardware_live_rviz.py`与`rviz2 -d config/rviz/hardware_live.rviz`。脚本当前绑定此run，非通用控制入口。

串口最初无数据；用户确认供电并重新插拔后，重新连接得到PX4姿态与ESTIMATOR_STATUS flags129。本地位置无有效标志，仅显示姿态，不显示有效位置路径，EV融合未验证。VINS TRACKING、轨迹持续增长。证据artifacts/runs/hw09-live-view-20261104：verified-status.json、view-node.txt、px4-pose-sample.yaml、日志和PID。RViz真实窗口存在、Path发布1/订阅1，PX4 Pose回读通过；节点输出仅/hardware_view等显示/ROS诊断话题，无fmu/control。3个显示坐标数学断言、2串口分帧回归、py_compile通过，结构/diff检查通过。

用户查看期间保留Nano相机/VINS/localization、PC视图/串口与RViz，无规划目标/桥/真实EV控制/参数修改。停止原因：显示已交付，PX4融合位置因当前估计无效未可用。结束查看时kill -INT本run view.pid与rviz.pid，再在Nano执行bash tools/hardware.sh stop，确认所属进程退出/rmem恢复；当前rmem8388608为活动会话需要。唯一下一步：用户观察慢速手持轨迹；真实融合需后续HW08安装/HW10，不凭轨迹外观标通过。
