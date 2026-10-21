# P5 VINS 逐特征视觉 residual 诊断（#203）

## 本轮目标

在不改变 VINS 求解、健康门、PX4 freshness 或控制路径的前提下，将首次 normalized-cost 越线的视觉 residual 关联到 track ID、帧时刻和双目像素坐标；仍保持无真值闭环图。

## 决定

- 新增仅用于 run-local 副本的 VINS 可选 patch 0006；默认 `sources.json` 和常规 VINS 安装不变。
- 只在 `VINS_DIAGNOSTIC_FEATURE_RESIDUALS=1` 且首次 normalized_cost 达到1.0时，以一次批量 `Problem::Evaluate` 读取 raw visual residual；在原 Huber loss 下重新汇总，输出 top features/observations 和近似像素等效值。
- #203 复用 #181 的图像计时 overlay，建立新的 VINS build/install；运行中导航、PX4 与配置门限不变，无真值订阅。

## 结果

- VINS `camera_models` 与 `vins` 隔离构建2/2通过；完整自维护 overlay 构建6/6，运行记录确认 `vins` 前缀指向 #203 install。
- 目标通过前置门、起飞并发送 zero-offset goal；normalized_cost 首次为1.08720后由现有门控中止，最终 landed/disarmed。直接 PX4 lockstep 时间路径有效，无 timestamp error。
- 首次越线样本有860个二维视觉 residual blocks、51条独立 track；视觉 cost 1026.470，Huber 逐项重算与 Ceres 分组视觉代价一致，额外评估0.2313 ms。visual／marginalization／IMU组占88.977%／10.814%／0.209%。
- 排名最高的20个观测位于640×480图像左下区域（anchor x=28–162、y=358–370），20/20 horizontal residual 同向。该模式支持空间聚集判断，但不能区分边缘图像内容、匹配、标定或运动估计原因。
- ULog见EV position/yaw/velocity各21/39样本融合、GNSS aiding 0/39、无dropout、电池warning/fault为零。触地后约0.78秒短暂 DESCEND/failsafe，随后解除武装。

## 待决

没有保存越线帧图像或在线真值，无法判定误差与图像纹理/遮挡或真实机体运动的关系，也没有独立复测确定空间聚集是否可重复。下一步只读保存匹配越线时刻的左右相机图像并叠加 residual；质量门仍保持1.0，P5与最终 A–H 均未通过。

数值和 SHA-256 见 [轻量报告](../../progress/evidence/p5-vins-feature-residual-diagnostic-20261020-203.json)；本摘要不作为验收证据。
