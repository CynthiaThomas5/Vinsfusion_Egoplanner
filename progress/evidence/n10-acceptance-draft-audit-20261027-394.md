# N10.4/#394 acceptance 草案与离线判断器审计

## 结论

N10.4 草案与回放判断器已通过本轮静态/归档验证，状态仍为 **draft**，revision 3；这不是 N10.4 正式冻结或 N10 通过。新增的 tracking-clearance 指标保持 `INSUFFICIENT`，因为现有数据不能支持场景相关的跟踪误差门限。全程没有 SITL。

唯一入口 [config/acceptance.json](../../config/acceptance.json) 仍声明离线评估、真值只读、无起飞/取消/暂停/降落控制门。0.60 m 跟踪 P95 与 1.20 m 单样本最大值保留为诊断候选，`acceptance_thresholds` 仍为 null；0.10 m 净空候选及故障、资源项目的原门槛/不足状态没有放宽。

## 本轮变更

- 跟踪评估现接收 schema v2 的逐点平移净空下界报告，并校验 run id、runtime-contract SHA、goal/epoch/map identity 及其源输入哈希。无报告、旧 schema、错身份或源哈希不匹配均为 `INSUFFICIENT`。报告有效时仍输出诊断统计，不自动判 PASS。
- Acceptance 单独输出 `ego_tracking_clearance_budget`：公式沿用相同时间样本、同一实际姿态扩展包络下的“命令净空 − 欧氏位置误差”。负值仅表示保守标量预算不能证明正余量，不判成碰撞；指标无接受阈值，且无运行时效果。
- Acceptance draft 加入综合采集合同：使用 VINS 配置引用的左右目和 IMU topic、记录 source/receipt 时间与帧身份、保存用于漂移诊断的图像/IMU 内容；保存身份绑定 raw/inflated 快照、查询请求与半径回显、每 4 ms 真值/接触、重规划、资源/队列和终态记录。记录失败不得拒绝或中止任务，结果只能不足。
- 修复验收脚本直接执行时导入仓库模块失败的问题。另修正总评：runtime identity 不匹配时仍保留已观察的直接 goal/safety FAIL；identity 自身另列为 `INSUFFICIENT`，不互相覆盖。

## 归档回放

| 运行 | 总评 | 到达 | 跟踪几何项 | identity/inputs | 解释 |
| --- | --- | --- | --- | --- | --- |
| #381 | FAIL | FAIL | INSUFFICIENT | 两者匹配 | 保留原 2.34 sim s 联合窗口失败；跟踪候选超出但无几何接受门限 |
| #385 | INSUFFICIENT | PASS | INSUFFICIENT | 两者匹配 | 到达与驻留通过；全程 physics-step/接触几何证据仍不完整 |
| #391 | FAIL（部分行回放） | 不重算 | INSUFFICIENT | 两者匹配 | 全机净空/接触行记录 86 个禁止接触，fault 行确认紧急 closeout 不能代替原生落地 |

#381/#385 的完整回放文件位于 `artifacts/runs/n10-20261027-389-archive-reuse/acceptance-replay-{381,385}-v2.json`。#391 只保存相关指标行，报告明确不补造缺失的聚合分段：`acceptance-diagnostic-row-391-v3.json`。当前 evaluator 将 #391 tracking report 的 run、contract、goal/epoch/map 和全部源文件哈希判为匹配；由于无几何接受门限，仍返回 `INSUFFICIENT`。

## 验证

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tools.test_n10_acceptance tools.test_n10_clearance`：26 tests passed。
- `PYTHONPYCACHEPREFIX=/tmp/codex-pycache-n10 python3 -m py_compile tools/debug_truth/evaluate_n10_acceptance.py tools/debug_truth/evaluate_n10_tracking_clearance.py tools/test_n10_acceptance.py tools/test_n10_clearance.py`：通过。
- `python3 -m json.tool config/acceptance.json`：通过。
- #381/#385 通过 `tools/debug_truth/evaluate_n10_acceptance.py` 实际 CLI 重放；#391 的 tracking/clearance/contact/fault 行由现 evaluator 对原归档直接复算。
- 静态引用检查确认 acceptance 配置只被离线 evaluator、arrival evaluator、测试和 runtime manifest 读取；未接入起飞或控制状态机。

轻量机器报告：[JSON](n10-acceptance-draft-audit-20261027-394.json)，SHA-256 `c05cf33c004881c15f4a1a841077408a6e69749499931d3d7130f3cf5e587eef`。配置 SHA-256 `eec909ef9c97b4e390d5ec7a880fdf26a6669d9b28ae82328e52b8c7ff175d4d`；该哈希只标识当前草案输入，不是最终冻结身份。

## 下一步

N10.4 草案机制已验证，数值依据仍待综合校准。下一项 N10.3/#395 先补综合运行的连续传感器 receipt/图像记录与 query echo 输入，运行只读模式、缺数据处理和启动后 manifest 身份检查；完成格式/工具验证后再冻结本轮运行身份。N10 保持 `in_progress`，N15/N16 正式运行仍在冻结后。
