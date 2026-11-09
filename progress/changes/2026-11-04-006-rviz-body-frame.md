# RViz统一机体参考点与轴

对话：[摘要](../../collaboration/dialogues/2026-11-04-006-rviz-body-frame.md)。

修改hardware_live_rviz.py与replay_hw10_rviz.py，共用既有imu_to_body_flu完整安装变换，VINS姿态与位置/轨迹同时从IMU换到机体参考点；PX4保持既有NED/FRD→ENU/FLU显示。canonical rig未测时仅显示使用既有用户接受近似，未改rig状态或原始ROS定位/EV数据。RViz图例标注BODY FLU/近似安装；世界帧未配准，分区+3m仍明确标注，非位置误差。当前只读47s记录回放保留，Nano/飞控不启动。

验证：主机Humble下python3 tools/test_hardware_live_view.py通过原3旋转断言及新增非零杆臂/前左上轴4项解析检查；py_compile通过。实际重启唯一回放节点与RViz，各Path发布者1，Pose回读实测水平差0.002676°，记录artifacts/runs/hw10-20261104-01/body-display-check.json；这仅证明显示轴统一，不是新的安装/定位质量资格。python3 tools/project_status.py与git diff --check通过。

停止原因：显示修改完成；保留RViz/回放供查看。原约2°完整姿态残差、板上近似安装、HW10未完成事实保持。下一步仍以CURRENT的HW10.3为准，未做算法实验/飞行，未提交/推送。
