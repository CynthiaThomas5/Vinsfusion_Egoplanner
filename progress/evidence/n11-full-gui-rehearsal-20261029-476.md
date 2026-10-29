# #475–#476 N11完整GUI采集预演

N11仍in_progress，正式0/3。#476是协议preparation下的端到端预演，不抵扣正式次数。

#475在发goal前因脚本按无GUI写死订阅数2而拒绝；真实图有uav_navigation单发布者，以及bridge/planner/navigation_visualization/n10_readonly_sensor_capture四个合法订阅端。拒绝日志完整保留；同run重试又被一次任务目录保护拒绝，未删marker绕过。独立读回DISABLED/control-disabled/disarmed/landed后停止exit0。外部试验脚本修正图身份集合，飞行代码未改，#476使用新冷启动。

#476在桌面:11显示Gazebo与RViz，完成12m目标、20仿真秒保持和正常降落。独立到达联合窗口3.532仿真秒，最大位置误差0.299476m、yaw0.197163rad，均满足冻结GOAL F。违规接触0；15秒独立终态读回全部safe checks通过，容器受控停止exit0，未紧急disarm。静态记录器保存14张完整身份raw/inflated快照，2次no_fresh_fused_depth拒绝亦保留；记录器不控制飞行。

离线适配的v1快照路径检查不接受跨目录symlink，v2将快照复制到独立reanalysis view解决；会话manifest与arrival-v2别名缺失也在view中显式补齐，原归档未重写。旧N10字段名兼容视图明确注明来源为真实N11静态观察器，无动态障碍注入事件。静态墙面表面最大观测误差0.057589m≤0.1m；可见free控制311566，整格遮挡raw-free为0，两个地图指标通过；未观测墙面不推断。

真实未通过项：运动段10s平移RPE P95=0.0833339948m>0.05m；IMU current queue OLS slope=0.00500706237items/sim_s>0。阈值保留，不能把任务成功作为全指标通过。区间物理步完整且瞬时端点身份经独立复算PASS，但外部tool-freeze遗漏镜像ID/启动前源码声明，原有区间评估器判INSUFFICIENT_MODEL_IDENTITY；不倒填历史声明。

下一实验已有证据支持：#476使用默认max_vel0.5/max_acc0.8，与#470短程回归相同；#460长程校准则使用已冻结的0.4/0.25配置。下一次恢复该既有长程校准profile并在启动前固定完整来源/镜像身份，再验证同一数值标准。主要变量为planner profile，不声称速度和加速度的单独因果作用；不恢复经验速度门或新增拒飞/取消门。

验证：21项适用层/静态几何测试通过；实际ROS采集已验证；结构检查和diff检查最终执行。产物：[原始#476](../../artifacts/runs/n11-20261029-476-empty-rehearsal/)、[v2复算](../../artifacts/reanalysis/n11-20261029-476-full-rehearsal-v2/n11-20261029-476-empty-rehearsal/)、[#475拒绝](../../artifacts/runs/n11-20261029-475-empty-rehearsal/)。Goal仍active，继续修复和验证，不关闭N11。
