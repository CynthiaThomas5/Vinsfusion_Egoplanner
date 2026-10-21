# 房间穿越续测与故障降落终态修复

对应[对话摘要](../../collaboration/dialogues/2026-10-21-048-ego-room-crossing-yaw-check.md)、[运行证据](../evidence/ego-room-crossing-yaw-check-20261021-07.json)。

repair07采用已隔离构建的LM VINS与0035 EGO候选，保留纹理实验、0.5m/s上升、40m地图、0.5m膨胀和原健康门限。40秒只读前检通过，连续稳定39.6秒、RTF约0.578、优化odom最大接收间隔0.143秒。实际进入ACTIVE，16米目标被接受；12条样条、2208条匹配READY，首条yaw与目标相差3.56e-9 rad。本次初始航向边界验证成立，不扩大为动态重规划导数或短样条终端通过。

最终导航估计[4.059,1.319,0.909]m，距目标11.99m，未到达。按同一flight probe墙钟：55.14秒桥因位置对齐差0.15013m先进入LANDING；56.03秒优化odom记录0.434秒接收间隔；导航随后pose_stale取消；58.92秒定位normalized_cost锁定。不能将后出现的pose_stale当作首次降落原因。PX4日志和最终桥armed=false/landed=true确认落地上锁；脚本landed_and_disarmed=false，因为桥phase仍LANDING，正式终态条件未满足。

源码变更：`src/own/uav_px4_bridge/uav_px4_bridge/px4_bridge_node.py`中，持续bridge/alignment故障只在非LANDING阶段调用disable；LANDING继续执行既有supervisor.step，允许观察落地上锁并转LANDED。故障仍锁定，不重启控制。新增`tools/test_px4_bridge_fault_landing.py`直接调用实际timer，分别验证两种故障下只发一次land、不发布Offboard、故障保留及完成终态。

验证命令（容器中source Jazzy、#297依赖及own install）：`python3 tools/test_px4_bridge_fault_landing.py` 1项含两种故障PASS；`python3 tools/test_px4_bridge_control.py` 11项PASS。colcon隔离构建uav_px4_bridge通过（1包，2.03秒），日志`artifacts/runs/ego-room-crossing-repair-20261021-07/bridge-fix-build.log`。修复未热替换进repair07，不声称新增SITL通过；无实机／回放验收。

近似离线诊断：固定frame_yaw_offset=0.036127rad（约2.07°），548组按源时间插值配对，保留该偏角最大位置差约0.144m；仅作诊断去掉偏角时最大约0.0096m。只使用VINS与PX4估计，不使用真值；使用heading近似杆臂、缺少roll/pitch且VINS打印精度有限，不能直接修改为零偏角。线索指向启动时EKF航向未收敛就固定对齐。下一步完整录制同时刻姿态／里程计、查对齐捕获时刻，设计静止稳定窗口后固定的验证；保持0.15m门限。

Gazebo和RViz保持打开，任务已结束且PX4上锁；地图可能因定位锁定被清空。未升级任何里程碑。结构检查只说明结构一致；`git diff --check`通过。
