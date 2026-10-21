# P5 图像边缘与逐特征残差关联（#204）

## 任务摘要

延续 #203 逐特征 residual 诊断，使用只读 observer 在 normalized-cost 越线时保存匹配的 D435i 双目灰度帧，并把 top residual 叠加回原图。observer 仅订阅左右 rectified image 与 VINS estimator telemetry，不订阅 debug_truth，也不发布控制。

## 用户约束

- 当前范围限于 P0–P6 单 D435i 仿真导航；真值诊断不得进入最终验收组合。
- PX4 控制设定点和 OffboardControlMode 仍由 uav_px4_bridge 独占。
- 不放宽 normalized_cost、PX4 freshness 或 65 ms source-future 门限。
- 在没有可复现证据前，不把图像边缘关联当成已确认根因。

## 结果与决定

- #204 domain 230 SITL 保存了越线 telemetry stamp 29175999999 ns 对应的左右 640×480 mono8 图像；双目 stamp skew 为0，图像相差1 ns。
- 20个 top residual observations 中，全部落在图像梯度拟合出的斜边 0.463 px 内；每项残差切向分量大于法向分量，且沿线方向相同。该结果支持边缘方向歧义假设，但不是因果证明；20项包含12个重复 feature ID。
- observer 在线生成的第一版彩色标注不适配 mono 灰度格式。保留原文件和运行日志，使用保存的 PNG 做了离线 BGR 重绘；离线标注无运行效果。
- zero-offset action 仍由原 normalized_cost=1.0 门限以1.06652中止，PX4 最终 landed/disarmed。该轮不是导航通过；PX4 ULog 有 EV 融合、零 GNSS aiding、零 dropout，并在触地后短暂出现 DESCEND/failsafe。

## 待决

在独立运行中重复图像—残差关联，并比较越线前低代价帧的完整特征分布与角点/边缘响应。需要排除采样子集、跟踪误差、标定和运动估计等解释，再决定是否有足够证据提出算法改动。质量门和 PX4 时序门限保持不变。

轻量证据报告：[P5 图像与 residual 关联 #204](../../progress/evidence/p5-vins-feature-image-correlation-20261020-204.json)。本摘要不是测试证据。
