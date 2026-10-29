# N10.3/#428 综合故障诊断：已复现，未完成安全收尾

## 主要结论

本次直接FAIL：真实rotor_0先碰unit_cylinder_4，随后机体翻滚，再出现propagated_invalid_quaternion和EGO timeout。首次非地面接触源戳132.168秒；四元数故障133.808秒，接触早1.640仿真秒，故障前已记录5个非地面接触事件。不能将适配器完整性检查作为初次碰撞原因，更不能通过归一化/放宽门限称作碰撞修复。

故障四元数xyzw=[-0.5416312483,-0.0721393516,0.8084716729,0.2680683139]，范数1.0119563044。该时刻最近IMU gyro=[0.2654,9.3670,31.1827] rad/s。真值记录在此之前已出现翻滚/大速度。VINS fastPredictIMU使用未显式归一化的小角度deltaQ乘积，可能在大角速度时累积范数偏离，但尚未用完整原始输入逐步重放证明，且该假设不能解释更早的碰柱。

同一PX4本地NED参考点，在首次接触前1秒／接触时位置setpoint对local-position误差分别0.43650／0.45410m。两边查询均无外推，setpoint括区40ms，local样本精确匹配。它是跟踪修复的重要线索；不等于VIO对真值误差，也不证明参考机体轨迹本身安全。后续必须核对接触前地图/参考净空与跟踪误差，速度前馈缺失仍为单变量修复候选。

## 故障末态

#426有限LAND重试确实发生：full-flight probe收到了三条command21 ACCEPTED ACK，PX4时间分别134.352、138.444、139.380秒。随后PX4仍为armed/failsafe DESCEND、local XY invalid、EV pos/yaw fusion false、land_detected=false；桥接LANDING/control enabled。ACK accepted不等于落地成功，#426不足以解决该物理翻覆后的原生终态。最后有效r02六秒读回无terminal；safe-to-stop=false。没有再次发送紧急disarm，没有停止活动控制栈。

truth/contact仅收到身份核验后的SIGINT以导出故障前后部分记录，报告明确signal_requested且safe_session_terminal_observed=false。full-flight只读probe也以信号写出208.374秒观察和ACK记录；alignment/bridge/resource/sensor观察与SITL控制栈继续保留。不能把部分报告当完整终态证据。

已提出当前#428一次紧急disarm与受控停止的新授权请求；#391的一次性授权已消费，不复用。等待新明确授权或原生安全终态，未把等候视作授权。未经收尾不再启动新飞行或改运行源码。

## 实施与身份

沿用#415速度0.4m/s、yaw cap0.10、compact trace ROI、航迹、20秒诊断hold、障碍几何及触发。使用#426修复后源码，并将runner设为expected native depth timeout时保留桥接故障路径。只读probe新增稳定终态后退出及可中断导出，ACK补记录接收时ROS clock；控制发布行为未改。

本次runtime SHA为1951ec60e96459618f4a882bc1a43cfb3bb1751170a7fa31071307bf116c4db3。prelaunch/tool-freeze均重新生成。第一次prelaunch调用未source ROS，第二次缺DDS profile导致CLI图查询失败；均在目标前，修正调用环境后同一会话prelaunch通过，未通过重启重飞消除问题。

继承的障碍injector仍读取#414协议，报告的baseline标签陈旧。已核对其injection对象与#428逐字段相同；inputs唯一差异为planner路径（#414为verbose trace，#428实际launch固定compact trace配置）。当前planner由新launch/prelaunch独立核对。该来源/标签问题如实保留，不将旧baseline充作当前身份；后续工具需指向对应run的协议。未在活动运行中修改它。

## 验证、产物与下一步

- Python语法和shell bash -n通过，13项observer/terminal定向测试通过。
- 固定ROS镜像内对新probe发SIGINT的无飞行smoke exit0，验证部分报告落盘且无terminal误判。
- flight结果FAIL；safe-to-stop=false。未完成安全终态，不能停止控制栈或标N10通过。
- 可复算脚本：artifacts/runs/n10-20261028-428-integrated-fault-diagnostic/analyze_fault_sequence.py；输出n10-fault-sequence-analysis.json含输入SHA、原始故障、接触先后与ACK。该分析脚本已执行成功。

唯一当前子项：#428安全收尾；完成后保存剩余观察器与sensor MCAP，继续定位首次接触前的误差来源，按证据实施下一项修复。父N10保持in_progress，N15/N16无正式次数增加。

对话摘要：../../collaboration/dialogues/2026-10-28-428-n10-integrated-fault-diagnostic.md
