# D435i-VINS-EGO-ROS2：单 D435i 视觉导航仿真

啊城对于 EGO 和 VINS 的探索。

ROS 2 Jazzy · Gazebo Harmonic · PX4 v1.17.0。

单 D435i 双目与 IMU → VINS → 深度占据建图 → EGO → `uav_px4_bridge` → PX4。定位、规划使用CPU；Gazebo传感器和RViz使用NVIDIA GPU渲染。在线定位／规划不使用GNSS、真值位姿或完整世界地图；真值评估独立且只读。

当前默认参数来自[当前房间三连导航基线](progress/evidence/cpu-navigation-convergence-20261021-051.md)：20×20m房间、19柱、相对16m目标。源码／入口整理后的构建与复测状态见[当前进度](progress/CURRENT.md)，不能把旧构建结果自动算到新构建。

## 快速开始

需要Linux、Docker、NVIDIA Container Toolkit；固定镜像随[分享包](docs/running.md)交付。初次在干净项目内执行：

```bash
bash tools/project.sh fetch             # 固定上游、补丁哈希与许可；拒绝覆盖已有依赖
bash tools/project.sh build             # 单一 install/，构建ROS与PX4
bash tools/project.sh test              # 回归测试
./start.sh                             # 自动识别桌面，打开Gazebo与RViz，不起飞
./start.sh fly                         # 前检→起飞→16m目标→降落→独立评估
./start.sh status                      # 当前会话和最近任务结果
./start.sh stop                        # 关闭已落地的会话
```

`start.sh`自动生成新run id；任务完成后再次`fly`会从新会话开始。已有部署直接使用这四条命令，无需重复fetch/build。须先登录服务器桌面；脚本支持当前DISPLAY或自动识别自己的XRDP桌面，底层仍调用`tools/project.sh`。

任务报告在 `artifacts/runs/<run_id>/qualification.json`；新会话不复用PX4参数状态或VINS epoch。每次只启动一套项目仿真，所有PX4控制消息由桥独占。

## 工程入口

| 目录 | 职责 |
| --- | --- |
| `src/own/` | 6个自维护ROS包：接口、传感器、定位、建图、导航、PX4桥 |
| `src/vendor/` | 从锁定清单重建的唯一第三方源码，下载内容不入Git |
| `config/` | 运行、标定、规划与控制参数的单一来源 |
| `simulation/` | 机体／D435i模型、房间和纹理 |
| `dependencies/` | 上游revision、补丁顺序、哈希和许可 |
| `tools/project.sh` | 获取、构建、测试、仿真、任务、停止与分享入口 |
| `tools/diagnostics/`、`tools/debug_truth/` | 独立只读记录与离线评估；真值不回馈控制 |
| `tools/test_*.py`、其余`probe_*` | 开发回归与故障注入工具，不随默认启动运行 |
| `progress/` | 当前状态、阶段条款、轻量证据；原始运行数据在`artifacts/` |

[运行与分享](docs/running.md) · [架构](docs/architecture.md) · [坐标与控制契约](docs/contracts.md) · [目标及范围](GOAL.md) · [依赖](dependencies/README.md)

## 验证范围

#062已增加目标原始体素球准入：未知、占据、越界或查询失败会阻止向EGO转发。已完成构建、隔离测试和不解锁查询；历史16m演示通过不能继承到新版本，完整轨迹及失效降落净空仍待验证。见[当前进度](progress/CURRENT.md)。

当前房间候选曾完成三次独立冷启动；不是任意目标／场景或实机验收。未知空间、完整机体扫掠、制动预算、长时负载和正式A–H仍按GOAL推进。虚拟IMU250Hz对齐4ms物理步，不声明真实D435i标定已经完成。

工程未指定自维护代码的对外授权许可证；第三方GPL／BSD／Apache／MIT各自保留。房间上游未声明许可，来源与现状如实记录在依赖清单。分享包在本地生成，不自动上传、提交或推送。
