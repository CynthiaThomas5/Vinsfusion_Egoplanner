# P5 全量 visual residual 与边缘各向异性诊断（#206）

## 任务摘要

在 #204/#205 top20 图像关联复测后，扩展 run-local VINS 诊断，只扩大首次质量越线 telemetry 中 visual residual observation 的序列化数量，收集全部因子块像素坐标和 residual。将所有 observation 按 target frame/相机连接到对应保存图像，并评估边缘距离、残差方向和局部梯度结构张量。

## 用户约束

- 仅推进 P0–P6 单 D435i 仿真导航；final 验收组合无真值输入。
- `uav_px4_bridge` 继续独占 PX4 控制设定点和 OffboardControlMode。
- normalized_cost=1.0、PX4 freshness、65 ms source-future 约束不变。
- run-only 诊断补丁不得进入默认 VINS 来源补丁链；不把诊断结果当导航通过。

## 结果与决定

- 新增 `0007-all-feature-residual-observations.patch`，仅接在 #0006 run-local diagnostic source 后，将首个 quality crossing 的 telemetry observation 列表从前20扩为全部视觉 residual observations；常规 `dependencies/sources.json` 不变。
- #206 在新 Jazzy build/install 中构建 camera_models 与 VINS 2/2、自维护 overlay 构建6/6通过；使用新 ROS domain228、Gazebo partition 和 epoch，无真值、无 observer 控制发布。
- normalized_cost=1.07801 后由现有1.0门中止，最终 landed/disarmed。798个二维视觉 residual block 全部有对应双目目标图像，图像与各目标戳精确匹配，skew为0；逐项重算的 Huber 总和与 VINS 视觉组 cost误差为4.55e−13。
- 38个 pixel-equivalent norm>1.5的 observation（6个 feature ID）全部距各自图像最大垂直梯度拟合边缘≤0.289 px，残差切向分量38/38大于法向。该组累积视觉 Huber cost=891.526，占视觉组98.502%。其11×11 Sobel结构张量 min/max eigenvalue ratio中位数为0.00256；其余760个 observation的中位数为0.78359。强烈支持弱各向异性边缘特征是本次越线的近端来源，但不能区分 tracking、几何／标定或场景因果。

## 待决

下一步做显式 opt-in 的 run-only 特征各向异性过滤对照，测量被保留 feature 数、视觉代价和导航结果；质量门和 PX4 安全边界不变。只有过滤后仍满足定位精度、可用特征数量与稳定性约束，才讨论 canonical 算法修改。

证据报告：[P5 全量视觉 residual 与边缘关联 #206](../../progress/evidence/p5-vins-all-feature-edge-correlation-20261020-206.json)。本对话摘要本身不作验收证据。
