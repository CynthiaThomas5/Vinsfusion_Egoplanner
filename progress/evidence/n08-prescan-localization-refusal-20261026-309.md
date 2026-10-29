# N08 #309：前置 N05 扫描定位健康拒绝

状态：未进入 N08 mission。全机支架扫描在第 7/15 阶段被现有定位健康门安全中止；没有 post-release N05、任务区准入、目标、解锁或制动证据。

## 运行结果

- 新 cold start：run `n08-cancel-highspeed-prescan-20261026-308`，配置 `n08_low_speed_trial.json`，profile `n08_overhead_free_sector_negative_y_side_view`。
- 扫描前 raw-map N05 baseline 因 `ground_plane_insufficient_raw_occupied_voxels` 拒绝；快照为 9,600,000 unknown、0 free、0 occupied。该检查是支架观测前的 baseline，不是 post-release 准入结论。
- 支架行进到第 7 阶段返回段时，localization health 在 sim 312.380 s 锁存 `normalized_cost_exceeded`：1.094002 > 原门限 1.0。对应 VINS 样本 final cost=2948.417、4927 residuals；其中 visual cost=2813.960/4734，IMU cost=6.889/120，marginalization cost=127.568/73。输入特征 180、stereo 167、continued tracks 178，accel bias 0.03387 m/s²。
- 同一进程随后 VINS solver 样本的重算代价回到约 0.51，但 health latch 已按 fail-closed 规则锁存，不能把后续低代价样本当作恢复或准入。
- #305 曾用相同 15 阶段负 Y 侧视 profile 完成扫描并通过 post-release 与 mission-current-area N05；本次 profile 路线数据相同，但 helper 源码 hash 已变化，因此这是当前 helper/runtime 上的新证据。当前与 #305 的源码差异和 hash 记于 JSON。

## 安全末态

fixture 已 detach，Gazebo 确认模型已移除；PX4 独立读回为 DISARMED、landed、at-rest；bridge 为 DISABLED、control_enabled=false、armed=false、landed=true。仅停止本 run 的项目容器，stop 命令和容器退出码均为 0。未运行 N08 mission，也没有起飞或制动样本。

机器摘要与 SHA256：[#309 JSON](n08-prescan-localization-refusal-20261026-309.json)。原始材料位于 `artifacts/runs/n08-cancel-highspeed-prescan-20261026-308/`。

## 下一步假设

只再做一次相同 profile 的独立 cold start，变量为 estimator 的 cold-start realization。判据是能否完成 15/15、fixture release 与同身份 post-release N05；若定位健康门再次在相同返程阶段触发，就停止重复这条路线，改用两次锁存时序来设计后续有界 profile。任何 N05 或 N08 准入拒绝都不发目标、不解锁。N08 父目标仍未通过。
