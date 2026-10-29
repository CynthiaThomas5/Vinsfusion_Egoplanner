#272 N08 observer 假设受 N05 扫描门控阻断

- 按 #272 假设在 runner 中将未使用 `/grid_map/occupancy` PointCloud2 observer 的销毁时点移至 raw-map capsule/home-pad admission 之后、offboard enable 之前。修改后的门控单测12/12通过，3个Python文件内存编译通过。
- Fresh run 初始N05 raw map仍按既有规则拒绝，离线重算一致。支架扫描在10/15阶段因`accel_bias_norm_exceeded`停止，bias最高0.15522m/s²超过原0.15门限；normalized cost 0.572。未到N08 runner，observer变化未执行。
- 夹具确认detach并从Gazebo删除，PX4 landed/disarmed；直接读回bridge DISABLED/control0后停止仿真，project stop exit0，容器exit0。
- 证据：[`N05前置拒绝报告`](../evidence/n08-observer-prerequisite-refusal-20261025-272.md)、[`安全读回`](../../artifacts/runs/n08-20261025-272-observer-pre-enable/final-safety-readback.json)。对话摘要：[`#272`](../../collaboration/dialogues/2026-10-25-272-n08-observer-prerequisite-refusal.md)。
- 后续#273只做一次fresh N05重复性判别：同一固定profile下检验bias失败是否epoch相关。若重现同一返回平移bias越界，就停掉重复扫描并分析输入；通过才继续起飞回调负载试验。
