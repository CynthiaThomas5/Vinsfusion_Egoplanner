# #159 N07 远端 +0.15rad yaw 观察结果

run `n07-20261023-159-01` 以 spawn `(-6.5,0,0.3)` 启动。初始 fresh N05 因 raw-ground occupied 样本不足拒绝；独立 offline replay 结果一致。未解锁。

## 扫描结果

profile 目标为 9 阶段；完成0–5阶段后，在阶段6（yaw 已复位为0的返程）触发 `normalized_cost_exceeded`，未完成返程或后续降落阶段。`vio.log` 记录 mapping gate 首次关闭于 sim 204.932s；此前最后一条 fixture trace 在 sim 205.104s 仍是有效旧状态，cost 0.8147。health 锁存后的最新 cost 为1.0743。

- 远端转入 +0.15rad、保持15s和复位阶段均 VINS valid，epoch 连续；实际 yaw 峰值0.15068rad。
- 返程阶段最后可见 cost 峰值0.86739；long tracks 最低45，随后 health 锁存。accel bias 峰值0.148700m/s²，仍低于0.15门限。
- 因定位锁存，没有 `n05-prescan-ready.json`，也没有 attached/released fresh N05 检查。不能从本 run 判断 yaw 是否清除了3个 HOLD unknown。

## 安全状态

fixture helper 执行安全清理并确认 detached；remove service ack，Gazebo model list 不含 fixture，`fixture_may_remain_attached=false`。PX4 arming state=1（DISARMED）。独立 ROS 状态查询显示 bridge `DISABLED`、control disabled、armed=false、landed=true；定位仍 invalid。项目容器按流程停止并退出0。没有悬停或飞行。

## 解释与下一步

yaw 转向和保持本身保持有效；锁存出现在复位后的返程，视觉 long tracks 明显下降。#160 将 +0.15rad 维持到返程结束，返回原点后再单独复位 yaw=0。平移距离仍1.8m，pitch=0，其他门限不变。新 run 必须先完成支架释放和 fresh N05；未接受前不解锁。

机器可读摘要：[n07-retreat-observation-20261023-159.json](n07-retreat-observation-20261023-159.json)。静态路线：[geometry JSON](n07-retreat-180-yaw015rad-route-geometry-20261023-159.json)。原始日志与哈希位于 `artifacts/runs/n07-20261023-159-01/`。
