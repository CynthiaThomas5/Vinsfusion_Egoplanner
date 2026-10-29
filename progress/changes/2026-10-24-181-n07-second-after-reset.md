# N07.27 #181：第二次连续悬停冷启动（#179 重置后）

## 执行模式与范围

Goal 完成模式；用户指定范围 N07。父目标保持 `in_progress`，#180通过后连续计数为1/3。只完成下一次固定版本 N07 cold start；不改代码、参数、健康门、N05阈值、地下边界规则或验收条件。

## 已有基础与当前缺口

#180在ready marker后仍attached且DISARMED等待2.000070387秒，随后attached、post-release、current-area N05 online/offline gates均fresh接受；30.0仿真秒no-goal hover、独立11/11 evaluator、PX4 ULog 12/12及ROS graph检查通过。支架helper返回fresh DISARMED状态错误并exit 1，但12/12阶段、fixture移除、N05 gate和最终安全状态各自保留原证据。#180为失败重置后的1/3；N07还需两个连续独立cold start。

## 固定条件与完成标准

- 新 run/container/epoch，固定镜像 `099ab9afecd28b7354f6d6494944b1db30c7c67c973e9b93b03f87aca7ad6f8`、contract SHA `12b1c17cccfcb5c9f035516baa3d40c05ab7b8a4d5c32c4e28bef47d15b46233`、spawn `(-6.5,0,0.3,0,0,0)`、wall layout和`n06_full_airframe_retreat_240_oblique_separated_return` profile。
- ready marker后保持 fixture attached、PX4 DISARMED等待2墙钟秒，再运行原attached N05 online/offline gate。该等待作为已确认运行流程保持，不再改变其他变量。
- attached、post-release、current-area N05 gates 必须在同一 epoch/map 下fresh接受；任一门失败则不解锁并安全收尾。
- 支架12/12阶段、fixture移除和安全readback有记录。支架helper的错误必须原样保留。
- 至少30仿真秒无目标悬停；独立位置/保持误差、EV/GNSS/ULog、唯一bridge control publisher、有效tracking/时间域和最终landed/disarmed全部按N07原出口检查。
- 成功后连续计数2/3；任何失败按规则重置，不降低门限。

## 当前状态

**结果：FAIL，未飞行；N07连续计数为0/3。** 固定run目录为 `artifacts/runs/n07-20261024-181-01/`。

初始N05 gate按预期拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。支架12/12阶段到达ready marker，epoch `0c31f662925a48d5bf1a3b4960331703`、map_id `0c31f662925a48d5bf1a3b4960331703-becb9b0d0faf490bb3d84ccbb9b98980`。由于本轮首次读取marker时误用了`px4_arming_state`字段名，assert失败；shell未启用`set -e`，因此仍执行了一次只读attached gate。该gate接受，snapshot/source/fusion age为0.108/0.132/0.036秒；ready marker到该检查报告写入相差22.586秒。没有enable、arm、goal或控制命令。

核实真实字段`vehicle_arming_state=1`后，明确记录了attached且DISARMED等待2.000072843秒，再运行同一attached gate。该次检查因`localization_not_tracking`在120秒内未就绪而fail-closed，没有产生任何准入报告；未继续post-release/current-area gate或起飞。错误记录见`n05-after-settle/n05-live-entry-check-error.json`。

触发release后，支架helper报告`localization changed or became invalid during physical scan`并exit 1；同时12/12阶段完成、attached→detached、fixture已移除、`fixture_may_remain_attached=false`。fixture结果中的887个PX4状态样本均DISARMED，LandDetected样本均landed，最终安全清理验证detached/landed。独立readback为bridge `DISABLED`、reason `localization_not_tracking`、armed=false、landed=true、PX4 `arming_state=1`、land detector landed，Gazebo model list无fixture。VINS支架流有2419/2419个solver usable/current/finite记录，但结束时LocalizationStatus为state 4、invalid、`telemetry_stale`；未用这些solver记录覆盖健康门失败。没有生成`flight.json`，没有飞行。

容器经`bash tools/project.sh stop n07-20261024-181-01`停止，确认`Exited (0)`；没有运行中的项目容器。完整失败和逐文件哈希见[证据报告](../evidence/n07-preflight-localization-failure-20261024-181.md)及[结构化记录](../evidence/n07-preflight-localization-failure-20261024-181.json)。下一子项#182修正marker字段读取并启用shell fail-fast；采用ready marker后单次明确2秒settle和单次attached gate，不重复请求，所有门fresh且tracking有效才继续。
