# N07 #181：定位失效阻止悬停准入

**结果：FAIL；未飞行，N07 连续计数为 0/3。** 固定run目录：`artifacts/runs/n07-20261024-181-01/`。

## 固定身份与支架扫描

Run使用镜像 `sha256:099ab9afecd28b7354f6d6494944b1db30c7c67c973e9b93b03f87aca7ad6f8`、固定contract SHA-256 `12b1c17cccfcb5c9f035516baa3d40c05ab7b8a4d5c32c4e28bef47d15b46233`、spawn `-6.5,0,0.3,0,0,0`、`wall_box_column`和`n06_full_airframe_retreat_240_oblique_separated_return`。新epoch为`0c31f662925a48d5bf1a3b4960331703`，map_id为`0c31f662925a48d5bf1a3b4960331703-becb9b0d0faf490bb3d84ccbb9b98980`。

初始N05在线/离线gate均按预期因`TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`拒绝；PX4未武装、bridge DISABLED/landed。未武装全机支架路线完成12/12后写入ready marker，marker记录fixture attached、`vehicle_arming_state=1`、未使用真值且未发布控制／目标。

## N05 gate时序与失败

首次等待脚本误读marker字段，断言了不存在的`px4_arming_state`而失败；因shell未启用`set -e`，后续只读N05 gate仍执行。此gate接受，snapshot/source/fusion ages为 **0.108/0.132/0.036秒**，online/offline一致且同epoch/map。marker到该gate报告文件写入相差22.586秒；这一检查不是计划中的明确2秒settle后检查，执行偏差保留，不据此声称2秒假设复现。

核实正确字段`vehicle_arming_state=1`后，在fixture仍attached且DISARMED时单独等待 **2.000072843秒**，重复同一attached N05检查。它在120秒内未取得tracking前置，结构化错误为`N05 online prerequisites did not become ready: localization_not_tracking`，因此fail-closed。没有post-release/current-area门通过记录，没有enable/arm/goal命令，也没有生成`flight.json`。首个gate的地图准入结果不能覆盖之后的定位失效。

## 安全收尾与解释

请求fixture release后，支架helper以`localization changed or became invalid during physical scan`退出，错误原样保留；但12/12阶段完成、attachment从attached转为detached、fixture移除确认成功、`fixture_may_remain_attached=false`。helper记录887个PX4状态样本全为DISARMED，LandDetected样本全为landed，最终cleanup验证detached和landed。VINS支架流2419/2419记录的solver usable/current/finite均为true；然而fixture末态LocalizationStatus为state 4、invalid、`telemetry_stale`，独立bridge readback为DISABLED、`localization_not_tracking`、armed=false、landed=true。PX4 `arming_state=1`且LandDetected landed，Gazebo模型列表确认fixture不存在。

容器通过`bash tools/project.sh stop n07-20261024-181-01`停止并确认`Exited (0)`；没有活动项目容器。该次没有空中悬停或EKF2飞行资格证据，作为失败尝试保留。下一次#182使用修正后的marker字段、fail-fast顺序，在marker后单次明确等待2秒再做一次attached gate；只有tracking与所有freshness条件均有效才继续。

逐文件哈希和原始结果见[结构化报告](n07-preflight-localization-failure-20261024-181.json)。地下空间仍不作为飞行区域。
