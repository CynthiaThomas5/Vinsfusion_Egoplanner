# #076：loop_fusion姿态修正只读审查

[用户批准与约束](../../collaboration/dialogues/2026-10-22-076-loop-yaw-weight-audit.md)。本轮审查loop_fusion旋转约束到修正里程计输出的当前路径，不改源码、补丁、参数或控制，不启动仿真；保留既有未提交修改。正式P0–P6／S1–S6状态未变。

运行身份已核对：074-02 immutable session的`vins.yaml`包含`imu: 1`，其SHA-256与manifest一致；运行manifest中的loop_fusion binary SHA-256与本地安装二进制一致。`pose_graph.cpp`、`pose_graph.h`和`pose_graph_node.cpp`文件哈希与`dependencies/sources.json`锁定值一致，代码行号对应运行所用固定源码。

数据审查使用074-02最终图快照`revision=[101,4,4]`，将四条已接受边的PnP yaw目标与raw VIO／最终优化keyframe yaw做比较。残差分别从0.507→0.451°、0.698→0.639°、1.300→1.224°、0.947→0.871°；变化方向均符合闭环约束，但仍有0.451–1.224°残差。上一轮误差比较中全程yaw RMSE仅0.810→0.791°，第7轮返航末10秒为1.365→1.287°。

主要可检验解释来自当前4DoF因子：回环yaw残差显式除以10，并且回环残差块使用HuberLoss(0.1)；同序相邻VIO边的yaw残差没有这项缩放，也没有robust loss。优化结束后，IMU模式只由当前keyframe yaw差生成`r_drift`，再将该变换乘到后续`odometry_rect`姿态。这里存在明确的yaw约束权重差，可解释小姿态改变量；但不构成充分因果证明。PnP yaw精度、Huber实际权重和仅5次Ceres迭代同样可能影响结果，运行记录未保存逐因子鲁棒权重或收敛摘要。

最小验证建议：仅对保存的074-02最终4DoF图做离线重放。先以当前yaw残差缩放0.1复现已记录优化状态和第7轮输出；基线未复现则停止解释。复现后只将回环yaw残差缩放改为1.0，保持其他约束、Huber、初始化、迭代上限和数据不变，对照loop yaw残差、第7轮yaw RMSE及位置RMSE。该干预是第9目标候选，尚未执行或获批。

证据及逐边数值见[只读审查报告](../evidence/loop-yaw-weight-audit-20261022-076.md)和[机器报告](../evidence/loop-yaw-weight-audit-20261022-076.json)。没有软件构建或回归，因为这轮未改代码；`git diff --check`在收尾核验。
