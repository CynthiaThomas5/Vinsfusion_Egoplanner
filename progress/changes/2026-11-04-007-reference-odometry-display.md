# 对照Shepherd010/UAV里程计显示

对话：[摘要](../../collaboration/dialogues/2026-11-04-007-reference-odometry-display.md)。

参考基准：`git@github.com:Shepherd010/UAV.git` commit `7b8d33c729b7895cf1cb80bbe15a4597ea20df14`，只读检出/tmp/shepherd-uav-reference-20261104；未运行其脚本/构建/控制，不迁入源码。原路径与SHA记录artifacts/runs/hw10-20261104-01/reference-repo-audit.json；只参考功能/配置行为，未将该仓库代码或许可外推为本项目依赖。

实际核对：resource/uav_flight_deck.rviz的Odometry Shape=Axes/Keep=1、轴长0.45/radius0.045、Path Billboards、黑底、固定odom和Orbit跟随base_link；config/shared/config.yaml生效颜色255;80;170/线宽0.06；odom.cc确认Odometry父odom/子base_link与动态TF。其机体点并非激光轴，当前RViz资源也没有单独PX4位姿对照。雷达点云与导航控制面板是独立功能，不由这次里程计显示迁入。

实现：自有hardware_live_rviz.py/replay_hw10_rviz.py对已换算机体点增加仅显示的/hardware_view/vins_odom和hardware_display→hardware_view/vins_body TF；使用原有完整安装/杆臂换算。config/rviz/hardware_live.rviz采用同款三色轴、粉色轨迹、黑底、固定世界/跟随机体Orbit(Distance12/Pitch0.72/Yaw3.9)，PX4作为默认关闭的可选分区对照(+3m)，状态标注明确回放。只发布显示Odometry，不替换/localization/imu_odom、不改EV或PX4变换。

显示适配：现有录制不含VINS twist/covariance，twist与其covariance用NaN表未知；Humble RViz源码validateFloats要求pose covariance有限，即使关闭协方差绘图也如此。显示适配的pose covariance填0占位，并明确禁用Covariance显示，不能用于不确定度/导航输入。位置/姿态为真实记录的机体换算结果，没有伪造运动/地图。实际显示固定帧/TF使用隔离名称，和参考的odom/base_link语义对应，不隐式接管在线TF。

验证：python3 tools/test_hardware_live_view.py通过旋转3项、机体杆臂/三轴4项及新增Odometry/TF一致性/有限pose covariance/未知twist断言；py_compile通过。主机Humble实际运行记录回放和唯一RViz，Odometry发布1/RViz+核查订阅2，TF查询成功；结果reference-style-check.json，截图rviz-reference-style.png视觉核对坐标轴/布局，Global Status OK。实际读取RViz Humble官方odometry_display.cpp核实消息浮点验证。结构/diff检查通过，不重跑SITL/硬件采集。

停止原因：显示请求完成，保留RViz与PC回放供用户查看；Nano/飞控仍停止，无控制/参数变化。HW10动态/时序/控制资格均未新增。画面是原静态47s记录，不会有参考雷达房间点云或实际移动长轨迹。下一任务仍为CURRENT的HW10.3。
