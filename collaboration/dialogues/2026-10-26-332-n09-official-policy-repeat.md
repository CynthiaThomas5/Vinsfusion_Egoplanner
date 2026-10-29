# N09 官方规则下的独立 PX4 冷启动（#332）

用户已明确要求按 FAST Lab 官方规则实施，并采用单 D435i，不加入后下视相机。按 N09 原验收规划，使用官方起飞状态门和 `inflated occupied` 碰撞语义，在真实 PX4 SITL 完成单程 3D/yaw 目标；抵达即结束，不隐含返航。保持 localization health 阈值不变。

固定运行 SHA256：`6b95d5fe48ea17f41649947547ccab4bf0798e9907a565dbb2dfd65cf0579f30`。重复01和02的独立 PX4/VINS/map/goal 身份均不同，两个 N09 evaluator 都通过。重复03起飞并进入 ACTIVE，但 VINS 在 source t=79.036 s 出现一次 normalized cost 1.100656（门限1.0）的视觉残差尖峰，health 锁存后 PX4 安全降落；不计通过。特征数量和 solver finite/usable 状态正常，下一帧 cost 回到0.4888；底层视觉不一致的成因仍未知。无时钟回退、无违规接触；落地、disarm、控制关闭和终态无设定点均经独立读回。保留不通过结果，不改门限。

最终通过的独立冷启动为 repeat01、repeat02、repeat04，三者都使用同一运行与目标哈希，三个 VINS epoch/map_id/goal_id 各不相同；每次 11/11 任务检查通过，无违规接触并独立确认 landed/disarmed。repeat03 的一次 VINS normalized-cost 锁存仍保留为失败，不计成功，且未通过改门限规避。N09 已通过；next_goal 更新为 N10，但用户本轮授权范围止于 N09，N10 未启动。详细报告：[证据](../../progress/evidence/n09-official-policy-qualification-20261026-332.md)、[变更记录](../../progress/changes/2026-10-26-332-n09-official-policy-qualification.md)。
