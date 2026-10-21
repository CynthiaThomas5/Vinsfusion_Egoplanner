# GOAL C EGO 全局规划失败冷却 #315

对话摘要：[2026-10-20-064](../../collaboration/dialogues/2026-10-20-064-p2-ego-global-plan-retry-cooldown.md)

本次实质修改：

- 新增隔离第三方补丁 `dependencies/patches/ego/0028-global-plan-retry-rate-limit-experiment.patch`，使用 `steady_clock` 和现有 `fsm/thresh_replan_time`，仅节流 `SEQUENTIAL_START`、`GEN_NEW_TRAJ` 的 `planFromGlobalTraj` 失败重试。补丁可在 #314 源树上 `git apply --check`，应用后两个改动文件与实验树逐字节一致；没有修改 `src/vendor/ego_planner` 或 `dependencies/sources.json`。
- 建立 #315 的隔离 Release overlay，五个 planner 包构建通过；真实 `GridMap`/`AStar` endpoint 用例4/4通过。构建报告、来源清单和运行素材位于 `artifacts/runs/p2-ego-global-plan-retry-20261020-315/`。
- planner-only run 与 #314 使用相同 planner config、运行参数、生成 SDF 和墙面相位；D435i/VINS运动样本不是精确回放。#315 观测到22个失败日志簇，中位起始间隔1.009 s；20次 `GEN_NEW_TRAJ` 自循环；A*汇总199次（init 113，collision 86），相对 #314 的20,385次按各自探针窗口归一化低约99.1%。旧“drone is in obstacle”逐次错误为0。
- 探针收到两个不同轨迹ID的 B-spline。无 PX4、controller、trajectory server、控制或真值 topic，未执行轨迹，也未调用 occupancy snapshot。该结果只说明实验重试节奏发生变化，不能证明曲线安全。

验证：`bash artifacts/runs/p2-ego-global-plan-retry-20261020-315/build-and-test-container.sh`（五包 Release 构建通过；endpoint GTest 4/4）、`bash artifacts/runs/p2-ego-global-plan-retry-20261020-315/run-container.sh`（planner-only目标探针成功接收 spline）、`bash -n` 三个 runner、`git apply --check` 补丁应用基树、`python3 -m json.tool progress/evidence/p2-ego-global-plan-retry-20261020-315.json`。

证据：[报告](../../progress/evidence/p2-ego-global-plan-retry-20261020-315.json)、[build report](../../artifacts/runs/p2-ego-global-plan-retry-20261020-315/build-report-0028.json)、[source manifest](../../artifacts/runs/p2-ego-global-plan-retry-20261020-315/source-manifest-experiment-0028.json)。局限：未捕获 spline 发布同刻地图、未测 unknown/净空、没有回放、执行或 PX4 验收；其他阶段状态不变。下一步在 B-spline 订阅点附近请求只读快照并离线评估路径采样。
