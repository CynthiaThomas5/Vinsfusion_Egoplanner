# N10.3/#436：0060后的正常导航校准

完成一次正常16m导航、20sim s保持和正常降落；action succeeded、禁止接触0、PX4 landed/disarmed/control-disabled及终态零控制已独立确认。容器在确认物理安全后受控停止，exited0，未用紧急disarm。按#434没有故障注入或故障后校准。N10.3仍未通过。

严格收尾未通过：postflight探针仍收到同goal/epoch的READY参考。原safe-to-stop=false保留，normal-controlled-stop.json单独记录物理末态与协议失败；不将其倒算成严格终态通过。#437已修正常控制结束后的参考清理，尚缺现场回归。

## 参考点复核与有效结论

逐步真值0.004s完整，禁止接触0的独立证据有效。初版到达/定位/净空/跟踪报告对OdometryPublisher参考点的解释不一致，其数值不得直接用于最终冻结。robot_base_frame仅为消息标签；Gazebo源码读取model worldPose并应用显式offset；本模型无offset。地面raw truth z=-0.013m也符合model origin，而不是IMU。包络配置明确以D435i IMU为原点；由固定SDF得到model→IMU=[0.12,0,0.32]m。#403把该包络当base_link使用的说明也需更正；这不是新飞行证明。

只读复算保留所有原始文件：corrected采样全机最小净空0.438014m，raw位置误差p95/max=0.116039/0.137796m。运动RPE10平移p95=0.060495m（原草案0.05m仍未过）；保持RPE10平移p95=0.039139m，保持速度误差p95=0.015137m/s（草案0.01仍未过）。这些是参考点审计结果，尚未替代统一生产评估器或建立连续区间保证；不抬阈值、不删除门限。

上游来源：https://github.com/gazebosim/gz-sim/blob/gz-sim8/src/systems/odometry_publisher/OdometryPublisher.cc 。具体本地SDF、输入哈希与复算结果见run/n10-truth-reference-audit.json。

## 复用证据

方箱插入ACK、前后同身份raw/inflated数组已保存，snapshot pair=SUPPORTED；已观察面最大中心误差原报告0.064281m，但世界坐标对齐在统一参考后仍需复算。重规划分析已移除对可选point query文件的硬依赖，直接复用数组与归档。资源180个样本、VINS队列2337个样本，acc/gyr/feature高水位30/30/1，不能将高水位当容量保证或正式N16。

## 运行与版本

run：artifacts/runs/n10-20261028-436-normal-map-halo-calibration。准备工具：artifacts/n10-prepared/n10-20261028-436-normal-map-halo-calibration。prelaunch冻结runtime=94c852e3bdeeaaab6cfe823300155c20f27f9f9ccfe3c750f579a48464d8a3ef；实际飞行使用的记录器与navigation源码快照保存在flight-source-snapshots，回建版本与目标前SHA完全匹配。后续#437修复没有追溯修改本次飞行源码身份。

验证和局限：动作/SITL为本次实际证据；离线复算不是新飞行。完整ROS/PX4干净重建、重建回归及最终冻结仍未做。下一项#438先统一真值、包络和误差参考、复算现有归档并完成预算依据，再安排受变更影响的正常回归；不重启故障校准。
