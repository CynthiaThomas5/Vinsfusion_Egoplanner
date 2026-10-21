# GOAL F 里程计 QoS 与无目标地图复核

- 任务：在 #247 多几何地图采样后排查 EGO `no odom`，确认输入话题、运行 install 和 EGO `flight_type` 语义；验证无目标等待时的里程计／地图数据链。
- 约束：仅单 D435i 仿真；不启动 PX4、控制桥或轨迹跟踪控制器；真值只由诊断进程离线对齐，定位、建图和 EGO 不订阅真值。失败及错误配置轮保留并单独分类。
- 发现：#248 的旧 install 中优化里程计发布 QoS 为 BEST_EFFORT，与 EGO RELIABLE 订阅不兼容。#249 使用当前 reliable install 后数据送达，但源码表明 `flight_type=2` 是 PRESET_TARGET，会加载预设航点。
- 复核：#250/#251 用 `flight_type=1`（MANUAL_TARGET）且不发布目标。#250 因 `left_stale` 在2.2秒锁定；#251 EGO 保持 `WAIT_TARGET`，观察到547条优化里程计、1,026组深度／位姿和最大1,256点占据云。表面区域残差仅作离线几何描述，圆柱 P95 为16.4 cm；主探针窗口结束后的 EGO 日志出现输入陈旧告警；位姿源龄 P95/最大0.627/1.641秒，墙钟接收最大间隔2.220秒，终端定位状态未观测。
- 静态复核：EGO 深度路径按 `ceil(inflation/resolution)` 对 x/y/z 三轴做方块膨胀；当前默认是27格/占用源格，0.482 m 包络的几何下界为5步、1331格/源格。另一 cloud callback 垂直方向固定1格，当前 adapter 未发布 cloud，未在这些 run 中用到。
- 决定：修正 #248/#249 run-local manifest 中的 flight_type 解释；#248 作为 stale install 排除，#249 仅计 QoS/规划器接线诊断。#250/#251 作为无目标路径诊断，不冻结 GOAL F 阈值，也不宣称建图、避障或净空通过。
- 待办：查明 #251 尾段 EGO staleness；增加独立圆柱地图覆盖复测；在健康定位与有效目标运行下测量跟踪误差、最小机体间距、数据年龄、重规划、制动和故障退出时间。
