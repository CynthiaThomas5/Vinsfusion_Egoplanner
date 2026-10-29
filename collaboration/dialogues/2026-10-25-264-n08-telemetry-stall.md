# 2026-10-25 #264 N08 telemetry_stale 记录

## 范围

Goal 完成模式继续推进用户指定的 N08：厘清速度参数与真实曲线关系，完成有依据速度下的制动测量，并验证返航方向。返航必须先原地转头约 180°，再按 EGO 机头前向规则飞行，不能倒飞。

## 已确认

- #264 的 launch manifest 使用正确低速 profile（0.10 m/s、0.25 m/s²），所以本轮没有重现 #263 的 profile 配置错误。
- 扫描前只读 N05 因 ground plane raw occupied 数为 0 拒绝；之后未武装支架扫描完成 6/15 阶段，在 telemetry 源龄 324 ms 时触发既有 300 ms 锁存门。
- 接收龄为 264 ms，低于 500 ms 门限；normalized cost=0.46155，solver usable。根因尚未定位，不能断言 source timeline observer 造成超限。
- 扫描清理后已确认 fixture detached/removed、PX4 disarmed/landed，容器安全停止；无 release gate、目标、起飞或飞行。

## 决定

#265 采用一次单变量诊断：仅设置 `N05_N08_SOURCE_TIMELINE=0`，保持布局、支架 profile、planner 低速配置、健康门和其他准入规则不变。若不再锁存，也只作为 observer 影响的支持证据，不凭单次运行定根因；若再次锁存，停止同类重复，分析已有 raw VINS、adapter 和源时序记录。

## 证据

- [#264 证据报告](../../progress/evidence/n08-prescan-telemetry-stale-20261025-264.md)
- 原始数据：`artifacts/runs/n08-20261025-264-yaw-first-return/`
