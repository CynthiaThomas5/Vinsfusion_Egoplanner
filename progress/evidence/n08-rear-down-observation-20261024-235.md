# N08.2y #235：定位健康失败，未到达后向下视姿态

## 结果

**本轮未检验后向下视覆盖假设。** 新 profile `n08_overhead_rear_down_view` 共 22 stages；冷启动 N05 before gate 仍拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。支架扫描在前 4 个 stage 完成后、仍处 yaw≈0 的初始远移/俯仰路径时因 localization helper 报错中止，未到达后向 yaw=−π 或 pitch=+0.45 阶段。after/post-release gate 没有运行，compute-only 未启动。

最后一条 scan trace 在 sim 194.132 s 仍显示 LocalizationStatus valid、normalized cost 0.5765；helper 末态报告 `normalized_cost_exceeded`、cost 1.401698。转换发生的具体时刻未被记录。独立 stream 文件中 raw VINS telemetry/source odometry 继续到约 241.3/241.7 s，而 adapter optimized odometry 最后记录约 193.9 s；可能是失效锁存后的结果，现有数据不能判定先后因果。

## PX4 与环境读回

实时 bridge 状态为 `DISABLED`、`localization_not_tracking`、`control_enabled=false`、`armed=false`、`landed=true`，没有目标或控制命令。PX4 log 另有重复 vehicle-IMU sample timestamp 报错；本次没有进入飞行，也未测量其与 #206 HRT 修复的关系，因此不归因于 PX4 时间参考。

同次 bridge detail 读回 `alignment_pair_gap_sim_s=100.392`、最近有效配对的 wall age 为 `111.949 s`。源码定义该 gap 为 PX4 local-position 与 adapter optimized-odometry **源戳**之间的差；它不是 PX4 HRT 与 ROS `/clock` 的直接差。该值可能使 alignment bridge fail-closed，但当前保存的读回没有保留独立 `px4_ros_clock_gap_sim_s` 数值，也没有记录它相对 localization 健康失效的先后。因此不能将它归因于 #206，也不能断言其为本次健康中止的触发原因；#237 专门增加同步事件时间线来判别。

fixture trace 停滞时，项目容器 CPU 约 582%，Gazebo 进程约 321%，VINS 进程约 92%；宿主机有 64 个逻辑 CPU，运行后 load average 约 8.86/9.95/11.50，另有两个非项目模拟器进程各占用多核。这些同时读数不能证明宿主机整体饱和或因果；未停止任何非项目进程。

## 安全收尾与判定

fixture helper 的清理确认 detached、Gazebo model absent、最终 land detector landed。bridge DISABLED／未解锁；`bash tools/project.sh stop n08-20261024-235-rear-down-observation-01` exit 0，container `Exited (0)`，无匹配项目进程。fixture runner exit 1，outer N05 wrapper exit 12（没有达到 prescan-ready）。

静态验收先通过：`python3 -m unittest tools.test_preflight_scan`（30 项）、preflight JSON parse、`bash -n tools/run_n05_preflight_layout.sh`、`python3 tools/project_status.py` 和 `git diff --check`。未得到 post-release N05 admission、曲线、XY 或任何制动量测。

**状态：N08 继续 `in_progress`。** #235 的下视假设待实际到达视角后再判断；本次是定位健康失败，不是对地图覆盖效果的否定。下一步应在共享 CPU 负载/时间推进稳定后，使用同一 profile 并额外捕获 `LocalizationStatus`、`/clock` 与 optimized-odometry 状态转换；保持现有健康和准入门限，N05 fresh gate 不通过仍不得发 goal。

原始输入、trace 与 hashes 见 [`n08-rear-down-observation-20261024-235.json`](n08-rear-down-observation-20261024-235.json) 和 `artifacts/runs/n08-20261024-235-rear-down-observation-01/`。
