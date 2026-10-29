# N10 #384–#386 进度摘要

## 任务范围

继续用户授权的 N10.1–N10.7 Goal 完成任务。保留 GOAL F 的位置≤0.30 m、yaw≤15°、连续≥3.0仿真秒合同；只将 #385 native goal dwell 设为4.0仿真秒。不得重新引入项目自加健康／源龄／速度拒绝门，也不得将单次诊断标为正式资格。

## 结果

- #384 的动态障碍注入观察器因协议缺少 `injection` section 在发送目标前退出。PX4原生话题读回disarmed，bridge disabled/landed，零控制样本；已安全停止，作为无飞行准备失败保留。
- #385 完成16 m目标和600仿真秒ACTIVE hold。独立真值同时位置/yaw窗口3.320仿真秒，167样本，窗口最大位置误差0.2979 m、最大yaw误差3.17°；禁止接触0，最终独立读回landed/disarmed/control-disabled/zero-control。
- 同次动态箱体创建ACK、occupied ROI和新trajectory ID有记录；离线箱体净距分析依赖未验证的初始坐标假设且包含零中心线净距，因此不宣称避障通过。全机采样间隙调整后的净空值0.118 m仅是采样诊断。
- #385 原始driver因冻结的离线分析器读取缺失 `ground_rotation` 而退出1。#386保存旧评估器字节，扩展当前到达报告的固定变换字段，并用独立 v2 输出复算；6项到达评估边界测试通过。新的后处理报告仍为diagnostic sample。

## 记录与待办

证据见 `progress/evidence/n10-arrival-dwell-setup-abort-20261027-384.md`、`n10-arrival-dwell-calibration-result-20261027-385.md` 和 `n10-arrival-simtime-analyzer-compatibility-20261027-386.md`。N10仍 `in_progress`。下一项 #387 对 #385 的注入障碍、轨迹与固定真值／里程计 SE(3) 进行只读坐标复核；之后还要闭合全机净空连续界、N15端到端故障退出、N16完整负载资源依据，以及 N10.4–N10.7。
