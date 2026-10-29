# #258拒绝与#259地图快照接口回归

#258完成15阶段扫描和N05释放后准入，但新试验执行器单次raw snapshot检查拒绝，service_calls=[]、action_goal_sent=false，未enable／起飞／发送目标，随后新鲜落地上锁、控制0、fixture absent后安全停止。旧异常未保存具体服务拒绝reason，不能追溯声称其确切原因为pending融合。

代码审查发现新执行器未复用已有compute-only记录器的有限快照重试协议。plan_env快照服务严格拒绝pending fusion，返回no_fresh_fused_depth；这一规则保持。修复仅对既有三类瞬态拒绝在2秒截止内重试，每次仍检查map／epoch／frame／input_ready和原源龄门，绝不使用拒绝快照。硬身份／深度门故障直接拒绝；逐次服务响应写入当前run，重试间服务ROS回调并限速。

#259未武装、无fixture、无enable／目标的真实SITL读取中，40次快速请求均返回no_fresh_fused_depth；有限等待后3次快照均成功，原始响应次数分别45／1／53。这个短实验明确复现单次请求易被pending融合拒绝的接口行为，支持修复，但不把#258未记录的reason当已证实。

6项真实ROS方法测试通过：瞬态后成功、wrong epoch、depth_pose_gate_closed、固定超时、等待中换图、accepted但源龄过期。安全读回DISARMED／landed／bridge DISABLED／控制0后停止。产物：`artifacts/runs/n08-20261025-259-snapshot-contract-regression/`；[机器报告](n08-trial-snapshot-contract-20261025-259.json)。

下一项#260：使用修正后的专用执行器重新取得当前run扫描／准入，再执行限定末端制动测量。N08仍未通过。
