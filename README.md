# D435i-VINS-EGO-ROS2

单 D435i 等效相机的室内视觉导航仿真：双目与相机 IMU → VINS → 在线深度占据建图 → EGO → 唯一 PX4 桥接器 → PX4 SITL。

定位和规划使用 CPU；Gazebo 相机与 RViz 使用 NVIDIA GPU。默认视觉链路从初始化开始不使用 GNSS、真值定位或完整世界地图；真值记录仅作独立离线评估。

**交付状态：N17 最终版本回归与发布审计进行中。** 干净依赖重建、18 个 ROS 包及 PX4 构建、729 项单元测试和 ROS 集成、默认 16 m GUI 飞行及地图／关键帧接口回读已验证。最终进度以 [CURRENT](progress/CURRENT.md) 为准；[最终验收报告](progress/evidence/FINAL_ACCEPTANCE.md) 在全部出口完成后定稿。

## 环境

当前验证环境为 Ubuntu 24.04 x86_64、NVIDIA RTX 4090、Docker 与 NVIDIA Container Toolkit、可访问的 X11 桌面。固定容器内含 ROS 2 Jazzy、Gazebo Harmonic、OpenCV 和 Ceres；不需要在宿主机另装 ROS、Gazebo 或 CUDA 定位库。其他硬件组合须先验证同一入口；本项目不包含 ARM 或实机资格。

## 新设备部署

先准备 Docker、NVIDIA 驱动／Container Toolkit、Git、Git LFS 和 zstd，并配置你自己的仓库访问权限。源码与固定环境分开存放，源码分支不携带大镜像或历史飞行日志。

```bash
git clone git@github.com:CynthiaThomas5/D435i-VINS-EGO-ROS2.git
# 在另外一个目录取得固定运行环境
git clone --single-branch --branch runtime-environment-v1 \
  git@github.com:CynthiaThomas5/D435i-VINS-EGO-ROS2.git d435i-runtime
git -C d435i-runtime lfs install --local
git -C d435i-runtime lfs pull
(cd d435i-runtime && sha256sum -c SHA256SUMS)
zstd -dc d435i-runtime/container-images.tar.zst | docker load

cd D435i-VINS-EGO-ROS2
bash tools/project.sh fetch
bash tools/project.sh build
bash tools/project.sh test
./start.sh fly
```

固定环境的不可变 commit、归档 SHA256 和内容指纹见 [docker/environment.json](docker/environment.json)。镜像跨 Docker 存储后端可能显示不同 ID，入口会核对固定文件层、完整运行配置和架构。已有部署更新时，使用新源码目录重新构建，避免把旧 vendor／install 混入新版本。

## 日常使用

```bash
./start.sh          # 打开 Gazebo 与 RViz，保持未武装
./start.sh fly      # 起飞、执行默认 16 m 目标、正常降落并独立评估
./start.sh status   # 当前会话和最近结果
./start.sh stop     # 任务结束、确认落地上锁后停止本项目会话
```

默认场景为 20×20 m 房间及 19 个圆柱，默认起点 x=-8 m，目标为起飞后相对 ENU +16 m；规划速度 0.4 m/s、加速度 0.25 m/s²。独立到达标准为位置 ≤0.30 m、yaw ≤15°、连续 ≥3 仿真秒。相机 IMU 的已知零陀螺偏置约束只适用于当前无注入噪声／偏置的仿真模型。

结果位于 `artifacts/runs/<run_id>/qualification.json`，同时保存运行指纹、原始状态、接触和终态记录。缺失证据不会被当作通过。默认演示使用新 PX4 状态和新 VINS epoch。

## 代码与接口

| 位置 | 内容 |
| --- | --- |
| `src/own/` | 7 个自维护 ROS 包：接口、仿真、定位、建图、导航、PX4 桥和独立真值调试 |
| `src/vendor/`、`external/` | 按固定上游和补丁获取的第三方源码，不入 Git |
| `config/`、`simulation/` | 运行参数、标定、模型、默认房间与固定资格场景 |
| `dependencies/`、`docker/` | 来源、补丁顺序、许可、环境身份和分发说明 |
| `tools/project.sh` | 获取、构建、测试、仿真、任务、停止与导出入口 |
| `tools/diagnostics/`、`tools/debug_truth/` | 只读记录及离线评估；其余探针和测试用于开发回归 |
| `progress/` | 轻量证据、状态与变更；大数据保留于本地 `artifacts/` |

提供 `NavigateToPose` action、取消／反馈、地图查询、RGB-D 关键帧、定位与 epoch 接口。独立样例及真实回读方式见 [运行手册](docs/running.md) 和 [接口契约](docs/contracts.md)。语义、信念、自主探索与真实设备仍在当前交付范围之外；故障专项按用户要求排除，现有 PX4／EGO 原生行为保持。

[运行与迁移](docs/running.md) · [架构](docs/architecture.md) · [固定环境](docker/README.md) · [来源与许可](dependencies/README.md) · [目标与范围](GOAL.md)

`src/own` 各 ROS 包沿用已有 Apache-2.0 声明；第三方分别保留其许可。其他文件及上游未声明许可的场景来源按依赖说明如实列明，未添加一份覆盖全仓库的授权。
