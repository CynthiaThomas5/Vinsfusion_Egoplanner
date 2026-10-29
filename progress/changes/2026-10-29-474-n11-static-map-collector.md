# #474 N11静态地图采集实现（进行中）

用户启动Goal完成模式：完成N11剩余任务，正式飞行必须有Gazebo/RViz。本轮新增tools/diagnostics/record_n11_static_map.py：只订阅目标和MapStatus，只请求只读快照服务，周期保存同一响应的raw/inflated数组、来源/融合/快照时间、goal/epoch/map身份、数据哈希。记录错误不发布控制，也不改变飞行状态。

验证：py_compile通过；固定镜像中导入真实ROS接口，合法快照解码及4种错误数组/shape/order拒绝通过。第一次容器命令覆盖PYTHONPATH导致rclpy缺失，保留原PYTHONPATH并使用/usr/bin/python3后通过；不是运行库缺失。尚未进行live采集验证，未计正式次数。

下一步：静态墙面离线几何/分类评估，live只读采集验证，完整记录/评估入口联调，随后三个GUI独立冷启动。N11保持in_progress/0/3，Goal保持active。

继续进展：新增evaluate_n11_static_map.py，按固定PRESTREAM对齐把快照转换到静态墙面，计算表面误差与完整体素solid false-free；合成反例确认能发现实体内free体素，零分辨率拒绝。尚缺visible-free/外部遮挡控制，因此分类只允许FAIL或INSUFFICIENT，不允许以solid子检查替代完整分类通过。标准py_compile因旧__pycache__写权限失败，内存compile语法检查通过；未改目录权限。下一步继续补齐可见性控制和live验证。
