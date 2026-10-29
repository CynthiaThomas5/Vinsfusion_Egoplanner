#267 对话摘要

- 用户要求返航时禁止倒飞：机头原地旋转约 180°，确认回正后，再按 EGO 机头前向规则飞返航路径。
- #267 已完成 N05 入口和 0.6 m 前向 EGO 制动测量。单次实测停止距离为 0.28794 m，参考／实际峰值速度约 0.0808／0.0810 m/s。
- 前向目标 action 与连续样条证书通过；在定点 yaw 前，fresh raw map 对 1.03062 m 转向 hold 球查询发现 30 个 unknown，0 个 occupied。控制器 fail-closed，没有 yaw 或返航。
- 起飞前同身份 raw map 将同一 30 格分类为 free；飞过 0.6 m 后，它们变为 unknown，集中在当前 +x 航向后方。证据证明分类变化和空间位置，不唯一证明相机遮挡或 mapper 内部原因。
- 返航必须先转向、获取更新融合图、检查 forward corridor，再由 EGO 执行；不能借旧图或把 unknown 当 free。
- 下一子项 #268 计划在原制动测量段结束后，若转向球仍因 unknown 被拒，只增加一个经 fresh raw map capsule 认证的 0.22 m 前向 EGO 定位目标；随后重查转向球、原地转头、等 fresh map、检查返航 corridor。门限保持不变，任何检查失败都落地。
