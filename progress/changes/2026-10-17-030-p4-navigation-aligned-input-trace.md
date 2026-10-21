# P4 导航回调与独立输入时间线对齐

对话摘要：[2026-10-17-030](../../collaboration/dialogues/2026-10-17-030-p4-navigation-aligned-input-trace.md)

继续调查 P4 正常时钟活动目标关闭和导航回调空档。未改生产源码、配置、时钟、freshness guard 或 EGO timeout；未启动控制器或 PX4。#63–#66 的独立 run manifest 与输出 SHA-256 保存在各自 `artifacts/runs/p4-navigation-live-ego-20261017-{63,64,65,66}/run-inputs.json`。

#63 在外部 freshness 检查全通过、B-spline/READY 匹配后完成活动 SIGINT/ABORT；但独立 timeline 晚于先前导航回调空档才启动，无法对齐。该次 36 条 EGO `odom or depth lost!` 都发生在轨迹 ABORT 后。#64 使用 ROS domain 233 时 Fast DDS 因映射端口过高拒绝创建传感器图，未进入导航测试。#65 让运动先于 VINS 静态初始化，定位持续 `LOCKED/propagated_stale`，无有效 odometry、非空地图、目标或 SIGINT；作为启动顺序混杂运行排除。#66 先完成5秒静态初始化，再启动独立 observer、导航、运动；正常 canonical `/clock` 下再次完成匹配 B-spline/READY 与活动目标 SIGINT ABORT，后续 READY 为0，导航和 probe 退出码均为0。

#66 观察到导航记录优化里程计回调间隙419 ms；同一 wall-clock 窗口内，独立 observer 收到3条优化里程计、9条有效 TRACKING 状态、2组 pose/depth，边界最大 receipt gap 分别为115.868、50.936、231.708 ms。这使下一诊断集中到导航节点的订阅 take／executor／callback 路径，但还不能区分 RMW reader 交付与 executor 调度。EGO 有10条 solver error，均在成功规划前；没有 `odom or depth lost!`。导航停机仍出现两条异步 Destroyable 异常，因此进程退出码0不算 clean teardown。

验证：`python3 tools/project_status.py` 返回结构检查 PASS（仅表示骨架一致）；JSON 解析和 #59–#66 manifest 的输入／输出 SHA-256 共检查397个文件，P4 evidence path/hash 参考检查350项，全部通过；#59–#66 wrapper 的 `bash -n` 与 run-private probe 的 Python `compile()` 全通过；`git diff --check`、`git diff --cached --check` 和10个本轮记录／清单的尾随空白检查通过。容器 `docker top` 未发现导航、EGO、traj_server、Gazebo、运动驱动或 probe 进程；跨运行的 sleep 与 ros2cli daemon 仍在，未清理或改变它们。#64/#65 保留为排除运行；四次有效正常时钟关闭路径观察（#61/#62/#63/#66）不代表 P4 通过。

下一步在相同 canonical `/clock` 与启用 observer 的条件下，记录导航 executor readiness、订阅 take、callback entry/exit 并与独立 receipt timeline 对齐，重复观察至少一次长间隙。保持现有时钟、freshness guard、EGO timeout 和单控制发布者边界不变；输入与回调稳定后再做轨迹跟踪／到达验收。
