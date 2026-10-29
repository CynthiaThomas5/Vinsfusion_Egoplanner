# N07 #172：同一路线bias越线复现

## 结论

#172在与#171相同的全机支架路线第7段返程中再次触发`accel_bias_norm_exceeded`。扫描7/12中止，没有released N05 gate或N07 hover结果。支架清理及PX4 landed/disarmed已确认，容器经项目stop流程正常退出。当前N07连续悬停计数保持0/3。

## 运行条件与初始门禁

- Run：`n07-20261024-172-01`；epoch `3af1963433c34902a4365c6b1fd5468f`。
- 镜像：`sha256:099ab9afecd28b7354f6d6494944b1db30c7c67c973e9b93b03f87aca7ad6f8`；runtime contract SHA-256：`856bf1f2222a5286493813c9702731f7e5166844eb2bfd98c6f525f3f36924eb`。
- 与#171相同的`wall_box_column`、`n06_full_airframe_retreat_240_oblique_early_view`和`-6.5,0,0.3,0,0,0` spawn。
- 初始N05 online/offline结果一致拒绝`TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。没有绕过raw unknown，也未发布goal或控制。

## Bias时序

支架扫描完成阶段0–6。阶段6将pitch从0.45 rad回到0，`accel_bias_norm`在该段由约0.057167增至0.117803。阶段7从远端向起点返程平移，进入该段8.18仿真秒后，于sim t=282.680首次超过既有0.15 m/s²健康界（0.150472），之后最高升至0.179247。定位最终锁存`accel_bias_norm_exceeded`；失败前solver仍usable，normalized cost约0.592。

对比#171：同样在stage6 pitch归零后bias上升，随后stage7越线。相同`oblique_early_view` profile在#165、#167、#168和#170完成12/12，bias最大分别为0.143668、0.127973、0.077681和0.080401；#166、#171、#172于stage7失败。该分布表明失效与这套长斜视／pitch回零／返程动作序列相关，但没有证明具体上游因果。

既有profile `n06_full_airframe_retreat_240_oblique_separated_return`将0.45-rad pitch暴露从约130秒缩至30秒：#138 wall与#148 corridor均完成12/12，VINS bias最大0.085480与0.076170。#138的released N05仍因ground-plane raw occupied不足而拒绝，且发生在#142相机安装坐标修复前；#148 corridor release gate通过。故该profile是需在当前wall和模型组合下重新验证的假设，不是已证明的修复。

## 安全收尾

fixture回执确认detach、Gazebo场景无fixture模型、final landed且vehicle state为DISARMED。runner后直接只读回读为bridge DISABLED/unarmed/landed、PX4 arming state 1、land detector landed。`bash tools/project.sh stop n07-20261024-172-01`成功，容器`exited`、exit code 0，无活动项目容器。

## 原始数据与后续

主要运行数据在[`artifacts/runs/n07-20261024-172-01/`](../../artifacts/runs/n07-20261024-172-01/)：`n05-run-inputs.json`、runtime contract、初始N05 online/offline结果、`fixture-result.json`、`fixture-stages.json`、`fixture-trace.jsonl`和`fixture-vins.jsonl`。SHA-256清单见[JSON证据](n07-support-scan-health-failure-20261024-172.json)。

#173只改变为既有`oblique_separated_return` profile，其他版本、wall world、N05 gate和0.15 m/s²健康界不变。release gate未fresh通过前不进入hover。具体执行假设和判据见[#173变更记录](../changes/2026-10-24-173-n07-separated-return-health-pilot.md)。
