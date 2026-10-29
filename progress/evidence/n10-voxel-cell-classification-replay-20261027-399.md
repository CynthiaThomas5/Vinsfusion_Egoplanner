# N10.3/#399：#398 体素体积分类与验收器复算

## 目的与输入

复用 #398 已成功的 16 m 综合校准和同一 epoch/map 的 raw/inflated occupancy 快照，补足“中心落在真值箱体内”对边界 voxel 的歧义，并离线重放 N10 验收判断器。未启动新运行、未改运行控制和 acceptance 数值。

运行目录：`artifacts/runs/n10-20261027-398-speed040-integrated-calibration/`。

## 结果

- #398 `flight.json`：action succeeded，联合位置/yaw 容差驻留 3.344 仿真秒，正常完成 15 仿真秒诊断保持，并落地、上锁。goal ID `00c2771cd5534b98b7b8a7d8731b5980`；epoch `26a9d1edcc27473a8258d967adca08af`；runtime contract SHA-256 `01c674db1c9af1ae2e8fb20c0cb8fb9b75a46e83c7947a95ad300364e5119bc9`。
- 真值净空覆盖 25,444 个连续 Gazebo 物理步状态，最大源戳间隔 4 ms。观测离散最小机体净空为 0.18604 m；扣去端点间实际观测位移后的离散余量为 0.18301 m。报告明确指出，端点位移不是连续时间运动界；零违规接触也不是连续轨迹证明。
- tracking/clearance 配对 11,920 点，truth bracket 最大 4 ms；tracking P95/max `0.32679/0.34033 m`。平移误差下界在 583 点（4.89%）为负，最差 `-0.13879 m`。此诊断不代表碰撞或验收阈值。
- 固定 SE(3) 对齐的 raw VINS 目标航段绝对位置误差 P95/max `0.09525/0.09803 m`，yaw `0.1647/0.1674°`；10 s RPE 平移 P95 `0.03797 m`、旋转 P95 `0.1999°`。这些是单次校准观察值，不单独建立阈值。
- 快照地图分辨率为 0.10 m，与箱体、goal、epoch/map identity 匹配。按 voxel 中心计，箱体内 unknown/free/occupied 为 `1739/34/19`。新增的体积判别将 34 个 known-free cell 中的 13 个计为八角全部落入实体箱体，21 个计为中心在内但 cell 未完全包含；这避免把所有 34 个边界/内部中心值一概称为 occluded-free。按草案 `truth_occluded_raw_free_count_max=0`，13 个完整位于实体内的 known-free voxel 使该离线指标为 `FAIL`。
- 表面支持只覆盖 x-negative 与 y-negative 两面；另外四面无 occupied voxel 支持。该几何覆盖指标仍为 `INSUFFICIENT`，原因是缺少其它面可见性/遮挡证据。
- 注入 ACK 在 sim `124.220 s`；第一条**被记录**的箱体 ROI raw cloud header 为 `127.768 s`，快照在 `128.520 s` 请求（比该 cloud 晚 752 ms）。快照 latest depth source 为 `128.372 s`（比第一条被记录 cloud 晚 604 ms），fusion stamp 为 `128.496 s`；第二条被记录 cloud header 为 `128.388 s`，比 latest depth source 晚 16 ms。raw occupancy cloud 仅每十条采样一条，所以此前是否有未记录 cloud、以及 snapshot 是否融合了某个精确 cloud frame，不能确定。该时间线确认 source stamp 已越过第一条被记录 ROI cloud，但未越过快照前最后一条被记录 cloud。13 个几何内 known-free cell 保留为离线分类失败候选。
- 同身份的 26 个只读点查询均被接受并回显查询几何；point-query identity 与快照匹配。点查询 verdict 与稠密快照不是同一时刻，报告不将查询结果拼接成同一时刻地图。
- sensor capture 评估为 `PASS`：64,813 bag payload、64,850 receipt、一个 active identity tuple、payload 无 receipt 为 0；边界缺收据仅记为 4 左图、4 右图、29 IMU。资源观察 298 个约 1 s 样本、覆盖 301.077 wall s、终态安全；观测内存峰值 3.49 GB，OOM 事件 0。Map depth 队列高水位 8/容量 8、丢弃 36；keyframe 丢弃 31；VINS 内部队列容量未暴露，资源标准仍不足。
- 离线 acceptance v6 总评仍为 `INSUFFICIENT`：到达、raw VIO/RPE/速度、时效、离散真值净空/接触和观察器身份项可判；tracking threshold、map surface coverage、故障终态校准和平台资源依据未解决。raw map classification 候选项为 `FAIL`。配置仍为 draft；这些值均未连接控制。

## 方法与限制

新几何判别将每个中心位于真值箱体内的 voxel 八个角经固定 `world_from_odom` 变换后，逐一检查其是否完全处于凸实体箱体内部。只有全部八角都在内部的 known-free 单元才计入 truth-occluded raw-free 数；边界跨越单元单独保留。该法不使用全图真值、不发布控制，也不能从当前稀疏表面支持推出箱体外部自由空间的相机可见性。

快照触发安排在首个有 ROI 点的 decimated cloud 后 750 ms；source stamp 晚于第一条被记录 cloud 604 ms，但比下一条被记录 cloud 早 16 ms。该 source-time 进展有证据，精确 frame 吸收关系仍不可判定。#398 的成功任务、离散物理步覆盖与 sensor capture 可复用，但 N10.3 与 N10.4 不通过。不得把校准计入冻结后的 N15/N16 正式次数。

## 产物与复算

- 体素体积报告：`artifacts/runs/n10-20261027-398-speed040-integrated-calibration/n10-box-map-snapshot-analysis-v3.json`
- 验收重放：`artifacts/runs/n10-20261027-398-speed040-integrated-calibration/n10-acceptance-evaluation-v6.json`
- 原始输入和逐文件 SHA-256 见配套 JSON。
- 定向测试：`PYTHONPYCACHEPREFIX=/tmp/n10-399-pycache python3 -m unittest tools.test_n10_occupancy_snapshot tools.test_n10_acceptance`，29 项通过。

仍需解决：动态观测 cloud 是否进入 snapshot 的时间覆盖、其它面覆盖、truth-occluded 分类与实际安全语义、故障到 PX4 最终状态、tracking 几何预算以及平台/内部队列依据。父 N10 保持 `in_progress`。
