# N07 #187：early-view 路线触发加速度偏置健康门

**结果：FAIL_NO_FLIGHT；N07连续计数为0/3。** Run目录：`artifacts/runs/n07-20261024-187-01/`。

## 固定条件与失败

镜像 `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`；runtime contract文件SHA `856bf1f2222a5286493813c9702731f7e5166844eb2bfd98c6f525f3f36924eb`、embedded SHA `12b1c17cccfcb5c9f035516baa3d40c05ab7b8a4d5c32c4e28bef47d15b46233`；spawn `-6.5,0,0.3,0,0,0`；wall布局；支架profile `n06_full_airframe_retreat_240_oblique_early_view`。epoch `f58b25c520d545e09a4fb3575d148bb6`。初始N05 online/offline一致按`TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`拒绝，bridge DISABLED、PX4未解锁且落地。全机扫描在第7/12阶段失败，helper原始错误`localization changed or became invalid during physical scan`；没有ready marker、attached gate或飞行。

## Bias健康门证据

当前配置`max_accel_bias_m_s2=0.15`未改。`fixture-vins.jsonl`中首次超过门限的遥测source stamp为 **250.276s**，accel bias norm=`0.150160589`，最终捕获最大值=`0.192768800`。最近支架轨迹为仿真`250.180s`、leg `7`、x=`-2.361m`、z=`1.000m`，处于early-view路线pitch回正后的回程起点。helper末态定位reason为`accel_bias_norm_exceeded`、valid=false、normalized_cost `0.5316170445095941`；所以本次不是normalized cost门拒绝。为什么估计偏置在该支架路线升高，现有数据尚不能定因；不提高0.15门限。

## 安全收尾

helper安全cleanup attempted、verified detached，attachment attached→detached，fixture移除、remove-service ack与场景模型缺失均确认；557条PX4 status全DISARMED，303条LandDetected全landed。独立读回bridge `DISABLED/localization_not_tracking`、armed=false、landed=true，PX4 arming_state=1、LandDetected landed。容器通过`bash tools/project.sh stop n07-20261024-187-01`停止，`exited 0`，活动项目容器数0。

## 下一步

early-view路线没有通过当前冷启动健康门。N07仍0/3、无飞行证据。#188回到已有#180/#182成功使用的`n06_full_airframe_retreat_240_oblique_separated_return`支架路线，以新container/epoch继续；源码、镜像、spawn、悬停参数和所有阈值不变，成功后#189仍固定该路线。地下体素仍仅按既有ground-boundary规则处理，不作为可飞空间。逐文件哈希见[JSON报告](n07-preflight-health-failure-20261024-187.json)。
