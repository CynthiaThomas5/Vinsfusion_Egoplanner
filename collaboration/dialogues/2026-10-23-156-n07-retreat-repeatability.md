# #156 N07 后退路线独立冷启动复核

用户授权继续 N07 Goal；本轮仅用于 fresh N05 准入和路线诊断，未授权绕过 N05 gate。runtime 固定 spawn 为 -6.5m。

## 结果

复用 #155 的 2.4m 纯平移后退/返回。轨迹向后到达 x=-2.4m；返程接近原位时 accel bias 首次越过 health.json 0.15m/s² 门限，LocalizationStatus 锁存 `accel_bias_norm_exceeded`，MapStatus 随后 reset。支架安全回位、脱离并确认场景模型删除，PX4 DISARMED、bridge DISABLED、landed。释放后 fresh N05 等待 150s 未获得 optimized odometry；未起飞。与 #155 对比，2.4m 路径跨冷启动并不稳定。

下一项 #157 会先将纯平移后退距离缩短至 1.5m，保持 yaw/pitch、运动时间和 N05 判据不变，评估地图覆盖与 health margin。报告见 `progress/evidence/n07-retreat-health-failure-20261023-156.md`。
