# N10.3/#395 零飞行采集烟测

## 结果

最终烟测 `n10-20261027-395-capture-smoke-final` 的离线 payload/receipt 一致性评估为 `PASS`。这仅证明左右目图像和相机 IMU 的记录及 source-stamp/frame 收据可对应，不是任务、校准或验收结果，也不计 N15/N16 次数。

MCAP 共解码 9,995 条消息，JSONL 有 10,034 条收据。三条流中每条 bag payload 均有匹配收据，内部未匹配数为零；收据侧多出的 4/4/31 条都位于 bag 时间窗边界，符合观察器与 bag 开闭时刻不同步的记录窗口。bag 通过 `SIGTERM` 以退出码 0 闭合，capture report 无写入错误。

本次没有 NavigationCommand 或起飞。独立读回持续 6 秒：PX4 未武装且 landed，bridge 为 `DISABLED`、`control_enabled=false`，控制样本为零；容器正常退出。该零飞行读回不构成飞行终态或故障降落证据。

## 改动与验证

- 传感器观察器保留 ROS 订阅句柄并使用单线程 executor；订阅队列有界为 KEEP_LAST 100、best-effort/volatile。
- 收尾先正常关闭 rosbag，再停止订阅观察器，避免 bag 尾部 payload 无收据；SIGTERM 正常关闭，SIGINT 暂停造成的旧尝试仍保留为诊断失败。
- 资源报告显式列出传感器 observer 队列容量与内存预算；VINS 内部队列未暴露，保持 unknown。容量计算不连接起飞/任务门。
- 修正点云查询报告的 goal identity：可从 query spec 绑定任务目标，在 flight record 尚未落盘时也检查声明与活动身份冲突。归档 #391 injector 未改写，下一次运行须用新 run-local injector 并带齐 runtime/goal/epoch/map/frame。
- 定向回归：`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tools.test_n10_acceptance tools.test_n10_clearance tools.test_n10_sensor_capture tools.test_observer_window tools.test_n10_map_query_contract`，48 项通过。
- 语法/结构检查：相关脚本 `py_compile`、`bash -n` 通过；`python3 tools/project_status.py` 通过（仅结构/设计检查）；`git diff --check` 通过。

## 归档

运行目录：`artifacts/runs/n10-20261027-395-capture-smoke-final/`。逐文件 SHA-256 和运行身份见同名 JSON 证据。两次先前失败尝试及其原因没有删除。

## 未覆盖与下一步

该烟测没有验证任务期 identity、occupancy query request/echo、physics-step 净空、地图变化与重规划、飞行负载队列/资源、PX4 原生故障退出和最终 landed/disarmed 链路。随后已在新 run-local 目录准备 #396 injector/driver：query spec 等待 active goal 和 runtime hash，并显式绑定 run/runtime/goal/epoch/map/frame；新协议只把诊断保持缩至 15 仿真秒，避免重走 #391 的约49.7秒故障暴露窗口。新 stack 启动后还要在任何导航目标提交前生成实际 runtime/prelaunch freeze。紧急 disarm 的一次性授权已在 #391 用完；新运行必须依靠预先检查的正常 PX4 终止路径，不能假设可再次紧急 disarm。
