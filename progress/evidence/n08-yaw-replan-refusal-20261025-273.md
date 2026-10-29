#273：起飞与前向制动通过，180°转向重规划被拒

## 本轮结论

N08仍未通过。#273解决了#271的起飞阶段定位状态回执空窗未复现问题，也完成了一次有效的前向制动测量；但在返航前的定点180°转向过程中被watchdog安全中止。没有完成转向确认、转向后地图检查、机头前向EGO返航或回到N05 home pad。

## 命令边界

普通EGO目标到达并停止后即结束，不自动返航。#273是专用往返验收编排：runner先发送去程`NavigateToPose`并收到`succeeded`，再单独发送180°转向目标；只有转向成功且新地图／返航走廊通过后，才会再单独发送home目标。本轮在第二个（转向）action中止，因此返航action从未发送。这个试验编排不改变普通单目标的命令语义。

## 入口、起飞和前向制动

本轮为fresh epoch `97f57872b7de4418815b3562c02cd0fa`，manifest使用`config/components/mapping/n08_low_speed_trial.json`，配置hash为`f8216372bdeda44f02b891381adbdb806c8866f252698dda87c29d14a6e29cce`（逐轴`max_vel=0.10 m/s`、`max_acc=0.25 m/s²`）。起飞前销毁了未使用的`/grid_map/occupancy` PointCloud2订阅者（1个移除、剩余0个）。

初始地面raw-map证书仍按原门限拒绝，原因是`ground_plane_insufficient_raw_occupied_voxels`；之后`n08_far_small_pitch_view`支架扫描完成15/15阶段。扫描器保留泛化的`localization changed or became invalid during physical scan`警告，但同epoch/map_id的post-release及mission current-area在线／离线检查通过，`diagnostic_pass=true`。40.0025秒只读preflight通过；optimized-odometry最大回执间隔0.1296秒，overguard计数0。起飞前raw-map capsule与home-pad证书通过。

起飞稳定门通过：在等待4.099秒后取得1.004秒稳定窗口；门限为总速度<0.03 m/s、垂向速度<0.01 m/s。运行中2054条LocalizationStatus样本均有效；活跃状态阶段最大回执间隔约0.079秒，未复现#271的0.344954秒空窗。关闭observer后本轮成功与#271失败相符，但单次对照只能支持、不能证明因果。

机头前向0.6 m EGO目标、停车保持和独立制动测量通过：参考峰值速度0.08029 m/s，实际水平峰值0.08105 m/s；从参考减速起点到实际速度持续低于0.03 m/s的距离0.28201 m，持续减速响应时差0.112 s，最大独立跟踪误差0.07191 m，阈值停车后1秒位置变化0.02005 m。该结果是一条有效制动测量，不等于完整N08通过。

## 中止点与另外发现的问题

初始定点转向位置球未知时，执行器先通过fresh raw map认证并执行0.22 m机头前向EGO定位段；实际前进0.23309 m，端点误差0.01317 m。重新采图后转向区域为free，故提交了约180°原地转向目标。

第一条转向样条（traj_id 3）位置参考固定，yaw控制率上界0.4284 rad/s，低于已有0.5 rad/s监控界。转向约18.84仿真秒后EGO发布部分重规划（traj_id 4），yaw从2.32465 rad继续到目标3.13752 rad，`yaw_dt=1 s`。当前watchdog却对每条转向样条都要求从原始起始yaw开始、单段完成完整π转角，因此将这个合法“剩余转角”样条判为`live_yaw_turn_spline_misses_requested_heading`并触发降落。该判据需要识别部分重规划；但不能直接放宽0.5 rad/s界，因为这条部分样条的保守yaw率上界约2.4386 rad/s，确实超过现有界，应让EGO在重规划时延长时间或以其他方式满足原限值。

