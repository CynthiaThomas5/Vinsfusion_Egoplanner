# P2 EGO clock/domain 对照诊断

日期：2026-10-17

- 用户目标：继续完成 GOAL.md 的 P0–P6 与 A–H 验收，不降低范围。
- 用户约束：保护已有 staged／unstaged 工作；旧 EGO/vendor 源码只读；只推进单 D435i 仿真链路；不发布 PX4 控制、不解锁或实机飞行。
- 观察：限频 EGO `/clock` 的 #45/#46 中，pose take 常见延迟低于1 ms，但仍出现长尾，最大0.530/2.062 s。未限频 #47 在 domain187 的60秒窗口中无超过0.1 s 的 pose take；未限频 #48/#49 在 domain186 分别有30/498、32/536个窗口样本超过0.1 s，最大1.541/1.958 s。#49 使用新 Gazebo partition 后仍复现。UDPv4-only #50 配对数降至241、pose P95/最大1.925/2.820 s，mapper 最大 pose 发布间隔1.044 s，不能隔离共享内存影响。六个 trace 中 mapper pose/depth source timestamp 最终均与 EGO take 完全对应，trace 未报告丢事件。
- 运行图：#49 只观察到预期 application node；`/clock` 只有 `d435i_bridge` 发布，pose 只有 `mapping_input_adapter` 发布和 EGO 订阅。容器中存在 Fast DDS `fastrtps_port*` 共享内存对象及多个 ROS CLI daemon；没有清理，因果关系未测试。
- 排除尝试：#51 将 `ROS_HOME` 指向运行目录，但 ROS CLI 报 domain186 daemon already running；定位适配器锁定 `imu_stale`，mapping probe exit 1 且没有配对样本。未纳入测量。该操作停止了原 domain186 CLI daemon，随后已恢复为运行状态。
- 决定：clock 限频不是修复；数据支持 domain186 相关性，但不能证明 ROS domain ID 是根因。没有修改生产配置、自维护代码或 vendor 源码。P2、timeout 和地图边界阈值继续保留现有状态；EGO 多线程仍需先保护共享 GridMap 状态。
- 下一步：在新隔离 middleware 状态下重复 domain/partition 对照，观察 Fast DDS reader notification/availability 与 EGO executor ready-entity 选择；不启动 PX4 控制。
- 轻量证据：[p2-ego-clock-domain-diagnostic.json](../../progress/evidence/p2-ego-clock-domain-diagnostic.json)；#45–#51 原始 trace、运行日志与 SHA-256 manifest 位于各自 `artifacts/runs/` 目录，#51 在证据中标为排除尝试。#50 使用的 Fast DDS 2.14.6 环境变量定义见[官方文档](https://fast-dds.docs.eprosima.com/en/v2.14.6/fastdds/env_vars/env_vars.html)。
- 对应改动记录：[progress/changes/2026-10-17-015-p2-ego-clock-domain-diagnostic.md](../../progress/changes/2026-10-17-015-p2-ego-clock-domain-diagnostic.md)。
