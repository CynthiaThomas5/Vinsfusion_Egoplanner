# N08 #305 负侧观察与前向准入结果

## 结果
- 15/15 支架阶段完成，负Y视角到达并回中。最后健康检查有helper warning；后续after、post-release与mission current-area N05 online/offline均同identity通过，地面平面z≈−0.35m。
- mission preflight通过；N08 motion-cancel runner在目标/enable前因unknown拒绝。N05 home pad通过；取消走廊start hold 105 unknown、首扫掠136、terminal hold14；普通0.6m capsule首查询217。action_goal_sent=false。
- 同identity原始图显示unknown集中在x≈−1.05m后向薄层；这解释了负Y侧视仍不足。独立PX4末态DISABLED、disarmed/landed、control0，容器Exit(0)。
- evaluator因无运动数据报源戳非递增和缺少 odometry-evaluation，作为次生诊断保留。

## 决策
#306在既有profile基础上增加yaw−π后向观察，并经−π/2分段回中。所有健康与地图门限不变；只有post-release/current-area N05与N08方向/hold门均过后才进入motion-cancel。

证据：[运行报告](../../progress/evidence/n08-negative-y-forward-corridor-unknown-20261026-305.md)。
