# P2 EGO message_filters 输入回调诊断 #291

对应对话摘要：[2026-10-20-047](../../collaboration/dialogues/2026-10-20-047-p2-ego-filter-callback-receipt.md)。轻量证据：[p2-ego-filter-callback-receipt-20261020-291.json](../evidence/p2-ego-filter-callback-receipt-20261020-291.json)。完整源码、构建、运行与哈希清单见 `artifacts/runs/p2-ego-filter-callback-receipt-20261020-291/run-report.json`。

## 结果

- 从 #289 run-local源码副本开始，按 `0012→0013→0015` 次序应用 timeout上下文、同步回调和既有 message_filters 输入计数诊断，并保留 unknown-as-obstacle候选 `0020`。canonical vendor与标准依赖链不变。
- `patch --dry-run`顺序通过；Jazzy fresh build完成 `traj_utils`、`plan_env`、`path_searching`、`bspline_opt`、`ego_planner` 五包。`ego_planner_node` SHA-256 `f884323cbc003b18f5146ea6f1bc681c9262453b748bed9bb652abd883620b00`；`libplan_env.so` SHA-256 `58e59c48d5263a7fb34b5702520ed6e64002295e1997b9cb47344dc7fba8d9dc`。
- #291使用新 ROS domain 138 与新 Gazebo partition，约70秒planner-only运行无 `odom or depth lost`；独立位姿观察者收到1,204条样本与70条心跳，源戳单调，最大header-stamp间隔66 ms。目标探针收到120条 spline，后续定位因`normalized_cost_exceeded`关闭 mapping gate。没有PX4、控制节点/话题或真值输入。
- 因 timeout计数只在 timeout warning里打印，0条warning意味着没有可分析的内部 pose/depth count窗口。本轮验证了诊断构建和无超时运行，未区分 filter reader或同步器根因。
- #290实际复用#289的ROS_DOMAIN_ID=136与Gazebo partition；前置检查时没有项目容器/节点，但并非跨domain独立试验。#291换新domain后无超时；由于domain、诊断overlay和run变异同时变化，不做因果结论。

## 验证与局限

- 诊断补丁以隔离源码副本应用；VINS/EGO来源commit与候选patch哈希记录于run manifest。其余文件 SHA-256 与字节数均列于run report。
- #291 observer SIGINT退出写入 stopped marker，无清理错误；容器运行成功。没有独立深度图观察者，因此无超时时只能确认EGO timeout为零和外部pose stream连续，不能报告EGO内部两路回调计数。
- 不做地图覆盖、规划净空或 trajectory tracking推断；unknown patch仍不进入canonical依赖链。

## 状态与下一步

GOAL C仍pending。下一步让run-local EGO filter callback counts按稳态时间周期输出，并在新domain重复planner-only run；必要时同一binary做对照，确保能比较内部pose/depth receipt、同步计数、MapStatus与独立位姿observer。然后继续实现并验证可回读的occupied/free/unknown地图状态。P2阶段状态不变，GOAL A–H未完成。
