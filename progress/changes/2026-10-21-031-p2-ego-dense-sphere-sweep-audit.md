# GOAL C 第二障碍布局连续机体包络审计 #383

关联对话：[2026-10-21-031](../../collaboration/dialogues/2026-10-21-031-p2-ego-dense-sphere-sweep-audit.md)。

使用 #321 两条完整 active B-spline 和各自已接受的同 epoch、map_id、frame 快照，独立检查完整机体包络。车辆尺寸来自 #246 固定 PX4 x500 碰撞模型与名义 D435i 外壳，IMU 原点的方向不变包围球半径为 0.4819358707 m。分析按 1 ms 采样，使用 B-spline 导数控制多边形的速度上界扩大样本球，覆盖连续采样间隔；逐体素盒分类 unknown/free/occupied、inflation 与地图外。

两条样条均与目标及快照匹配 epoch/frame，且 requested/returned map_id 相同；快照时间差为 +1 ms、0 ms，深度源龄为 130 ms、99 ms。完整机体球扫掠分别触及 1,342/1,241 个 unknown voxel，937/841 个 inflation voxel 和 141/153 个唯一地图外 voxel；没有触及 raw occupied。相对地图中已知 raw occupied voxel 的保守几何下界为 5.94 cm/10.90 cm。来源运行清单的19个输入产物哈希均匹配。

该路径不能判为已知自由：两条模型碰撞 AABB 均比快照最低 z 边界 -0.15 m 低约 5.3–5.5 cm，且unknown与inflation仍在完整包络内。unknown／地图外交叠不是物理碰撞证据；这个运行也未执行轨迹，不能证明跟踪、最小机距或制动安全。保留现有 fail-closed 行为，不改 canonical 参数或源码；GOAL C与P4状态不变。

验证：`python3 artifacts/runs/p2-ego-dense-sphere-sweep-audit-20261021-383/audit_body_sweep.py` 退出0并生成分析及运行清单；19/19来源产物哈希通过；`py_compile`、JSON解析、`python3 tools/project_status.py` 和 `git diff --check` 结果见本次完成检查。轻量报告：[证据](../evidence/p2-ego-dense-sphere-sweep-audit-20261021-383.json)；原始分析：[body-sweep-analysis.json](../../artifacts/runs/p2-ego-dense-sphere-sweep-audit-20261021-383/body-sweep-analysis.json)。

下一步核对本地 odom 下的地面高度、机体有效起飞高度与 map z 下界；在新 epoch 中以同一机体包络复测可分类的完整路径，再继续第二障碍布局和轨迹执行验收。
