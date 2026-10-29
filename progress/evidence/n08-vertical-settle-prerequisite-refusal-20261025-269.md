#269：N05 扫描在起飞前因定位健康门中断

## 本轮代码变化

保留原起飞后 PX4 三维总速度 `<0.03 m/s` 稳定 1 s 的判断，并增加 `|vz|<0.01 m/s` 稳定 1 s 才发送首个 EGO 目标。0.01 m/s 仅是本轮沉稳假设的运行前置条件，不是曲线或 N08 验收门限；5 cm 曲线界、速度 profile、N05 admission 与 unknown 语义均未改变。门控定向测试 12/12 通过，三个 Python 文件内存语法编译通过。

## SITL 结果

新冷启动 epoch `6f9536ea2ba84060af79fcf49d383e85`。初始地图的地面 raw occupied 样本不足，但流程继续执行 N05 支架扫描。扫描完成 10/15 阶段，在返回视角的第 11 阶段（目标 `[0, 1.0, 0, 0]`）因定位状态锁存 `normalized_cost_exceeded` 而中止。状态报告 cost `1.06881249`，高于现有 `max_normalized_cost=1.0`。因此没有 post-release 准入、没有 mission current-area gate、没有解锁、起飞或 EGO 目标；本轮未测试 #269 垂向沉稳门。

扫描器确认支架已脱离、PX4 landed，场景中支架模型已移除。中止时 bridge `DISABLED`、control disabled、disarmed、landed；直接 PX4 读回 `arming_state=1`，LandDetector `landed=true`。`project.sh stop` 返回 0，容器之后为 `exited`，没有继续运行。

## 证据局限与下一步

已归档的 `fixture-vins.jsonl` 按定位健康节点公式重算，最大 normalized cost 为 `0.67345692`，未含能解释 `1.06881249` 的触发样本；`fixture-trace.jsonl` 末段仍记录有效状态。因此当前可确认“健康门发生 fail-closed 锁存”，不能从已保存的原始指标归因到特定残差，也不能判断该峰值是否瞬时。门限不调整。

下一步 #270 使用新 cold start 和同一 N05 profile，保持全部 gate 不变；仅在完整扫描释放后和同 run N05 gate 通过时进入 flight。若扫描再次因 health cost 锁存，则增加对触发时刻状态／指标的定向归档后再判断，不绕过 N05。

## 文件

- [支架扫描结果](../../artifacts/runs/n08-20261025-269-vertical-settle/fixture-result.json)
- [阶段记录](../../artifacts/runs/n08-20261025-269-vertical-settle/fixture-stages.json)
- [VINS 原始指标](../../artifacts/runs/n08-20261025-269-vertical-settle/fixture-vins.jsonl)
- [扫描轨迹](../../artifacts/runs/n08-20261025-269-vertical-settle/fixture-trace.jsonl)
- [最终安全读回](../../artifacts/runs/n08-20261025-269-vertical-settle/final-safety-readback.json)
- [门控测试](../../tools/test_n08_trial_gate.py)
