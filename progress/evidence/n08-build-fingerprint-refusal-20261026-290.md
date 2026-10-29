# N08 #290：旧 build fingerprint 在发目标前拒绝当前 0047 源码

## 结论

**N05及任务前门通过；motion-cancel runner 在任何goal或PX4控制前被来源指纹拒绝。** 本次没有EGO任务、起飞、取消或制动数据，不能作为N08试飞结果。

## 前置门

Run：`n08-cancel-translation-prescan-20261026-290`。独立冷启动VINS epoch=`d213cae204af4346964b2861406854ae`。N05支架扫描6/6阶段完成；fixture removal已确认且模型缺席；同一epoch/map的post-release online/offline admission接受，摘要`diagnostic_pass=true`。扫描期间的泛化定位状态警告被保留；本run的6阶段、同身份快照和post-release准入均有正证据。

40.0010s只读preflight通过，最大optimized odometry receipt gap=0.4152s，小于0.5s门。一次样本计入内部guard统计但没有触发拒绝。mission current-area N05 online/offline再检查也接受。

## 指纹拒绝与修正

任务runner在使用#276构建证据时拒绝`dependencies/sources.json`：历史#276记录的SHA=`8f097a21…`（EGO patch 0046），而当前0047源码锁SHA=`e825ddef…`。这是严格的编译源码保护在拒绝旧build身份；任务没有越过该门。

已在[新的#289 build证据](n08-cancel-stop-build-20261026-289.json)保存当前0047源码、依赖补丁链、installed `ego_planner_node`哈希、17包构建和348项测试身份，并将runner的build证据路径改到该记录。runner脚本本身和Python helper仍由每次cold-start `runtime-contract.json`认证。该修正没有改变速度、地图、健康、tracking或安全门。更新后的完整回归通过。

## 安全收尾

`flight.json`是runner未生成terminal record后写入的fail-closed占位，`flight.log`记录`trial_source_fingerprint_mismatch:dependencies/sources.json`。没有navigation goal或enable服务调用。独立4s PX4/bridge读回：phase `DISABLED`、control disabled、PX4 disarmed、landed=true、`vehicle_remained_disarmed=true`；OffboardControlMode、TrajectorySetpoint、VehicleCommand消息均为0。`bash tools/project.sh stop n08-cancel-translation-prescan-20261026-290`退出0。

## 下一步

用新冷启动#291重做同一N05流程和只读preflight，确认runner加载#289 build记录且源／二进制与新runtime manifest一致；只有所有门通过，才运行`single_goal motion_cancel 0.04 0.06`。
