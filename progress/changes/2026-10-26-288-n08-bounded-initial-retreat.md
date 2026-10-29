# #288：用实测和几何余量约束 N08 启动回摆

## 目标与当前范围

N08 Goal 完成模式，父 N08 保持 `in_progress`。本子项处理 #287 在第一条真实 EGO 样条处的拒绝，之后必须用新冷启动完成取消测量；没有把失败运行计入任何通过次数。普通目标到达后停止，不隐式返航；返航仍是用户单独发出的第二段命令。

## 证据与修改

- #287 在合法 N05 准入和空闲方向性地图证书之后，首条 B-spline 最低前向位移为 −2.532 mm，连续采样需要的间隔上界为 0.500 mm。临时的 `x >= 0` 下界因此触发 watchdog，取消测量未开始。
- `tools/n08_trial_gate.py` 增加固定 5 mm 初始回摆界，并将它纳入方向性走廊的连续可达中心界。结合原 5 cm 横／垂向参考管、0.15 m tracking 上限、0.25 m margin 和 25 mm 采样间距，实测地图上的可达中心上界 0.244340 m，小于 0.262500 m 的可用上界，余量 18.160 mm。
- `tools/run_n08_braking_trial.py` 的普通前向实时曲线检查使用同一个 5 mm 下界。参考管道、最大前向距离、动力学速度门、在线跟踪 watchdog、raw-map 分类、新鲜度／identity 和 landing 规则未改变。
- `tools/test_n08_trial_gate.py` 加入 #287 实测样条回放、超过 5 mm 的拒绝，以及启动回摆计入几何余量的断言。
- #287 原始地图复算通过 25/25 个 raw 查询球，0 unknown／occupied，start hold 与 symmetric terminal hold 通过。复算不是 SITL 资格。

## 验证

- `python3 -m unittest tools.test_n08_trial_gate -v`：20 项通过。
- `bash tools/project.sh test`：348 项单测通过，navigation-adapter integration 通过。
- Python runner／helper 改动未涉及 ROS/C++ 编译源码，不需要重建 PX4、EGO 或 ROS 包；本次规则须在下一个冷启动 runtime manifest 中重新取指纹。
- #287 flight 仍是 FAIL；`cancel_stop_trace`、替换停止 spline 和制动评估均未产生有效测量。

## 下一步与未解项

先用完整 N05 支架扫描／释放后准入启动 #288 新冷仿真；40 秒只读 preflight、mission current-area N05、runtime 指纹和全部地面／空中走廊门通过后，运行 `single_goal motion_cancel 0.04 0.06`。只有看到 action caller-cancel 三字段、经过认证的替换 stop spline、旧轨迹不恢复、真实停止／保持及 landed/disarmed 才算取消测量。若仍失败则保留 FAIL 并基于最早分歧定位。

取消行为闭合后，完成 hold／compute-only／native execute 对照审计，整理 N05/N06 预算；最终修复冻结后用同一有效版本取得至少三次独立 `terminal_stop` 普通单目标通过。N08 尚未完成。

记录：[#287 tube 拒绝](../evidence/n08-initial-reverse-tube-refusal-20261026-287.md)、[#286 N05 顺序拒绝](../evidence/n08-n05-prescan-order-refusal-20261026-286.md)、[#288 对话摘要](../../collaboration/dialogues/2026-10-26-288-n08-initial-transient.md)。


## #288 冷启动结果与后续修复

#288 的N05 6/6支架扫描、移除确认、释放后在线／离线准入、40.002s preflight、当前区域N05和空中方向性地图证书全部通过。caller cancel在PX4实测水平速度0.04020m/s、EGO参考速度0.05745m/s触发，action结果为`status=5, success=false, outcome=canceled, reason=caller_cancel`。EGO按0.246m距离规划，但三个重试都在`reboundReplan`固定的`<0.2m`局部目标门被拒：取消位置x≈0.00117m，活动样条参考x≈0.06008m，因此目标相对参考起点仅约0.187m。没有replacement spline或制动数据。末态独立读回bridge LANDED/control disabled、PX4 disarmed/landed、控制消息0，项目容器停止。详见[#288诊断报告](../evidence/n08-cancel-reference-anchor-refusal-20261026-288.md)。

#289以活动EGO参考样条位置锚定停止目标，速度距离公式和其他限值保持不变。0047依赖补丁和哈希已更新；ROS 17包构建、348项全仓测试及navigation-adapter integration通过。下一步是新冷启动完整N05扫描及motion-cancel SITL。
