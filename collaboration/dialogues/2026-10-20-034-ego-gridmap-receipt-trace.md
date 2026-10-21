# GOAL B/C 定位 telemetry 接收与 EGO 输入诊断 #260

## 任务摘要

在保持#259全栈和0.5 m运行期膨胀设置的条件下，用行为中性的EGO GridMap诊断overlay复测深度／位姿同步间隙。健康与地图前置门保持不变；只有TRACKING和地图稳定时才发短目标。没有控制器、PX4或真值。

## 已确认

- 当前vendor源码树哈希`c5caa40f…`与#225构建overlay时的树不同，因此没有复用旧二进制；在当前树上按0012→0013→0015补丁顺序run-local构建，5/5个EGO包通过。补丁不改变map、timeout或控制行为。
- 独立图像／IMU观察器未看到配置源龄限值越界。raw VINS只读探针记录686条优化、9,080条传播和695条telemetry，输出有限且无解析错误。
- 定位进入TRACKING后，在观察器elapsed 13.842秒转为`telemetry_stale`；mapping gate关闭并reset地图，目标探针40秒未发目标。
- 独立raw VINS telemetry样本在仿真戳13.842秒之后仍以约66 ms间隔持续，直到48.511秒；这些数据来自第二个DDS订阅者，不能证明定位适配器收到。
- EGO仍为WAIT_TARGET，锁定后没有有效depth-pose同步和占据更新，故这一轮没有覆盖#259的EGO超时簇。

## 决定与限制

- 记录为健康门前置诊断，不视作规划或地图验收。
- 观测将下一步指向定位适配器telemetry订阅／回调或其DDS／执行调度路径；具体原因未确认。
- 保持健康护栏、配置、控制所有权不变。先记录adapter回调计数、源戳、接收间隔及锁定时各流年龄；只有TRACKING和MapStatus恢复稳定后再做EGO边界复测。

详细数据和哈希见[证据报告](../../progress/evidence/p2-ego-gridmap-receipt-trace-20261020-260.json)；运行产物位于`artifacts/runs/p2-ego-gridmap-receipt-trace-20261020-260`。
