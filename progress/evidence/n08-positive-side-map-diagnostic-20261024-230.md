# N08.2t #230：正侧观察后的动作失败地图

**结果：** 19 阶段支架扫描和 N05 release/current-area 准入完成；compute-only 在 B-spline 前以 `planner_full_curve_unknown` 拒绝目标。失败态 observer 成功保存同身份 raw map。无 READY 样条、无 XY、无制动数据；停止包络未证明，N08 继续 `in_progress`。

## 运行和健康

- Run：`n08-20261024-230-positive-side-view-01`，场景 `n08_overhead_calibration`，profile `n08_overhead_positive_side_view`，完成 19/19 stages。该 profile 在 #228 overhead scan 后增加 +π/2 水平观察并回中。
- Fixture helper 原样报告 `localization changed or became invalid during physical scan`，所以 `fixture.outcome=failed`；独立记录显示完成 19 stages、attached→detached、模型移除、最终 landed。不得把 helper 错误改写为通过。
- N05 post-release 与 mission current-area 的 online/offline admission 均为 `all_entry_phases_known_and_clear`，结果逐项一致，同 epoch/map：`64b0353771b849b488b37d02917f6cef`／`64b0353771b849b488b37d02917f6cef-e1dd9d22d50e43fd904ea80de7fa4d5f`。current-area raw map SHA-256：`fd3e34032b51945b2af4b2220b06dbae554afc099d705022973addeb262363b7`。
- 只读 preflight 通过 40.003 s，最大 optimized-odometry receipt gap 83.4 ms，没有超过 guard。source timeline 覆盖 40.4 s：806/806 LocalizationStatus valid，175/175 MapStatus `ready`，无 source-stamp 倒退。
- `flight.json` 为 FAIL，目标终态 `aborted:planner_full_curve_unknown`；没有 READY、没有 PositionCommand 样本，也没有 cancel/hold 后续阶段。桥通过 operator disable 进入着陆，最终 `LANDED`、未武装、landed；容器 stop 后退出码 0。

## 失败态 raw map

Observer 记录匹配 goal ID `20d7a8ce20f04142aa7d37b4a554140d`，并在 spline 缺失时保存 raw snapshot。目标时间为 sim 573.332 s，快照时间为 579.400 s，相差 6.068 s；epoch、map_id、frame 一致。它是任务拒绝后的同身份快照，不冒充失败瞬间的逐样本地图。

使用该 run 的 goal 和 `n08_compute_only_fresh_map_goal.json` 的 `[0.5,0.2,0] m` offset 反推起点，再以 `tools/probe_n06_live_layout.py` 的 production-mirror raw query 复算。current-area 与失败后 raw map 得到相同结果：

| 查询 | 结果 |
| --- | --- |
| 起点 body，半径 0.730618 m | free，0 unknown |
| 起点 hold，半径 0.980618 m | unknown，309 cells |
| 目标 body，半径 0.730618 m | free，0 unknown |
| 目标 hold，半径 0.980618 m | unknown，42 cells |
| 目标前的 production-mirror 直线 sweep | 首次查询即 unknown，6 cells；cover radius 0.742857 m |

首个失败查询中心为 `[0.599408,-0.163693,0.964707] m`。起点／目标坐标由目标 offset 反推；因为没有生成 B-spline，直线复算只能定位缺失区域，不能宣称它等于 EGO 内部曲线的精确查询点。Unknown voxel 位于实测地面 `z=-0.35 m` 以上。N05 起降准入使用机体包络并已通过；较大的 N08 hold sphere 与连续曲线 cover query 仍发现 unknown，这两个结论范围不同。

PX4 boot readback 中 `MPC_ACC_HOR=3`、`MPC_ACC_HOR_MAX=5`、`MPC_JERK_AUTO=4`、`MPC_XY_VEL_MAX=12` 都是最大限制；运行没有可用的响应延迟上界或最小可用减速度。因此不能从当前配置推得停止距离，也不能解锁 execute。

## 产物与复核

- 原始 run：`artifacts/runs/n08-20261024-230-positive-side-view-01/`
- map capture：`n08-live-curve-map.json` / `.npz`；compute-only result：`flight.json` 与 `n08-compute-only-evaluation.json`。
- 主输入和结果的 SHA-256、结构化查询与机器可读状态见同目录 JSON 证据文件。
- 运行期间的容器均已退出；没有活跃仿真进程。

## 下一子项

曾离线找到“释放点 +Y 0.30 m”候选，但复核 `tools/probe_preflight_scan.py` 的 `AXES=('x','z','yaw','pitch')` 后确认，现有 N05 支架没有 y 轴；该释放位姿不能按现有支架流程实施，也未改 spawn／场景去绕开此限制。

当前可直接复核的旧图候选保留同一释放点，compute-only 目标改为相对起点 `[+0.10,+0.25,0] m`（位移 0.269 m）。该旧图上 body 与目标 terminal-hold 均 free，连续 path 11 个查询全 free；目标后继续 0.50 m 的 swept body corridor 20 个查询全 free，末端 hold 球也 free。**起点 hold 球仍有 309 unknown**，所以它尚不是完整 geometry certificate。下一步 fresh N05 / compute-only 只用来验证新 epoch 的实际曲线和地图；旧图不授权 XY，动态停止边界仍未实测，execute 继续锁定。
