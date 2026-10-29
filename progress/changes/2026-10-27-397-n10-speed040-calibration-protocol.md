#397 N10.3 单变量跟踪与地图采集协议

对话摘要：[2026-10-27 #397 跟踪/地图校准准备](../../collaboration/dialogues/2026-10-27-397-n10-speed040-calibration-protocol.md)

## 假设与唯一主要变量

基于 #396 的 PX4 同域设定点误差 P95 0.665 m、EGO 跟踪 P95 0.707 m 和 4 ms 离散机体净空最低 0.228 m，只把 planner `max_velocity_m_s` 从 0.8 改为 0.4。加速度、horizon、inflation、spawn、16 m 目标、4 s native dwell、15 s 诊断保持、动态箱体几何/触发、PX4 与控制路径均保持不变。协议为 [JSON](../evidence/n10-integrated-calibration-protocol-20261027-397.json)。

只读观察器在第一次采到箱体 ROI raw occupied cloud 后 0.75 仿真秒请求一份同 identity raw/inflated 快照；若 +8 s 仍无 ROI 点，则只采一份 fallback 快照并如实判表面证据不足。point-query RPC 不再通过反复等待来追结果；服务不可用记录为离线证据不足。离线依赖顺序改为 arrival→sim-time alias→校准汇总/map snapshot→动态世界 SDF→tracking/clearance→replan geometry→acceptance。

## 运行前验证

- 运行目录、准备目录、速度配置及协议文件均为新路径，不覆盖旧运行。
- 单变量 planner 配置从 #396 speed080 配置派生，唯一数值运行差异为 `max_velocity_m_s=0.4`；`max_acceleration_m_s2=0.25` 及其他规划参数保持相同。
- run-local injector/driver/prelaunch freezer均将固定 run ID、planner path 和 `max_vel=0.4` 做身份核对；预期 tool/config/runtime hash 在启动后、发 goal 前冻结。
- driver 后处理兼容 #383 之后的 sim-time arrival report schema；动态 SDF 生成在 tracking/clearance 之前。点查询/快照和离线报告不进入控制流程。
- 尚未启动 SITL 或发送目标。所有下一步仍以实际 freeze identity、原生 PX4 preflight 和安全终态为依据。
