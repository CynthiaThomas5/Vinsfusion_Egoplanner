# GOAL B/C 定位 telemetry 接收与 EGO 输入诊断 #260

关联对话：[2026-10-20-034](../../collaboration/dialogues/2026-10-20-034-ego-gridmap-receipt-trace.md)。

沿用#259全栈和健康／地图门，增加behavior-neutral EGO GridMap回调诊断。当前vendor树哈希与较早#225 overlay不同，因此从当前树按EGO patch 0012→0013→0015构建run-local overlay，5/5包通过；项目源码、配置和canonical健康阈值未修改。

独立左右图／IMU观察未见源龄越限。raw VINS观察器继续收到初始化后的telemetry，其仿真戳间隔在定位锁定附近约66 ms，并持续到48.511秒。定位适配器在观察elapsed 13.842秒以`telemetry_stale`锁定；mapping gate关闭并reset地图，短目标探针40秒没有发送goal。EGO保持WAIT_TARGET，没有同步深度／位姿输入或占据更新，所以本轮不能分析#259出现的EGO超时簇。

独立VINS订阅不能证明定位适配器收到了相同消息。当前结果只把下一步缩小到adapter telemetry订阅／回调、DDS投递或执行调度观测，不定根因。先对run-local定位适配器增加低频回调计数、header source stamp、接收间隔和健康锁定快照；健康和地图稳定后再重复EGO输入边界诊断。

证据报告：[p2-ego-gridmap-receipt-trace-20261020-260.json](../evidence/p2-ego-gridmap-receipt-trace-20261020-260.json)。原始运行目录：`artifacts/runs/p2-ego-gridmap-receipt-trace-20261020-260`。overlay构建日志、patch manifest、安装二进制及样本均以运行清单哈希记录。

验证：run-local overlay colcon构建5/5通过；容器退出0；`gz sdf -k`报告Valid（保留已有`gz_frame_id` schema warnings）；4个shell脚本通过`bash -n`、5个Python脚本通过编译检查；运行后`docker ps`为空。仿真因健康门锁定被安全排除，不执行goal、轨迹或PX4。
