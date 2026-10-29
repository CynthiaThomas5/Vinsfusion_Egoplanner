# N07.11 #165：复用已验证的全机支架观测路线

## 执行模式与范围

Goal 完成模式；用户指定 N07。父目标保持 `in_progress`。本子项尝试在新冷启动取得 N05 released 五阶段正向准入，并在同一epoch继续EKF2无GNSS/真值辅助和无目标悬停验证。

## 已有基础与假设

#164 的1.8m俯仰返航路线在stage 5触发既有 accel-bias health limit，未到N05检查marker。#146在相同 `spawn=(-6.5,0,0.3,0,0,0)`、wall layout、车辆与N05配置上以 `n06_full_airframe_retreat_240_oblique_early_view` 完整完成12/12阶段，attached/released online/offline五阶段均通过，且无控制、目标或真值输入。这是当前最强的直接复用证据，但不能替代本轮fresh epoch gate。

假设：复用该12阶段路线能再次到达完整观测点并保持N05相关地图身份；本轮唯一主要变量为路线。判据：attached与released在线检查均接受且离线结果完全匹配；released五个entry phases均无unknown/occupied/outside拒绝，epoch/map identity连续，PX4维持DISARMED、bridge DISABLED至gate结束。门限、配置与scope不变。

## 计划与停止条件

新run `n07-20261024-165-01`，wall layout。marker watcher在 `n05-prescan-ready` 立即执行attached checker；随后释放支架，确认detach、模型不存在、新鲜landed，再执行released checker与离线回放。只有released gate满足上述判据，才在同一容器核对EKF2 EV fusion、无GNSS/真值辅助和唯一控制发布者，然后运行现有 no-goal hover probe 请求≥30仿真秒，观察真实降落与DISARMED。任何门禁拒绝或健康失效都fail-closed，完成安全收尾，不解锁。

## 结果

Run `n07-20261024-165-01` 取得完整12/12阶段、fresh同epoch/map_id的attached/released N05五阶段gate；二者 online/offline 一致接受，released最大unknown/occupied均为0。ground plane z=−0.35m，contact阶段完全地下单元排除36格，ASCENT/DESCENT各排除30格，HOLD无地下排除。PX4保持DISARMED到gate结束。

支架runner原样报告 `outcome=failed`／`localization changed or became invalid during physical scan`，但12/12阶段均记录完成，末条localization valid，fixture已脱架移除，fresh LandDetected=true，PX4 DISARMED，释放后门禁接受，N05 run summary `diagnostic_pass=true`。保留runner报错，不把它改称PASS。

随后同一epoch的无目标hover probe PASS：30.0仿真秒、墙钟39.004s、无navigation goal、时钟无回退、781/781 localization状态有效、306/306 PX4时间域状态有效、最终landed/disarmed。独立评估PASS。VINS悬停位置误差RMSE/p95/max为0.00347/0.00433/0.00493m，绝对yaw最大0.0324°；PX4 local保持位移最大0.0756m，Gazebo只读真值位移最大0.0764m。N07未定义误差数值阈值，这些是描述性报告。

ULog复核通过：参数 `EKF2_EV_CTRL=15`、`EKF2_GPS_CTRL=0`、`SIM_GZ_EN_ODOM=0`、`UXRCE_DDS_SYNCT=0`；54/54 airborne samples的EV position/yaw/velocity/height flags全true，GNSS/GPS flags全程false；最终PX4 DISARMED且landed。ROS graph的airborne与landed快照确认四个控制输入topic均仅由`uav_px4_bridge`发布，且无ROS truth topic/node。

启动期graph快照发生DDS端点名称发现延迟：四个控制topic各只有一个publisher，但初期node name未知。该endpoint的每topic GID与之后airborne/landed中确认的bridge publisher完全一致。为保留原始审计，同时避免把“未解析”错误归为“非bridge”，增加了只按一对一endpoint-GID连续性解析的离线判据；原始报告存为`ros-graph-audit-raw.json`，复核结果及方法写入`ros-graph-audit.json`。不忽略重复publisher，也不改运行控制或飞行健康门。

诊断复核代码：`tools/diagnostics/n07_ros_graph_evidence.py`、`capture_n07_ros_graph.py`、`reconcile_n07_ros_graph.py`；针对未知GID、GID不匹配、重复publisher与真值topic新增4项单元回归，`python3 -m unittest discover -s tools -p 'test_n07_ros_graph_evidence.py'` 4 passed。AST解析通过；N07离线评估PASS。完整结果和哈希见[#165报告](../evidence/n07-no-goal-hover-20261024-165.md)。固定项目运行容器已按流程停止，exit 0。

N07连续悬停计数为1/3。下一项#166用fresh cold start在相同镜像、配置、spawn与路线复现同一套准入和30秒无目标悬停；N07保持`in_progress`。
