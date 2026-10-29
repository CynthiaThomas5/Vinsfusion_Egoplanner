# 对话摘要：N10.3/#415 运行结果与未完成安全收尾

用户指示按剩余方案完成 N10。#415 保持 #414 的路线、速度、0.10 rad/s yaw cap、同一体素 ROI、障碍、传感器和接受配置，只将只读 trace 从 verbose v1 对象改为 compact v2 数组。

观察到每体素更新字节从319.14降至66.37（79.2%下降）；覆盖区间200个fusion事件匹配，341格trace与source-covered after snapshot零分类不一致。该测量不证明飞行通过，也不归因此次故障。

16 m目标被EGO原生`full_curve_depth_odom_timeout`中止。bridge仍为LANDING；PX4仍armed、native DESCEND failsafe，EV position/yaw失效且`land_detected=false`。safe-to-stop为false。Gazebo机体位置近地但不能替代PX4/bridge末态。#391已用掉一次性紧急disarm授权，本次没有再次disarm或停止容器。

运行driver的SIGINT不能结束继承ignore的只读truth/contact recorder；action abort后仅停止这两个读取进程，最终真值/接触报告缺失，因此净空、跟踪与总评为INSUFFICIENT。当前D435i SITL/PX4栈仍保留运行并继续监护。新的紧急disarm授权或PX4自然安全末态是解除条件；安全收尾前不启动下一飞行、不做N10.5重建或运行时源码变更。
