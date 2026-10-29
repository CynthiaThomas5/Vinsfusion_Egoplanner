# #154 N07 在线悬停资格采集准备

对话摘要：[N07 实际 EKF2 融合与无目标悬停](../../collaboration/dialogues/2026-10-23-154-n07-live-hover-qualification.md)

## 范围与已有基础

N07 依赖 N02、N03、N05、N06 已满足；N06 证据只覆盖 planner 集成及合法未武装入口准入。N07 仍要求同一固定组合下 3 次独立 SITL 冷启动、每次至少 30 仿真秒无目标悬停、独立误差、实际 EKF2 EV 融合、无 GNSS／真值辅助、唯一控制发布者，并真实落地／DISARMED。历史 #054、#396 不代替本出口。

## 本次准备

- 将 N07 登记为 `in_progress`，设置 N07.1 为当前子项，保留 `execution_plan.next_goal=N07`。
- 无目标探针输出自身的 monotonic 时钟原点；Gazebo 原生只读真值采集器为每个真值样本增加 monotonic 时间，供独立保持误差按同机时间配对。
- 新增 [ROS graph 采集器](../../tools/diagnostics/capture_n07_ros_graph.py)，在预备和空中 ACTIVE 期间记录 PX4 输入控制话题 publisher identity 和 ROS 真值节点／话题。
- 新增 [ULog 分析器](../../tools/debug_truth/analyze_n07_ulog.py) 与 [N07 hover 误差评估器](../../tools/debug_truth/evaluate_n07_hover.py)，覆盖真实 EKF2 aiding flags、启动参数、VINS 固定预对齐真值误差和 PX4／Gazebo hover 位移误差。
- 真值采集使用 Gazebo Transport 原生话题，不启动 ROS `debug_truth` 适配器；控制、定位和规划链不订阅该通道。
- 首版 `n07_default_spawn_oblique_translation_only` 未武装支架profile 复用 #146 的低速路径，水平位移限制为 +1.2m（支架正向机械限位 +1.5m），无 yaw 转动；#154-02 表明进入 +0.45rad pitch 后定位锁存失效，故当前候选已收敛为相同路径、相同阶段时长与回程、yaw/pitch 全程为零的 `n07_default_spawn_translation_only`。wrapper 与 runner 均可选择当前 profile。
- 路线 SDF 静态审计包含原场景和运行时生成的 wall/column 两个障碍；按 N05 全机参考半径 0.730618m、1cm 采样及 Lipschitz 半采样间距下界计算，最小静态余量 1.029473m。该项不涵盖地面、支架结构或飞行停止距离。

## 验证／运行状态

准备阶段已运行 `python3 tools/project_status.py`，结构检查通过；Python 文件以 `ast.parse` 静态解析通过。首次 `py_compile` 因仓库 `tools/__pycache__` 中既有权限限制失败，未改动该目录。固定镜像缺少 `pyulog`；已在 `/tmp/n07-pyulog-packages` 安装 PX4 官方 `pyulog==1.2.4` 作为离线 ULog 评估器，未改镜像或仓库依赖。使用现有历史 ULog 核对了所需数据集字段：`estimator_status_flags`、`vehicle_land_detected`、`vehicle_status` 和 ULog 初始参数均可读取。

`n07-20261023-154-01` 是第一轮冷启动准入诊断，不计合格悬停。完整 VINS/EGO/PX4 stack 启动；新鲜 N05 live/offline 结果一致拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。raw ground plane 有效，z=−0.35m；HOLD 在 1m 高度有 565 个 unknown cell，subground 排除数为 0；bridge `DISABLED`、armed=false、landed=true、VINS Tracking。没有起飞。后续 coverage profile 在进入快速 yaw 段后于约 0.09rad 锁存 `accel_bias_norm_exceeded`；仅完成 3/12 阶段。安全清理确认支架 detached 且 Gazebo 模型已移除；PX4 样本均 DISARMED，随后容器停止。结果保存在 `artifacts/runs/n07-20261023-154-01/`，没有任何飞行证据。

`n07-20261023-154-02` 使用原始默认 −8m 起点与同一固定镜像，初始 fresh gate 仍拒绝 TAKEOFF_CONTACT。支架沿 +X 平移至 +1.2m、保持 yaw=0，VINS 在该段保持 valid；开始 pitch 到 +0.45rad 后，仅到约 +0.07rad 的最后有效 trace，随后在 `normalized_cost_exceeded` 锁存（最终 normalized_cost=1.435091），3/12 阶段完成。没有生成 scan-ready marker，未运行扫描中／释放后的 gate，也没有起飞。runner 回位、确认支架 detach／模型删除；保存的只读状态为 bridge `DISABLED`、armed=false、landed=true、PX4 arming_state=1（DISARMED）、vehicle_land_detected=true，Gazebo pose x=−8.000680m、z=−0.013001m、roll/pitch/yaw 约 0；容器 exit 0。日志与安全状态留在 `artifacts/runs/n07-20261023-154-02/`。

