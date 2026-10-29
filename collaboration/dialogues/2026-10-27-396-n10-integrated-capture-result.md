# 2026-10-27 #396 N10 综合采集校准

## 用户约束

- N10 冻结前做标准所需校准；N15 的六类故障正式重复与 N16 十分钟正式任务留在冻结后。
- 不把统计越线、CPU 峰值、评估器/记录器错误转成拒飞、暂停或降落分支；不恢复项目自加健康、速度或整曲线 raw-free 门。
- 真实断流、进程退出等需正确完成任务，依据 PX4 末态评价；一次性紧急 disarm 授权只用一次。
- N10 保持进行中，持续执行已授权计划。

## 本项结果

#396 16 m 目标、3.436 仿真秒联合位置/yaw 驻留、15 仿真秒诊断保持和正常落地上锁均完成。该次未触发故障，未用紧急 disarm。sensor capture 完整性通过。净空与跟踪诊断显示机体跟踪误差 P95 约 0.707 m、静态场景离散采样净空最低 0.228 m；相邻 4 ms 状态位移不是连续区间界。障碍 raw 点云 +3.588 s 才首次出现；raw/inflated 快照在 +1.016 s，箱体区域仍 unknown；point-query 服务不可用。因此总体评估 `INSUFFICIENT`，不能进入冻结。

工作区中的重规划几何 evaluator 导入路径错误已修复；归档复算成功。run driver 的到达字段兼容和离线 evaluator 依赖顺序仍需整理。

## 决定与待办

- 写回 #396 成功飞行与不充分证据，不计正式次数；修整 N10 run-local driver 的后处理依赖顺序。
- #397 单变量将 EGO planner 最大速度从 0.8 改为 0.4 m/s，观察真实跟踪误差、任务完成和净空；observer-only 地图快照安排在障碍点云出现后的窗口，并保存同一地图快照的 raw/inflated 数组与身份。
- 另补当前版本真实断流/规划器退出到 PX4 landed/disarmed 的校准。一次性 emergency disarm 已消费，后续若 run 出现异常按正常路径受控终止并独立确认，不调用紧急 disarm。

过程与限制见 [#396 change record](../../progress/changes/2026-10-27-396-n10-integrated-capture-result.md) 和 [证据报告](../../progress/evidence/n10-integrated-capture-result-20261027-396.md)。
