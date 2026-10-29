# N09.3：采用 FAST Lab 官方起飞与碰撞规则（#331）

Goal 模式继续 N09。用户已明确授权改为官方规则，见[对话摘要](../../collaboration/dialogues/2026-10-26-331-official-ego-policy.md)。具体规则、固定源 commit/hash 与平台适配边界见[对照文档](../../docs/official-ego-policy.md)。已有用户修改保留；不提交或推送。

## 实际改变

- `task_supervisor.json` 唯一选择 `official_ego`。GOAL/执行书/README/运行说明/N09 测试计划显式记录用户批准的策略修订。
- 独立起飞移除 N05 raw-known-free 五阶段和支架扫描前置；状态门保留 fresh VINS/PX4、landed/disarmed/control disabled、静止≤0.1m/s。导航目标在 bridge ACTIVE 后才能转发。
- 导航从大半径 raw 球改为官方 inflated occupied 零半径点谓词；unknown 仍标为 `unobserved_not_occupied`，没有伪造已知 free。
- 补丁 0049 恢复上游 `getInflateOccupancy` 的 inflated-layer-only 判据；官方模式不再追加项目 raw-free 全曲线/terminal-hold 球门禁。原生 EGO 碰撞与重规划保留。raw query/snapshot 仍准确保留 unknown。
- 标准 mission 与 N09 共用当前策略；旧 N08 专项 runner 仅作显式历史实验。地图外 action 拒绝诊断移至任务落地后，避免为独立起飞增加地图准入前置。
- 新增官方策略单测与 ROS action 集成；旧 known-free 集成明确使用临时历史配置，避免混淆两种 unknown 语义。

## 验证完成（#331 implementation；N09 flight qualification in #332）

- 固定官方源码和提交已保存到 `artifacts/runs/n09-official-policy-331/official-source-manifest.json`，对照与适配边界见 [`docs/official-ego-policy.md`](../../docs/official-ego-policy.md)。
- `bash tools/project.sh build ros` — 17 个 ROS 包构建成功；日志为 `artifacts/runs/n09-official-policy-331/build.log`。
- `bash tools/project.sh test` — 397 项 Python 测试通过，历史 strict-unknown ROS action 集成与当前 official-ego ROS action 集成都通过；日志为 `artifacts/runs/n09-official-policy-331/tests.log`。
- `python3 tools/fetch_dependencies.py --source ego_planner --target /tmp/n09-official-331-replay` — 0049 前固定补丁完整重放成功；日志为 `artifacts/runs/n09-official-policy-331/replay.log`。
- 实际在线官方 map-policy probe 验证 raw unknown 保留但不独立阻断、inflated occupied/out-of-map/旧 epoch 拒绝；结果在 pilot01。policy pilot 的旧 runtime 不计 N09 三次重复。
- N09 最终飞行 qualification 由 #332 报告：同一冻结 runtime `6b95d5fe48ea17f41649947547ccab4bf0798e9907a565dbb2dfd65cf0579f30` 下 repeat01、repeat02、repeat04 三次独立成功；repeat03 一次真实 VINS normalized-cost lockout 失败保留，不计入成功数。N09 11 项独立评估、三维/yaw 到达、接触、时效和落地末态均通过。

N09 limited exit 已通过；N09 的证据不表示后续 N11–N14 多场景正式验收或最终 A–H 回收已通过。
