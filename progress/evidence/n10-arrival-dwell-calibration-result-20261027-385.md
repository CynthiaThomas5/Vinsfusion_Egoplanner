# N10.3/#385 到达驻留校准诊断

**结论：任务与独立到达验收通过；这是单次诊断，不构成 N10/N12 正式资格。** #385 使用同一冻结 runtime，将 native goal dwell 设为 4.0 仿真秒；GOAL F 独立验收仍按位置 ≤0.30 m、yaw ≤15°、连续 ≥3.0 仿真秒判断。

独立真值窗口为 **3.32 仿真秒**（4.39 墙钟秒），167 个样本；窗口内最大位置误差 0.2979 m，最大 yaw 误差 3.17°。native action 成功，600 仿真秒 ACTIVE hold 完成，禁止接触 0，PX4/bridge 读回落地、disarmed、control disabled、零控制样本；容器安全停止。

raw VINS 速度与真值配对覆盖 100%（10180/10180）。这些单次误差统计仅作校准观察，不能据此冻结通用门限。

动态障碍注入获得 ACK，轨迹 ID 发生变化；但注入箱体中心附近的同身份 raw-map 查询在注入后 0.5/1.25 仿真秒仍返回 free（unknown=0、free=160、occupied=0）。记录的 occupied-cloud ROI 属于另一个静态圆柱接近观察，没有把点坐标关联到注入箱体；trajectory ID 变化本身也不能证明触发了避障。#387 复核后发现整条 B 样条几何最近点含在箱体内部的点，而按时间戳变换的实际 READY PositionCommand 中心线与箱体最近距离为 1.463 m；这两种数据不能混作执行路径。故该单次运行有实际轨迹采样避开箱体的证据，但没有确认地图占据响应和因果重规划。全机采样净空扣除观测到的样本间位移后为 0.118 m，为正的采样诊断值，仍不是连续动力学净空证明。

原 run driver 的退出码为 1，失败位于离线分析器：旧分析脚本索引缺失的 `ground_rotation`。#386 用不覆盖旧产物的 v2 独立报告与 post-run analyzer 完成复算；这修复分析链，不改飞行结果或把原 driver 退出码改写为 0。

机器报告：[JSON](n10-arrival-dwell-calibration-result-20261027-385.json)。完整 run 产物位于 `artifacts/runs/n10-20261027-385-arrival-dwell4-retry/`。
