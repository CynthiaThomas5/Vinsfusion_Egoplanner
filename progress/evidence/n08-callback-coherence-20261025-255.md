# N08 #254–#256：输入回调一致性修复与运行回归

#254完整15阶段扫描、N05释放后准入通过，compute-only任务在enable／目标之前被telemetry_stale锁存拒绝。健康检查看到源龄304.000001ms（原门限300ms）、接收龄240ms。独立源记录显示约0.305秒接收停顿后clock追赶，新的telemetry在锁存约3ms后到达；这支持局部回调批次不一致的解释，不能据此认定graph查询是根因。见 `artifacts/runs/n08-20261025-254-speed-output-validation/`。

#255保持所有原freshness／future／quality门限和Health状态机，TRACKING时仅对stale／future输入组合等待最多20ms。待确认期间不输出里程计、不刷新有效状态；到期、硬故障和质量失败仍锁存。新鲜数据只有在截止前到齐并通过原检查才恢复输出，源戳不改。

验证：真实ROS方法＋Health定向测试6/6；相关单元回归71/71；17个ROS包构建通过。日志位于 `artifacts/runs/n08-20261025-255-localization-callback-coherence/`。

#256未武装SITL干预：适配器SIGSTOP后生产者仍运行，恢复后valid；真实VINS生产者暂停约0.8秒则propagated_stale锁存，生产者恢复后仍invalid。始终无enable／目标；最终独立读回DISARMED、landed、bridge DISABLED、控制计数0，容器Exited0。该回归证明两类干预的不同处理，不替代飞行期连续性验证。

机器报告与哈希见 [JSON](n08-callback-coherence-20261025-255.json)。N07历史三次通过不复测，N08父目标仍in_progress；下一项#257新冷启动曲线验证，随后执行限定规划内末端制动测量。
