# N08.264：记录支架扫描 telemetry_stale 并准备单变量复测

对话摘要：[2026-10-25-264](../../collaboration/dialogues/2026-10-25-264-n08-telemetry-stall.md)

## 记录与判定

- 归档 #264 的初始 N05 拒绝、全机支架扫描中止、健康锁存指标、清理末态和原始数据哈希。
- 确认该轮加载了正确的 `n08_low_speed_trial.json` 参数；#263 的 profile 指纹问题已排除。
- 源龄 324 ms 超过现有 300 ms 门限，接收龄 264 ms 未超 500 ms 门限；normalized cost 和 solver 指标没有指向代价越线。
- 没有调低定位阈值，也没有得到 release、post-release N05 或飞行结果。
- #265 只关闭额外的 source timeline observer，以判断它是否对源龄造成可测影响；结论仍待新 run。

## 验证

- `python3 -m json.tool progress/evidence/n08-prescan-telemetry-stale-20261025-264.json` 与 `progress/milestones.json`：通过。
- `python3 tools/project_status.py`：`Structure/design check: PASS`；仅表示项目结构一致，不代表构建或 SITL 通过。
- `git diff --check`：通过。

## 下一步

执行 #265 同 profile fresh SITL 支架扫描。只有支架扫描完成、释放并确认末态安全、post-release N05 和 mission current-area N05 均通过后，才运行 N08 前向制动、原地 yaw 180°、转向后 fresh map、EGO 前向返航和独立方向评估。
