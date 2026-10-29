# N08.2aj #247：负 Y 观察完成，首段下降触发定位锁存

## 假设与唯一主要变量

在 #246 已通过的慢回程 N05 profile 上，增加 x=0、z=1.0 m、yaw=−π/2 的负 Y 观察／停留／回中，期望补上 #246 起点 hold 球负 Y 薄带。planner、目标、机体半径、unknown 规则及速度／地图阈值保持不变。

## 结果

新增负 Y 段及 yaw 回中完成。扫描在随后首段 z=1.0→0.5 m 下降中止：fixture trace 到 z≈0.76 m，health 锁存 `normalized_cost_exceeded`，归一化代价 1.000494（门限 1.0）。health 快照 `stale_observation=null`；当时 optimized/telemetry 源龄分别约 64/68 ms，prior evaluation 与 spectrum 检查通过。锁存后 adapter 停止跟踪，bridge 进入 `localization_not_tracking`。这不是 PX4 时钟拒绝，也不能证明负 Y 观察导致代价越线。

PX4 HRT／ROS 时间域在锁存后的独立只读读回中仍有效：39/39 bridge-detail 样本有效，gap −4…+8 ms。只读 probe 中 PX4 为 DISARMED、land detector 为 landed、bridge `DISABLED` 且 control disabled，控制模式／轨迹设定点／vehicle command 样本均为 0。支架 helper 已 detach 并确认 fixture 从 Gazebo 移除；fresh landed readback 成功，随后 `tools/project.sh stop` 成功、容器 exit 0。

N05 释放后 gate 没有执行，所以没有同图 hold unknown 数，负 Y 视角是否补齐未知空间**未判定**。compute-only、曲线证书、XY 和制动量测均未执行。N08 保持 `in_progress`。

## 验证与产物

- `python3 -m unittest tools.test_preflight_scan`：34 项通过。
- `bash -n tools/run_n05_preflight_layout.sh`、JSON 解析、`python3 tools/project_status.py`、`git diff --check`：通过。
- run：`artifacts/runs/n08-20261024-247-negative-y-coverage/`。核心原始产物 SHA-256 见同目录下方 `.json` 报告。
- profile 的完整 stage trace 显示 16 个阶段完成；health 锁存在第 17 阶段首段下降。helper 已清理 fixture，仿真停止前的末态摘要见 `final-safety-readback.json`，原始只读 PX4 probe 为 `final-safety-live.json`。

## 下一步

#248 保持 #247 的负 Y 观察和其余阶段不变，只把首次 z=1.0→0.5 m 下降从 8 s 延长到 20 s。假设是负 Y 观察后的下降视觉变化在当前速度下把代价推过门限；减慢下降用于验证这个交互，不改变任何健康或空间阈值。若再次锁存，先分析快照，不重复同类扫描。
