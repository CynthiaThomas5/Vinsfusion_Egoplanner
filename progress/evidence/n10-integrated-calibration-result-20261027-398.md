# N10.3/#398 综合校准结果

## 运行身份与任务

运行目录：`artifacts/runs/n10-20261027-398-speed040-integrated-calibration/`。运行合同 SHA-256：`01c674db1c9af1ae2e8fb20c0cb8fb9b75a46e83c7947a95ad300364e5119bc9`；goal `00c2771cd5534b98b7b8a7d8731b5980`，epoch `26a9d1edcc27473a8258d967adca08af`，map `26a9d1edcc27473a8258d967adca08af-fb4b5f89c26e44a29fbb388e4843ae80`。冻结的 EGO 规划 profile 为逐轴 `max_velocity=0.4 m/s`、`max_acceleration=0.25 m/s²`、horizon 5 m。

PX4 原生 preflight/EV 融合和起飞准入通过。16 m action succeeded；独立联合位置/yaw 容差窗口 3.344 仿真秒，窗口最大位置误差 0.29955 m、最大 yaw 0.15703 rad。完成 15 仿真秒诊断保持并按正常 bridge/PX4 路径落地上锁。`flight.json` 为 PASS、`landed_and_disarmed=true`；driver 退出 0；安全末态独立读回后才停止项目会话。未使用 emergency disarm。

## 校准数据

- 目标航段固定对齐 raw VINS 位置误差 P95/max `0.09525/0.09803 m`，yaw `0.1647/0.1674°`；10 s RPE 平移 P95 `0.03797 m`、旋转 P95 `0.1999°`。这些数据补充当前版本的分段校准，不构成通用门限。
- tracking/clearance 有 11,920 个同目标 identity 配对点，最大真值括区间 4 ms；tracking P95/max `0.32679/0.34033 m`。平移-only 下界在 583 点（4.89%）为负，最差 `-0.13879 m`；该下界不是碰撞结论。对应几何预算仍无依据，不能据此冻结追踪限值。
- 从 goal stamp 到首个 LANDED 样本记录 25,444 个 Gazebo 物理步真值状态，覆盖 101.772 sim s；最大间隔为完整的 4 ms physics step，off-grid 状态 0。采样最小全机包络净空 `0.18604 m`；扣除实际相邻观测包络位移后的离散余量 `0.18301 m`。全程禁止接触事件 0。相邻步观测位移不是速度/角速度连续界，以上不证明连续时间净空。
- 单次动态方箱体注入在 sim `124.220 s` 得到创建 ACK；首条**被记录**的箱体 ROI raw cloud header 为 `127.768 s`。ACK 后 `0.416 s` 已见第一条替换样条，早于该点云，因此不把该样条归因于箱体。样条/真值记录及箱体 SDF 离线评估显示箱体全机采样净空最低 `1.10954 m`；零违规接触。该样本不足以定义重规划响应期限。
- 同一 epoch/map 的 raw/inflated snapshot 和 26 个 raw sphere/planning point query 均身份匹配并被接受。快照分辨率 0.10 m。后续 #399 的体素体积复算发现 34 个中心位于箱体内的 known-free cells 中有 13 个 cell 的八角完整位于实体箱体；raw classification 草案候选为 `FAIL`。快照 latest depth source (`128.372 s`) 比首条被记录 box cloud (`127.768 s`) 晚 604 ms，但比快照前第二条被记录 box cloud (`128.388 s`) 早 16 ms；ROI cloud 每十帧采样一次，无法关联到精确被融合的 cloud frame。fusion stamp 为 `128.496 s`。仅 x-negative、y-negative 两面有 occupied surface 支持，其余四面覆盖不足。
- 只读 sensor capture 评估 PASS：64,813 bag payload、64,850 receipts、单一 active identity、payload-without-receipt 为 0。资源采样 298 点，覆盖 301.077 wall s；观测内存 peak 3.49 GB，OOM 0；depth queue 高水位 8/容量 8、drop 36，keyframe drop 31。VINS 内部 queue capacity 未暴露，缺平台容量基准，资源 acceptance 保持不足。

## 结论与后续

本次校准补齐了成功任务、当前版本 tracking/VIO、4 ms 离散净空、sensor receipt、动态方箱和正常 landed/disarmed 的证据。它没有进行故障注入。离线验收总评 `INSUFFICIENT`；map raw classification 是未冻结草案下的指标 `FAIL`，表面覆盖、tracking 几何预算、故障终态、资源/队列依据仍不足。不得把该校准当成冻结后的 N15/N16 正式次数。

详细的字段、方法与逐文件哈希见[#399 体素分类与验收器复算](n10-voxel-cell-classification-replay-20261027-399.md)。
