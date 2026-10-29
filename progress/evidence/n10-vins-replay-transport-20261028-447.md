# N10.3/#447：监视器完整性修复与原生处理帧差异

同bag在相同新协议下重放default和#442 gyro候选：bag writer/只读input monitor采用RELIABLE，原VINS SensorDataQoS保持不变。两组监视器均完整IMU39181/左4749/右4749，全部源戳SHA匹配原bag，首帧记录缺口已修复。真实估计器各2364位姿；共同源时间观察default运动RPE10p95=0.073868m、保持速度p95=0.017070m/s；gyro候选0.078140m/0.009987m/s。未复现#442运动误差改善，均未通过原门限，不部署。

新判别信息：default447首feature telemetry=7.924s/115 features，原同配置439=7.888s/180 features，初始化与raw输出源戳相位也不同；447两组feature源戳一致，但监视器输入完整不能证明估计器原生接收/实际处理帧完全相同。源码sync_process存在paired-frame catch-up discard loop：双方buffer>1时直接pop旧配对帧。因此严格因果支持保留不足；旧#439–446参数结果仅限实际观察条件，不再把外部监视器完整等同原生实际输入一致，也不把#442部分改善当已验证实现。

下一#448隔离副本仅增加只读回调/处理/丢弃时间戳记录，再对比保留配对帧的单处实现变化与队列代价。原vendor/install未改；先真实构建/完整证据后决定。不通过改变0.05m RPE/0.01m/s hold数值收尾；父N10.3未完成，无新飞行/故障校准。

产物artifacts/replays/n10-20261028-447-vins-replay-transport（包括native-frame-phase-audit.json）和对应n10-prepared。输入完整性修复/同bag实回放已完成，严格原生输入等价验证未完成。
