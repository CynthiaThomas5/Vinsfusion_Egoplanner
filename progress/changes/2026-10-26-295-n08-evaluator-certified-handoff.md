# #295 修复 N08 evaluator 对 certified trajectory handoff 的误拒绝

## 目标

让独立N08评估正确解释 #294 中同一 `/clock` 时刻的 outgoing/incoming B-spline 状态，同时继续保留时间倒退和真实冲突 fail-closed。

## 修改

- `_reference_samples` 识别 incoming live spline certificate 的准确 `source_clock_ns`；只有同 goal、同 epoch、且新trajectory从该stamp开始，才允许同一时间戳状态切换。
- 时间序列使用 certified incoming 状态，记录两状态 position/velocity/acceleration/yaw差值。
- 同trajectory状态变化、无证书或时间不匹配的跨trajectory冲突继续失败；相同状态重复仍单独计数。
- motion-cancel report 增加 old trajectory→certified stop trajectory handoff check。

## 验证

- `bash tools/project.sh test`：359 tests passed，navigation-adapter integration passed。
- 不覆盖 #294 原 `n08-braking-evaluation.json`。使用新 evaluator 对原始run只读重放，report PASS、35/35 checks true；报告与制动曲线放在run目录 `diagnostics/`，明确记录新旧 evaluator hash不同。
- 本次只改offline evaluation，不需ROS/C++ build；新的正式flight须锁定当前evaluator hash。

## 下一步

审计hold／compute-only／execute既有对照的源版本和可复用字段；用#260/#267/#273正常末端停车数据加#292/#294 motion-cancel测量形成受支持范围的制动预算，确认N05/N06实际消费的唯一参数。然后冻结候选版本，以独立冷启动`terminal_stop`至少三次通过完成N08重复出口。
