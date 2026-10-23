# N04 raw 地图几何与空间分类证据

状态：**通过（两种布局的测量与复算出口）**。机器可读摘要：[JSON](n04-map-geometry-20261023.json)。

该结果关闭 N04 的诊断测量交付，不代表完整 GOAL C、轨迹净空、飞行或正式任务验收通过。本轮未新增地图误差门限；所有不一致和时序变化均保留在报告中。

## 运行身份与快照

两轮使用同一固定镜像 sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8 和同一当前源码／配置运行契约。每轮都是新 VINS epoch，运行未启动 PX4、控制桥或导航目标。ROS 图分别为 7 个节点、59 个 topic，PX4、控制、真值节点和 topic 检查均为 0。在线建图输入不含真值；Gazebo 真值只用于单独的离线投影、轨迹对齐与遮挡几何检查。

| 布局／运行 | Epoch | map_id | source stamp（3 个快照，秒） | 单次 SE(3) 对齐位置误差 RMSE / p95 |
|---|---|---|---|---:|
| 墙、箱、柱：[wall run](../../artifacts/runs/n04-20261023-wall-r02/analysis/n04-map-geometry-analysis.json) | 98321642285f4968bb05400a4bcd2c47 | 98321642285f4968bb05400a4bcd2c47-6c78a77e19a44cffac13dfa63d0d870c | 8.977 / 15.115 / 20.725 | 0.00693 / 0.01292 m |
| 墙、通道、箱、柱：[corridor run](../../artifacts/runs/n04-20261023-corridor-r01/analysis/n04-map-geometry-analysis.json) | e2d221739bbe41b8a786ed2c37af0997 | e2d221739bbe41b8a786ed2c37af0997-b0d618a271c341a193cd9502b276b09e | 8.746 / 16.006 / 22.771 | 0.00557 / 0.01021 m |

每轮 3 张 raw occupancy 快照均保持同一 epoch、map_id 和 odom frame；栅格为 400×400×60、0.1 m 分辨率、origin [-20,-20,-0.15]。快照保留 source/fusion/snapshot stamp、相机 K 与外参、模型／配置哈希及 raw 和 inflation 数组。六个 occupancy NPZ 均完成精确归档回读。

两布局相机内参为 fx=fy=337.20964、cx=320、cy=240；深度到机体平移 [0,0.025,0] m，外参旋转及逐张快照配置哈希见各自分析文件。深度—VINS 位姿精确源戳配对覆盖率均为 1.0；raw 深度头到建图输入戳覆盖率分别为 0.9980 和 0.9960；CameraInfo K 与模型差值小于 1e-3。

两种布局的 truth 投影使用同一批已融合深度的离线相机真值替换，不进入在线地图。143,317 / 154,800 个抽样返回点对解析 SDF 表面的 p95 误差分别为 1.84 / 3.06 mm。轨迹对齐是单次刚体 SE(3)，尺度固定为 1，只用时间配对的 VINS IMU odometry 与真值拟合；地图点不参与拟合。

## raw 分类、遮挡与表面

| 布局／快照 | 表面中心误差 p95 / 最大值 | 位于半体素对角线内 | 中央墙面厚度（中位 / p95 / 最大层数） | occupied 集 Jaccard／墙面移动 |
|---|---:|---:|---:|---:|
| wall 1 | 0.0488 / 0.0611 m | 100% | 1 / 1 / 1 | 首张 |
| wall 2 | 0.0467 / 0.0662 m | 100% | 1 / 1 / 2 | 0.697 / 0.00023 m |
| wall 3 | 0.0457 / 0.0589 m | 100% | 1 / 1 / 2 | 0.962 / 0.00004 m |
| corridor 1 | 0.0746 / 0.0915 m | 99.3% | 1 / 1 / 1 | 首张 |
| corridor 2 | 0.0777 / 0.0949 m | 98.4% | 1 / 1 / 1 | 0.876 / 0.00015 m |
| corridor 3 | 0.0694 / 0.0954 m | 98.4% | 1 / 1 / 2 | 0.349 / 0.09821 m |

半体素对角线为 0.08660 m；通道布局有少量表面中心超过该界，但全部小于一个 0.1 m 体素。墙面中心截面以单层为主。通道布局第三张快照相对第二张出现接近一体素的墙面位移和较低 Jaccard，作为时序量化不稳定保留；它没有被平均或重配准消掉。

| raw 分类检查 | wall 布局 | corridor 布局 |
|---|---|---|
| 障碍前预期 free ROI | 每张 168/168 raw free；inflation 分别 120、120、102 | 每张 81/81 raw free；inflation 分别 45、45、33 |
| 全程被 SDF 遮挡的后方 ROI | 549/549 条相机视线被离线 SDF 阻挡；每张 784/784 raw unknown | 558/558 条相机视线被离线 SDF 阻挡；每张 785/785 raw unknown |
| 遮挡区 inflation（独立掩码） | 每张 336 | 281、281、393 |
| 深入实体内部超过半体素对角线的中心 | 8 个体素均 unknown，raw free 为 0 | 1 个体素为 unknown，raw free 为 0 |
| 预期可见 free 射线样本中却为 raw occupied | 13/12,327；5/19,759；3/19,855 | 276/5,338；4/5,892；2/5,951 |
| 无冲突 free 投票的预期表面 hit 中为 raw occupied | 624/630（99.0%）；876/1,028（85.2%）；501/626（80.0%） | 263/263（100%）；42/46（91.3%）；354/367（96.5%） |

