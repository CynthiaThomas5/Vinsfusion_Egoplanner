# 对话摘要：N08 #226 首动停止边界审计

- #225 隔离 compute-only 与 same-run N05 门禁通过；它没有实际水平运动或制动数据。
- #226 在同一 raw map 上重建 live B-spline，43 次带速度余量的 raw sphere query 全 free，目标 stop 球 free；曲线起点 terminal-hold 球仍有 49 unknown，0.8 m 沿程边界 free，到 0.9 m terminal-hold 出现 2 unknown。
- 该次 live B-spline 峰值总速度约 0.194 m/s、x 分量约 0.179 m/s，超过运行配置 0.15 m/s 及源码 tolerance 后 0.1576 m/s 分量门限。当前曲线不能被当成 0.15 m/s 矢量速度界。
- PX4 仿真快照没有记录水平控制参数；固定源码中的水平最大加速度／速度是上限，不是最低制动能力。没有 response-delay 上界或 minimum deceleration，故无法证明地图剩余 0.262 m 足够停止。
- 结论是 no-go：execute 保持 fail-closed，不执行 XY。下一项应先做 live B-spline 速度／几何 certificate 和 PX4 水平参数读回，解决曲线速度门和停距来源。
