# N06.6 r29 wall-layout live EGO lateral curve

日期：2026-10-23。Goal 完成模式，范围 N06。父目标 N06/S4 保持 `in_progress`。

## r29 结果

r29 复用 r28 的 wall layout、纹理 surround 和单轴 X 后退／回程观察 profile，truth 最大后退 `2.40552 m`，最终 x 残差 `-0.01569 m`、yaw全程0°。输入记录104.133秒，2,015条LocalizationStatus全部有效，441条MapStatus均为同一epoch/map_id的`ready`；runner自然exit0，容器和匹配进程已停止。

三张snapshot共享epoch=`1b31ac63617b40559ec245779e9e7c24`、map_id=`1b31ac63617b40559ec245779e9e7c24-7298214ffdb64675afa4ddad45518c45`和对应`odom_...` frame。source age为0.141／0.144／0.113s，fusion age为0.047／0.045／0.048s；错误epoch／map_id拒绝均通过。对每张snapshot以自定义probe记录的actual VINS位置复算，body球为2,219 free／0 unknown／0 occupied；terminal hold球为4,862 free／0 unknown／0 occupied。`(0,+0.6,0)m`目标的terminal hold也均为4,862 free，snapshot-03上的直线body sweep按planner provisional速度界0.5m/s经25次闭格查询通过。

在snapshot-01之后、snapshot-02之前执行自定义planner-only probe，目标相对当时VINS起点为`[0,+0.6,0]m`。MapStatus source/fusion age为0.076／0.068s；probe前后epoch/map_id/frame不变且ready。EGO发布1条与goal_id、epoch匹配的order-3 B-spline，证书日志为`queries=45 wall_ms=0.430 reason=free`；fault为0、fault后迟到曲线为0，曲线SHA-256为`b7a29c00010acbb1a04fea8dedf80e36aba485ec70a5b8f584b41ff5ee68cdea`。probe graph未发现PX4／bridge／controller／traj_server／navigation supervisor、setpoint或控制topic。

自定义和runner默认probe的起点body query各自一次返回`no_fresh_fused_depth`，虽MapStatus fresh；两者后续planner曲线认证与快照body/hold raw复算均成功。该服务瞬时拒绝继续记录，需后续区别 pending occupancy update；不把它表述为live body-query success。runner默认目标`(+0.5,0,+0.5)m`另外收到`full_curve_terminal_hold_occupied`，0条曲线；r28 snapshot replay已证实此hold球含5个occupied cells。故障与正向goal分开写入[custom probe](../../artifacts/runs/n06-20261023-wall-r29/n06-live-layout-probe-lateral.json)和[default probe](../../artifacts/runs/n06-20261023-wall-r29/n06-live-layout-probe.json)。

完整输入、motion、三张快照、两个live probe及哈希见[运行目录](../../artifacts/runs/n06-20261023-wall-r29/)；结构化结果见[机器报告](n06-live-ego-lateral-curve-20261023-104.json)。该结果建立了 wall layout 下的一条真实EGO完整曲线和raw-free body／terminal hold快照，但没有完成N06：corridor layout、活动期间和replan handoff、hold/emergency hold切换、新障碍／错误身份／过期／查询失败故障矩阵仍待验证。

## 下一项：r30 corridor layout

以 r29 为 wall 对照，使用同一单轴X后退／回程profile及纹理surround，在`corridor_box_column`第二布局复核健康、三张fresh map和一个live EGO曲线。corridor内部宽约1.5m，body clearance半径0.7306m，terminal hold半径0.9806m；后者不能留在窄走廊内，因此先对实际snapshot精确查询起点和后方候选hold。只在起始body与选定目标的terminal hold及直线body sweep均raw free时，才用planner-only probe请求曲线；目标候选优先沿-X退出走廊，在线身份／新鲜度仍由probe确认。无候选时不发goal，保留明确no-go证据。

```bash
bash tools/run_n04_map_layout.sh n06-20261023-corridor-r30 corridor_box_column 93 motion_n06 config/components/simulation/n06_x_visibility_slow.json
```

r30仍是 sensor-only Gazebo/VINS/EGO，不连接任何控制消费者，不修改N05预算或N06验收阈值。通过后继续N06 hold、replanning与拒绝故障出口。