无冲突的预期表面 hit 中，其余 raw free／unknown 分别为 wall 6/0、0/152、0/125 格；corridor 0/0、4/0、12/1 格。这些 free cells 是表面漏分，unknown cells 是尚未分类；均与 occupied 比例分开报告。

射线分类每次只取融合深度帧与像素的确定性子集，因此是可见覆盖下界，不宣称穷尽整张地图。表面 hit 与 free 投票冲突的体素单独标注；包含任意 hit 的格子里仍有 wall 布局 26.9%–47.7%、corridor 布局 0%–36.2% 为 raw free 或 unknown。分析同时保留这些离散冲突、false occupied 与表面 false-free 数，不用 inflation 掩盖。

## 融合与快照延迟

| 布局 | source stamp→融合完成仿真时间 p50 / p95 / 最大值 | callback→完成稳态时间 p50 / p95 / 最大值 | 快照服务耗时范围 |
|---|---:|---:|---:|
| wall | 99 / 138.2 / 149 ms | 47.6 / 69.1 / 73.8 ms | 78.0–101.4 ms |
| corridor | 99 / 132 / 145 ms | 41.4 / 61.7 / 66.5 ms | 72.5–99.0 ms |

source 年龄与 steady-clock callback 耗时分别统计；snapshot service 耗时也单独报告，不相互替代。

## 身份、原始产物与复算

两次运行 runtime-contract.json 的文件哈希完全一致；契约覆盖的 473 个仓库文件与当前工作区逐一匹配。聚合源码文件集哈希为 d6142c01791f37d534ac2de3118a80ba0f63416e4c02e4bba56b6dc8b05d4cd1，契约文件本身 SHA256 为 ef281cf24abc0a283db3c320919320124d0afd9ed7137fd16589e377fe8199a3。corridor run 另存的 19 项采集／评估工具链哈希也均与当前文件匹配。

| 运行 | 输入与分析摘要 SHA256 | 三张 raw occupancy archive SHA256 |
|---|---|---|
| wall | mapping input e6a7b2c82ef25e6e25eaca37109ded9ee036fb8c0aec32ddca0fa66ff31a7ac6；深度 NPZ 4f27dae18f3c44d1e4fb3cc29a18825b7981a2f1db81bc655f311ea153f75e73；分析 JSON fdb9561aaf76f1829e3ea61d025c32c750b2bd1ae60f21b236f8d715a2312f40 | [1](../../artifacts/runs/n04-20261023-wall-r02/snapshots/snapshot-01/occupancy_snapshot.npz) a4686940ee53a2f7272b045e0ff286f50beec4cc4f2d568f837a56ae7087b537；[2](../../artifacts/runs/n04-20261023-wall-r02/snapshots/snapshot-02/occupancy_snapshot.npz) 8008c958d46258f2cf718a5e237c516fddbe083014c4a30a3bccee9f83ed99be；[3](../../artifacts/runs/n04-20261023-wall-r02/snapshots/snapshot-03/occupancy_snapshot.npz) 84673b47e72440afb140b50b5beade7261ca7f435d1b4c6d8b23e3bac6a540f8 |
| corridor | mapping input 095fcf8bbb7d436b1abb4e6855ec1f2f8c9ccef024bb15e0ad92e4c28387c141；深度 NPZ 0a74474ec161d164086903aae0941ddb1f53101b133125904295d23c6d661edc；分析 JSON 70d8c5e383d7827971b24806c71d40092618ddaf994aaf3c9e043ebc09f42007 | [1](../../artifacts/runs/n04-20261023-corridor-r01/snapshots/snapshot-01/occupancy_snapshot.npz) 1edaae63e42402e7f8fdf54d2389895e0668b19e43ebc61ce1437bbe6997ada8；[2](../../artifacts/runs/n04-20261023-corridor-r01/snapshots/snapshot-02/occupancy_snapshot.npz) 8641e341da849a4a538d564a8f5764907a9269021aaf938eafcdb2233899762a；[3](../../artifacts/runs/n04-20261023-corridor-r01/snapshots/snapshot-03/occupancy_snapshot.npz) 06a757efd19f41fe60eb56c6fd1789106fc64f3ed447b3d9ace6f1be5e887ff1 |

重新运行 python3 -m unittest tools.test_n04_map_geometry -v：5 项通过。两布局与独立 truth SDF 共 4 个生成 SDF 均经 gz sdf -k 验证有效。评估器在包含原始 run 和配对 stack/session 的临时副本中再次运行成功；分类计数与已存报告一致，几何字段只有浮点尾数差异。原始采集目录由容器 root 持有，直接重算在写射线 NPZ 时收到 PermissionError；未改写原始文件。

python3 tools/project_status.py：结构／设计检查通过；检查器列出 80 条历史 artifact 链接缺失提示，不影响通过状态。git diff --check：通过。该结构检查不替代构建或 SITL。

首个 wall 启动尝试 n04-20261023-wall-r01 因 ROS 环境在 nounset 下加载失败而在 Gazebo/VINS 启动前终止，原始失败记录保留且不计入几何结果。两次有效诊断容器均已停止。

验证范围止于 N04 的 raw 几何和空间分类诊断；N05 起降入口、整机扫掠、制动与所有正式场景验收仍未通过或未执行。
