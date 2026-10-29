# N07 #185：支架路线完成但定位／readiness拒绝，未飞行

**结果：FAIL_NO_FLIGHT；连续计数为0/3。** Run目录：`artifacts/runs/n07-20261024-185-01/`。

## 固定身份与准入

镜像 `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`；runtime contract文件SHA-256 `856bf1f2222a5286493813c9702731f7e5166844eb2bfd98c6f525f3f36924eb`、embedded SHA `12b1c17cccfcb5c9f035516baa3d40c05ab7b8a4d5c32c4e28bef47d15b46233`；spawn `-6.5,0,0.3,0,0,0`；`wall_box_column`布局；支架路线 `n06_full_airframe_retreat_240_oblique_separated_return`。epoch `bdcee586935e43caba090bdd70d90fde`，map_id `bdcee586935e43caba090bdd70d90fde-e1c63c746c794d4f81ec22379543c0b1`。初始入口按预期online/offline一致拒绝`TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`，初始bridge DISABLED、PX4未解锁且落地。

支架路线完成12/12并创建ready marker：attached、`vehicle_arming_state=1`、未使用truth、未发控制/目标。明确等待 `2.000073489s` 后，唯一一次attached online/offline N05 gate同epoch/map接受，reason `all_entry_phases_known_and_clear`；snapshot/depth/fusion freshness分别为 `0.092/0.120/0.056s`，均低于原0.4秒门限。

## Helper错误与停止依据

fixture helper exit code 1，原错误保留：`localization changed or became invalid during physical scan`。它记录12/12已完成、`n05_live_check_completed=true`、attachment attached→detached、fixture removed；末次定位样本为state 1、valid=true、`fresh_inputs_and_usable_solver`、normalized_cost `0.4386971394716981`。fixture-vins遥测归一化代价最高 `0.797141`，未记录大于1.0的样本。helper同时记录`safety_cleanup.attempted=false`和`verified_detached=false`；独立移除确认中remove-service ack和scene model absent均为true。

独立PX4读回803条status均DISARMED，425条LandDetected均landed。bridge readback第一次echo碰到ROS discovery race（完整信息保留）；在再次读取topic info后以显式类型重试成功：bridge `DISABLED`、reason `localization_not_tracking`、ready=false、armed=false、landed=true，PX4 `arming_state=1`、LandDetected landed。这个bridge readiness结果与helper末次单样本状态不一致；本run未采集独立`/localization/status`连续时间线，不能确定两者之间的时序。

因独立bridge readiness快照未满足`localization_not_tracking`，未运行post-release/current-area gate，也未发送arm/goal或启动flight；无N05 14/14报告和N07 flight资格证据。通过`bash tools/project.sh stop n07-20261024-185-01`停止后容器`exited 0`、项目活动容器数0。地下体素仍按既有ground-boundary规则处理，不代表可飞。

## 下一步

N07计数保持0/3，健康门和门限不变。#186将在同一固定条件的新epoch中，在回程段启动只读VINS/status freshness时间线探针以定位health状态转换时刻；探针只补充诊断，不代替任何live/offline N05 gate。完整逐文件哈希见[JSON报告](n07-preflight-health-failure-20261024-185.json)。
