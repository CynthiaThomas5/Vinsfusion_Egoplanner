# N07.24 #178：第二次连续无目标悬停冷启动

## 执行模式与范围

Goal 完成模式；用户指定范围 N07。父目标保持 in_progress，当前连续合格冷启动为 1/3。仅重复 N07 当前固定版本的支架准入、EV 融合与无目标悬停，不改代码、配置、参数、健康门、N05 阈值或出口。

## 已有基础与缺口

#177 在新 epoch 中完成 12/12 全机支架路线，attached、post-release、current-area N05 online/offline gates fresh 一致通过；连续只读 stream probe 未见 stale，30 仿真秒 no-goal hover 与独立 11/11 N07 评估通过。N07 仍需至少两次连续且独立的 cold start。

## 固定条件与完成标准

- 固定镜像 SHA-256 `099ab9afecd28b7354f6d6494944b1db30c7c67c973e9b93b03f87aca7ad6f8`、runtime contract SHA-256 `856bf1f2222a5286493813c9702731f7e5166844eb2bfd98c6f525f3f36924eb`、spawn `(-6.5,0,0.3,0,0,0)`、`wall_box_column` 与 `n06_full_airframe_retreat_240_oblique_separated_return`。
- 使用新 container/run/epoch；N05 live/offline gate 不接受或 hover 前定位不 fresh 时 fail-closed，不解锁。
- N05 attached、post-release、current-area gates 必须 fresh 接受且同一 epoch/map；支架 12/12 完成、脱离与模型缺失由独立证据确认。
- 完成至少 30 仿真秒 no-goal hover，独立误差、时序、PX4 EV/GNSS/ULog、唯一 bridge publisher 与最终 landed/disarmed 证据齐全。
- 成功后连续计数 2/3；任一验收失败重置连续计数。禁止放宽任何门限。

## 结果

#178 通过，连续合格冷启动为 2/3。attached、post-release、current-area N05 online/offline gates 共用同一 epoch/map、全部 fresh 接受；N05 汇总 14/14 通过。30.0 仿真秒无目标悬停、独立 N07 11/11、PX4 EV/no-GNSS ULog、ROS graph 唯一 bridge 控制 publisher、最终 landed/disarmed 均通过。支架 helper 的 `localization changed or became invalid during physical scan` 错误原样保留；12/12 阶段、2212 个 sampled VINS records 全部 usable/current/finite、最后 localization valid、fixture removal 与独立 landed readback均有证据。容器 Exited(0)。完整结果见[证据报告](../evidence/n07-no-goal-hover-20261024-178.md)。

## 下一项

N07.25 #179：相同固定版本启动第三个独立 cold start；成功后 N07 连续序列达到 3/3，随后检查全部 N07 出口证据一致性并更新父目标状态。任何新健康、准入或悬停失败都按原标准重置计数。
