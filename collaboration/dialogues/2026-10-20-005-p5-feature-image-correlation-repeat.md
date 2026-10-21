# P5 图像边缘与逐特征 residual 独立复测（#205）

## 任务摘要

复测 #204 观察到的 top visual residual 与图像强边缘空间关系，使用相同 VIO/EGO/PX4 profile 和 run-local VINS binary，更换 ROS domain 与 Gazebo partition，保持只读双目图像 observer。

## 用户约束

- 仍只推进单 D435i 仿真导航；无真值进入最终组合。
- PX4 控制发布者独占约束继续由 uav_px4_bridge 保持。
- normalized_cost=1.0、PX4 freshness 与65 ms source-future 限值不变。
- 观察到相关性不自动等于因果；不得伪称 P5 通过。

## 结果与决定

- #205 使用 domain229、独立 Gazebo partition 和新 epoch；自维护包构建6/6通过，VINS安装复用 #203 固定二进制。
- 前置门、起飞和 zero-offset goal 均通过；normalized_cost 首次为1.01641 后由现有质量门中止，最终 landed/disarmed。
- 第二次 top20 residual 复测中，20/20 的边缘切向分量大于法向；15/20 在拟合强图像边缘1 px内，最大距离1.95 px，16/20 切向符号相同。相较 #204（20/20 在1 px内且同向），切向主导关系复现，但边缘距离与符号并不完全相同。
- 这加强“边缘方向残差”可重复线索，但仍未证明唯一根因。下一步扩展 run-local 诊断输出以包含全部二维 visual residual blocks，确认现象是否超出排名前20项。

轻量证据：[P5 图像/residual 关联独立复测 #205](../../progress/evidence/p5-vins-feature-image-correlation-repeat-20261020-205.json)。摘要本身不作为测试证据。
