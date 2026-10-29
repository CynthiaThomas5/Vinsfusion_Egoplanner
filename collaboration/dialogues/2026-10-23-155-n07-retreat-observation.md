# #155 N07 远后视角诊断

用户授权继续 N07 Goal。用户追问地下空间的相关性；#154 双向扫描后的逐格审计确认 HOLD 未知格全部高于地面，地下 unknown 为 0。

## 本轮依据与假设

- #154-03b 在 `spawn=-8m` 使用 0.8m 后退、随后前进并回原点，释放后 HOLD unknown=422，N05 仍拒绝；地下 unknown=0。
- #146 已在 `spawn=-6.5m` 下执行 2.4m 单轴后退/返回，并获得释放后 N05 五阶段 online/offline 接受；全程 DISARMED。
- 本轮唯一主要变量是向后观测距离扩展到 2.4m。选择 `spawn=-6.5m` 是为复用 #146 已证实的同一全机静态走廊净空。yaw、pitch、门限及传感器配置不变。

## 限制与判据

本轮仅做 DISARMED 物理支架扫描与只读 N05 门禁，不解锁、不飞行。必须保持定位和身份连续、扫描后确认支架移除，且 N05 五阶段 online/offline 一致接受；拒绝时保留结果，不得以地面下规则放宽准入。结果记录在 `progress/changes/2026-10-23-155-n07-retreat-observation.md`。

## 结果

#155 完成 6/6 阶段、2.4m 后退和返回；10,177 条定位 trace 全有效且 epoch 单一。fixture 仍连接时 N05 五阶段 online/offline 一致接受，maximum unknown/occupied 均为 0。fixture 随后已确认 detached 并从场景删除，PX4 状态 DISARMED；helper 在 detach 后短状态等待返回码 2，外层脚本因此没有执行 release 后 N05 gate，容器退出 0。故本轮不是准入通过或飞行，下一步 #156 在 detach 后直接复验 fresh gate，只有通过才执行 N07 首次 hover。
