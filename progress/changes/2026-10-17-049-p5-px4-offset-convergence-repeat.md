# P5 PX4 estimated_offset 重估独立复核

对话摘要：[2026-10-17-049](../../collaboration/dialogues/2026-10-17-049-p5-px4-offset-convergence-repeat.md)。

## 结果

- #110 使用 ROS domain 226、独立 Gazebo partition 和新的 PX4 build 副本，复跑45秒只读SITL。PX4/Agent `estimated_offset` 再次在启动后调整：14.595秒开始、19.779秒最后变化；与 #109 的15.121–20.638秒窗口接近；该字段停止变化不表示timesync收敛，详见[#111](../evidence/p5-px4-observed-offset-diagnostic-20261017-111.json)和[#112](../evidence/p5-px4-offset-cycle-75s-20261017-112.json)。
- 用相同的 `/clock`–monotonic 插值方法，attitude 167/1820、local-position 87/909条样本超20 ms未来界限，全部位于 offset 调整窗口。最后 offset 变化后，这两源年龄 P95 为4.679 ms和9.028 ms；各 telemetry detail 的41次源龄门违规位于14.678–19.778秒。bridge状态主原因由 `localization_not_tracking` 占优，不能把0次 `px4_telemetry_stale` 状态理由解释成遥测从未 stale。
- VINS原始里程计输出284条，原始探针收到左/右图像565/564条；定位适配器短暂进入 TRACKING 后于0.747秒以 `left_stale` 锁定。定位探针没有收到优化里程计、仅收到6条传播里程计，PX4因此收到0条外部里程计且未观察到EV融合。按规则排除出融合证据，仅支持 PX4/Agent 时间戳窗口可重复这一诊断；图像到适配器的年龄差异仍待定位。没有真值、控制样本或解锁；车辆保持 disarmed。
- PX4 v1.17 源码路径显示 timesync offset 由 `Timesync::update()` 在线滤波，并有连续高偏差触发滤波重置的代码；#112后来直接观察到estimated_offset归零再初始化，且Agent日志无DDS重连，因此高偏差重置是最有力解释，但内部计数器/debug事件未直接记录。没有修改 PX4 只读来源。

轻量证据与完整 raw artifact/source/config 哈希见[报告](../evidence/p5-px4-offset-convergence-repeat-20261017-110.json)。本 run 的 qualification 报告因 VIO 缺失标记失败并保留。

## 验证与限制

- harness shell 语法检查通过；SITL 运行按只读探针收集原始时间戳及 timesync offset。
- 本轮不是融合或 readiness 通过证据；P5仍 `in_progress`。observed_offset与重置状态由#111/#112补充。下一步量化滤波重置与lockstep `/clock`、Agent wall-clock的关系，保持freshness阈值不变并继续fail closed。
- 关联 #109 有效融合诊断：[P5 原始时间戳与 offset 收敛](../evidence/p5-px4-raw-timestamp-correlation-20261017-109.json)。P4/P5/P6 与 GOAL A–H 均未完成。
