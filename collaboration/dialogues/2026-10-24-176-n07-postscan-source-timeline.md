# N07 #176：attached 后观测 release 时序

## 用户约束

- 用户已授权Goal完成模式，范围N07，持续至N07出口通过。
- 健康门和N05/N07验收条件不变；release gate未fresh接受不得飞。
- N06 ground-boundary已经关闭，不重新展开。

## 证据与决定

#175不启用额外probe时完成12/12和attached N05 online/offline一致接受，但release后缺optimized odom，localization锁存`telemetry_stale`。当前回读raw VINS stamp已达约620.3/620.9，而adapter仍锁在435.304；原生fixture记录有一个约2.772s observer gap，但无法确认adapter是否看到相同断档。

#176采用同profile新冷启动，不在支架运动时运行额外observer。attached N05 fresh通过后、release动作前才启动read-only stream probe，以区分首个断点在raw source还是adapted odometry。probe不发布控制，不改变门限。release gate通过后停止probe，再由正式no-goal hover工具复核fresh前置；否则安全停止且不飞。

## 当前状态

#176 已运行并安全结束。用户指出地下不是飞行空间；确认 N05 只用 raw occupied 地面拟合边界，并在地面确认、PX4 landed/disarmed 的接地阶段排除地面以下体素，不会把地下作为 free flight volume。#176 所有 attached、post-release 和 current-area N05 online/offline gate 均 fresh 同意，五阶段入口 sweep 的地下排除数量有记录。

尽管门禁通过，no-goal hover 脚本启动时定位适配器已经锁在 propagated_stale。raw VINS telemetry/odometry 仍连续，而该 61 秒窗口没有 adapted optimized odometry；脚本在 enable/arm 前退出。当前 0/3，父目标仍 in_progress，N07 不算完成。

下一项 #177 固定所有运行条件，不在支架运动时探测；释放后延长只读 probe，覆盖 current-area gate 到 hover 前置，定位首次 raw/adapted 断点。门限不变，N05 或 localization gate 不 fresh 时不飞。
