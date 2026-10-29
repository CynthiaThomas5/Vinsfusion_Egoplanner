# N08 #311：验证 rear unknown 观测 profile

- 用户授权：按规划完成 N08；普通目标单程前向，到点停止，不自动返航。
- #310 raw-map live gate 的全部 unknown 都在起点后方 rotor-1 扩张范围，仅影响起点和最初 2.5 cm 查询；当前几何预算仍要求这些 cell known-free。
- 决定：在 DISARMED N05 fixture scan 中使用 rear-facing 观察来测量该区。修改唯一变量：#307 yaw 回中后的首段下降从 8 秒调到 12 秒；不改变 flight 方向、地图门或任何阈值。
- 静态 `tools.test_preflight_scan` 42/42 通过；尚无 SITL 通过证据。
- 下一步：run `n08-cancel-highspeed-prescan-20261026-311`。只有 fixture 完全移除、landed/disarmed、同 identity N05 与只读 preflight 通过，才继续检查实时 N08 forward corridor；若仍有 unknown，不发 goal/enable。
- 证据：`progress/evidence/n08-rear-short-hold-slow-descent-profile-20261026-311.md`。
