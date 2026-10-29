# N07 #179：attached N05 freshness 阻断，无飞行

**结果：FAIL；N07 连续合格计数从 2/3 重置为 0/3。** N05 attached gate 没有接受，因此本轮没有解锁或起飞，不计 N07 悬停次数。

## 固定身份与扫描

Run `n07-20261024-179-01` 使用固定镜像 `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`、runtime contract `12b1c17cccfcb5c9f035516baa3d40c05ab7b8a4d5c32c4e28bef47d15b46233`、wall_box_column 与 `n06_full_airframe_retreat_240_oblique_separated_return`。epoch `94b4bc9fa796466aa712ba8cb541e18d`，map_id `94b4bc9fa796466aa712ba8cb541e18d-fe38a68aff11471ab864abc46a099ea6`。初始 N05 按既有规则拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`；支架按 DISARMED 流程完成 **12/12** 阶段并到达 attached ready marker。采样到 2185 条 VINS 记录，其中 0 条 nonusable/current/finite 检查失败；最后 localization 为 state 1/valid。

attached N05 检查生成结构化 fail-closed 结果，随后报错：`map source, fusion, or snapshot age exceeds the N05 freshness limit`。错误没有给出单独的 snapshot、source、fusion 数值；原 0.4 秒门限没有改变。门未接受，未运行 hover。

## 释放后诊断与安全状态

释放支架后的一次标准 post-release N05 检查在同 epoch/map 恢复为 `all_entry_phases_known_and_clear`，online/offline replay 匹配；freshness 为 snapshot/source/fusion **0.108/0.156/0.028 s**。这只说明稍后的 release 状态新鲜，不能替代失败的 attached gate。

fixture runner 错误 `localization changed or became invalid during physical scan` 原样保留；同时记录 12/12 完成、attached→detached、fixture removed、`fixture_may_remain_attached=false`、final landed 和车辆状态 DISARMED。post-release gate 报告 bridge `DISABLED`、unarmed、landed、control disabled，land detector 为 landed；Gazebo model list 没有 fixture。一次性 bridge topic echo 没发现 publisher，但 `ros2 node list` 确认 bridge 节点存在，post-release gate 的状态快照有效。项目容器按流程停止，`Exited (0)`。

## 下一次可判别动作

现有证据支持一个待验证假设：最终支架回位后立即读取 attached N05 时，snapshot/source/fusion 刷新短暂落后；支架释放后系统恢复新鲜。#180 只改变一个时序变量：ready marker 后、保持支架附着和 DISARMED 的状态下等待 **2 墙钟秒**，再执行原 attached online/offline gate。profile、镜像、runtime、N05 阈值和飞行前置均不变。此举不预先接受 gate，也不允许 gate 失败后起飞。

完整结构化字段和逐文件哈希见同名 JSON；原始运行产物在 `artifacts/runs/n07-20261024-179-01/`。
