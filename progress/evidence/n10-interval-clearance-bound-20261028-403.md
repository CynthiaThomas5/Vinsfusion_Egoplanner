# N10.3/#403：#398 物理步间净空下界

> 2026-10-28 #438更正：本页为历史结果；当时将IMU包络按base_link使用，并将平滑twist视作瞬时端点，其连续界通过结论不能用于N10冻结。原始记录保留，正确参考及当前不足见[n10-reference-unification-20261028-438.md](n10-reference-unification-20261028-438.md)。

## 结论

复用 #398 归档完成离线评估，没有新增 SITL。修正真值参考点与机体包络坐标后，4 ms 无接触物理步区间的保守全机净空下界为正，最小值 **0.174355 m**。该结果仅是当前 Gazebo 模型下的空气中几何校准；着陆滑橇接触区间单独分类，不宣称碰撞期间也有自由飞行动力学界，也不作为 N10 最终净空阈值或实机保证。

## 方法与来源

真值 odometry 的 pose/twist 参考 Gazebo `x500_d435i` 模型原点；配置包络则以 `base_link` 为参考。PX4 Gazebo X500 base SDF 将 `base_link` 放在模型原点上方 0.24 m。评估器现将每个真值位姿转换到 `base_link` 后计算包络净空，并将旋转半径和线加速度统一换算到 odometry 模型原点。模型原点到包络最远点的保守半径为 0.544076 m。

对每个完整 4 ms 区间，使用两端真值速度/角速度较大值，加上由模型约束的区间内最大线/角加速度，得到机体任一点速度上界；再以“点到最近端点最多半个物理步”的距离扣减端点包络净空。动力学上界使用 X500 质量/惯量、4 个转子的最大推力和 SDF 最大转速、推力力臂、气动反扭矩、一个完整物理步内最大转子角动量变化、转子阻力和滚转力矩，并对角速度、转子链速度作自洽上界。世界文件配置步长为 0.004 s、重力 9.8 m/s²；动态方箱按最终 SDF 的位置和尺寸视作全程存在，早于实际注入时也计入，属于保守处理。

接触事件逐碰撞对分类：仅配置文件列出的 `base_link_collision_3/4` 与 `ground_plane::link::collision` 可归入允许滑橇接触；其他碰撞对、空碰撞对均不纳入自由飞行界。contact observer 的 run/goal/epoch/runtime 身份与 #398 匹配，独立接触评估报告禁止接触 0，观察到着陆地面接触。

运行身份链核对通过：#398 runtime contract 中的依赖锁 SHA 与当前 `dependencies/sources.json` 相同；PX4 主仓库 revision 为 `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`，Gazebo 子模块 gitlink/锁定 revision 为 `b6127f4ec20de867e215fb5f78ae88b80f371909`，X500 模型 SDF SHA 为 `cfe92f98360967faa895b77aa8a6fff3fc9b290286e94e45297c4bdd7b62fbf9`。相机组合模型、D435i、x500_base、motor plugin、ESC bridge、运行镜像和预飞行冻结记录也均匹配。#398 没有单独保存 `x500/model.sdf` 的 run-local SHA，因此此项依据冻结依赖锁、主仓库 gitlink、子模块清单和未修改的锁定文件建立来源链；不是逐次运行直接记录的 SDF 哈希。

## #398 归档复算

- 目标至首个 `LANDED` 时间域：101.772 s，25,444 个真值状态，覆盖每个配置的 4 ms 求解步。
- 24,627 个无接触区间（98.508 s）全部得到正下界；最小下界 0.174355 m，位于 151.596–151.600 s。该区间端点最小包络净空 0.186661 m，区间运动扣减 0.012306 m。
- 816 个与接触事件相交的区间全部只含允许的两根滑橇对；禁止接触区间及接触事件戳数均为 0。这些区间不计入空气中动力学下界。
- 全部求解状态的采样包络净空最小值为 0.186661 m。整个 goal-to-landed 时间段仍应按“空气中区间有正模型界，滑橇接触阶段另行接触评估”解释。

机器可读报告：`artifacts/runs/n10-20261027-398-speed040-integrated-calibration/n10-interval-clearance-bound.json`。该报告 SHA-256：`d17bf86e376124e88c6166aeed1e44889d8ae09bcfdadff4319fd51d4f7d775c`。

## 验证与限制

- `PYTHONPYCACHEPREFIX=/tmp/n10-pycache-20261027 python3 -m py_compile tools/debug_truth/evaluate_n10_interval_clearance_bound.py tools/test_n10_interval_clearance_bound.py`：通过。
- `PYTHONPYCACHEPREFIX=/tmp/n10-pycache-20261027 python3 -m unittest tools.test_n10_interval_clearance_bound tools.test_n10_clearance tools.test_n09_contact`：20 项通过。
- `PYTHONPYCACHEPREFIX=/tmp/n10-pycache-20261027 python3 tools/debug_truth/evaluate_n10_interval_clearance_bound.py artifacts/runs/n10-20261027-398-speed040-integrated-calibration`：退出 0，状态 `AIRBORNE_MODEL_BOUND_POSITIVE_CONTACT_PHASE_SEPARATE`。
- `git diff --check`：通过。

下界只针对记录到的 Gazebo SDF/动力学，不包含制造误差、未建模部件、定位/地图/跟踪不确定度或控制输入到地图的测量误差，不得直接作为场景验收阈值。#403 没有飞行或改变在线控制。N10.3 仍需补 #402 source-covered live snapshot、场景跟踪/定位误差预算、故障类校准及资源/队列依据；N10.4–N10.7 未通过，N15/N16 仍在 N10 冻结后。