`n07-20261023-154-03` 的纯平移 +1.2m profile 完成 12/12 阶段，scan trace 的位移与回程期间保持 VINS valid、yaw/pitch≈0、同一 epoch/map_id。扫描后附着状态和释放后的两次 fresh N05 online/offline 都拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`；HOLD unknown 从 565 降至 449，subground exclusion 为0。释放后 VINS 仍 Tracking 且身份不变；fixture runner 在 detach 观察时记录一次 status-change 错误（最后 localization 有效），支架已实际 detached/删除。无起飞，当前容器仍只作为诊断会话。逐格复算见 [unknown-volume audit](../evidence/n07-hold-unknown-volume-20261023-154.json)：449 个 HOLD unknown 中心 z=0.55–1.25m，raw ground plane z=−0.35m，0个中心在地面以下；356个在 x<0 的相机后侧。

该空间分布支持后侧可视覆盖缺口。新增候选 `n07_default_spawn_bidirectional_translation_only`：从默认起点向后平移−0.8m，再向前至+1.2m，原路回到0；始终 yaw/pitch=0。含动态 wall/column 布局的静态 SDF 连续余量下界为0.389407m，详见 [bidirectional route audit](../evidence/n07-bidirectional-scan-route-geometry-20261023-154.json)。profile回归 21 passed；该次profile变更晚于#154-03启动，因此当前会话后续 gate 仍属诊断，不能算入 N07 三连。

当前合格悬停仍为 0/3。`n07_default_spawn_translation_only` profile 阶段 `python3 tools/test_preflight_scan.py` 为20 passed，加入 bidirectional 候选后为21 passed；JSON、wrapper shell syntax、`git diff --check` 通过，`python3 tools/project_status.py` 为结构检查 PASS（80 个历史可选 artifact links 缺失，且该检查不验证 ROS build/SITL）。原 `config/runtime.json` 字节未改，SHA-256 仍为 `a862e521dd738dba71d960cda95458509336f1e2cd845228b46311fd57928221`。

`n07-20261023-154-01` 关键 SHA-256：N05 live gate `45f2242fea6feaf8eefa1b35bed6b6710bff1c2ebfe7f4a47ed541c33015c113`，fixture result `9a81c9c063794ec24576ed05ace7e5155ca273b40db1bd9b3ca6a7835425bca8`，fixture trace `8072cd2321bca0e9ab379e6a51a5666804e328fb1843c229d619032bd68d3c8c`。`n07-20261023-154-02`：初始 gate `622a032993a21e410c43fd9c9a588033d4af04c755f45006afd3573222f5e10b`，fixture result `834d1677e9772f519b2d9cac99cbc3cd2c14468285dcdd117b1eaf9307d9ed51`，fixture trace `dc3e88512c530848bf106f11bcb5e90c7fb9e6ea28a1d54afdb6495e0a4e3da5`，安全状态 `3b883260fec52463507d0aa6cc2ac2add4a1392173b6b19fd8f661ef68a19f5b`。`n07-20261023-154-03`：初始 gate `5ee33a33e85e26e7e33fa9aa89a7cc205a8da81fc33bff25654e06c6e1648344`，附着 gate `787ebddb3a343d5ab7f22548055f6f7300de64caafea0b618a0b1af001102a79`，释放 gate `5c559ad9e0e432be454ef287a917183d137f969796792ac93dd7d7e009de095a`，fixture result `b04fd38cfff4c0b28b36bbeffe930e3a9373c21a813b11f6882fe441ae4b4090`，trace `94ccbe544576a2ce1f83ea3836063dd4e181489e008c576b8673624b05bdfb59`。unknown-volume audit `progress/evidence/n07-hold-unknown-volume-20261023-154.json` SHA-256 `ad4e4b53d7da6d8e16ca994e1e0764b43aea7573fe19ba27af7992cbe40f2988`；bidirectional route audit `progress/evidence/n07-bidirectional-scan-route-geometry-20261023-154.json` SHA-256 `78a3bcd8a4cadd09fd645b4f3022f70c1a0563201636af9a56f5ad22703aac18`。

## 未解项与下一步

采集与评估工具已就绪，但默认起点尚未取得 fresh N05 正向准入。当前继续在 #154-03 的 DISARMED 诊断会话中执行 bidirectional 纯平移 profile，验证后侧观测假设并检查释放后的 fresh gate；配置变更后该会话不计 N07 冷启动资格。只有 gate 五阶段全部接受，才停止该会话并用同一固定新配置开始三次独立冷启动与无目标悬停；拒绝时保留拒绝并继续依据剩余未知分布选择最小观测动作。
