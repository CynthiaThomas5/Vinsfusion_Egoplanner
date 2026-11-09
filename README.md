# VINS-Fusion · EGO-Planner · D435i Groundstation

基于 Intel RealSense D435i、VINS-Fusion、EGO-Planner 和 PX4 的 ROS 2 室内视觉导航工程，包含仿真导航、Jetson Nano 端感知与规划，以及 Debian 地面站实时显示和诊断工具。

仓库：<https://github.com/CynthiaThomas5/Vinsfusion_Egoplanner>

当前为 `explore` 探索分支；`main` 与 `demo-baseline-2026-11-09` 保留现有演示源码。目录隔离、环境边界与晋级方法见 [分支工作流](docs/branch-workflow.md)。

## 功能与数据链

```text
D435i 双目 / IMU ──→ VINS-Fusion ──→ 定位与 epoch 管理
D435i 深度 + 定位 ──→ 在线占据地图 ──→ EGO-Planner ──→ 导航 action
                                                        │
                                      唯一 PX4 桥 ──────→ PX4
Nano 端视觉 / 状态 ──→ SSH 只读传输 ──→ Debian RViz / 记录与诊断
```

- 单相机双目惯性定位，在线深度占据建图与局部轨迹规划。
- `NavigateToPose` action、取消与反馈，以及定位、地图和会话身份接口。
- 地面站显示双目特征、稀疏点、机体轴、轨迹、占据地图与规划参考采样。
- 分层启动、运行记录、时延诊断、依赖版本和补丁哈希管理。
- 仿真定位和规划使用 CPU；Gazebo 和 RViz 的渲染使用 NVIDIA GPU。真值只用于隔离调试和离线评估。

## 当前状态与适用范围

本仓库整理自 `gs02-20261106-freeze01`，包含截至 2026-11-09 的本地工作树更新。原有实现和历史证据保留，整理发布不产生新的运行验收结论。

| 路径 | 环境与已确认范围 | 当前限制 |
| --- | --- | --- |
| 仿真 | Ubuntu 24.04 x86_64、ROS 2 Jazzy、Gazebo Harmonic、固定 Docker 环境；历史室内导航证据保留 | X500 与 quad250 的资格分别记录，不继承到实机 |
| Nano 计算端 | Jetson Nano / ROS 2 Foxy；已有 D435i、VINS、建图与规划地面实验记录 | 最新 fresh build 和地面链路待目标机复核 |
| Debian 地面站 | Jazzy 容器、RViz、SSH 传输；GS02 动态展示出口通过 | 历史动态显示长滞后触发原因尚未定位 |
| 实机 PX4 | 已有 DDS、时间同步、EV 与坐标转换实现及台架记录 | HW08/HW10 未完整通过，不具备实机飞行验收结论 |

最新状态以 [progress/CURRENT.md](progress/CURRENT.md) 为准；硬件主线仍为 HW10-EV-028。最新系统整改范围及待验证项见 [整改计划](docs/tasks/SYSTEM-AUDIT-001-remediation-plan.md)。

## 获取源码

```bash
git clone git@github.com:CynthiaThomas5/Vinsfusion_Egoplanner.git
cd Vinsfusion_Egoplanner
python3 tools/project_status.py
```

源码仓库不包含 Docker 大镜像、第三方展开源码、构建安装目录、原始运行日志、崩溃转储或本地 CAD 参考资料。第三方版本、补丁顺序、哈希与许可见 [依赖说明](dependencies/README.md) 和 [sources.json](dependencies/sources.json)。

## Debian 地面站快速使用

以下命令适用于**已部署并配置好的** Debian 地面站和 Nano，完整步骤见 [中文使用指南](docs/使用指南.md)。克隆源码本身不会安装 ROS、相机驱动或 Nano 环境。

1. 检查 `config/groundstation/debian.env` 中的镜像、Nano SSH 别名、工作区及 ROS 域，按自己的设备修改。SSH 别名与密钥配置在本机 `~/.ssh/`，不入仓库。
2. 确认 Nano 已有匹配的 Foxy / RealSense 环境和构建安装，地面站已导入所需镜像并具备图形桌面。显示镜像构建配方见 [groundstation.Dockerfile](docker/groundstation.Dockerfile)，完整部署约束见 [Debian 说明](docs/groundstation-debian.md)。
3. 在仓库根目录检查、启动和正常停止纯感知实验：

```bash
bash tools/groundstation.sh check
bash tools/groundstation.sh status
bash tools/groundstation.sh experiment-start
# 等待定位有效及起点记录提示后，再进行缓慢移动与观察。
bash tools/groundstation.sh experiment-stop
```

`experiment-start` 启动纯感知与显示，不启动地图、规划、EV 或控制。运行记录保存在 `artifacts/runs/<run_id>/`，原始数据不入 Git。

需要建图与规划计算时，在结束旧会话后执行：

```bash
bash tools/groundstation.sh nano-start plan
# 另开终端显示地图；不会自动发送导航目标。
bash tools/groundstation.sh map-view
# 按使用指南结束显示，并停止所属计算会话。
bash tools/groundstation.sh nano-stop
```

地面站通过 SSH 调用 Nano 原生 ROS，并在本地隔离域显示，不依赖 Foxy 与 Jazzy 直接 DDS 互通。Nano 分层构建与运行约束见 [硬件运行说明](docs/hardware-running.md)；设备标定和安装身份不能用示例值代替。

## 仿真运行

历史 X500 验收版本为 `sim-nav-v1.0.0`，证据见 [最终验收报告](progress/evidence/FINAL_ACCEPTANCE.md)。quad250 快照 `sim-nav-quad250-2026-10-30` 已有默认房间和柱群 16 m 单次任务记录，不继承 X500 的多场景、重复和长时资格，详见 [模型说明](docs/quad250-simulation.md)。这些名称是原项目的历史版本引用，不保证新远程已包含同名标签。

