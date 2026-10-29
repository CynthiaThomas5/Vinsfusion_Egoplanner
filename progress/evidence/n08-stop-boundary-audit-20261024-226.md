# N08 #226：首动停止边界审计

**结果：不能证明安全停止边界，执行保持锁定。** 本项只审计 #225 的 compute-only 轨迹、固定源码和 raw map；没有执行 XY。

## 同图 EGO 曲线与几何

使用 #225 post-release／mission current-area 同字节 raw map（SHA-256 `2d7fec586fa7d3873b36f2d2fa5611178b73b963ba7663c2f2b95183c1b29de1`）重建 live `Bspline`。它对应本 run goal/epoch，长度约 0.564 m、时长 5.267 s。以 B-spline 导数控制点凸包给出速度上界 0.201797 m/s，再按 body radius 0.730618 m 和 `speed × dt / 2` cover inflation 做 43 次 raw midpoint sphere query，整条曲线都 free；终点机体球和 0.980618 m terminal-hold 球也都 free。

但实际曲线起点的 terminal-hold 球有 49 个 unknown。沿曲线终点方向做同图延伸，距离曲线起点 0.8 m 的 stop sphere 仍 free，0.9 m 处已有 2 个 unknown；因此从 EGO 目标到已知边界只剩约 0.262 m 的中心位移余量。这是地图几何空间，不是测得的可用制动距离。

## 速度和 PX4 制动信息

`n08_low_speed_calibration.json` 配置 `max_velocity_m_s=0.15`。运行 manifest 确认该值传到 EGO；固定 EGO 源码的 feasibility check 按各坐标轴分别检查，并允许 5% tolerance，对应每轴阈值 0.1576 m/s。#225 实际 READY B-spline 的 x 轴峰值约 0.1787 m/s，导数控制点 x 最大 0.1860 m/s；向量峰值约 0.1937 m/s。因此不能把当前 profile 的 0.15 当作总速度上界，也不能把当前输出算作满足每轴门限。该曲线仅在桥输入隔离时生成，没有实际执行。

run 内 PX4 参数快照没有记录 `MPC_ACC_HOR`、`MPC_ACC_HOR_MAX`、`MPC_JERK_AUTO` 或 `MPC_XY_VEL_MAX`。固定 PX4 v1.17 源码中的对应值是水平最大加速度 3／5 m/s²、自动 jerk 4 m/s³、水平最大速度 12 m/s；这些是最大控制限制，不是制动减速度下限或响应延迟保证。当前没有可信的 `response_delay_max` 和 `a_min`，所以无法计算合格的 `d_stop`。

若只按 0.8 m free boundary，曲线目标后最多还有 0.262 m 中心位移。对已观察峰值 0.1937 m/s，即便先假设 0.2 s 响应延迟，也需要至少约 0.088 m/s² 的最小减速度；对每轴配置推得的向量上界 0.273 m/s，则需要至少约 0.169 m/s²。上述只是边界条件反算，不是已测得或已保证的制动能力。

## 结论与下一步

- 不运行实际 XY；mission execute 继续 fail-closed。
- 新增 same-run live B-spline 速度／raw-map certificate，按向量速度门验收真实输出，并在取消前拿到可核验地图证据。
- 记录 PX4 水平参数，并建立有来源的延迟上界和最小减速度；未满足前继续不执行。

完整数值、输入路径和源码 SHA-256 见 [`JSON 审计`](n08-stop-boundary-audit-20261024-226.json)。
