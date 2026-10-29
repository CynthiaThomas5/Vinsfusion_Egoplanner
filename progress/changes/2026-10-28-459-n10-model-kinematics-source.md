# N10.3/#459：修正并验证 PX4 根模型 observer 来源

## 改动

- `tools/sim_runtime.sh` 在 N09 contact overlay 与 `D435I_N10_KINEMATICS=1` 同时启用时，将 `PX4_GZ_MODELS` 指向本轮 run-local overlay；未启用 observer 时仍沿用原模型根目录。
- 启动时写入 `n10-px4-model-source.json`，记录直接选中的 SDF 路径、SHA、解析状态及 observer 插件条数。该文件仅作为离线证据，不影响目标提交或控制。
- `kinematics_evidence.py`、区间净空评估器和总验收器绑定模型来源报告、overlay manifest 和实际 SDF 哈希；缺失或不匹配时离线判为证据不足。
- 增加模型来源缺失、SHA 不符和路径不符的定向测试。

## 验证

- no-flight SITL `n10-20261028-459-kinematics-startup-diagnostic`：PX4 实际根 SDF 指向 run-local overlay，SHA 与 manifest 一致，根模型含一个 observer；Gazebo topic 发布，5.10 wall s 内记录 854 条、元数据错误 0、源戳单调、最大间隔 0.004 sim s。
- 独立结束读回：bridge DISABLED、PX4 disarmed/landed、control disabled、控制话题零样本、无任务/规划事件；随后 `project.sh stop` 与容器退出码均为 0。PX4 native preflight 报告 false，但本轮未请求起飞，也未新增项目拒绝规则。
- `PYTHONPATH=tools python3 -m unittest tools.test_n10_kinematics_evidence tools.test_n10_interval_clearance_bound tools.test_n10_acceptance`：40 项通过。
- `PYTHONPYCACHEPREFIX=/tmp/n10-459-pycache python3 -m py_compile tools/debug_truth/kinematics_evidence.py tools/debug_truth/evaluate_n10_interval_clearance_bound.py tools/debug_truth/evaluate_n10_acceptance.py tools/test_n10_kinematics_evidence.py tools/test_n10_acceptance.py`、`bash -n tools/sim_runtime.sh`、`git diff --check`：通过。

## 结论与下一步

#459 的 observer 来源与短时传输诊断通过；该短记录不证明完整任务覆盖或连续净空。N10 仍 `in_progress`。#460 复用 #458 正常综合任务，仅补齐整段物理步账本；不注入故障，不计 N15/N16 正式次数。
