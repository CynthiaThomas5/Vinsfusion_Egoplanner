# #257：新鲜运行曲线验证通过

新冷启动使用0044最终动力学检查、#255定位回调一致性修复、逐轴0.10m/s／0.25m/s²配置与0.12m/s参考向量门。15阶段扫描完成且支架移除；助手结束时的健康状态提示仍保留，最终定位valid、normalized_cost0.4688，释放后独立N05在线／离线准入通过。

EGO运行日志确认2次refine后最终动力学通过；最终样条14.222秒，实际密采样峰值向量0.081033649m/s、导数凸包上界0.081092391m/s，逐轴界均通过。起终机体／保持球unknown0 occupied0、47次连续扫掠通过；同身份图源龄0.132秒、融合龄0.060秒均低于0.4秒。详见[机器报告](n08-coherent-speed-validation-20261025-257.json)。

`D435I_N08_MODE=compute_only ... project.sh mission`退出0；独立compute-only检查12/12通过，实际桥保持、目标取消确认、最终落地上锁。独立VIO位置RMSE0.00455m、最大0.00973m，飞行区间invalid状态0。没有执行前向曲线或测制动，不能称N08通过。

原始证据：`artifacts/runs/n08-20261025-257-coherent-speed-validation/`。任务后新鲜5秒读回DISARMED、landed、bridge LANDED、control_enabled=false、控制样本0、fixture absent，然后stop成功。host首个安全谓词误限DISABLED导致保留会话，已以真实成功终态LANDED重新核验后安全停止，修正记录保留。

下一项#258：新冷启动专用native execute末端制动测量，前方0.6m→保持→返回原N05 pad→降落；依然要求当前run capsule、健康和实时速度／跟踪门全部通过。
