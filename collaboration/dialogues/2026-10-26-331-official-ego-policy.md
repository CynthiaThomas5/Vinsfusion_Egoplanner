# 采用 FAST Lab 官方规则（#331）

用户暂不采用后下视第二颗 D435i，并明确要求“按照高飞官方的规则实施，把该改的环节改掉”。本次授权覆盖独立垂直起飞和 EGO 的未知空间碰撞策略调整；不再等待 #330 的政策选择。

核对官方 Fast-Drone-250 操作流程及 PX4CtrlFSM、ego-planner grid_map/optimizer 后确认：独立起飞不查询 N05 raw-known-free 包络；导航在起飞悬停后触发；EGO 的原生 inflated occupied buffer 不把 unknown 单独标为碰撞。官方教程要求操作人员监督和接管，公开代码没有自动证明后方盲区安全。

实施选择：保留现有单 D435i/VINS/ROS2/PX4 唯一 bridge 集成和已修复的 action/epoch/时间行为，采用官方起飞与 inflated occupied 谓词；停用当前导航链中额外 N05 raw-free、目标大球及全曲线/hold raw-free 门；raw map 诊断仍区分 unknown。用户授权同时记录进 GOAL/执行书/当前状态，以免旧合同与运行行为矛盾。固定官方源提交、哈希、补丁及实际验证另存 evidence/changes。

N09 的独立三维/yaw 真实到达、零违规接触、持续新鲜数据、三个独立冷启动成功出口仍需当前版本证据。旧拒绝/飞行报告保留原适用范围，不改写为当前版本通过。
