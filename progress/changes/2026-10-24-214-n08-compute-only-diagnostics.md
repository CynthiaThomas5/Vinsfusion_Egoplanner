# #214 N08 compute-only 失败诊断改进

- 变更：runner 在等 READY 时同时观察 action 终态，保存 task-level outcome/reason；异常路径取消仍活动的 action，再禁用 bridge，明确记录 `landed_and_disarmed` 与最终桥接状态。增加 ROS-free action-result 序列化 helper。
- 变更：compute-only evaluator 要求 runner 终态 `result=PASS` 才可通过，并在评估输出保留失败原因；防止仅凭其他记录字段齐全把失败运行判成通过。
- 配置：新增 `config/components/navigation/n08_compute_only_known_free_goal.json`，将单一候选目标设为 ENU -Y 0.4 m。它来自 #213 frozen map 的 offline raw sphere 查询，只供 compute-only；每次冷启动仍需 fresh live admission，不能执行。
- 验证：`tools/project.sh test`：284 项通过；`python3 tools/test_n08_compute_only.py`：3 项通过；`python3 tools/test_odometry_evaluation.py`：7 项通过；`py_compile` 与 `git diff --check` 通过。
- 局限：改动后尚未运行 compute-only 冷启动；候选点的 live query、READY 轨迹、取消／hold、落地都未验证。没有降低半径／未知门槛，没有执行平移。
- 下一步：新冷启动进行 N05 支撑／释放与 fresh current-area admission，然后对 -Y 0.4 m 目标做 compute-only；任一 live gate 拒绝即保持不运动。
- 对话摘要：[N08.2d #214](../../collaboration/dialogues/2026-10-24-214-n08-compute-only-diagnostics.md)
