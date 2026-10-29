# N07 #183：支架扫描定位健康失效，未进入飞行

**结果：FAIL；没有N05 ready marker、attached gate或飞行，N07连续计数重置为0/3。** Run目录：`artifacts/runs/n07-20261024-183-01/`。

## 固定身份

镜像 `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`；runtime contract文件SHA-256 `856bf1f2222a5286493813c9702731f7e5166844eb2bfd98c6f525f3f36924eb`，内嵌契约SHA-256 `12b1c17cccfcb5c9f035516baa3d40c05ab7b8a4d5c32c4e28bef47d15b46233`；spawn `-6.5,0,0.3,0,0,0`；布局 `wall_box_column`；支架profile `n06_full_airframe_retreat_240_oblique_separated_return`。新epoch `d19007b088ff45ed9a6418dd04718064`。无ready marker，故没有后续map_id。初始N05入口因`TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`拒绝；bridge为DISABLED、未解锁、已落地。

## 失败与飞行判定

未武装全机支架扫描在第7/12阶段中止。helper原始结果为`outcome=failed`、`error="localization changed or became invalid during physical scan"`。末次定位状态为state 4、`valid=false`、`reason="normalized_cost_exceeded"`、normalized_cost=`1.0589551679721994`。因此没有`n05-prescan-ready.json`，没有attached live/offline gate，也没有发出enable、arm、目标或飞行命令；`flight.json`不存在。不能用此前的N05准入证据覆盖此次定位健康失败。

## 安全收尾

helper安全清理`attempted=true`、`verified_detached=true`，attachment记录为attached→detached；`fixture_removed=true`、`fixture_may_remain_attached=false`；remove-service ack和场景模型缺失均为true。588条PX4状态样本全为`arming_state=1`（DISARMED），312条LandDetected样本全为landed。独立topic读回确认bridge `DISABLED`、reason `localization_not_tracking`、control disabled、armed=false、landed=true；PX4 arming_state=1；LandDetected `landed=true`；Gazebo列表不含扫描夹具模型。

原始ROS读回中保留了PX4/Gazebo的warning。使用`bash tools/project.sh stop n07-20261024-183-01`后，`docker inspect`显示`exited 0`，项目活动容器数为0。

此次仅记录一次固定版本冷启动失败，连续通过计数按N07规则重置为0/3。下一子项#184将使用新的container/epoch、相同镜像／契约／spawn／布局／profile与原有门限；若健康或准入门拒绝，继续fail-closed并完成独立安全读回。地下体素仍按既有ground-boundary规则处理，不作为可飞空间。

逐文件SHA-256与机器可读字段见[结构化报告](n07-preflight-localization-failure-20261024-183.json)。
