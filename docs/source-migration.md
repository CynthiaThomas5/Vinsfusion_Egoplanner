# 初始文件来源与迁移顺序

`dependencies/initial-sources.json` 保存项目初始化时的只读来源快照，不是当前迁移清单或可移植依赖锁。此后 VINS 与 EGO 规划核心已按固定上游版本迁入；本表保留初始迁移背景，当前工程统一由`tools/fetch_dependencies.py`从清单重建，运行不读取旧工程。当前版本、补丁与验证见 [sources.json](../dependencies/sources.json) 和下表。

| 来源位置 | 新项目目标 | 迁移方法 |
| --- | --- | --- |
| ../PX4-ROS2-SLAM-Control-Deploy/src/px4_dlio_bringup | src/own/uav_px4_bridge、uav_navigation、uav_bringup | 先审计当前未提交 diff，再按职责迁入必要逻辑与相关测试 |
| 旧工程 src/ego_planner、plan_env、bspline_opt、path_searching、traj_utils、quadrotor_msgs | src/vendor/ego_planner/planner | 旧工程 HEAD `92b0030150f8ba35da3b55e57f5b426dd2c22cb0` 且工作树脏；完整差异与 EGO-only 差异保存在 `artifacts/runs/p0-source-audit-20261016/legacy-tracked.patch`、`artifacts/runs/p0-ego-build-20261016-02/legacy-ego-only.patch`。旧 EGO 添加了 `control_hold` 暂停／恢复修改，但包许可证为 TODO；旧 quadrotor_msgs 声称 MIT 但包内无 LICENSE，均未导入。改用 ZJU-FAST-Lab `ros2_version` 固定提交 `23a8d5a191711dd65633df689bd00f55d4dea8f9`，仅导入五个规划核心包，保留 GPL-3.0 许可证，以自有 `uav_interfaces/PositionCommand` 替代 quadrotor_msgs。初始三份补丁与Jazzy构建历史见 [EGO 审计](../progress/evidence/p0-ego-planner-build.json)。旧 hold/resume 行为须在自主执行前由 own 集成层实现。 |
| ROS_SEARCH/.artifact-work/vins-integration/fully_fixed.patch | dependencies/patches/vins | 核对补丁 base 和内容覆盖，不盲目叠加 final／before 等历史补丁 |
| 同目录 internal_health/telemetry_only.patch | dependencies/patches/vins | 确认与修复版组合、源码提交及候选二进制对应 |
| 同目录 internal_health/session_protocol/vins_session_interface.py | src/own/uav_localization | 提取会话、锁定和状态契约，去除实机专用启动路径 |
| 同目录 rgbd_geometry/geometry_20261016_152901/geometry_contract.json | config/components/calibration/real_d435i | 作为 PROVISIONAL 实机参考；仿真外参重新由 SDF 生成 |
| Kinang2/Ego-Planner-System | 深度输入及 launch 的参考差异 | 只读参考；不导入整套第二份 Offboard 控制，不作为当前 planner 来源 |
| zinuok/VINS-Fusion-ROS2 | src/vendor/vins_fusion | 固定上游提交并恢复实机已测修复，再适配 Jazzy |
| 官方 PX4 v1.17.0 与本机只读 PX4 checkout | `external/PX4-Autopilot`（已按固定提交独立构建）与 `src/vendor/px4_msgs` | 官方 tag 解为 commit `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`；px4_msgs v1.17.0 对应 commit `86d8239e962f6939e05c3737784f60c02fa884db` 已以无补丁归档导入并通过 Jazzy 构建。记录 uXRCE client 子模块与 `dds_topics.yaml`；本机 checkout 的唯一未跟踪工具链归档保持不动。详见 [版本核验](../progress/evidence/p0-dependency-pins.json) 与 [px4_msgs 构建](../progress/evidence/p0-px4-msgs-build.json)。 |

## 导入检查

1. 记录原仓库 HEAD、git status 和必要 diff；提交号不能代表脏工作树全部内容。
2. 对照旧实现与上游接口，列出保留修复、舍弃原因和许可。
3. 在新目录导入所需源码或固定版本 checkout，不移动／修改来源。
4. 记录 base、补丁应用顺序、源码版本和构建二进制哈希。下载目录被 Git 忽略，因此 manifests 与 patches 才是重建依据。
5. 补齐构建与回归，更新 dependencies/sources.json 的 imported、revision、patch 状态及 progress。

旧工程的 DLIO 与 Livox 插件仅作为回归参考，不进入视觉最终验收输入。不要复制 build、install、log、.env 或完整 .git。完整原方案保存在 ROS_SEARCH，当前项目只维护与实施相关的权威架构和进度。
