# 2026-10-27 #397 N10 跟踪与地图校准准备

## 用户范围

持续按 N10.1–N10.7 完成任务；校准在冻结前，N15/N16 正式矩阵在冻结后。离线门限越线、记录器或 evaluator 错误不得新增起飞拒绝、取消或降落。PX4 原生 preflight、EV 融合与 EGO 原生 watchdog/collision 路径照常工作。一次性紧急 disarm 已在 #391 使用，不再调用。

## 依据和假设

#396 正常完成目标与落地，但验收总体 `INSUFFICIENT`。PX4 同域设定点误差 P95 0.665 m，EGO 位置跟踪 P95 0.707 m，静态场景 4 ms 离散采样最低净空 0.228 m。障碍 ROI 点云在插入后 3.588 仿真秒出现；原始 map snapshot 在 +1.016 s，故箱体内部仍 unknown。真实跟踪差异尚无根因证明。

## #397 协议

- 唯一飞行参数变量：EGO `max_velocity_m_s` 0.8→0.4；保持 max acceleration 0.25 m/s²、route、spawn、目标、障碍、PX4 以及其余参数不变。
- map snapshot 只改 observer 时序：第一次观察到箱体 raw-cloud ROI 点后 0.75 sim s 取一份同 identity raw/inflated arrays；无点时 +8 sim s 取 fallback并标记不足。服务缺失不反复重试，不改变飞行。
- 离线评估器按输入依赖顺序运行，另修正 #396 已暴露的 arrival schema 兼容和 tracking evaluator 的动态 SDF 顺序。
- 开工协议、准备器和 run-local driver 已落盘；尚未启动 stack 或发送目标。下一步在新 run ID 启动 stack，确认桥处于 DISABLED/PX4 landed-disarmed，冻结运行、参数、镜像与 observer 身份，然后执行单次校准并按普通路径落地。

详见 [protocol](../../progress/evidence/n10-integrated-calibration-protocol-20261027-397.json) 与 [change record](../../progress/changes/2026-10-27-397-n10-speed040-calibration-protocol.md)。
