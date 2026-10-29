# #285 起飞后前向走廊拒绝与离线方向证书复算

## 运行事实

冷启动 `n08-cancel-translation-prescan-20261026-285` 的 N05 纯平移扫描完成 6/6，释放后 N05 在线／离线准入通过。任务前 full symmetric corridor、home pad、只读 preflight 和 runtime 指纹检查通过。飞机解锁、起飞并稳定后，旧式对称 raw capsule 在首个采样球内发现 32 个 unknown、0 occupied，于是 fail-closed 落地；`action_goal_sent=false`，没有 EGO 目标、轨迹、取消动作或制动测量。

空中快照仍为同一 epoch／map_id，源龄 0.168 s、融合龄 0.068 s。32 个格子仅位于起点机尾侧的薄层：x `[-1.1,-1.0]` m、y `[-0.3,0.3]` m、z `[0.6,1.2]` m。旧首个采样球半径 0.993118 m，最近格面距球心 0.956765 m；这解释了拒绝来自后方盲区，而不是前方占据或 EGO 输出。

独立 PX4／bridge 读回确认：bridge `LANDED`、控制关闭、未解锁、LandDetector landed、PX4 arming state=1、控制样本为 0。项目运行容器已停止。该次飞行结论仍是失败／未完成，不能计入 N08。

## 方向走廊离线复算

用当前 runtime gate 对 #285 **同一张**空中 raw map 离线重放：保持机体半径 0.730618 m 和 0.25 m N08 margin，固定前移查询球 0.075 m，按 25 个位置采样前向路线；实际曲线必须留在 5 cm 横／垂向管道内、x 不得倒退，实际跟踪误差仍受 0.15 m watchdog 限制。连同采样间覆盖上界，reachable-center bound 为 0.240139 m，查询可用 margin 为 0.262500 m，余量 0.022361 m；起点 hold 余量 0.025 m。

复算结果：前向路线 25/25 查询 raw free，unknown=0、occupied=0；起点 hold 球通过；目标端仍检查未平移、全向 `body+0.25 m` hold 球并通过。原对称查询仍能重现首球 32 个 rear unknown 拒绝。候选目的地的下降／接触几何也在同一快照离线复算通过，21 个阶段样本无 unknown／occupied；它不是本次实际降落路径的运行证据。

这一复算只证明几何门可以在实际存档图上按已约束的单段前向路径工作，不能代替后续冷启动、EGO 运行、取消停车／保持、独立制动测量和 landed/disarmed 验收。完整逐站查询、地图 hash 与离线降落阶段计数见 [机器报告](../../artifacts/runs/n08-cancel-translation-prescan-20261026-285/n08-airborne-forward-corridor-offline-replay.json)。原始地图及原始失败运行保留在 [#285 产物目录](../../artifacts/runs/n08-cancel-translation-prescan-20261026-285/)。
