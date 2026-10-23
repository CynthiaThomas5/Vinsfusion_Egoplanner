# #076：loop_fusion yaw约束与输出姿态审查

**结论：**074-02运行了IMU模式4DoF位姿图。代码把回环yaw残差除以10，而局部相邻VIO yaw残差未缩放；最终图中四条回环的相对yaw残差都只小幅下降。这是“位置改善明显、yaw改善有限”的强代码／数据一致解释，但现有单次记录不能证明它是唯一原因。

## 运行与源码身份

只读检查运行`real-loop-20261022-074-02`。会话配置[ `vins.yaml`](../../artifacts/runs/real-loop-20261022-074-02-stack/session/vins.yaml)中的`imu: 1`，哈希与[observer manifest](../../artifacts/runs/real-loop-20261022-074-02/loop-observer-manifest.json)相符；`pose_graph_node.cpp`明确调用`setIMUFlag(true)`。该节点实际运行二进制哈希与manifest记录一致。当前固定vendor文件`pose_graph.cpp`、`pose_graph.h`、`pose_graph_node.cpp`的哈希均匹配`dependencies/sources.json`，因此下列静态代码结论绑定074-02的运行版本。

固定源码位置：[`pose_graph.cpp`](../../src/vendor/vins_fusion/loop_fusion/src/pose_graph.cpp#L53)的模式选择、4DoF因子和drift更新；[`pose_graph.h`](../../src/vendor/vins_fusion/loop_fusion/src/pose_graph.h#L201)的两类误差因子；[`pose_graph_node.cpp`](../../src/vendor/vins_fusion/loop_fusion/src/pose_graph_node.cpp#L106)的`odometry_rect`发布路径。

## 代码路径

- VIO/IMU输入选择`optimize4DoF`。状态只有位置XYZ和yaw；roll与pitch取自当前VIO姿态作为已知量，适合由IMU保持重力方向。
- 局部同序边以`FourDOFError`构造，yaw残差为相邻yaw差与原始VIO相对yaw之差，不除以其他尺度；这类边没有robust loss。
- 闭环边使用PnP估计的相对位置和`relative_yaw`。`FourDOFWeightError`的前三个平移残差不缩放，yaw残差先乘权重1，再除以10；该闭环残差块外还套`HuberLoss(0.1)`。因此回环yaw相对局部相邻yaw项明显较弱，Huber是否进一步降权取决于该边完整残差范数，本次没有逐因子权重日志。
- yaw变量与`Utility::R2ypr`以度为单位，归一化范围是±180°；`/10`作用于度值，不是弧度。
- 优化后用当前图中keyframe的优化yaw与VIO yaw差生成yaw-only `r_drift`，再求平移偏移。`on_odometry`将该变换乘到之后收到的原始姿态并发布`odometry_rect`；已经发布的过去样本不回溯重发。因此输出姿态并未被丢弃，但每次可应用的旋转修正受当前图解及4DoF模型限制。

## 074-02数值对照

最终图快照revision为`[101,4,4]`。下面把最终优化图中相连关键帧yaw差与该边PnP yaw目标比较；yaw采用`atan2(R10,R00)`并wrap到±180°。

| 回环边 | PnP yaw目标 | Raw VIO相对yaw | 最终图相对yaw | 残差：优化前 → 后 |
|---|---:|---:|---:|---:|
| 5→63 | 0.235° | 0.741° | 0.685° | 0.507° → 0.451° |
| 7→68 | −0.005° | 0.693° | 0.634° | 0.698° → 0.639° |
| 4→92 | −0.185° | 1.116° | 1.039° | 1.300° → 1.224° |
| 6→94 | 0.155° | 1.102° | 1.025° | 0.947° → 0.871° |

这些是四条PnP相对yaw因子在**最终**图快照中的残差，不是每次独立优化刚结束时的值。它们显示回环约束都向目标方向拉动了图，但没有消除沿途累积相对yaw。独立相对几何核验的完整姿态误差为0.109–0.317°，所以残差不能简单归结为四条PnP边完全错误。

实际`odometry_rect`样本中，raw→corrected的总旋转差依次为0.0112°、0.0249°、0.0535°、0.0777°，总平移差为3.40、4.20、8.12、7.56cm。相邻全局变换之间新增的旋转量更小，依次为0.0112°、0.0137°、0.0286°、0.0242°；平移变更依次为3.40、1.94、3.94、0.96cm。#075离线误差比较的全程yaw RMSE为0.810→0.791°，第7轮返航最后10秒为1.365→1.287°。这与代码中的弱回环yaw因子相符，同时说明yaw误差仍然累积。

## 解释边界与可证伪验证

当前最强假设是：1/10 yaw残差缩放使图优化优先满足相对强的顺序VIO约束与平移闭环，回环只能对yaw作小幅调整。另有HuberLoss(0.1)、PnP相对yaw误差，以及5次Ceres迭代上限等可能影响；运行没有记录逐因子loss weight或Solver Summary，所以静态审查不能把假设升格为根因。

建议的下一小目标是做一次纯离线、单变量回放：

1. 使用074-02保存的最终VIO关键帧、四条PnP边及完全相同的局部边，在`/10`缩放、Huber(0.1)、原初始化与5次迭代下先复现已记录最终图和第7轮修正结果。复现不达预先设定的数值容差则停止，不解释A/B结果。
2. 仅把回环yaw残差缩放从0.1改为1.0；平移边、相邻VIO因子、Huber、初值和数据全部固定。
3. 比较两组的回环yaw残差、第7轮最后10秒yaw RMSE及位置RMSE。若yaw残差与真值yaw RMSE同步下降且位置误差未明显恶化，支持“回环yaw权重过低”假设；否则该假设不足以解释有限的yaw改善。

该验证只拟定为第9个小目标，尚未实施／获批。本轮没有改代码或启动仿真，故不运行构建／软件回归；loop评估原有13项检查均为true，后端没有真值输入、控制或TF输出。机器可读数据及哈希见[JSON报告](loop-yaw-weight-audit-20261022-076.json)。
