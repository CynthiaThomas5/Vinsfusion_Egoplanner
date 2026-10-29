# N08 正式出口最终审计（#327）

**结论：N08 当前仿真版本的正式出口通过。** 冻结 runtime-contract `75aaa541f7684b38fe0805b958e029fa21f8c6dd6ab00d2ebe1fae92c7e8a772` 下，#322、#324、#325 是三次独立 PX4/VINS/map cold start 的普通单程 `single_goal terminal_stop`；三次均原生任务成功、独立制动 evaluator 全检查通过、N05/N06 当前准入通过、实际停车保持及目的地区降落成功。普通目标没有返航 action，符合“到达即结束；返航另发命令”的语义。

| Run | 实际峰值向量速度 | 减速开始至停车路径 | 持续减速响应 | 最大独立跟踪误差 | 3 秒保持位置变化 |
| --- | ---: | ---: | ---: | ---: | ---: |
| [#322](n08-terminal-stop-20261026-322.md) | 0.07550 m/s | 0.28106 m | 1.504 s | 0.08008 m | 0.02209 m |
| [#324](n08-terminal-stop-20261026-324.md) | 0.08282 m/s | 0.28868 m | 0.816 s | 0.08379 m | 0.02152 m |
| [#325](n08-terminal-stop-20261026-325.md) | 0.07639 m/s | 0.29568 m | 1.532 s | 0.08671 m | 0.01920 m |

## 出口证据

- **hold／compute-only／执行受控对照：** #212 固定 hold 作为 30 秒无目标漂移基线；其 idle binary 与定位健康配置不同，只作描述基线。#257 compute-only 与 #260 native execute 使用相同 runtime-contract `661ea2154b9190c981e82eb9b12e8d238aef3b9527d630cb5261821e33128844`，模式差异是 bridge 是否接收 EGO 输出。对照和边界见[#296预算审计](n08-cancel-stop-budget-admission-20261026-296.md)。
- **取消后的停止／保持：** #321 单独通过 `motion_cancel`，取消请求时 PX4 水平速度 0.04014 m/s、EGO 参考速度 0.05848 m/s；替代停止样条通过证书、旧轨迹未恢复、取消至停车 0.30407 m、3 秒保持、终点落地通过。它不计入普通目标 3/3。
- **三次正常单目标：** 三次使用同一 runtime、goal 和 planner hash；epoch 与 map_id 各不相同。N05 释放后及任务 current-area online/offline 门、40 秒只读 preflight、25 点全机前向 corridor、停止保持与终点降落候选均通过。#325 末态另由 6 秒独立 bridge/PX4 读回和 PX4 ULog 确认 `LANDED`、disarmed、控制消息为零。
- **预算已接入真实门禁：** caller-cancel `cancel_stop_distance_envelope_m=0.50 m` 是当前前向低速协议的有限样本候选，实际被取消任务的 pre-enable／airborne raw-map corridor 和独立距离评估器消费。它不是通用保证或额外径向机体半径。N05 机体参考清距 0.730618 m、合并空间不确定度 0.248682 m、N08 tracking margin 0.25 m 及最大跟踪误差 0.15 m 均未增大；正常目标路径仍用完整全机曲线和 terminal-hold 证书，停止路径是沿路线长度，不与这些半径重复相加。受限几何的可达中心界 0.250778 m ≤ 可用界 0.262500 m，余量 0.011722 m。

## 未扩大的结论范围

- 减速度 p10 只是这三次有限样本的描述值，不是保证下界。响应时差包含控制动力学和 0.22 秒对称平滑，不是纯通信延迟。
- 详细计划 D.6 建议的近峰值 0.08–0.09 m/s 取消触发补测已由 #326 尝试，但 fresh N05 接触体积有 51 个 raw-unknown cell，门禁正确拒绝；无 goal、enable 或飞行。它不是正式 N08 出口规定的额外取消重复数，但该速度点没有取得测量，见[#326](n08-cancel-peak-refusal-20261026-326.md)。
- #323 是起飞前 telemetry freshness 锁存拒绝，未执行 fixture/goal/enable，不减少已通过计数。N07 不重测。
- mission 外层 wrapper 在 native PASS 后因可选 matplotlib 绘图依赖缺失返回 1；每个合格 run 保存的独立无图 evaluator 通过。仿真证据不构成真实硬件保证。

机器审计：[JSON](n08-final-completion-20261026-327.json)。N08 `status` 已写为 `passed`，`execution_plan.next_goal` 指向 N09；N09 尚未启动。
