# N08 #293：终端样条保持判据未覆盖高频命令流

## 结论

本次前置检查通过并实际执行运动中 caller-cancel，但 native runner 仍 `FAIL`，不能计入 N08 成功次数。问题在新加入的终端参考判据：它要求最新两条 PositionCommand 相隔至少 50 ms，而 EGO 以约 8 ms 周期持续发布稳定终端命令，导致每次比较都只看到相邻的高频样本并返回“尚未完成”。

## 前置准入与安全状态

- Run：`n08-cancel-translation-prescan-20261026-293`，epoch `9289a33bfc114c1b9b34e505aa556a7e`，map id `9289a33bfc114c1b9b34e505aa556a7e-b2823d59bade4ea3a4a13437a8a66988`。
- N05 支架扫描完成 6/6；release 后 online/offline admission 均为 `all_entry_phases_known_and_clear`，`diagnostic_pass=true` 且 identity 连续。fixture helper 在末尾因 freshness 窗口报错并返回 1；其记录显示支架 detached、fixture removal 记录为 true、模型列表无支架实体。helper 最后 landed 状态样本过期，故先独立读回再继续。
- 6 秒独立 PX4/bridge 读回确认 `DISABLED`、control disabled、PX4 disarmed/landed、local position 有效，控制消息计数均为 0。随后 40 秒只读 preflight 通过，mission current-area online/offline admission 再次接受。

## 实际取消与 timeout 证据

目标实际发送。触发时 PX4 水平速度 `0.04032 m/s`、EGO reference 速度 `0.05823 m/s`。action 结果为 status=5、outcome=`canceled`、reason=`caller_cancel`、success=false；轨迹 ID 1 被 ID 2 替换。停止样条实时向量导数界 `0.08961 m/s < 0.12 m/s`，reference tube 和 live raw-map 证书通过，无旧轨迹恢复、无 spline rejection、无 watchdog。

样条有效终点为 sim `381.344031495 s`。终点后记录到 3,578 条同 goal/epoch/trajectory 的 PositionCommand；全部 flag=READY，终端位置完全稳定、速度和加速度为零。相邻 source stamp 间隔为 8 ms。独立 PX4 local-position 序列在终点后有超过 21 仿真秒连续样本满足水平 `<=0.03 m/s`、垂直绝对值 `<=0.05 m/s`。但 native helper 每轮只取最新两条命令，二者间隔小于 50 ms，于是 terminal reference 判据返回空并把 stop-hold 累计清零。最终报 `cancel_stop_spline_or_measured_hold_timeout`，缺少官方 `post_goal_hold_end_sim_ns`，未执行 stop 后 destination landing admission/command。

## 安全收尾

runner operator-disable 后独立 5 秒读回确认 bridge `LANDED/control disabled`、PX4 `DISARMED/landed`、控制消息为 0；项目容器以 exit 0 停止。此次安全落地不替代停止后目标区 landing admission，因此整次 N08 run 保持 `FAIL`。

修复方向是对最近至少 50 ms 的整个终端命令窗口做稳定性与零导数核验，而不是要求两个相邻高频样本之间隔 50 ms。未改任何健康、速度、地图、hold 或 landing 阈值。
