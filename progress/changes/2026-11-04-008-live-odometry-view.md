# 实时VINS机体里程计显示

对话：[摘要](../../collaboration/dialogues/2026-11-04-008-live-odometry-view.md)。

实际行为：停止回放，Nano /home/jetson/D435i-VINS-EGO-ROS2-hardware执行bash tools/hardware.sh start perception --run-id hardware-live-20261104-01；PC source /opt/ros/humble/setup.bash后执行python3 tools/diagnostics/hardware_live_rviz.py --live --vins-only --run-path /home/jetson/D435i-VINS-EGO-ROS2-hardware/artifacts/runs/hardware-live-20261104-01。保留唯一RViz。无Agent/EV/PX4参数/模式/控制/武装/规划。

代码：新增--live只tail新产生的health和原生VINS Pose行，0.1s tail检测。核对src/vendor/vins_fusion/vins/src/utility/visualization.cpp:213打印的确是刚发布优化Odometry的相同位置/姿态；解析wxyz后转换为xyzw，保持源采样顺序、有限值及健康有效性约束，完整安装/杆臂转换仍共用现有实现。不改VINS算法/原始消息，不用重复旧pose伪造新数据。显示开始前先预热PC节点，不在Nano加ROS参与者。顺带修正旧通用字符串替换意外将PX4显示写入VINS显示TF的分支；本次vins-only未走该分支。

验证：Humble下python3 tools/test_hardware_live_view.py新增原生日志有效/无效/非有限/零四元数解析检查通过，既有坐标/机体参考点/Odometry-TF检查通过；py_compile通过。真实12s窗口76条显示Odometry，约6.2516Hz，发布者1；epoch e3e5697efb504a3e9fd1806820997f93、TRACKING/点数持续增长，证据artifacts/runs/hardware-live-20261104-01。尾随文件建立前的缺文件提示是预热等待，随后正常追踪。结构/diff检查通过。

停止原因：用户实时显示请求已交付，按要求保留相机/VINS/localization/PC视图和RViz；PX4融合仍停止。终止本会话的PID/stop/rmem恢复方式在CURRENT。未验证长时间/动态精度，HW10原时序等缺口保留，未做新飞行资格或推送。
