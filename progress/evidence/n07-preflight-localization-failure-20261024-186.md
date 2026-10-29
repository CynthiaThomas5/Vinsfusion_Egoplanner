# N07 #186：遥测尖峰触发定位健康拒绝

**结果：FAIL_NO_FLIGHT；N07连续计数为0/3。** 固定run目录：`artifacts/runs/n07-20261024-186-01/`。

## 固定身份与安全入口

镜像 `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`；runtime contract文件SHA `856bf1f2222a5286493813c9702731f7e5166844eb2bfd98c6f525f3f36924eb`、embedded SHA `12b1c17cccfcb5c9f035516baa3d40c05ab7b8a4d5c32c4e28bef47d15b46233`；spawn `-6.5,0,0.3,0,0,0`；wall布局；支架路线 `n06_full_airframe_retreat_240_oblique_separated_return`。epoch `3d56eed32e9e4f76896ff6a6789061a0`，map `3d56eed32e9e4f76896ff6a6789061a0-4fedace1fc294a9785f73dbfaa5afe60`。初始N05 online/offline一致按`TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`拒绝，bridge DISABLED、PX4未解锁且落地。定位时间线probe在回程leg 6启动，仅读取clock、raw VINS telemetry/odom、适配器输出与`/localization/status`，不发布控制／真值。

## 触发时序与数据

raw telemetry在source stamp **261.692s**出现一帧：final_cost `2558.806137`、residual components `4365`，按既有公式`sqrt(2 × final_cost / residual_components)`复算为 **1.082783**，超过原配置 `1.0`。该帧仍有`1122`个视觉观测、双目特征 `155`、long tracks `121`，solver finite/current/usable均true。最近fixture轨迹在仿真261.680s、leg 6、机体x约−1.749m、z约1.000m，目标正在沿x回程。

独立probe捕获`/localization/status`在source stamp **261.796s**转为state 4、valid=false、reason `normalized_cost_exceeded`，normalized cost同为`1.082783`。下一条raw telemetry（261.760s）cost回落至约0.509，但直到`fixture-result.json`之后2秒尾窗内status仍invalid。该因果顺序确认了这次拒绝来自单帧残差超限；**单帧异常的物理／视觉根因仍未确定**。Clock最大源戳间隔/接收间隔 `0.148/0.103s`，raw telemetry `0.068/0.168s`，status `0.056/0.051s`；探针未观察到大于0.25s的这些主题间隔。没有调整健康门限。

支架helper在6/12阶段原样以`localization changed or became invalid during physical scan`失败；安全清理verified detached，fixture移除及scene model absence均确认。484条PX4状态全DISARMED、263条LandDetected全landed。独立读回bridge `DISABLED/localization_not_tracking`、armed=false、landed=true；PX4 `arming_state=1`、LandDetected landed。没有ready marker、attached gate、post-release/current-area gate或飞行命令。容器停止后`exited 0`，活动项目容器数0。

## 下一步

N07仍为0/3，N07及N05阈值不变。#187将回到已有证据支持的`n06_full_airframe_retreat_240_oblique_early_view`支架路线：相同镜像和runtime此前#165/#167/#168/#170完成12/12并取得30秒no-goal hover PASS；随后从#187开始固定此路线连续重复，减少返回段异常尝试的风险，不改变悬停控制或判据。逐文件哈希及probe事件见[JSON报告](n07-preflight-localization-failure-20261024-186.json)。
