# P5 图像边缘与逐特征 residual 关联（#204）

对话摘要：[2026-10-20-004](../../collaboration/dialogues/2026-10-20-004-p5-feature-image-correlation.md)。轻量证据：[图像与 residual 关联报告](../evidence/p5-vins-feature-image-correlation-20261020-204.json)。

## 变更

- 新增 #204 run-local 只读图像 observer，按 VINS telemetry 中的 residual 坐标保存最近的左右 rectified 灰度图。运行仅订阅相机图像和本 epoch VINS telemetry，无真值订阅、无控制发布；新增 ROS 发布者数为0。
- 保留采集脚本原版灰度图层输出。由于单通道底图上画彩色标记不明显，新增离线 BGR annotation helper 以已保存 PNG 重绘，不改变 SITL、估计器或控制行为。
- 新增 ULog 摘要与 image-edge correlation 分析脚本；所有输入 PNG、离线 overlay、ULog、运行日志、脚本和有效配置均在报告中留 SHA-256。

## 结果

- #204 run-local 自维护包构建6/6通过；复用 #203 独立构建的 VINS 诊断安装。PX4 lockstep direct-current 时间路径无 timestamp error，导航前置门通过并派发 zero-offset goal。
- 越线样本 normalized_cost=1.0665178732，首次样本 stamp=29175999999 ns，final_cost=1110.1613；目标由 unchanged normalized_cost=1.0 门限中止并降落，最终 landed/disarmed。
- 越线双目图像 stamp 为29176000000 ns，与 telemetry 相差1 ns，左右 skew=0。20个排名靠前的观测涉及12个 feature ID；图像内拟合边缘残差 RMS约0.29 px，观测到边缘距离中位0.212 px、最大0.463 px。20/20 残差切向大于法向且同向，支持 edge-aligned ambiguity 假设，但不能确认语义边界或根因。
- PX4 ULog仿真时长29.820秒，无 dropout；EV position/yaw/velocity 各24/41样本融合，GNSS position/velocity/yaw 与 GPS height aiding 均0/41，battery warning/fault为0。触地后短暂出现 DESCEND/failsafe，随后解除武装。

## 验证

- `python3 artifacts/runs/p5-px4-vio-ego-no-motion-direct-20261020-204/analyze_image_edge_correlation.py`：20个 top observations 全部在拟合图像边缘1 px内；沿边缘残差占优20/20。
- `python3 artifacts/runs/p5-px4-vio-ego-no-motion-direct-20261020-204/analyze_px4_ulog.py`：dropout=0，EV/GNSS与降落时间线符合报告。
- `bash -n` 检查 #204 run scripts；observer、annotation、分析脚本通过 `py_compile`。
- 运行与图像生成属于 SITL 诊断证据，不是 replay、实机或 P5 导航成功证据。没有修改 canonical VINS patch stack、算法阈值或 PX4 控制路径。

## 局限与下一步

20条排名观测不是独立样本，来自12个 feature ID，且图像梯度线没有语义标签。空间吻合强，但匹配、相机/IMU标定、短时运动和场景纹理仍可能共同影响。下一轮应在独立 run 中复现，并将越线前后完整 feature 分布与局部边缘/角点响应对齐；在此之前不改求解器或质量门。P5 与 GOAL A–H 仍未完成。
