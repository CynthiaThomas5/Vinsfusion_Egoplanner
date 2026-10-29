# 构建、迁移与运行

当前入口采用 FAST Lab 官方 EGO 碰撞语义：独立垂直起飞后导航，按 inflated occupied layer 判碰撞，raw unknown 保留且不单独拒绝。epoch／frame／源时间完整性、唯一控制桥、PX4 原生 preflight／EV 融合和 EGO 原生输入超时继续生效。旧 N05 known-free 准入及经验质量门不在默认路径。

## 从空目录重建

按根 README 克隆源码和固定环境分支。环境的准确 commit、约1.48GB归档大小和SHA见 `docker/environment.json`，可先checkout该commit再运行 `git lfs pull`。校验SHA后再解压加载，不能把未下载的LFS指针当镜像。固定环境已在空Docker引擎导入并启动ROS/Gazebo；完整源码已在另一空目录实际fetch和构建。当前实物异机资格与干净环境证据分开记录，不宣称任意设备均已实测。

```bash
bash tools/project.sh fetch
bash tools/project.sh build
bash tools/project.sh test
python3 tools/check_container_image.py
```

`fetch`按commit、许可和补丁哈希获取源码，拒绝覆盖已有目标。ROS只使用本目录的 `build/install`；PX4位于 `external/PX4-Autopilot/build/px4_sitl_default`。正常构建／运行不读取旧项目、历史run或其他设备的安装目录。需要网络下载固定上游；镜像归档提供已验证二进制环境，原始基础镜像的完整构建配方尚不可追溯，不承诺仅靠Dockerfile从任意基础系统重新制作完全相同环境。

GitHub 22端口不可达时，可按[GitHub官方SSH443说明](https://docs.github.com/en/authentication/troubleshooting-ssh/using-ssh-over-the-https-port)使用 `ssh.github.com:443`。本次发布已验证该通道；不需要修改项目源码、复制作者私钥或更改仓库可见性。

## GUI和默认任务

登录桌面后执行 `./start.sh` 或 `./start.sh fly`。脚本识别当前用户Xorg/XRDP的DISPLAY和XAUTHORITY；无桌面时会明确报告。命令行指定run时：

```bash
bash tools/project.sh sim room-demo-01 --gui
bash tools/project.sh mission room-demo-01
bash tools/project.sh stop room-demo-01
```

`sim`保持未武装，`mission`才显式请求飞行。默认房间起点x=-8m，相对目标+16m，正常结束后降落上锁。一个run只执行一次任务，新任务使用新run/epoch。`stop`只在确认落地上锁后执行。脚本只清理本项目会话，不处理其他GPU服务。

无GUI的底层入口为 `project.sh sim RUN_ID`，仍使用NVIDIA传感器渲染。当前最终回归包含GUI；实际验证范围见最终验收报告。多GPU服务器可用 `PROJECT_GPU_DEVICE=1 bash tools/project.sh sim RUN_ID --gui` 选择宿主GPU，实际UUID记录在run内。

## 状态、取消与降落

结果与日志在 `artifacts/runs/RUN_ID/`。`qualification.json`给出普通任务的独立到达、接触、正常终态和唯一控制检查，正式场景／连续负载另有专门报告。评估程序不发布控制。

进入运行中的容器查看ROS接口：

```bash
docker exec -it d435i-RUN_ID bash
source /opt/ros/jazzy/setup.bash
source /workspace/install/local_setup.bash
ros2 topic echo /mapping/status
# 另一个终端可查看定位／导航状态或实际PX4状态
ros2 topic echo /localization/status
ros2 topic echo /fmu/out/vehicle_status_v1
```

独立导航调用使用 `/navigation/navigate_to_pose`（`uav_interfaces/action/NavigateToPose`），目标frame为当前 `odom_<epoch>`。取消通过标准action客户端或对应CancelGoal服务；只处理当前任务，旧epoch目标与轨迹失效。

显式请求正常降落由唯一桥接器协调。在上述容器ROS终端执行：

```bash
ros2 service call /uav_px4_bridge/enable_offboard \
  uav_interfaces/srv/EnableOffboard '{enable: false}'
```

观察PX4和bridge确实落地、未武装、控制关闭后再停止容器。普通 `fly` 会自动完成该过程。正常降落接口可用范围不代表用户排除的故障退出专项已经验收。

## 独立接口调用与持久数据回读

已正常落地、仍保持运行的会话可运行独立调用样例：

```bash
python3 tools/probe_handoff_interfaces.py \
  --output artifacts/runs/RUN_ID/handoff-interface-result.json
```

在容器中执行。程序实际查询地图、检查旧epoch拒绝、读取定位和带位姿RGB-D，并提交观察位姿目标、获取到达或明确失败结果；不使能Offboard、不发布PX4控制。#573实际得到 `map_query_occupied` 的明确终态。

用ROS原生MCAP保存实际关键帧和地图状态，在同一容器ROS终端执行，若干帧后Ctrl-C停止记录器：

```bash
ros2 bag record --storage mcap --storage-preset-profile zstd_fast \
  --output artifacts/runs/RUN_ID/handoff-archive \
  --topics /mapping/rgbd_keyframes /mapping/status
python3 tools/inspect_handoff_archive.py \
  artifacts/runs/RUN_ID/handoff-archive \
  --output artifacts/runs/RUN_ID/handoff-archive-inspection.json
```

回读直接反序列化文件，不向在线ROS重放。报告保留完整图像字节哈希、CameraInfo K、图像源时间位姿、epoch、map_id、标定与输入配置身份。#573已有10组真实记录回读通过。

三维占据数组服务为 `/mapping/get_occupancy_snapshot`。`tools/capture_live_occupancy_snapshot.py --help`给出模型、输入/规划配置、实际ROS参数dump及源清单绑定方式；它保存同一快照的raw/inflated数组、坐标原点、分辨率、源/融合/快照时间和身份，并实际回读校验。#573在同一epoch/map内完成该路径。未知值仍为unknown，局部快照不提供跨重启重定位。

## 离线误差与证据

```bash
python3 tools/debug_truth/evaluate_odometry.py artifacts/runs/RUN_ID --plot
```

需同轮raw VINS、真值、状态时间线、模型和运行身份。一次起飞前固定scale=1刚体对齐，不逐段拟合。NumPy/Matplotlib可在分析机安装；它们不进入控制链。位置/yaw/速度/RPE、跟踪、地图、净空与资源保留实测；当前正常功能验收的必要项以冻结配置及用户范围修订为准，不恢复取消的数值否决。

## 导出和版本更新

```bash
bash tools/project.sh export artifacts/exports/my-delivery
bash tools/project.sh export artifacts/exports/code-only --code-only
```

完整包包含源码、固定镜像、逐文件manifest和SHA256SUMS；排除vendor/external下载、build/install、原始运行日志、本机配置、凭据和raw聊天。历史归档不存在时，导出器先精确校验本地镜像的固定内容再生成归档；已有归档校验失败仍拒绝。GitHub源码和环境分支是分开的交付入口；所有接收方都需要相应访问权限。

早期实验说明保留在 [历史运行手册](history/running-before-n17-20261029.txt)，其中的旧门禁、参数和未完成状态不适用于当前默认入口。固定版本场景与历史失败在最终验收报告中分别登记；实机、语义/信念/自主探索和故障专项均不在当前完成范围。
