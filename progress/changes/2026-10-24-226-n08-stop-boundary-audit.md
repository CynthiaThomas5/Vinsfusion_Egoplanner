# N08.2p #226：首动停止边界审计

## 假设与判据

- #225 的隔离 compute-only READY 曲线和 same-run N05 raw map 可用于只读设计首动边界，但不构成运动许可。
- 从 B-spline 的位置／时间数据求实际命令速度上界，用同身份 raw map 检查曲线、终点和延伸 stop 区；核对 EGO 与固定 PX4 源码，查找可追溯的响应时间上界和减速度下界。
- 若任一速度上界不满足或缺少物理制动界，结论 no-go，execute 保持 fail-closed，不运行 XY。

## 实施与结果

- 从 `planner-observation.json` 还原本次 live cubic B-spline；对应 #225 goal/epoch。#225 post-release 和 mission current-area raw NPZ 逐字节相同、epoch/map 相同。
- 用 NumPy/SciPy 1.11.4 评估 B-spline 与导数；速度导数控制点凸包给连续路径 raw query 速度上界 0.201797 m/s。按 body radius 0.730618 m 加半个采样周期速度余量做 43 次 raw sphere query，整条 live 曲线全 free；终点 body 与 terminal-hold sphere 全 free。起点 terminal-hold 球仍有 49 unknown。
- launch manifest 确认 EGO 参数 max_vel=0.15、max_acc=0.25；固定源码的速度 feasibility 按 XYZ 分量检查，5% tolerance 后每轴门限 0.1576 m/s。live B-spline 的 dense x 速度峰值 0.178692 m/s、导数控制点 x 峰值 0.186011 m/s，实际不能按 0.15 m/s 总速度或每轴上限作为证书。
- 同图沿末端方向延伸到距起点 0.8 m，terminal-hold 仍 free；0.9 m 处有 2 unknown。曲线终点到已知 stop 边界约 0.262 m。该距离是 map geometry，不是实测 stop distance。
- PX4 run 参数快照未记录水平速度／加速度／jerk 参数；固定 PX4 源码对应默认值是最大限制，不给出最小制动能力。run 内也没有控制响应延迟或动态减速度测量，故无法证明上述 0.262 m 余量足够。

## 决策与验证

- 结论：没有可追溯的 worst-case response delay 或 minimum deceleration，停止边界未证明；保持 execute 锁，不执行 XY。
- 报告与源文件 SHA-256：[`n08-stop-boundary-audit-20261024-226.json`](../evidence/n08-stop-boundary-audit-20261024-226.json)。方法是从 #225 归档重建 B-spline，调用 `tools/probe_n06_live_layout.py` 的生产 raw sphere/line 查询函数；没有在线输入、truth 或控制发布。
- 下一项：添加 live B-spline 速度／几何证书，补 PX4 水平参数读回和保守制动界证据。
