# N07 #174：输入与适配odometry时序

## 用户约束

- 用户已授权Goal完成模式，范围N07，持续至N07出口通过。
- 健康门、N05 gate、hover验收标准不变，不绕过raw unknown拒绝。
- 仅PX4 SITL；fresh attached/released N05 gate未通过不解锁。

## 本项结果

#174在stage4 pitch转入出现单个normalized-cost=1.162528样本并锁存健康失败；probe确认raw VINS telemetry/odometry最大source gap均0.096s，且越过失效时刻后仍继续发布。定位status在sim 220.508s以`normalized_cost_exceeded`失效，代价来自stamp 220.408s的telemetry。之后adapter optimized/propagated odom停发，status持续带锁存错误。该run的首要失效是代价越线而非源龄断档；不能据此否定#173的其他成因。详情见`progress/evidence/n07-support-scan-normalized-cost-failure-20261024-174.md`。

下一子项#175复用同profile与全部门限，只移除额外高频只读probe，保留runner原生VINS/odometry/status样本。若扫描及attached/released N05都通过，才进入同epoch no-goal hover；health lock、N05拒绝或缺少fresh odom都停止，不解锁飞行。
