# N08.261：原地转向后前向返航

对话摘要：[2026-10-25-261](../../collaboration/dialogues/2026-10-25-261-n08-yaw-first-return.md)

## 目标与已有基础

#260 已测得前向 0.6 m EGO 目标的真实停车曲线，但原航向返航 action 被拒 `map_query_unknown`，飞行器随后在前向终点安全降落并解除上锁。该拒绝没有定位 unknown 体素或证明根因是后向视野。用户明确要求返航不能倒飞：先机头旋转 180°，再让 EGO 按机头前方规则飞回。

## 改动

- `dependencies/patches/ego/0045-stationary-yaw-only-return.patch`：为零位置位移、显著 yaw 改变的导航目标生成位置恒定的 EGO B 样条，加入同一 full-curve raw-map 与 terminal-hold 证书。该改动补齐了常规 `planGlobalTraj` 的零持续时间及 `reboundReplan` 小于 0.2 m 直接拒绝问题。
- `dependencies/sources.json`、EGO 补丁说明：将 0045 加入规范链，记录补丁哈希与最终源文件哈希。
- `tools/run_n08_braking_trial.py`：停车保持后先核验转向区域、执行 EGO 定点 180° yaw 目标；等待转向后的新鲜深度与融合，再核验返航 capsule 与机体系前向速度方向，然后向 EGO 提交原 home 位置目标。失败路径继续取消当前 action、关闭桥接并着陆。
- `tools/debug_truth/evaluate_n08_braking.py`、`tools/test_n08_braking_evaluation.py`：用独立真值审计转向位置偏移、转向顺序、返航期间速度相对机头方向；增加 forward/backward 方向对照。
- `config/components/navigation/n08_forward_braking_trial_goal.json`：将禁止倒飞及 yaw-first 返航写入本次专用准入说明。
- #261 构建指纹用于运行时锁定 0045 编译后的 EGO 二进制；保留 #251 的 moving-trajectory 动力学源证据，忽略其旧 EGO binary hash，因为 #261 明确记录了新二进制。

## 验证

- `bash tools/project.sh build ros`：17 包完成，EGO 编译成功。
- `PYTHONPATH=. python3 -m unittest tools.test_n08_braking_evaluation`：9 项通过。
- `PYTHONPYCACHEPREFIX=/tmp/codex-pycache python3 -m py_compile tools/run_n08_braking_trial.py tools/debug_truth/evaluate_n08_braking.py tools/test_n08_braking_evaluation.py`：通过。
- 0045 在临时的 `src/planner/...` 上游布局重放成功，结果 SHA256 与 `dependencies/sources.json` 一致。
- `python3 tools/project_status.py`：结构检查通过；`bash -n tools/mission_runtime.sh` 与 `git diff --check` 通过。

完整构建指纹、验证范围和 SHA256 见[证据报告](../evidence/n08-yaw-first-return-build-20261025-261.md)及其 JSON。

## 限制与下一步

#261 不运行 SITL，不能证明地图允许转向、定点 yaw 曲线能由 live EGO 执行、实际转向保持位置，或真实返航没有倒飞。下一步 #262 使用全新仿真、新鲜 N05 admission 与 same-run raw map 执行一轮完整制动、转向、前向返航和着陆。原始地图、真值、run manifest 与最终结果保存在对应 `artifacts/runs/<run_id>`。
