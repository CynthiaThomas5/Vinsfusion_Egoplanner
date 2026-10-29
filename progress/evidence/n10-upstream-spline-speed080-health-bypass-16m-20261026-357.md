# #357 N10.3 完整航线诊断结果

## 任务和安全终态

同一 0.8 m/s/轴、0.25 m/s²/轴、5 m horizon 的独立冷启动航线完整执行。native action succeeded；独立真值评估最小三维目标误差 0.044 m，连续达标 3.160 s（要求3 s）。600 仿真秒 ACTIVE 保持完成，RTF 0.763；观察速度峰值为 PX4 0.636 m/s、EGO参考 0.711 m/s。

五类观察器全部等到终态 flight.json。接触评估通过：禁止接触0、最终落地接触观察到。独立6秒PX4/bridge读回为 LANDED、landed=true、armed=false、control_enabled=false、车辆保持disarmed、控制样本0；driver exit 0，随后该容器安全停止。

## 定位旁路实际影响

旁路被LocalizationStatus确认。normalized cost的p95为 1.858、峰值 2.615，超过未改的1.0门限；首次越线在墙钟 53.62 s、source stamp 104.152 s，cost 1.0039。这次诊断说明旁路后路线仍可完成，但不授予正式定位健康资格，也不证明1.0阈值可以删除或改高。

#356 的规划失败没有在 #357 复现；因此它是一次未复现的EGO inflated-occupancy规划失败。精确碰撞体素仍未知。

## 本次测量

- Raw VIO覆盖 667.888 仿真秒、配对真值路径 24.544 m；位置RMSE 0.346 m、p95 0.497 m、最大 0.514 m；yaw p95 8.692°、最大 8.763°。原始样本10120，时间支持 0.99995。
- EGO位置参考到独立真值跟踪误差p95 0.521 m、最大 1.099 m。现有0.15 m是未由runner执行的候选值，测量不支持冻结该值。
- Goal到landed期间map source age最大 0.164 s，occupancy age最大 0.100 s。0.4 s门限仍是候选值，不是最终标准。
- 全程无时钟回退；contact零禁止接触。该观察不提供最小障碍净空。
- 未在本次0.636 m/s实际PX4速度下测量caller-cancel制动。N08的低速结果只能作低速对照。

## N10.3 尚需处理

#357完成了代表性长航线、保持、完整真值/raw-VIO、地图时效、接触与PX4终态数据；但验收阈值仍未收敛：跟踪误差候选0.15 m与实测不符；raw VIO误差、yaw和速度/RPE预算需按最终GOAL F及运动适用范围核算；高实际速度的制动范围未测；接触事件没有替代净空量测。旁路健康数据不构成健康资格。N10.3继续处理中，不标记通过。

运行产物位于 artifacts/runs/n10-20261026-357-upstream-spline-speed080-health-bypass-16m/。机器可读摘要见 [JSON](n10-upstream-spline-speed080-health-bypass-16m-20261026-357.json)。
