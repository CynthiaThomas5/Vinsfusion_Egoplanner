# N10.3/#404 综合校准协议

- Run ID：`n10-20261028-404-speed040-integrated-calibration`。
- 复用：#398 的 16 m official EGO 场景、0.4 m/s planner profile、16 m 到达／15 s 诊断保持／正常降落与传感器/资源观察配置；#401 planner 退出校准结果保留。
- 本轮唯一变化：只读证据路径更新为 #402 的同身份 source-stamp watermark 与最多五次有界快照重试；补入 #403 的逐个 4 ms 物理步全机净空评估，并在起飞前复制并记录本次实际加载的 X500 model SDF SHA256。runtime goal、控制所有权、碰撞策略、速度和落地逻辑不变。
- 采集：raw/inflated occupancy 数组与 header/source/fusion 时间戳，ROI 正占据 cloud watermark，点查询，重规划与真实绕行，VIO 位置/yaw/速度/RPE，READY 跟踪，机体/桨/相机 SDF 净空，接触，MCAP/收据，CPU/RSS/RTF/暴露队列，PX4/bridge/action terminal。
- 故障注入：本次不注入。现有 parameter_bridge 是多路相机与 IMU 的共同桥；停它会同时切断多路输入，不构成深度单流断开。待建立并核实只影响深度输入的触发路径后，再单独记录触发至自然 PX4 终态；不使用紧急 disarm。
- 控制约束：没有基于评估器、CPU 峰值、记录器或统计越线的起飞拒绝、取消或降落分支；不恢复项目自加质量／年龄／经验速度／连续等待／raw-known-free 全包络门限。PX4 原生 preflight/EV 融合和 EGO 原生碰撞/输入超时继续生效。
- 当前状态：已完成单次 SITL 诊断校准。16 m action 与独立到达驻留成功，15 s 保持仅为诊断；source-covered snapshot 和 4 ms solver 记录完整。综合 acceptance 仍 `INSUFFICIENT`，raw-map 分类为 `FAIL`，跟踪/资源标准仍待依据。无故障注入、无运行门限变化。详细结果见 [#404 证据报告](n10-integrated-calibration-result-20261028-404.md)；正式 N15/N16 仍在冻结之后。
- 正式 N15/N16 测试仍保留在 N10 冻结之后。
