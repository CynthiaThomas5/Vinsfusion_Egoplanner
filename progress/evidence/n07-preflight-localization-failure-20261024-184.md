# N07 #184：返回段定位代价尖峰，未进入飞行

**结果：FAIL；N05 ready marker未生成，未执行attached gate或飞行；连续计数为0/3。** Run目录：`artifacts/runs/n07-20261024-184-01/`。

## 固定身份与入口门

镜像 `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`；runtime contract文件SHA-256 `856bf1f2222a5286493813c9702731f7e5166844eb2bfd98c6f525f3f36924eb`、embedded SHA `12b1c17cccfcb5c9f035516baa3d40c05ab7b8a4d5c32c4e28bef47d15b46233`；spawn `-6.5,0,0.3,0,0,0`；wall布局 `wall_box_column`；支架路线 `n06_full_airframe_retreat_240_oblique_separated_return`。epoch `a82f3a619ab5408ebc8695ca0a9e9677`，初始map_id `a82f3a619ab5408ebc8695ca0a9e9677-8630a456f77947bb8d19866c9db74958`。初始N05 online/offline一致拒绝：`TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`；当时bridge `DISABLED`、未解锁且落地，定位有效。

## 失败位置与可复核诊断

全机支架扫描在第7/12阶段、返回段约仿真 `328.208s` 终止。helper原始错误为`localization changed or became invalid during physical scan`；last localization为state `4`、`valid=false`、`normalized_cost_exceeded`，normalized cost `1.9696420427526087`。最近支架轨迹在x约`-0.568m`、z约`1.000m`，无yaw/pitch目标变化。

`fixture-vins.jsonl`里有一条与helper数值精确相符的VINS遥测：source stamp `328.252s`，final_cost `8620.226284`、residual_components `4444`，按未变公式`sqrt(2 × final_cost / residual_components)`得到 **1.969642**，超过现有配置门限 **1.0**。该样本有`1177`个视觉观测、`158`个双目特征，求解器字段`state_finite/solve_current/solver_usable`均为true；后续遥测代价回落，但健康门已按既定规则拒绝。没有调高门限、重启当前epoch或用后续有效帧覆盖失败。#183也在同一返回段失效，last normalized cost为1.058955；本次原始记录补充了与helper拒绝数值吻合的代价尖峰证据。

## 安全收尾与下一步

helper确认cleanup attempted、verified detached，attachment为attached→detached，fixture已移除且`fixture_may_remain_attached=false`；remove-service ack与Gazebo场景模型缺失均确认。603条PX4 status样本均DISARMED，320条LandDetected均landed。独立读回确认bridge `DISABLED`、`localization_not_tracking`、control disabled、armed=false、landed=true；PX4 `arming_state=1`、LandDetected `landed=true`，无fixture模型。通过`bash tools/project.sh stop n07-20261024-184-01`停止后容器`exited 0`，无活动项目容器。

N07计数按连续性重置为0/3，健康门与N05门限不变。下一子项#185使用新的container/epoch和同一固定flight/runtime条件及原支持路线，继续验证这项N07要求的冷启动重复性；失败仍不发飞行命令并安全收尾。地下体素仍按既有ground-boundary处理，不作为空中可飞空间。

逐文件哈希及机器可读字段见[结构化报告](n07-preflight-localization-failure-20261024-184.json)。