独立真值显示定点转向没有保持住相机位置：相对转向起点最大水平偏移0.20949 m、三维偏移0.20967 m，超过本动作0.05 m容差。分层对齐后，EGO位置参考固定；VIO估计位置只变化0.02975 m，桥内部PX4/VIO对齐漂移最大0.01011 m；但独立真值与VIO的定位误差由转向初始0.00507 m升至期间最大0.20054 m，watchdog时仍为0.18731 m。整段定位状态持续valid，VINS solver可用，normalized cost最大0.8227，未触发现有健康门。故当前证据把首个明显分歧定位在“VIO/PX4一致的估计位置”与独立真值之间，而非bridge的frame alignment；造成这项真值误差的具体因素仍未区分。

PX4位置设定点转向时的移动也已解释。首个记录点还属于转向前保持；从traj_id 3生效后的第一条PX4设定点到中止前，NED位置变化0.22376 m。按bridge现有转换，保持相机／IMU参考点不动时，需要随yaw旋转补偿0.12 m机头方向的传感器杆臂；用实际2.402 rad航向变化计算的杆臂补偿为0.22378 m，与设定点变化吻合。这是现有frame contract的预期，不是独立故障证据。仍需解释为何已按此转换控制时独立真值相机位置移动约0.21 m。

因此，最新直接中止原因仍是转向样条监控拒绝部分重规划；但N08不能只改watchdog后重飞。需保留并修正partial-replan判据，确保EGO生成的部分yaw段继续满足0.5 rad/s界；另需查明有效定位状态下估计与真值之间快速增至0.20 m的差异，且不放宽0.05 m位置容差。

## 安全末态与未完成出口

watchdog取消目标并请求降落。飞行记录显示最后bridge phase为`LANDED`、control disabled，PX4最后状态`arming_state=1`且`failsafe=false`；运行后直接读回亦为DISARMED、landed、bridge无控制。`project.sh stop`退出0，仿真容器已停止。

N08正式出口仍缺：完成hold／EGO计算但bridge保持／EGO执行的受控机制解释或针对性修复；测量运动中取消后的停止／保持；在**同一冻结版本**完成至少3次独立冷启动的普通单目标运行，每次参考与健康连续、目标实际停止／保持并安全落地上锁；把速度、观测距离、机体余量、延迟和制动数据回填N05/N06预算，并对实现／包络改动重跑受影响项。N08的正式出口没有要求普通目标自动返航或必须回到home pad。

#260、#267、#273各有一条有效去程制动曲线；三者的runner与goal配置指纹不同，不能合并成同一版本的三次验收。它们在去程目标处的成功／制动证据应独立保存。各run的专用runner随后编排的第二段转向／返航失败，只说明那条单独动作序列尚未完成，不应抹掉普通目标已经取得的去程证据。

另行保留用户要求的返航动作验收：明确发起第二条命令后，结束并保持去程、原地转头并确认航向、检查转向后的fresh地图，再由EGO沿机头前向返回。#273在这条第二段链的yaw action被监控器中止；真实位置偏移和yaw partial-replan问题仍未解决。这项返航链结果不改变普通单目标的完成语义，也不替代N08正式的制动重复次数。

## 产物与范围

原始运行目录：`artifacts/runs/n08-20261025-273-observer-pre-enable-repeatability/`。轻量[机器可读摘要](n08-yaw-replan-refusal-20261025-273.json)和[完整机器报告](../../artifacts/runs/n08-20261025-273-observer-pre-enable-repeatability/n08-yaw-replan-refusal.json)、[VIO/PX4输入时间线](../../artifacts/runs/n08-20261025-273-observer-pre-enable-repeatability/alignment-observation.json)、[独立VIO误差曲线](../../artifacts/runs/n08-20261025-273-observer-pre-enable-repeatability/odometry-errors.csv)及[桥接对齐轨迹](../../artifacts/runs/n08-20261025-273-observer-pre-enable-repeatability/bridge-alignment-timeline.jsonl)支持上述复算；各输入哈希记录在机器报告中。本报告不改变N08验收条件、健康门、未知空间规则、0.05 m转向容差或0.5 rad/s yaw率上限。
