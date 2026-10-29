# N10.3/#368：修复时间映射历史窗口后复测

- 唯一变量：PX4 bridge `clock_mapping_max_samples` 64→128；运行单箱障碍场景不变。
- 依据：#367在source age 0.296s仿真、约0.345s墙钟龄时因64样本窗口不足而报`source_stamp_outside_clock_history`；配置的源龄上限仍是0.35s。
- 保持源龄、映射后receipt龄、PX4时间/定位/融合保护原值；这是时间样本历史容量修正，不取消失联降落。
- 新增单测覆盖64拒绝/128正确映射/超过0.35s仍拒绝；`python3 tools/test_px4_bridge_time_mapping.py` 23/23通过。
- 预期：相同场景的EGO/PX4路线可以跨过合法短延迟；结果尚待SITL。

## 运行结果

#368已完成并失败于目标验收：128样本窗口下bridge运行未出现 `odometry_time_error`，但仿真103.876s时配对平移差达0.181539m，触发项目自加的0.15m `px4_frame_alignment_drift` 门限；yaw差峰值0.047647rad。Gazebo障碍创建ACK、D435i/EGO表面占据观测和后续轨迹均出现，目标最终 `goal_timeout`。净空采样扣减后0.920173m、禁止接触0；桥最终LANDED/disarmed/control disabled，末态控制样本0，观察器覆盖终态，容器已停止。详见[结果报告](../../progress/evidence/n10-live-obstacle-clock-history-result-20261027-368.md)。

源码审计确认平移与yaw最大误差字段是项目自维护bridge的本地数值门，无上游来源和独立校准依据。已移除两项拒绝门，仍保留误差观测、时间配对与有效变换要求；下一项#369在重建runtime上复测同场景。