仿真需要 Docker、NVIDIA 驱动与 Container Toolkit、X11、Git LFS 和 zstd。固定环境仍从 `docker/environment.json` 指定的**原环境仓库**获取，未随本次源码迁移复制；需要该仓库访问权限。原始固定镜像不能仅靠本仓库 Dockerfile 完整重建，见 [固定环境说明](docker/README.md)。

### 仿真固定环境部署

先准备 Docker、NVIDIA 驱动／Container Toolkit、Git、Git LFS 和 zstd，并配置你自己的仓库访问权限。源码与固定环境分开存放，源码分支不携带大镜像或历史飞行日志。

```bash
git clone git@github.com:CynthiaThomas5/Vinsfusion_Egoplanner.git
# 新仓库保存当前地面站快照；历史仿真资格见下文，不假定已迁入旧标签。
# 在另外一个目录取得固定运行环境，并检出源码清单中的不可变 commit
RUNTIME_COMMIT=$(python3 -c 'import json; print(json.load(open("Vinsfusion_Egoplanner/docker/environment.json"))["commit"])')
git clone --no-checkout --single-branch --branch runtime-environment-v1 \
  git@github.com:CynthiaThomas5/D435i-VINS-EGO-ROS2.git d435i-runtime
git -C d435i-runtime lfs install --local
git -C d435i-runtime checkout "$RUNTIME_COMMIT"
git -C d435i-runtime lfs pull
(cd d435i-runtime && sha256sum -c SHA256SUMS)
zstd -dc d435i-runtime/container-images.tar.zst | docker load

cd Vinsfusion_Egoplanner
bash tools/project.sh fetch
bash tools/project.sh build
bash tools/project.sh test
./start.sh fly
```

固定环境的不可变 commit、归档 SHA256 和内容指纹见 [docker/environment.json](docker/environment.json)。镜像跨 Docker 存储后端可能显示不同 ID，入口会核对固定文件层、完整运行配置和架构。已有部署更新时，使用新源码目录重新构建，避免把旧 vendor／install 混入新版本。

### 仿真日常入口

```bash
./start.sh          # 打开 Gazebo 与 RViz，保持未武装
./start.sh fly      # 起飞、执行默认 16 m 目标、正常降落并独立评估
./start.sh fly pillars # 多柱场景 16 m 任务，正常降落并独立评估
./start.sh status   # 当前会话和最近结果
./start.sh stop     # 任务结束、确认落地上锁后停止本项目会话
./start.sh start floorplan2  # 可选NavRL隔墙房间（未武装）
./start.sh fly floorplan2    # 可选场景默认任务；结果见各run报告
```

默认场景为 20×20 m 房间及 19 个圆柱，默认起点 x=-8 m，目标为起飞后相对 ENU +16 m；规划速度 0.4 m/s、加速度 0.25 m/s²。独立到达标准为位置 ≤0.30 m、yaw ≤15°、连续 ≥3 仿真秒。相机 IMU 的已知零陀螺偏置约束只适用于当前无注入噪声／偏置的仿真模型。

结果位于 `artifacts/runs/<run_id>/qualification.json`，同时保存运行指纹、原始状态、接触和终态记录。缺失证据不会被当作通过。默认演示使用新 PX4 状态和新 VINS epoch。

## 代码与接口

| 位置 | 内容 |
| --- | --- |
| `src/own/` | 8 个自维护 ROS 包：接口、传感器、仿真、定位、建图、导航、PX4 桥和真值调试 |
| `src/vendor/`、`external/` | 按固定上游和补丁获取的第三方源码，不入 Git |
| `config/`、`simulation/` | 运行参数、标定、模型、默认房间与固定资格场景 |
| `dependencies/`、`docker/` | 来源、补丁顺序、许可、环境身份和分发说明 |
| `tools/project.sh` | 获取、构建、测试、仿真、任务、停止与导出入口 |
| `tools/diagnostics/`、`tools/debug_truth/` | 只读记录及离线评估；其余探针和测试用于开发回归 |
| `progress/` | 轻量证据、状态与变更；大数据保留于本地 `artifacts/` |

提供 `NavigateToPose` action、取消／反馈、地图查询、RGB-D 关键帧、定位与 epoch 接口。独立样例及真实回读方式见 [运行手册](docs/running.md) 和 [接口契约](docs/contracts.md)。语义、信念与自主探索仅预留接口；已有实机地面计算链不代表飞行资格。故障专项按原仿真任务范围排除，历史未通过记录保留。

[运行与迁移](docs/running.md) · [架构](docs/architecture.md) · [固定环境](docker/README.md) · [来源与许可](dependencies/README.md) · [目标与范围](GOAL.md)

`src/own` 各 ROS 包沿用已有 Apache-2.0 声明；第三方分别保留其许可。其他文件及上游未声明许可的场景来源按依赖说明如实列明，未添加一份覆盖全仓库的授权。

## 文档与开发验证

- [中文使用指南](docs/使用指南.md)：当前地面站操作、记录与停止。
- [地面站接续上下文](GROUNDSTATION_CONTEXT.md)：现有部署和边界。
- [硬件迁移路线](docs/simulation-to-hardware-roadmap.md)：Nano、标定、DDS、EV 与控制的阶段约束。
- [GitHub 发布说明](docs/github-publishing.md)：源码范围、远程配置和后续更新。

文档与结构变更可执行 `python3 tools/project_status.py` 和 `git diff --check`；代码变更还需运行受影响模块的测试及对应 ROS 构建。结构检查不能替代 SITL、目标机或实机验证。
