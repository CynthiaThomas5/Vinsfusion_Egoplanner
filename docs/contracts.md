# 接口、坐标与控制契约

## 唯一控制所有者

uav_px4_bridge独占PX4设定点、OffboardControlMode与模式协调。VINS、定位/建图适配、导航规划、可视化和评估不得新增PX4控制发布者。外部算法通过导航action请求任务，使用地图/关键帧/定位接口读取状态。

默认链路只用单D435i双目、相机IMU、深度和CameraInfo。模拟器加载场景SDF；在线地图由实际深度与源时刻VINS位姿生成，不接收完整世界占据地图。只读真值记录和独立评估位于debug_truth范围，不回馈定位、规划或飞控。

## 坐标和时间

- VINS body是相机IMU，外参来自唯一simulation模型和config模板。定位适配输出 `odom_<epoch>`，优化IMU位姿稳定话题为 `/localization/optimized_imu_odom`。
- 公共NavigateToPose的PoseStamped目标为当前epoch局部ENU坐标中的绝对位姿。运行配置里的相对offset由任务runner按起飞后观测原点转换，不是Gazebo世界坐标。
- bridge处理ENU/NED、FLU/FRD、局部原点/yaw及传感器杆臂；调用方不再重复补偿。实际IMU参考点和模型安装关系须与SDF一致。
- 图像/IMU/位姿保留原始source stamp；深度在对应时间的优化位姿之间插值，不拿最新位姿替代。ROS模拟时间、PX4 HRT和墙钟接收时间分别记录。
- 固定scale=1起飞前SE(3)只用于独立评估，不发布回在线TF。到达驻留按连续仿真源时间计，不给缺样插值驻留信用，不拼接epoch。

## 导航与取消

`/navigation/navigate_to_pose` 类型为 `uav_interfaces/action/NavigateToPose`。目标包含当前frame位姿、位置/yaw容差、驻留、timeout及模式等，以消息定义为准。反馈和终态给出结果与明确原因；调用方需要处理拒绝、取消和失败。

外部程序使用标准action取消。内部 `/navigation/ego_goal` 与 `/navigation/trajectory_cancel` 由导航主管协调goal_id/epoch，不作为绕过主管的第二控制入口。旧目标、旧轨迹和迟到结果不能接管新任务。

`/uav_px4_bridge/enable_offboard` 类型为 `uav_interfaces/srv/EnableOffboard`。`enable:false`显式请求退出自主控制并由桥协调正常降落；观察实际landed/disarmed/control disabled后再停止容器。默认任务自动结束并落地上锁。用户排除的故障专项未因此取得资格。

## 地图与关键帧

| 接口 | 契约 |
| --- | --- |
| `/mapping/status`、`/mapping/get_map_status` | MapStatus与同epoch查询，提供epoch/map_id、输入/融合计数、时间和标定/输入配置SHA；旧expected_epoch明确拒绝 |
| `/mapping/get_occupancy_snapshot` | 只读raw/inflated同快照数组，绑定expected_epoch/map_id；保留origin/resolution/shape/data_order及源/融合/快照stamp |
| `/mapping/rgbd_keyframes` | RGBDKeyframe完整图像、CameraInfo、各自源时刻位姿、epoch/map_id与标定SHA；输入配置身份由同map的MapStatus绑定 |
| `/localization/status` | 定位epoch/状态/诊断；当前程序不以项目自设残差、bias、求解时长或valid/TRACKING质量状态阻断正常任务 |

raw占据码为unknown=-1、free=0、occupied=100；inflated mask单独表示膨胀占据。当前official_ego按inflated occupied判碰撞，未知不会被伪装成已观测free。无效深度不合成free ray；旧身份、越界或服务失败不当作普通unknown。

RGB-D持久化使用ROS原生MCAP，回读程序直接反序列化CDR，保留图像数据哈希、K、pose/source stamp/epoch/map和配置身份。占据数组可用capture_live_occupancy_snapshot保存和回读。两种回读证明持久数据可用，不声明跨重启重定位。

## 验收与范围

正常任务独立到达0.30m/15度/连续3sim秒、零违规接触和正常终态保持。被用户取消或转为诊断的RPE/地图表面/净空/质量/资源数值不恢复为运行门。源身份、时间完整性、唯一控制和PX4/EGO原生机制继续生效。

实际功能资格按冻结版本、场景与证据绑定；当前最终报告分别说明构建、回放、GUI SITL与迁移验证。语义/信念/探索仅预留接口，实机及故障专项不在当前完成范围。早期条款保留于 [历史接口契约](history/contracts-before-n17-20261029.txt)，与当前策略冲突的旧门禁不适用于默认运行。
